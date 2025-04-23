import os
import logging
import requests
import json
from flask import Flask, render_template, request, jsonify, session
from markupsafe import Markup

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Add nl2br filter to Jinja2 environment
@app.template_filter('nl2br')
def nl2br_filter(text):
    if text:
        return Markup(text.replace('\n', '<br>'))

# Constants
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-1.5-pro-latest"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Role-based prompt template
SYSTEM_PROMPT = """
You are a role-based AI Assistant specializing in Computer Science.

Your role: {role}  
(Examples: Student, Teacher, AI Researcher, Developer)

Your task is to ONLY answer questions strictly related to Computer Science.  
If the user's question is outside the Computer Science domain (like cooking, sports, movies, etc.), politely refuse to answer.

Current user's message: "{user_input}"

Respond clearly and concisely, and adjust your tone based on the role.
"""

@app.route('/')
def index():
    # Initialize or clear session data for a new conversation
    if 'chat_history' not in session:
        session['chat_history'] = []
    if 'role' not in session:
        session['role'] = "Student"  # Default role
    
    return render_template('index.html', 
                           chat_history=session['chat_history'], 
                           current_role=session['role'])

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        role = data.get('role', 'Student')
        
        # Update role in session
        session['role'] = role
        
        # Add user message to chat history
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        session['chat_history'].append({
            'role': 'user',
            'content': user_message
        })
        
        # Create the system prompt with the role and user message
        formatted_prompt = SYSTEM_PROMPT.format(role=role, user_input=user_message)
        
        # Prepare the request to Gemini API
        url = f"{GEMINI_API_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": formatted_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Send request to Gemini API
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            response_data = response.json()
            ai_response = response_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            
            # Add AI response to chat history
            session['chat_history'].append({
                'role': 'assistant',
                'content': ai_response
            })
            
            # Save session
            session.modified = True
            
            return jsonify({
                'response': ai_response,
                'success': True
            })
        else:
            logging.error(f"API Error: {response.status_code} - {response.text}")
            return jsonify({
                'response': f"Error communicating with the AI service. Status code: {response.status_code}",
                'success': False
            })
    
    except Exception as e:
        logging.exception("An error occurred while processing the chat request")
        return jsonify({
            'response': f"An error occurred: {str(e)}",
            'success': False
        })

@app.route('/clear', methods=['POST'])
def clear_chat():
    # Clear the chat history in the session
    session['chat_history'] = []
    session.modified = True
    
    return jsonify({
        'success': True,
        'message': 'Chat history cleared'
    })

@app.route('/set_role', methods=['POST'])
def set_role():
    data = request.json
    role = data.get('role', 'Student')
    
    # Update role in session
    session['role'] = role
    session.modified = True
    
    return jsonify({
        'success': True,
        'message': f'Role updated to {role}'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
