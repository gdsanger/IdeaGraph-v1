/**
 * ChatWidget - Main component for IdeaGraph Q&A Chat
 * 
 * Provides a modular chat interface for asking questions about items
 * and receiving AI-generated answers with source references.
 */

class ChatWidget {
    /**
     * Initialize ChatWidget
     * @param {Object} options - Configuration options
     * @param {string} options.containerId - ID of the container element
     * @param {string} options.itemId - UUID of the item
     * @param {string} options.apiBaseUrl - Base URL for API calls (default: /api/items)
     * @param {string} options.theme - UI theme: 'dark' or 'light' (default: dark)
     * @param {string} options.height - Container height (default: 500px)
     * @param {boolean} options.showHistory - Show question history (default: true)
     */
    constructor(options) {
        this.containerId = options.containerId;
        this.itemId = options.itemId;
        this.apiBaseUrl = options.apiBaseUrl || '/api/items';
        this.theme = options.theme || 'dark';
        this.height = options.height || '500px';
        this.showHistory = options.showHistory !== false;
        
        // Validate required parameters
        if (!this.itemId || this.itemId.trim() === '') {
            console.error('ChatWidget: itemId is required');
            throw new Error('ChatWidget requires itemId parameter');
        }
        
        // State
        this.messages = [];
        this.isLoading = false;
        this.currentQuestion = '';
        
        // Get CSRF token from cookie or meta tag
        this.csrfToken = this.getCSRFToken();
        
        // Initialize components
        this.messageRenderer = new ChatMessage();
        this.sourcesRenderer = new ChatSources();
        
        // Initialize UI
        this.init();
    }
    
    /**
     * Get CSRF token for API requests
     */
    getCSRFToken() {
        // Try to get from cookie first
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        // Fallback to meta tag
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        return '';
    }
    
