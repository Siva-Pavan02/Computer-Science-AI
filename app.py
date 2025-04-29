from dotenv import load_dotenv
load_dotenv()

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
MAX_MEMORY_PROMPTS = 10  # Maximum number of previous prompts to remember

# Computer Science prompt template
SYSTEM_PROMPT = """
You are an AI Assistant specializing in Computer Science.

Your task is to ONLY answer questions strictly related to Computer Science.  
If the user's question is outside the Computer Science domain (like cooking, sports, movies, etc.), politely refuse to answer.

Previous user messages (for context):
{conversation_memory}

Current user's message: "{user_input}"

Respond clearly and concisely. Focus on providing accurate, educational information about computer science topics.
Include examples when helpful. Format code snippets properly for easy reading. Use professional language but be friendly and approachable.
"""

def get_welcome_message():
    """Returns the welcome message for new users"""
    # Don't use format_response here, we want a simple text welcome message
    return """<i class="fas fa-info-circle me-2"></i> Only Computer Science related questions will be answered."""

def format_response(text):
    """
    Format the AI response for better display:
    - Properly format code blocks with syntax highlighting
    - Format lists, headings, etc.
    """
    import re
    
    # Format code blocks (```code```)
    pattern = r'```(?:\w+)?\n([\s\S]*?)\n```'
    replacement = r'<pre class="code-block"><code>\1</code></pre>'
    text = re.sub(pattern, replacement, text)
    
    # Format inline code (`code`)
    pattern = r'`([^`\n]+?)`'
    replacement = r'<code class="inline-code">\1</code>'
    text = re.sub(pattern, replacement, text)
    
    # Format headers (# Header)
    pattern = r'^(#{1,6})\s+(.+)$'
    
    def header_replacer(match):
        level = len(match.group(1))
        header_text = match.group(2)
        return f'<h{level} class="response-heading">{header_text}</h{level}>'
    
    text = re.sub(pattern, header_replacer, text, flags=re.MULTILINE)
    
    # Format unordered lists
    pattern = r'^(\s*)-\s+(.+)$'
    replacement = r'<ul><li>\2</li></ul>'
    text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    
    # Format ordered lists
    pattern = r'^(\s*)\d+\.\s+(.+)$'
    replacement = r'<ol><li>\2</li></ol>'
    text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    
    # Fix consecutive list items (remove redundant opening/closing tags)
    text = re.sub(r'</ul>\s*<ul>', '', text)
    text = re.sub(r'</ol>\s*<ol>', '', text)
    
    # Format strong/bold (**text**)
    pattern = r'\*\*([^*]+?)\*\*'
    replacement = r'<strong>\1</strong>'
    text = re.sub(pattern, replacement, text)
    
    # Format emphasis/italic (*text*)
    pattern = r'\*([^*]+?)\*'
    replacement = r'<em>\1</em>'
    text = re.sub(pattern, replacement, text)
    
    return text

def format_conversation_memory(prompts_memory):
    """Format the previous user prompts as context for the AI"""
    if not prompts_memory:
        return "None"
    
    formatted_memory = ""
    for i, prompt in enumerate(prompts_memory):
        formatted_memory += f"[{i+1}] {prompt}\n"
    
    return formatted_memory

@app.route('/')
def index():
    # Initialize or clear session data for a new conversation
    if 'chat_history' not in session:
        session['chat_history'] = []
        session['prompts_memory'] = []  # Initialize memory for previous prompts
        
        # Only add welcome message if this is a brand new session
        if len(session['chat_history']) == 0:
            welcome_message = get_welcome_message()
            session['chat_history'].append({
                'role': 'assistant',
                'content': welcome_message
            })
            session.modified = True
    
    return render_template('index.html', 
                           chat_history=session['chat_history'])

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        # Initialize session variables if they don't exist
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        if 'prompts_memory' not in session:
            session['prompts_memory'] = []
        
        # Add user message to chat history
        session['chat_history'].append({
            'role': 'user',
            'content': user_message
        })
        
        # Add user message to prompts memory (limiting to MAX_MEMORY_PROMPTS)
        prompts_memory = session.get('prompts_memory', [])
        prompts_memory.append(user_message)
        if len(prompts_memory) > MAX_MEMORY_PROMPTS:
            prompts_memory = prompts_memory[-MAX_MEMORY_PROMPTS:]  # Keep only the most recent ones
        session['prompts_memory'] = prompts_memory
        
        # Format the conversation memory for context
        conversation_memory = format_conversation_memory(prompts_memory[:-1])  # Exclude current message
        
        # Create the system prompt with the user message and conversation memory
        formatted_prompt = SYSTEM_PROMPT.format(
            user_input=user_message,
            conversation_memory=conversation_memory
        )
        
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
                "temperature": 0.2,  # Lower temperature for more focused responses
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
            
            # Format the AI response for better display
            formatted_response = format_response(ai_response)
            
            # Add AI response to chat history
            session['chat_history'].append({
                'role': 'assistant',
                'content': formatted_response
            })
            
            # Save session
            session.modified = True
            
            return jsonify({
                'response': formatted_response,
                'success': True
            })
        else:
            logging.error(f"API Error: {response.status_code} - {response.text}")
            
            # Handle rate limiting more gracefully
            if response.status_code == 429:
                error_data = response.json() if response.content else {}
                retry_after = 15  # Default retry time in seconds
                
                # Try to extract the retry delay if available
                if error_data and 'error' in error_data:
                    for detail in error_data['error'].get('details', []):
                        if '@type' in detail and 'RetryInfo' in detail['@type']:
                            retry_delay = detail.get('retryDelay', '15s')
                            # Extract the number from strings like "15s"
                            retry_after = int(''.join(filter(str.isdigit, retry_delay))) or 15
                
                return jsonify({
                    'response': f"Rate limit reached. The Gemini API free tier allows only 2 requests per minute. Please wait {retry_after} seconds before trying again.",
                    'success': False,
                    'retry_after': retry_after
                })
            
            return jsonify({
                'response': f"Error communicating with the AI service. Please try again later.",
                'success': False
            })
    
    except Exception as e:
        logging.exception("An error occurred while processing the chat request")
        return jsonify({
            'response': f"An error occurred. Please try again.",
            'success': False
        })

@app.route('/clear', methods=['POST'])
def clear_chat():
    # Clear the chat history and prompts memory in the session
    session['chat_history'] = []
    session['prompts_memory'] = []  # Also clear the prompts memory
    
    # Add welcome message after clearing
    welcome_message = get_welcome_message()
    session['chat_history'].append({
        'role': 'assistant',
        'content': welcome_message
    })
    
    session.modified = True
    
    return jsonify({
        'success': True,
        'message': 'Chat history cleared',
        'welcome_message': welcome_message
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)