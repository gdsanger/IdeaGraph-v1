/**
 * Semantic Network Visualization
 * 
 * This module provides interactive semantic network visualization using Sigma.js.
 * It displays semantically similar objects in a graph with multiple levels of similarity.
 */

class SemanticNetworkViewer {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        
        if (!this.container) {
            console.error(`Container ${containerId} not found`);
            return;
        }
        
        // Configuration
        this.options = {
            objectType: options.objectType || 'item',
            objectId: options.objectId || null,
            depth: options.depth || 3,
            generateSummaries: options.generateSummaries !== false,
            onNodeClick: options.onNodeClick || null,
            ...options
        };
        
        // State
        this.graph = null;
        this.sigma = null;
        this.networkData = null;
        this.isLoading = false;
        
        // Initialize
        this.init();
    }
    
    init() {
        // Create container structure
        this.container.innerHTML = `
            <div class="semantic-network-wrapper">
                <div class="semantic-network-header">
                    <h5 class="mb-3">
                        <i class="bi bi-diagram-3"></i> Semantisches Netzwerk
                    </h5>
                    <div class="semantic-network-controls mb-3">
                        <button class="btn btn-sm btn-outline-primary" id="snResetView">
                            <i class="bi bi-zoom-out"></i> Reset View
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" id="snToggleLabels">
                            <i class="bi bi-tag"></i> Labels
                        </button>
                    </div>
                </div>
                <div class="semantic-network-summary" id="snSummary"></div>
                <div class="semantic-network-graph" id="snGraph"></div>
                <div class="semantic-network-loading" id="snLoading" style="display: none;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-3">Generiere semantisches Netzwerk...</p>
                </div>
                <div class="semantic-network-legend">
                    <div class="legend-item">
                        <span class="legend-dot" style="background: #f59e0b;"></span>
                        <span>Ebene 1 (>80%)</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: #3b82f6;"></span>
                        <span>Ebene 2 (>70%)</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: #8b5cf6;"></span>
                        <span>Ebene 3 (>60%)</span>
                    </div>
                </div>
            </div>
        `;
        
        // Bind event handlers
        this.bindEvents();
    }
    
    bindEvents() {
        const resetBtn = document.getElementById('snResetView');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetView());
        }
        
        const toggleLabelsBtn = document.getElementById('snToggleLabels');
        if (toggleLabelsBtn) {
            toggleLabelsBtn.addEventListener('click', () => this.toggleLabels());
        }
    }
    
    async load(objectType, objectId) {
        if (this.isLoading) return;
        
        this.options.objectType = objectType;
        this.options.objectId = objectId;
        
        this.showLoading();
        this.isLoading = true;
        
        try {
            // Build API URL
            const url = new URL(`/api/semantic-network/${objectType}/${objectId}`, window.location.origin);
            url.searchParams.set('depth', this.options.depth);
            url.searchParams.set('summaries', this.options.generateSummaries);
            
            // Fetch network data
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load semantic network');
            }
            
            this.networkData = data;
            this.renderNetwork();
            this.renderSummaries();
            
        } catch (error) {
            console.error('Error loading semantic network:', error);
            this.showError(error.message);
        } finally {
            this.hideLoading();
            this.isLoading = false;
        }
    }
    
    renderNetwork() {
        if (!this.networkData || !this.networkData.nodes) {
            return;
        }
        
        const graphContainer = document.getElementById('snGraph');
        if (!graphContainer) return;
        
        // Clear existing graph
        if (this.sigma) {
            this.sigma.kill();
            this.sigma = null;
        }
        
        graphContainer.innerHTML = '';
        
        // Prepare graph data for Sigma.js
        const nodes = this.networkData.nodes.map(node => {
            const color = this.getNodeColor(node);
            const size = this.getNodeSize(node);
            const label = this.getNodeLabel(node);
            
            return {
                key: node.id,
                attributes: {
                    x: Math.random(),
                    y: Math.random(),
                    size: size,
                    label: label,
                    color: color,
                    originalData: node
                }
            };
        });
        
        const edges = this.networkData.edges.map((edge, idx) => ({
            key: `edge-${idx}`,
            source: edge.source,
            target: edge.target,
            attributes: {
                size: edge.weight * 2,
                color: '#4b5563',
                originalData: edge
            }
        }));
        
        // Create graph using graphology
        this.graph = new graphology.Graph();
        
        // Add nodes and edges
        nodes.forEach(node => {
            try {
                this.graph.addNode(node.key, node.attributes);
            } catch (e) {
                console.warn('Failed to add node:', node.key);
            }
        });
        
        edges.forEach(edge => {
            try {
                this.graph.addEdge(edge.source, edge.target, edge.attributes);
            } catch (e) {
                console.warn('Failed to add edge:', edge.source, '->', edge.target);
            }
        });
        
        // Apply force layout
        this.applyLayout();
        
        // Create Sigma instance
        this.sigma = new Sigma(this.graph, graphContainer, {
            renderEdgeLabels: false,
            defaultNodeColor: '#3b82f6',
            defaultEdgeColor: '#4b5563',
            labelSize: 12,
            labelColor: { color: '#ffffff' },
            labelWeight: 'normal',
            enableEdgeClickEvents: false,
            enableEdgeWheelEvents: false,
            enableEdgeHoverEvents: false
        });
        
        // Bind Sigma events
        this.bindSigmaEvents();
    }
    
    applyLayout() {
        // Use circular layout with ForceAtlas2 refinement
        const settings = forceAtlas2.inferSettings(this.graph);
        forceAtlas2.assign(this.graph, {
            iterations: 100,
            settings: {
                ...settings,
                gravity: 1,
                scalingRatio: 10,
                slowDown: 5
            }
        });
    }
    
    bindSigmaEvents() {
        if (!this.sigma) return;
        
        // Node click handler
        this.sigma.on('clickNode', (event) => {
            const nodeId = event.node;
            const nodeData = this.graph.getNodeAttributes(nodeId).originalData;
            
            if (this.options.onNodeClick) {
                this.options.onNodeClick(nodeData);
            } else {
                // Default behavior: navigate to object detail page
                this.navigateToObject(nodeData);
            }
        });
        
        // Hover handlers for tooltips
        this.sigma.on('enterNode', (event) => {
            const nodeId = event.node;
            const nodeData = this.graph.getNodeAttributes(nodeId).originalData;
            this.showTooltip(event, nodeData);
        });
        
        this.sigma.on('leaveNode', () => {
            this.hideTooltip();
        });
    }
    
    getNodeColor(node) {
        // Color by level
        if (node.isSource) {
            return '#22c55e'; // Green for source
        }
        
        const levelColors = {
            1: '#f59e0b', // Amber for level 1
            2: '#3b82f6', // Blue for level 2
            3: '#8b5cf6'  // Violet for level 3
        };
        
        return levelColors[node.level] || '#6b7280'; // Gray fallback
    }
    
    getNodeSize(node) {
        if (node.isSource) {
            return 20;
        }
        
        // Size based on similarity
        const similarity = node.similarity || 0.5;
        return 10 + similarity * 10;
    }
    
    getNodeLabel(node) {
        const props = node.properties || {};
        let label = props.title || 'Untitled';
        
        // Truncate long labels
        if (label.length > 30) {
            label = label.substring(0, 27) + '...';
        }
        
        return label;
    }
    
    renderSummaries() {
        const summaryContainer = document.getElementById('snSummary');
        if (!summaryContainer || !this.networkData || !this.networkData.levels) {
            return;
        }
        
        const levels = this.networkData.levels;
        let html = '';
        
        // Render summaries for each level
        Object.keys(levels).sort().forEach(levelKey => {
            const level = levels[levelKey];
            if (level.summary && level.node_count > 0) {
                html += `
                    <div class="alert alert-info mb-2">
                        <strong>Ebene ${level.level}</strong> (${level.node_count} Objekte, ≥${(level.threshold * 100).toFixed(0)}% Ähnlichkeit):
                        <p class="mb-0 mt-1">${this.escapeHtml(level.summary)}</p>
                    </div>
                `;
            }
        });
        
        if (html) {
            summaryContainer.innerHTML = html;
            summaryContainer.style.display = 'block';
        } else {
            summaryContainer.style.display = 'none';
        }
    }
    
    showTooltip(event, nodeData) {
        // Create tooltip if it doesn't exist
        let tooltip = document.getElementById('snTooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'snTooltip';
            tooltip.className = 'semantic-network-tooltip';
            document.body.appendChild(tooltip);
        }
        
        const props = nodeData.properties || {};
        const title = props.title || 'Untitled';
        const type = nodeData.type || 'unknown';
        const similarity = nodeData.similarity ? `${(nodeData.similarity * 100).toFixed(1)}%` : 'Source';
        
        tooltip.innerHTML = `
            <div class="tooltip-title">${this.escapeHtml(title)}</div>
            <div class="tooltip-meta">Type: ${type}</div>
            <div class="tooltip-meta">Similarity: ${similarity}</div>
        `;
        
        tooltip.style.display = 'block';
        tooltip.style.left = event.event.x + 10 + 'px';
        tooltip.style.top = event.event.y + 10 + 'px';
    }
    
    hideTooltip() {
        const tooltip = document.getElementById('snTooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    }
    
    navigateToObject(nodeData) {
        const type = nodeData.type;
        const id = nodeData.id;
        
        // Build URL based on object type
        let url = '';
        switch (type) {
            case 'item':
                url = `/items/${id}/`;
                break;
            case 'task':
                url = `/tasks/${id}/`;
                break;
            case 'github_issue':
                // GitHub issues might have a URL in properties
                const props = nodeData.properties || {};
                url = props.url || props.html_url || '';
                if (url) {
                    window.open(url, '_blank');
                    return;
                }
                break;
            default:
                console.warn('Unknown object type:', type);
                return;
        }
        
        if (url) {
            window.location.href = url;
        }
    }
    
    resetView() {
        if (this.sigma) {
            const camera = this.sigma.getCamera();
            camera.animate({ x: 0.5, y: 0.5, ratio: 1 }, { duration: 300 });
        }
    }
    
    toggleLabels() {
        if (this.sigma) {
            const settings = this.sigma.getSettings();
            settings.renderLabels = !settings.renderLabels;
            this.sigma.refresh();
        }
    }
    
    showLoading() {
        const loading = document.getElementById('snLoading');
        const graph = document.getElementById('snGraph');
        if (loading) loading.style.display = 'flex';
        if (graph) graph.style.display = 'none';
    }
    
    hideLoading() {
        const loading = document.getElementById('snLoading');
        const graph = document.getElementById('snGraph');
        if (loading) loading.style.display = 'none';
        if (graph) graph.style.display = 'block';
    }
    
    showError(message) {
        const graphContainer = document.getElementById('snGraph');
        if (graphContainer) {
            graphContainer.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem;"></i>
                    <p class="mt-3">${this.escapeHtml(message)}</p>
                </div>
            `;
            graphContainer.style.display = 'block';
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    destroy() {
        if (this.sigma) {
            this.sigma.kill();
            this.sigma = null;
        }
        
        this.graph = null;
        this.networkData = null;
        
        const tooltip = document.getElementById('snTooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SemanticNetworkViewer;
}
