/**
 * ChatSources - Component for displaying source references
 */

class ChatSources {
    /**
     * Render sources list
     * @param {Array} sources - Array of source objects
     * @returns {string} - HTML string for sources
     */
    render(sources) {
        if (!sources || sources.length === 0) {
            return '';
        }
        
        const sourceItems = sources.map((source, index) => 
            this.renderSource(source, index + 1)
        ).join('');
        
        return `
            <div class="message-sources">
                <div class="sources-header">
                    <i class="bi bi-book"></i>
                    <span>Quellen</span>
                </div>
                <div class="sources-list">
                    ${sourceItems}
                </div>
            </div>
        `;
    }
    
    /**
     * Render a single source
     */
    renderSource(source, index) {
        const relevanceClass = this.getRelevanceClass(source.relevance);
        const relevancePercent = Math.round((source.relevance || 0) * 100);
        const iconClass = this.getSourceIcon(source.type);
        
        return `
            <div class="source-item ${relevanceClass}">
                <div class="source-number">${index}</div>
                <div class="source-info">
                    <div class="source-header">
                        <i class="bi ${iconClass}"></i>
                        <span class="source-type">${this.escapeHtml(source.type)}</span>
                        <span class="source-relevance" title="Relevanz-Score">
                            ${relevancePercent}%
                        </span>
                    </div>
                    <div class="source-title">
                        ${source.url ? 
                            `<a href="${this.escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">
                                ${this.escapeHtml(source.title)}
                            </a>` :
                            this.escapeHtml(source.title)
                        }
                    </div>
                    ${source.description ? 
                        `<div class="source-description">${this.escapeHtml(this.truncateText(source.description, 150))}</div>` 
                        : ''
                    }
                </div>
            </div>
        `;
    }
    
    /**
     * Get relevance class based on score
     */
    getRelevanceClass(relevance) {
        if (!relevance) return 'relevance-low';
        
        if (relevance >= 0.9) return 'relevance-excellent';
        if (relevance >= 0.8) return 'relevance-high';
        if (relevance >= 0.7) return 'relevance-medium';
        return 'relevance-low';
    }
    
    /**
     * Get icon for source type
     */
    getSourceIcon(type) {
        const typeMap = {
            'task': 'bi-check-square',
            'file': 'bi-file-earmark-text',
            'document': 'bi-file-earmark-pdf',
            'spec': 'bi-file-earmark-code',
            'note': 'bi-sticky',
            'comment': 'bi-chat-left-text',
            'qa-response': 'bi-question-circle',
            'knowledge': 'bi-lightbulb'
        };
        
        const normalizedType = (type || '').toLowerCase();
        return typeMap[normalizedType] || 'bi-file-earmark';
    }
    
    /**
     * Truncate text to specified length
     */
    truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength) + '...';
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Make ChatSources globally available
window.ChatSources = ChatSources;
