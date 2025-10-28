/**
 * Semantic Graph Component
 * 
 * Main reusable component for visualizing semantic networks.
 * This component can be initialized with just a KnowledgeObject ID
 * and will handle all data fetching, rendering, and interactions.
 * 
 * Usage:
 *   const graph = new SemanticGraph('containerElementId', {
 *       objectType: 'item',
 *       objectId: 'uuid-here',
 *       depth: 3,
 *       generateSummaries: true
 *   });
 */

class SemanticGraph {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        
        if (!this.container) {
            console.error(`[SemanticGraph] Container ${containerId} not found`);
            return;
        }
        
        // Configuration
        this.options = {
            objectType: options.objectType || 'item',
            objectId: options.objectId || null,
            depth: options.depth || 3,
            generateSummaries: options.generateSummaries !== false,
            includeHierarchy: options.includeHierarchy || false,
            onNodeClick: options.onNodeClick || null,
            autoLoad: options.autoLoad !== false,
            ...options
        };
        
        // Components
        this.dataManager = null;
        this.toolbar = null;
        this.tooltip = null;
        
        // Sigma.js instances
        this.graph = null;
        this.sigma = null;
        
        // Initialize
        this.init();
    }
    
    init() {
        // Create container structure
        this.createContainer();
        
        // Initialize data manager
        this.dataManager = new SemanticGraphDataManager({
            depth: this.options.depth,
            generateSummaries: this.options.generateSummaries,
            includeHierarchy: this.options.includeHierarchy
        });
        
        // Initialize tooltip
        this.tooltip = new GraphNodeTooltip();
        
        // Initialize toolbar
        const wrapperElement = this.container.querySelector('.semantic-network-wrapper');
        this.toolbar = new GraphToolbar(wrapperElement, {
            onReset: () => this.resetView(),
            onToggleLabels: () => this.toggleLabels(),
            onToggleHierarchy: (enabled) => this.toggleHierarchy(enabled),
            onToggleLevel: (level, visible) => this.toggleLevel(level, visible)
        });
        
        // Auto-load if enabled and object is specified
        if (this.options.autoLoad && this.options.objectType && this.options.objectId) {
            this.load(this.options.objectType, this.options.objectId);
        }
    }
    
    createContainer() {
        this.container.innerHTML = `
            <div class="semantic-network-wrapper">
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
                        <span class="legend-dot" style="background: #22c55e;"></span>
                        <span>Quelle</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: #f59e0b;"></span>
                        <span>Item Ebene 1</span>
                    </div>
                    <div class="legend-item" id="level2Legend">
                        <span class="legend-dot" style="background: #3b82f6;"></span>
                        <span>Item Ebene 2</span>
                    </div>
                    <div class="legend-item" id="level3Legend">
                        <span class="legend-dot" style="background: #8b5cf6;"></span>
                        <span>Item Ebene 3</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: #ec4899;"></span>
                        <span>Task Ebene 1</span>
                    </div>
                    <div class="legend-item" id="taskLevel2Legend">
                        <span class="legend-dot" style="background: #a855f7;"></span>
                        <span>Task Ebene 2</span>
                    </div>
                    <div class="legend-item" id="taskLevel3Legend">
                        <span class="legend-dot" style="background: #6366f1;"></span>
                        <span>Task Ebene 3</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: #10b981;"></span>
                        <span>File Ebene 1</span>
                    </div>
                    <div class="legend-item" id="fileLevel2Legend">
                        <span class="legend-dot" style="background: #059669;"></span>
                        <span>File Ebene 2</span>
                    </div>
                    <div class="legend-item" id="fileLevel3Legend">
                        <span class="legend-dot" style="background: #047857;"></span>
                        <span>File Ebene 3</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: #f97316;"></span>
                        <span>GitHub Issue Ebene 1</span>
                    </div>
                    <div class="legend-item" id="githubIssueLevel2Legend">
                        <span class="legend-dot" style="background: #ea580c;"></span>
                        <span>GitHub Issue Ebene 2</span>
                    </div>
                    <div class="legend-item" id="githubIssueLevel3Legend">
                        <span class="legend-dot" style="background: #c2410c;"></span>
                        <span>GitHub Issue Ebene 3</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: #06b6d4;"></span>
                        <span>Pull Request Ebene 1</span>
                    </div>
                    <div class="legend-item" id="pullRequestLevel2Legend">
                        <span class="legend-dot" style="background: #0891b2;"></span>
                        <span>Pull Request Ebene 2</span>
                    </div>
                    <div class="legend-item" id="pullRequestLevel3Legend">
                        <span class="legend-dot" style="background: #0e7490;"></span>
                        <span>Pull Request Ebene 3</span>
                    </div>
                    <div class="legend-item" id="hierarchyLegend" style="display: none;">
                        <span class="legend-line" style="border-top: 2px dashed #6366f1;"></span>
                        <span>Hierarchie (Parent/Child)</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    async load(objectType, objectId) {
        this.showLoading();
        
        try {
            // Load data
            const data = await this.dataManager.load(objectType, objectId);
            
            if (!data || !data.success) {
                throw new Error(data?.error || 'Failed to load network data');
            }
            
            // Render graph
            this.renderNetwork(data);
            
            // Render summaries
            this.renderSummaries(data);
            
            console.log('[SemanticGraph] Network loaded and rendered successfully');
            
        } catch (error) {
            console.error('[SemanticGraph] Error loading semantic network:', error);
            this.showError(error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    renderNetwork(data) {
        if (!data || !data.nodes) {
            console.warn('[SemanticGraph] No network data to render');
            return;
        }
        
        console.log('[SemanticGraph] Starting network render with', data.nodes.length, 'nodes');
        
        const graphContainer = document.getElementById('snGraph');
        if (!graphContainer) {
            console.error('[SemanticGraph] Graph container not found');
            return;
        }
        
        // Ensure container is visible and has dimensions
        graphContainer.style.display = 'block';
        
        // Check if container has width
        const containerWidth = graphContainer.offsetWidth;
        const containerHeight = graphContainer.offsetHeight;
        
        console.log('[SemanticGraph] Container dimensions:', containerWidth, 'x', containerHeight);
        
        if (containerWidth === 0 || containerHeight === 0) {
            console.warn('[SemanticGraph] Container has no dimensions, retrying in 100ms...');
            setTimeout(() => this.renderNetwork(data), 100);
            return;
        }
        
        // Clear existing graph
        if (this.sigma) {
            this.sigma.kill();
            this.sigma = null;
        }
        
        graphContainer.innerHTML = '';
        
        // Prepare graph data for Sigma.js
        const nodes = data.nodes.map(node => {
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
        
        const edges = data.edges.map((edge, idx) => {
            const isHierarchy = edge.type === 'hierarchy';
            const edgeAttributes = {
                size: isHierarchy ? 3 : edge.weight * 2,
                color: isHierarchy ? '#6366f1' : '#4b5563',
                type: isHierarchy ? 'line' : 'line',
                originalData: edge
            };
            
            if (isHierarchy) {
                edgeAttributes.dashArray = [5, 5];
            }
            
            return {
                key: `edge-${idx}`,
                source: edge.source,
                target: edge.target,
                attributes: edgeAttributes
            };
        });
        
        // Create graph using graphology
        const GraphConstructor = typeof graphology !== 'undefined' && graphology.Graph ? graphology.Graph :
                                 (typeof window.graphology !== 'undefined' && window.graphology.Graph ? window.graphology.Graph : null);
        
        if (!GraphConstructor) {
            console.error('[SemanticGraph] Graphology library not found. Cannot create graph.');
            this.showError('Graphology library not loaded. Please refresh the page.');
            return;
        }
        
        this.graph = new GraphConstructor();
        
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
        const SigmaConstructor = typeof Sigma !== 'undefined' ? Sigma :
                                 (typeof window.Sigma !== 'undefined' ? window.Sigma :
                                 (typeof sigma !== 'undefined' ? sigma :
                                 (typeof window.sigma !== 'undefined' ? window.sigma : null)));
        
        if (!SigmaConstructor) {
            console.error('[SemanticGraph] Sigma.js library not found. Cannot render graph.');
            this.showError('Sigma.js library not loaded. Please refresh the page.');
            return;
        }
        
        this.sigma = new SigmaConstructor(this.graph, graphContainer, {
            renderEdgeLabels: false,
            defaultNodeColor: '#3b82f6',
            defaultEdgeColor: '#4b5563',
            labelSize: 12,
            labelColor: { color: '#ffffff' },
            labelWeight: 'normal',
            enableEdgeClickEvents: false,
            enableEdgeWheelEvents: false,
            enableEdgeHoverEvents: false,
            allowInvalidContainer: true
        });
        
        // Bind Sigma events
        this.bindSigmaEvents();
        
        // Apply initial level visibility from toolbar state
        if (this.toolbar) {
            const toolbarState = this.toolbar.getState();
            if (!toolbarState.showLevel2) {
                this.applyLevelVisibility(2, false);
            }
            if (!toolbarState.showLevel3) {
                this.applyLevelVisibility(3, false);
            }
        }
    }
    
    applyLayout() {
        let forceAtlas2;
        
        if (typeof window.graphologyLibraryLayoutForceAtlas2 !== 'undefined') {
            forceAtlas2 = window.graphologyLibraryLayoutForceAtlas2;
        } else if (typeof window.GraphologyLayoutForceAtlas2 !== 'undefined') {
            forceAtlas2 = window.GraphologyLayoutForceAtlas2;
        } else if (typeof GraphologyLayoutForceAtlas2 !== 'undefined') {
            forceAtlas2 = GraphologyLayoutForceAtlas2;
        } else if (typeof graphologyLayoutForceAtlas2 !== 'undefined') {
            forceAtlas2 = graphologyLayoutForceAtlas2;
        } else if (typeof graphologyLibrary !== 'undefined' && graphologyLibrary.layoutForceAtlas2) {
            forceAtlas2 = graphologyLibrary.layoutForceAtlas2;
        } else {
            console.warn('[SemanticGraph] ForceAtlas2 layout library not found. Skipping layout optimization.');
            return;
        }
        
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
                this.navigateToObject(nodeData);
            }
        });
        
        // Hover handlers for tooltips
        this.sigma.on('enterNode', (event) => {
            const nodeId = event.node;
            const nodeData = this.graph.getNodeAttributes(nodeId).originalData;
            this.tooltip.show(event, nodeData);
        });
        
        this.sigma.on('leaveNode', () => {
            this.tooltip.hide();
        });
    }
    
    renderSummaries(data) {
        const summaryContainer = document.getElementById('snSummary');
        if (!summaryContainer || !data.levels) {
            return;
        }
        
        const levels = data.levels;
        let html = '';
        
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
    
    getNodeColor(node) {
        if (node.isSource) return '#22c55e';
        if (node.isParent) return '#3b82f6';
        if (node.isChild) return '#f97316';
        
        const typeColors = {
            'item': { 1: '#f59e0b', 2: '#3b82f6', 3: '#8b5cf6' },
            'task': { 1: '#ec4899', 2: '#a855f7', 3: '#6366f1' },
            'file': { 1: '#10b981', 2: '#059669', 3: '#047857' },
            'github_issue': { 1: '#f97316', 2: '#ea580c', 3: '#c2410c' },
            'pull_request': { 1: '#06b6d4', 2: '#0891b2', 3: '#0e7490' }
        };
        
        const objectType = node.type || 'item';
        const colors = typeColors[objectType] || typeColors['item'];
        
        return colors[node.level] || '#6b7280';
    }
    
    getNodeSize(node) {
        if (node.isSource) return 20;
        const similarity = node.similarity || 0.5;
        return 10 + similarity * 10;
    }
    
    getNodeLabel(node) {
        const props = node.properties || {};
        let label = props.title || 'Untitled';
        if (label.length > 30) {
            label = label.substring(0, 27) + '...';
        }
        return label;
    }
    
    navigateToObject(nodeData) {
        const type = nodeData.type;
        const id = nodeData.id;
        const props = nodeData.properties || {};
        
        let url = '';
        switch (type) {
            case 'item':
                url = `/items/${id}/`;
                break;
            case 'task':
                url = `/tasks/${id}/`;
                break;
            case 'github_issue':
            case 'pull_request':
                // GitHub issues and PRs have a URL in properties
                url = props.url || props.html_url || '';
                if (url) {
                    window.open(url, '_blank');
                }
                return;
            case 'file':
                // Files can be viewed via their download endpoint
                if (id) {
                    window.open(`/api/files/${id}`, '_blank');
                }
                return;
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
    
    toggleHierarchy(enabled) {
        this.dataManager.updateOptions({ includeHierarchy: enabled });
        
        const legend = document.getElementById('hierarchyLegend');
        if (legend) {
            legend.style.display = enabled ? 'flex' : 'none';
        }
        
        if (this.options.objectType && this.options.objectId) {
            this.load(this.options.objectType, this.options.objectId);
        }
    }
    
    toggleLevel(level, visible) {
        this.applyLevelVisibility(level, visible);
    }
    
    applyLevelVisibility(level, visible) {
        if (!this.sigma || !this.graph) return;
        
        this.graph.forEachNode((nodeId, attributes) => {
            const node = attributes.originalData;
            if (node.level === level) {
                this.graph.setNodeAttribute(nodeId, 'hidden', !visible);
            }
        });
        
        const legendId = `level${level}Legend`;
        const legend = document.getElementById(legendId);
        if (legend) {
            legend.style.display = visible ? 'flex' : 'none';
        }
        
        // Also update task level legends
        const taskLegendId = `taskLevel${level}Legend`;
        const taskLegend = document.getElementById(taskLegendId);
        if (taskLegend) {
            taskLegend.style.display = visible ? 'flex' : 'none';
        }
        
        if (this.sigma) {
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
        
        if (this.tooltip) {
            this.tooltip.destroy();
            this.tooltip = null;
        }
        
        if (this.dataManager) {
            this.dataManager.clear();
            this.dataManager = null;
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SemanticGraph;
}
