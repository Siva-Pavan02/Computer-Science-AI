document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');
    const clearButton = document.getElementById('clear-btn');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Function to add a new message to the chat
    function addMessage(content, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user-message' : 'assistant-message'}`;
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'message-header';
        headerDiv.innerHTML = `<strong>${isUser ? 'You' : 'Assistant'}</strong>`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        // Handle newlines by converting them to <br> elements
        contentDiv.innerHTML = content.replace(/\n/g, '<br>');
        
        messageDiv.appendChild(headerDiv);
        messageDiv.appendChild(contentDiv);
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        scrollToBottom();
    }
    
    // Function to scroll chat to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Handle form submission
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, true);
        
        // Clear input
        userInput.value = '';
        userInput.style.height = 'auto';
        
        // Show typing indicator
        typingIndicator.style.display = 'flex';
        
        try {
            // Send message to server
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    role: 'default'  // Fixed role since we removed role selection
                })
            });
            
            const data = await response.json();
            
            // Hide typing indicator
            typingIndicator.style.display = 'none';
            
            if (data.success) {
                // Add assistant response to chat
                addMessage(data.response);
            } else {
                // Add error message
                const errorDiv = document.createElement('div');
                errorDiv.className = 'chat-message system-message';
                errorDiv.innerHTML = `<div class="message-content text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>${data.response}
                </div>`;
                chatMessages.appendChild(errorDiv);
            }
        } catch (error) {
            console.error('Error:', error);
            
            // Hide typing indicator
            typingIndicator.style.display = 'none';
            
            // Add error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'chat-message system-message';
            errorDiv.innerHTML = `<div class="message-content text-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>An error occurred while communicating with the server.
            </div>`;
            chatMessages.appendChild(errorDiv);
        }
        
        // Scroll to bottom
        scrollToBottom();
    });
    
    // Clear chat history
    clearButton.addEventListener('click', async function() {
        // Confirm before clearing
        if (!confirm('Are you sure you want to clear the chat history?')) {
            return;
        }
        
        try {
            const response = await fetch('/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Clear the chat messages (except for system welcome)
                while (chatMessages.children.length > 1) {
                    chatMessages.removeChild(chatMessages.lastChild);
                }
                
                // Add a message about clearing the chat
                const clearDiv = document.createElement('div');
                clearDiv.className = 'chat-message system-message';
                clearDiv.innerHTML = `<div class="message-content">
                    <i class="fas fa-check me-2"></i>Chat history has been cleared.
                </div>`;
                chatMessages.appendChild(clearDiv);
                
                // Scroll to bottom
                scrollToBottom();
            }
        } catch (error) {
            console.error('Error clearing chat:', error);
        }
    });
    
    // Enable textarea autosize
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    });
    
    // Enable Ctrl+Enter to submit
    userInput.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            sendButton.click();
        }
    });
    
    // Initial scroll to bottom
    scrollToBottom();
});
