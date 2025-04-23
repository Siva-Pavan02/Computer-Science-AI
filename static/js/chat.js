document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');
    const clearButton = document.getElementById('clear-btn');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Function to add a new message to the chat
    function addMessage(content, isUser = false, isFormatted = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user-message' : 'assistant-message'}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // If content is already formatted (has HTML), use it directly
        // Otherwise handle newlines by converting them to <br> elements
        if (isFormatted) {
            contentDiv.innerHTML = content;
        } else {
            contentDiv.innerHTML = content.replace(/\n/g, '<br>');
        }
        
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
                // Add assistant response to chat (the backend already formatted it)
                addMessage(data.response, false, true);
            } else {
                // Add error message
                const errorDiv = document.createElement('div');
                errorDiv.className = 'chat-message error-message';
                
                // Check if there's a retry_after value for rate limiting
                if (data.retry_after) {
                    const retrySeconds = data.retry_after;
                    errorDiv.innerHTML = `<div class="message-content">
                        <i class="fas fa-exclamation-triangle me-2"></i>${data.response}
                        <div class="retry-timer mt-2" data-seconds="${retrySeconds}">
                            Please wait <span class="countdown">${retrySeconds}</span> seconds before trying again.
                        </div>
                    </div>`;
                    
                    // Start countdown timer
                    const countdownEl = errorDiv.querySelector('.countdown');
                    let secondsLeft = retrySeconds;
                    const countdownTimer = setInterval(() => {
                        secondsLeft--;
                        if (secondsLeft <= 0) {
                            clearInterval(countdownTimer);
                            errorDiv.querySelector('.retry-timer').textContent = "You can try again now.";
                        } else {
                            countdownEl.textContent = secondsLeft;
                        }
                    }, 1000);
                } else {
                    errorDiv.innerHTML = `<div class="message-content">
                        <i class="fas fa-exclamation-triangle me-2"></i>${data.response}
                    </div>`;
                }
                
                chatMessages.appendChild(errorDiv);
            }
        } catch (error) {
            console.error('Error:', error);
            
            // Hide typing indicator
            typingIndicator.style.display = 'none';
            
            // Add error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'chat-message error-message';
            errorDiv.innerHTML = `<div class="message-content">
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
                // Clear all chat messages
                while (chatMessages.firstChild) {
                    chatMessages.removeChild(chatMessages.firstChild);
                }
                
                // Add a message about clearing the chat
                const clearDiv = document.createElement('div');
                clearDiv.className = 'chat-message status-message';
                clearDiv.innerHTML = `<div class="message-content">
                    <i class="fas fa-check me-2"></i>Chat history has been cleared.
                </div>`;
                chatMessages.appendChild(clearDiv);
                
                // Add welcome message after clearing
                if (data.welcome_message) {
                    // Create welcome info element
                    const welcomeDiv = document.createElement('div');
                    welcomeDiv.className = 'welcome-info mb-4';
                    welcomeDiv.innerHTML = `<div class="welcome-text">${data.welcome_message}</div>`;
                    chatMessages.appendChild(welcomeDiv);
                }
                
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
