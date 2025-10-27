/**
 * ChatWidget Component
 * 
 * Modular chat widget for IdeaGraph Q&A and support.
 * Integrates with Weaviate semantic search and KIGate question-answering agent.
 * 
 * Usage:
 *   const chatWidget = new ChatWidget('containerElementId', {
 *       itemId: 'uuid-here',
 *       apiBaseUrl: '/api/items',
 *       theme: 'dark',
 *       height: '500px',
 *       showHistory: true
 *   });
 */

class ChatWidget {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        
        if (!this.container) {
            console.error(`[ChatWidget] Container ${containerId} not found`);
            return;
        }
        
        // Configuration
        this.options = {
            itemId: options.itemId || null,
            apiBaseUrl: options.apiBaseUrl || '/api/items',
            theme: options.theme || 'dark',
            height: options.height || '500px',
            showHistory: options.showHistory !== false,
            ...options
        };
        
        // State
        this.messages = [];
        this.isLoading = false;
        
        // Elements
        this.messagesContainer = null;
        this.inputField = null;
        this.sendButton = null;
        
        // Initialize
        this.init();
    }
    
    init() {
        if (!this.options.itemId) {
            console.error('[ChatWidget] itemId is required');
            return;
        }
        
        this.render();
        this.attachEventListeners();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="chat-widget ${this.options.theme}" style="height: ${this.options.height}">
                <div class="chat-header">
                    <i class="bi bi-chat-dots-fill"></i>
                    <span>IdeaGraph Q&A Assistant</span>
                </div>
                <div class="chat-messages" id="${this.containerId}-messages">
                    <div class="chat-welcome-message">
                        <i class="bi bi-robot"></i>
                        <p>Hi! I'm your IdeaGraph assistant. Ask me anything about this item, and I'll search through the knowledge base to help you.</p>
                    </div>
                </div>
                <div class="chat-input-container">
                    <div class="chat-input-wrapper">
                        <input 
                            type="text" 
                            class="chat-input" 
                            id="${this.containerId}-input" 
                            placeholder="Ask a question..."
                            autocomplete="off"
                        />
                        <button 
                            class="chat-send-btn" 
                            id="${this.containerId}-send"
                            title="Send message"
                        >
                            <i class="bi bi-send-fill"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Get references to elements
        this.messagesContainer = document.getElementById(`${this.containerId}-messages`);
        this.inputField = document.getElementById(`${this.containerId}-input`);
        this.sendButton = document.getElementById(`${this.containerId}-send`);
    }
    
    attachEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.handleSendMessage());
        
        // Enter key press
        this.inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.isLoading) {
                this.handleSendMessage();
            }
        });
    }
    
    async handleSendMessage() {
        const message = this.inputField.value.trim();
        
        if (!message || this.isLoading) {
            return;
        }
        
        // Clear input
        this.inputField.value = '';
        
        // Add user message to UI
        this.addMessage('user', message);
        
        // Set loading state
        this.setLoading(true);
        
        try {
            // Call API
            const response = await this.askQuestion(message);
            
            // Add assistant response
            this.addMessage('assistant', response.answer, response.sources);
            
        } catch (error) {
            console.error('[ChatWidget] Error asking question:', error);
            this.addMessage('error', 'Sorry, I encountered an error processing your question. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    async askQuestion(question) {
        const url = `${this.options.apiBaseUrl}/${this.options.itemId}/chat/ask`;
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({ question })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP error ${response.status}`);
        }
        
        return await response.json();
    }
    
    addMessage(type, content, sources = null) {
        const messageElement = this.createMessageElement(type, content, sources);
        
        // Remove welcome message if present
        const welcomeMessage = this.messagesContainer.querySelector('.chat-welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
        
        // Store in state
        this.messages.push({ type, content, sources, timestamp: new Date() });
    }
    
    createMessageElement(type, content, sources = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message chat-message-${type}`;
        
        if (type === 'user') {
            messageDiv.innerHTML = `
                <div class="chat-message-content">
                    <div class="chat-message-bubble">
                        ${this.escapeHtml(content)}
                    </div>
                    <div class="chat-message-icon">
                        <i class="bi bi-person-fill"></i>
                    </div>
                </div>
            `;
        } else if (type === 'assistant') {
            messageDiv.innerHTML = `
                <div class="chat-message-content">
                    <div class="chat-message-icon">
                        <i class="bi bi-robot"></i>
                    </div>
                    <div class="chat-message-bubble">
                        ${this.renderMarkdown(content)}
                        ${sources && sources.length > 0 ? this.renderSources(sources) : ''}
                    </div>
                </div>
            `;
        } else if (type === 'error') {
            messageDiv.innerHTML = `
                <div class="chat-message-content">
                    <div class="chat-message-icon">
                        <i class="bi bi-exclamation-triangle-fill"></i>
                    </div>
                    <div class="chat-message-bubble chat-message-error">
                        ${this.escapeHtml(content)}
                    </div>
                </div>
            `;
        }
        
        return messageDiv;
    }
    
    renderSources(sources) {
        if (!sources || sources.length === 0) {
            return '';
        }
        
        const sourcesHtml = sources.map(source => `
            <div class="chat-source-item">
                <i class="bi bi-file-earmark-text"></i>
                <div class="chat-source-content">
                    <div class="chat-source-title">${this.escapeHtml(source.title || 'Untitled')}</div>
                    <div class="chat-source-type">${this.escapeHtml(source.type || 'Unknown')}</div>
                    ${source.score ? `<div class="chat-source-score">Relevance: ${(source.score * 100).toFixed(1)}%</div>` : ''}
                </div>
            </div>
        `).join('');
        
        return `
            <div class="chat-sources">
                <div class="chat-sources-header">
                    <i class="bi bi-book"></i>
                    <span>Sources</span>
                </div>
                <div class="chat-sources-list">
                    ${sourcesHtml}
                </div>
            </div>
        `;
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        
        if (loading) {
            this.sendButton.disabled = true;
            this.inputField.disabled = true;
            this.addLoadingIndicator();
        } else {
            this.sendButton.disabled = false;
            this.inputField.disabled = false;
            this.removeLoadingIndicator();
            this.inputField.focus();
        }
    }
    
    addLoadingIndicator() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'chat-message chat-message-assistant chat-loading-indicator';
        loadingDiv.id = `${this.containerId}-loading`;
        loadingDiv.innerHTML = `
            <div class="chat-message-content">
                <div class="chat-message-icon">
                    <i class="bi bi-robot"></i>
                </div>
                <div class="chat-message-bubble">
                    <div class="chat-typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        this.messagesContainer.appendChild(loadingDiv);
        this.scrollToBottom();
    }
    
    removeLoadingIndicator() {
        const loadingIndicator = document.getElementById(`${this.containerId}-loading`);
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    renderMarkdown(text) {
        // Simple markdown rendering - can be enhanced with marked.js if available
        if (typeof marked !== 'undefined') {
            return marked.parse(text);
        }
        
        // Fallback: simple line breaks
        return this.escapeHtml(text).replace(/\n/g, '<br>');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getCsrfToken() {
        // Get CSRF token from cookie
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Public methods
    
    clearHistory() {
        this.messages = [];
        this.messagesContainer.innerHTML = `
            <div class="chat-welcome-message">
                <i class="bi bi-robot"></i>
                <p>Hi! I'm your IdeaGraph assistant. Ask me anything about this item.</p>
            </div>
        `;
    }
    
    destroy() {
        // Cleanup
        this.container.innerHTML = '';
    }
}
