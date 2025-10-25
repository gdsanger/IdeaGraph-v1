/**
 * Graph Node Tooltip
 * 
 * Module for displaying hover information for graph nodes.
 * Provides rich information about nodes when hovering.
 */

class GraphNodeTooltip {
    constructor() {
        this.tooltip = null;
        this.init();
    }
    
    init() {
        // Create tooltip element if it doesn't exist
        if (!document.getElementById('snTooltip')) {
            this.tooltip = document.createElement('div');
            this.tooltip.id = 'snTooltip';
            this.tooltip.className = 'semantic-network-tooltip';
            document.body.appendChild(this.tooltip);
        } else {
            this.tooltip = document.getElementById('snTooltip');
        }
    }
    
    /**
     * Show tooltip for a node
     * 
     * @param {Object} event - Mouse event with x, y coordinates
     * @param {Object} nodeData - Node data object
     */
    show(event, nodeData) {
        if (!this.tooltip) {
            this.init();
        }
        
        const props = nodeData.properties || {};
        const title = props.title || 'Untitled';
        const type = nodeData.type || 'unknown';
        const similarity = nodeData.similarity ? `${(nodeData.similarity * 100).toFixed(1)}%` : 'Source';
        
        let hierarchyInfo = '';
        if (nodeData.isParent) {
            hierarchyInfo = '<div class="tooltip-meta"><strong>Rolle: Parent Item</strong></div>';
        } else if (nodeData.isChild) {
            hierarchyInfo = '<div class="tooltip-meta"><strong>Rolle: Child Item</strong></div>';
            if (nodeData.inheritsContext) {
                hierarchyInfo += '<div class="tooltip-meta">Erbt Kontext vom Parent</div>';
            }
        }
        
        // Check if this node has parent info in properties
        if (props.parent_id && props.context_inherited) {
            hierarchyInfo += '<div class="tooltip-meta">Kontext geerbt von Parent</div>';
        }
        
        this.tooltip.innerHTML = `
            <div class="tooltip-title">${this.escapeHtml(title)}</div>
            <div class="tooltip-meta">Type: ${type}</div>
            <div class="tooltip-meta">Similarity: ${similarity}</div>
            ${hierarchyInfo}
        `;
        
        this.tooltip.style.display = 'block';
        this.tooltip.style.left = event.event.x + 10 + 'px';
        this.tooltip.style.top = event.event.y + 10 + 'px';
    }
    
    /**
     * Hide tooltip
     */
    hide() {
        if (this.tooltip) {
            this.tooltip.style.display = 'none';
        }
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Destroy tooltip element
     */
    destroy() {
        if (this.tooltip && this.tooltip.parentNode) {
            this.tooltip.parentNode.removeChild(this.tooltip);
            this.tooltip = null;
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GraphNodeTooltip;
}
