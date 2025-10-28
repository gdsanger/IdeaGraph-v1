/**
 * Weaviate Indicator JavaScript Module
 * 
 * Provides functionality for checking Weaviate status and interacting with indicators.
 */

// Wrap in IIFE to prevent redeclaration errors
(function(window) {
    'use strict';
    
    // Check if already defined to prevent redeclaration
    if (window.WeaviateIndicator) {
        return;
    }

class WeaviateIndicator {
    constructor(objectType, objectId, containerElement) {
        this.objectType = objectType;
        this.objectId = objectId;
        this.containerElement = containerElement;
        this.isChecking = false;
    }

    /**
     * Initialize the indicator and check status
     */
    async init() {
        if (this.isChecking) return;
        
        this.isChecking = true;
        this.showLoadingIndicator();
        
        try {
            const exists = await this.checkStatus();
            this.renderIndicator(exists);
        } catch (error) {
            console.error('Error initializing Weaviate indicator:', error);
            this.renderErrorIndicator();
        } finally {
            this.isChecking = false;
        }
    }

    /**
     * Check if object exists in Weaviate
     */
    async checkStatus() {
        const response = await fetch(`/api/weaviate/${this.objectType}/${this.objectId}/status`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to check Weaviate status');
        }

        const data = await response.json();
        return data.exists || false;
    }

    /**
     * Add object to Weaviate
     */
    async addToWeaviate() {
        const response = await fetch(`/api/weaviate/${this.objectType}/${this.objectId}/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            }
        });

        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to add to Weaviate');
        }

        return data;
    }

    /**
     * Get Weaviate dump for object
     */
    async getWeaviateDump() {
        const response = await fetch(`/api/weaviate/${this.objectType}/${this.objectId}/dump`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to get Weaviate dump');
        }

        return data.dump;
    }

    /**
     * Show loading indicator
     */
    showLoadingIndicator() {
        this.containerElement.innerHTML = `
            <div class="weaviate-indicator loading" title="Checking Weaviate status...">
                <div class="spinner-border spinner-border-sm text-secondary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }

    /**
     * Render the indicator based on existence status
     */
    renderIndicator(exists) {
        const indicatorClass = exists ? 'weaviate-indicator-exists' : 'weaviate-indicator-missing';
        const indicatorColor = exists ? 'success' : 'danger';
        const indicatorIcon = exists ? 'check-circle-fill' : 'x-circle-fill';
        const indicatorTitle = exists ? 'In Weaviate - Click to view dump' : 'Not in Weaviate - Click to add';
        
        this.containerElement.innerHTML = `
            <button class="btn btn-sm btn-outline-${indicatorColor} weaviate-indicator ${indicatorClass}" 
                    title="${indicatorTitle}"
                    data-exists="${exists}">
                <i class="bi bi-${indicatorIcon}"></i>
            </button>
        `;

        // Add click handler
        const btn = this.containerElement.querySelector('.weaviate-indicator');
        btn.addEventListener('click', (e) => this.handleClick(e, exists));
    }

    /**
     * Render error indicator
     */
    renderErrorIndicator() {
        this.containerElement.innerHTML = `
            <button class="btn btn-sm btn-outline-secondary weaviate-indicator" 
                    title="Error checking Weaviate status"
                    disabled>
                <i class="bi bi-exclamation-triangle"></i>
            </button>
        `;
    }

    /**
     * Handle click on indicator
     */
    async handleClick(event, exists) {
        event.preventDefault();
        event.stopPropagation();

        const btn = event.currentTarget;
        btn.disabled = true;

        if (exists) {
            // Show dump in modal
            await this.showDumpModal();
        } else {
            // Add to Weaviate
            await this.handleAddToWeaviate(btn);
        }

        btn.disabled = false;
    }

    /**
     * Handle adding object to Weaviate
     */
    async handleAddToWeaviate(btn) {
        try {
            const result = await this.addToWeaviate();
            
            // Show success toast
            this.showToast(result.message || 'Added to Weaviate successfully', 'success');
            
            // Update indicator to show it exists now
            this.renderIndicator(true);
        } catch (error) {
            console.error('Error adding to Weaviate:', error);
            this.showToast(error.message || 'Failed to add to Weaviate', 'danger');
        }
    }

    /**
     * Show dump modal
     */
    async showDumpModal() {
        try {
            const dump = await this.getWeaviateDump();
            
            // Create modal if it doesn't exist
            let modal = document.getElementById('weaviateDumpModal');
            if (!modal) {
                modal = this.createDumpModal();
                document.body.appendChild(modal);
            }

            // Update modal content
            const modalBody = modal.querySelector('.modal-body');
            modalBody.innerHTML = `<pre class="bg-dark text-light p-3 rounded" style="max-height: 500px; overflow-y: auto;"><code>${this.escapeHtml(JSON.stringify(dump, null, 2))}</code></pre>`;

            // Show modal
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        } catch (error) {
            console.error('Error showing dump:', error);
            this.showToast(error.message || 'Failed to load Weaviate dump', 'danger');
        }
    }

    /**
     * Create dump modal
     */
    createDumpModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'weaviateDumpModal';
        modal.tabIndex = -1;
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content bg-dark text-light">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-database"></i> Weaviate Object Dump
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <!-- Content will be inserted here -->
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        // Try to use existing showAlert function if available
        if (typeof showAlert === 'function') {
            showAlert(message, type);
            return;
        }

        // Fallback: create a simple alert
        const alertContainer = document.querySelector('.container-fluid') || document.body;
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        alertContainer.appendChild(alert);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }

    /**
     * Get CSRF token
     */
    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

/**
 * Initialize Weaviate indicator for an element
 */
function initWeaviateIndicator(objectType, objectId, containerElement) {
    const indicator = new WeaviateIndicator(objectType, objectId, containerElement);
    indicator.init();
    return indicator;
}

/**
 * Initialize all Weaviate indicators on the page
 */
function initAllWeaviateIndicators() {
    const indicators = document.querySelectorAll('[data-weaviate-indicator]');
    indicators.forEach(element => {
        const objectType = element.dataset.weaviateType;
        const objectId = element.dataset.weaviateId;
        if (objectType && objectId) {
            initWeaviateIndicator(objectType, objectId, element);
        }
    });
}

// Auto-initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', initAllWeaviateIndicators);

// Export to window for global access
window.WeaviateIndicator = WeaviateIndicator;
window.initWeaviateIndicator = initWeaviateIndicator;
window.initAllWeaviateIndicators = initAllWeaviateIndicators;

// Export for use in other scripts (CommonJS/Node.js)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { WeaviateIndicator, initWeaviateIndicator, initAllWeaviateIndicators };
}

})(window);