    /**
     * Initialize the chat widget UI
     */
    init() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error(`ChatWidget: Container with id "${this.containerId}" not found`);
            return;
        }
        
        container.innerHTML = this.renderTemplate();
        this.attachEventListeners();
        
        // Load history if enabled
        if (this.showHistory) {
            this.loadHistory();
        }
    }
    
    /**
     * Render the main template
     */
    renderTemplate() {
        return `
            <div class="chat-widget-container" data-theme="${this.theme}" style="height: ${this.height}">
                <div class="chat-widget-header">
                    <div class="chat-widget-title">
                        <i class="bi bi-chat-dots"></i>
                        <span>IdeaGraph Q&A Assistant</span>
                    </div>
                    <div class="chat-widget-actions">
                        <button 
                            id="chat-delete-button" 
                            class="chat-action-button"
                            title="Chat-Verlauf löschen"
                        >
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                    <div class="chat-widget-status" id="chat-status">
                        <span class="status-indicator"></span>
                        <span class="status-text">Bereit</span>
                    </div>
                </div>
                
                <div class="chat-widget-messages" id="chat-messages">
                    <div class="chat-welcome-message">
                        <i class="bi bi-robot"></i>
                        <h4>Willkommen beim IdeaGraph Q&A Assistant!</h4>
                        <p>Stelle mir Fragen zu diesem Item und ich werde dir mit relevanten Informationen aus dem Projektkontext antworten.</p>
                    </div>
                </div>
                
                <div class="chat-widget-input-container" id="chat-input-container">
                    <div class="chat-widget-input">
                        <textarea 
                            id="chat-input-field" 
                            class="chat-input-field" 
                            placeholder="Stelle eine Frage zu diesem Item..."
                            rows="2"
                            maxlength="512"
                        ></textarea>
                        <button 
                            id="chat-send-button" 
                            class="chat-send-button"
                            title="Frage senden"
                        >
                            <i class="bi bi-send"></i>
                        </button>
                    </div>
                    <div class="chat-input-footer">
                        <span class="chat-input-counter" id="char-counter">0 / 512</span>
                        <span class="chat-input-hint">Enter zum Senden, Shift+Enter für neue Zeile</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Attach event listeners
     */
    attachEventListeners() {
        const inputField = document.getElementById('chat-input-field');
        const sendButton = document.getElementById('chat-send-button');
        const deleteButton = document.getElementById('chat-delete-button');
        
        if (!inputField || !sendButton) {
            console.error('ChatWidget: Input elements not found');
            return;
        }
        
        // Send button click
        sendButton.addEventListener('click', () => this.handleSendMessage());
        
        // Delete button click
        if (deleteButton) {
            deleteButton.addEventListener('click', () => this.handleDeleteChat());
        }
        
        // Enter key to send (Shift+Enter for new line)
        inputField.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });
        
        // Character counter
        inputField.addEventListener('input', (e) => {
            const counter = document.getElementById('char-counter');
            if (counter) {
                counter.textContent = `${e.target.value.length} / 512`;
            }
            this.currentQuestion = e.target.value;
        });
    }
    
    /**
     * Handle sending a message
     */
    async handleSendMessage() {
        const inputField = document.getElementById('chat-input-field');
        const question = inputField.value.trim();
        
        if (!question || this.isLoading) {
            return;
        }
        
        // Add user message to UI
        this.addMessage({
            type: 'user',
            content: question,
            timestamp: new Date()
        });
        
        // Clear input
        inputField.value = '';
        this.currentQuestion = '';
        document.getElementById('char-counter').textContent = '0 / 512';
        
        // Set loading state
        this.setLoading(true);
        
        try {
            // Prepare conversation history (last 5 messages, excluding the current question)
            const conversationHistory = this.messages.slice(-10); // Take last 10 to get 5 Q&A pairs max
            
            // Call API with conversation history
            const response = await this.askQuestion(question, conversationHistory);
            
            if (response.success) {
                // Add bot response
                this.addMessage({
                    type: 'bot',
                    content: response.answer,
                    sources: response.sources,
                    timestamp: new Date(),
                    qaId: response.qa_id,
                    relevanceScore: response.relevance_score
                });
            } else {
                this.addMessage({
                    type: 'error',
                    content: response.error || 'Ein Fehler ist aufgetreten. Bitte versuche es erneut.',
                    timestamp: new Date()
                });
            }
        } catch (error) {
            console.error('Error asking question:', error);
            this.addMessage({
                type: 'error',
                content: 'Verbindungsfehler. Bitte überprüfe deine Internetverbindung und versuche es erneut.',
                timestamp: new Date()
            });
        } finally {
            this.setLoading(false);
        }
    }
    
    /**
     * Add a message to the chat
     */
    addMessage(message) {
        this.messages.push(message);
        
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
        
        // Remove welcome message if it exists
        const welcomeMessage = messagesContainer.querySelector('.chat-welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        // Render and append new message
        const messageElement = this.messageRenderer.render(message);
        messagesContainer.appendChild(messageElement);
        
        // Scroll to bottom
        this.scrollToBottom();
    }
    
    /**
     * Scroll chat to bottom
     */
    scrollToBottom() {
        const messagesContainer = document.getElementById('chat-messages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    /**
     * Set loading state
     */
    setLoading(loading) {
        this.isLoading = loading;
        
        const sendButton = document.getElementById('chat-send-button');
        const inputField = document.getElementById('chat-input-field');
        const statusText = document.querySelector('.status-text');
        const statusIndicator = document.querySelector('.status-indicator');
        
        if (loading) {
            sendButton.disabled = true;
            inputField.disabled = true;
            sendButton.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';
            if (statusText) statusText.textContent = 'Denkt nach...';
            if (statusIndicator) statusIndicator.classList.add('loading');
        } else {
            sendButton.disabled = false;
            inputField.disabled = false;
            sendButton.innerHTML = '<i class="bi bi-send"></i>';
            if (statusText) statusText.textContent = 'Bereit';
            if (statusIndicator) statusIndicator.classList.remove('loading');
        }
    }
    
    /**
     * Call the API to ask a question
     */
    async askQuestion(question, conversationHistory = []) {
        const url = `${this.apiBaseUrl}/${this.itemId}/ask`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            credentials: 'include',
            body: JSON.stringify({ 
                question,
                conversation_history: conversationHistory
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    /**
     * Load question history
     */
    async loadHistory() {
        try {
            const url = `${this.apiBaseUrl}/${this.itemId}/questions/history`;
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken
                },
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.questions && data.questions.length > 0) {
                    // Add historical messages (most recent first, so reverse for chronological order)
                    const questions = [...data.questions].reverse();
                    questions.forEach(qa => {
                        this.addMessage({
                            type: 'user',
                            content: qa.question,
                            timestamp: new Date(qa.created_at)
                        });
                        this.addMessage({
                            type: 'bot',
                            content: qa.answer,
                            sources: qa.sources,
                            timestamp: new Date(qa.created_at),
                            qaId: qa.id,
                            relevanceScore: qa.relevance_score
                        });
                    });
                }
            }
        } catch (error) {
            console.warn('Could not load history:', error);
            // Silently fail - history is optional
        }
    }
    
    /**
     * Handle delete chat action
     */
    async handleDeleteChat() {
        // Confirm before deleting
        if (!confirm('Möchtest du wirklich den gesamten Chat-Verlauf löschen? Diese Aktion kann nicht rückgängig gemacht werden.')) {
            return;
        }
        
        try {
            const url = `${this.apiBaseUrl}/${this.itemId}/questions/history`;
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.csrfToken
                },
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Clear local messages
                    this.messages = [];
                    
                    // Clear UI and show welcome message
                    const messagesContainer = document.getElementById('chat-messages');
                    if (messagesContainer) {
                        messagesContainer.innerHTML = `
                            <div class="chat-welcome-message">
                                <i class="bi bi-robot"></i>
                                <h4>Willkommen beim IdeaGraph Q&A Assistant!</h4>
                                <p>Stelle mir Fragen zu diesem Item und ich werde dir mit relevanten Informationen aus dem Projektkontext antworten.</p>
                            </div>
                        `;
                    }
                    
                    // Show success notification
                    this.showNotification('Chat-Verlauf wurde erfolgreich gelöscht', 'success');
                }
            } else {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
        } catch (error) {
            console.error('Error deleting chat history:', error);
            this.showNotification('Fehler beim Löschen des Chat-Verlaufs', 'error');
        }
    }
    
    /**
     * Show a temporary notification
     */
    showNotification(message, type = 'info') {
        const statusText = document.querySelector('.status-text');
        if (statusText) {
            const originalText = statusText.textContent;
            statusText.textContent = message;
            statusText.style.color = type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#6b7280';
            
            setTimeout(() => {
                statusText.textContent = originalText;
                statusText.style.color = '';
            }, 3000);
        }
    }
}

// Make ChatWidget globally available
window.ChatWidget = ChatWidget;
