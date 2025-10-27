/**
 * ChatMessage - Component for rendering individual chat messages
 */

class ChatMessage {
    /**
     * Render a message element
     * @param {Object} message - Message object
     * @param {string} message.type - Message type: 'user', 'bot', or 'error'
     * @param {string} message.content - Message content
     * @param {Array} message.sources - Optional sources (for bot messages)
     * @param {Date} message.timestamp - Message timestamp
     * @param {string} message.qaId - Optional Q&A ID
     * @param {number} message.relevanceScore - Optional relevance score
     * @returns {HTMLElement} - Message DOM element
     */
    render(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message chat-message-${message.type}`;
        
        if (message.type === 'user') {
            messageDiv.innerHTML = this.renderUserMessage(message);
        } else if (message.type === 'bot') {
            messageDiv.innerHTML = this.renderBotMessage(message);
        } else if (message.type === 'error') {
            messageDiv.innerHTML = this.renderErrorMessage(message);
        }
        
        return messageDiv;
    }
    
    /**
     * Render a user message
     */
    renderUserMessage(message) {
        return `
            <div class="message-bubble message-bubble-user">
                <div class="message-content">
                    ${this.escapeHtml(message.content)}
                </div>
                <div class="message-meta">
                    <span class="message-time">${this.formatTime(message.timestamp)}</span>
                </div>
            </div>
        `;
    }
    
    /**
     * Render a bot message with markdown support
     */
    renderBotMessage(message) {
        const renderedContent = this.renderMarkdown(message.content);
        const sourcesHtml = message.sources && message.sources.length > 0 
            ? new ChatSources().render(message.sources) 
            : '';
        
        return `
            <div class="message-avatar">
                <i class="bi bi-robot"></i>
            </div>
            <div class="message-bubble message-bubble-bot">
                <div class="message-content markdown-content">
                    ${renderedContent}
                </div>
                ${sourcesHtml}
                <div class="message-meta">
                    <span class="message-time">${this.formatTime(message.timestamp)}</span>
                    ${message.relevanceScore ? `<span class="relevance-score" title="Durchschnittliche Relevanz der Quellen">Relevanz: ${Math.round(message.relevanceScore * 100)}%</span>` : ''}
                </div>
            </div>
        `;
    }
    
    /**
     * Render an error message
     */
    renderErrorMessage(message) {
        return `
            <div class="message-bubble message-bubble-error">
                <div class="message-icon">
                    <i class="bi bi-exclamation-triangle"></i>
                </div>
                <div class="message-content">
                    ${this.escapeHtml(message.content)}
                </div>
                <div class="message-meta">
                    <span class="message-time">${this.formatTime(message.timestamp)}</span>
                </div>
            </div>
        `;
    }
    
    /**
     * Render markdown content
     * Uses marked.js if available, otherwise falls back to plain text
     */
    renderMarkdown(content) {
        if (typeof marked !== 'undefined') {
            // Configure marked for security
            marked.setOptions({
                breaks: true,
                gfm: true,
                headerIds: false,
                mangle: false,
                sanitize: false // We'll use DOMPurify if needed
            });
            
            try {
                return marked.parse(content);
            } catch (error) {
                console.error('Error parsing markdown:', error);
                return this.escapeHtml(content).replace(/\n/g, '<br>');
            }
        } else {
            // Fallback: simple text formatting
            return this.escapeHtml(content).replace(/\n/g, '<br>');
        }
    }
    
    /**
     * Format timestamp
     */
    formatTime(timestamp) {
        if (!timestamp) return '';
        
        const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        // Less than 1 minute
        if (diff < 60000) {
            return 'gerade eben';
        }
        
        // Less than 1 hour
        if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return `vor ${minutes} Min.`;
        }
        
        // Less than 24 hours
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `vor ${hours} Std.`;
        }
        
        // More than 24 hours - show date and time
        return date.toLocaleString('de-DE', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Make ChatMessage globally available
window.ChatMessage = ChatMessage;
