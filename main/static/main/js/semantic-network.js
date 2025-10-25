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
            includeHierarchy: options.includeHierarchy || false,
            onNodeClick: options.onNodeClick || null,
            ...options
        };
        
        // State
        this.graph = null;
        this.sigma = null;
        this.networkData = null;
        this.isLoading = false;
        this.showLevel2 = true;  // Track Level 2 visibility
        this.showLevel3 = true;  // Track Level 3 visibility
        
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
                        <button class="btn btn-sm btn-outline-info" id="snToggleHierarchy">
                            <i class="bi bi-diagram-2"></i> Hierarchie
                        </button>
                        <button class="btn btn-sm btn-outline-warning" id="snToggleLevel2">
                            <i class="bi bi-eye"></i> Ebene 2
                        </button>
                        <button class="btn btn-sm btn-outline-warning" id="snToggleLevel3">
                            <i class="bi bi-eye"></i> Ebene 3
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
                        <span class="legend-dot" style="background: #22c55e;"></span>
                        <span>Quelle</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: #f59e0b;"></span>
                        <span>Ebene 1 (>80%)</span>
                    </div>
                    <div class="legend-item" id="level2Legend">
                        <span class="legend-dot" style="background: #3b82f6;"></span>
                        <span>Ebene 2 (>70%)</span>
                    </div>
                    <div class="legend-item" id="level3Legend">
                        <span class="legend-dot" style="background: #8b5cf6;"></span>
                        <span>Ebene 3 (>60%)</span>
                    </div>
                    <div class="legend-item" id="hierarchyLegend" style="display: none;">
                        <span class="legend-line" style="border-top: 2px dashed #6366f1;"></span>
                        <span>Hierarchie (Parent/Child)</span>
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
        
        const toggleHierarchyBtn = document.getElementById('snToggleHierarchy');
        if (toggleHierarchyBtn) {
            toggleHierarchyBtn.addEventListener('click', () => this.toggleHierarchy());
        }
        
        const toggleLevel2Btn = document.getElementById('snToggleLevel2');
        if (toggleLevel2Btn) {
            toggleLevel2Btn.addEventListener('click', () => this.toggleLevel(2));
        }
        
        const toggleLevel3Btn = document.getElementById('snToggleLevel3');
        if (toggleLevel3Btn) {
            toggleLevel3Btn.addEventListener('click', () => this.toggleLevel(3));
        }
    }
    
    toggleHierarchy() {
        // Toggle hierarchy option
        this.options.includeHierarchy = !this.options.includeHierarchy;
        
        // Update button state
        const btn = document.getElementById('snToggleHierarchy');
        if (btn) {
            if (this.options.includeHierarchy) {
                btn.classList.remove('btn-outline-info');
                btn.classList.add('btn-info');
            } else {
                btn.classList.remove('btn-info');
                btn.classList.add('btn-outline-info');
            }
        }
        
        // Show/hide hierarchy legend
        const legend = document.getElementById('hierarchyLegend');
        if (legend) {
            legend.style.display = this.options.includeHierarchy ? 'flex' : 'none';
        }
        
        // Reload network with new setting
        if (this.options.objectType && this.options.objectId) {
            this.load(this.options.objectType, this.options.objectId);
        }
    }
    
    toggleLevel(level) {
        // Toggle level visibility
        if (level === 2) {
            this.showLevel2 = !this.showLevel2;
        } else if (level === 3) {
            this.showLevel3 = !this.showLevel3;
        }
        
        // Update button state
        const btnId = `snToggleLevel${level}`;
        const btn = document.getElementById(btnId);
        if (btn) {
            const isVisible = level === 2 ? this.showLevel2 : this.showLevel3;
            const icon = btn.querySelector('i');
            if (isVisible) {
                btn.classList.remove('btn-outline-warning');
                btn.classList.add('btn-warning');
                if (icon) {
                    icon.className = 'bi bi-eye';
                }
            } else {
                btn.classList.remove('btn-warning');
                btn.classList.add('btn-outline-warning');
                if (icon) {
                    icon.className = 'bi bi-eye-slash';
                }
            }
        }
        
        // Update legend visibility
        const legendId = `level${level}Legend`;
        const legend = document.getElementById(legendId);
        if (legend) {
            const isVisible = level === 2 ? this.showLevel2 : this.showLevel3;
            legend.style.display = isVisible ? 'flex' : 'none';
        }
        
        // Update node visibility in the graph
        this.updateNodeVisibility();
    }
    
    updateNodeVisibility() {
        if (!this.sigma || !this.graph) return;
        
        // Iterate through all nodes and update their hidden state
        this.graph.forEachNode((nodeId, attributes) => {
            const node = attributes.originalData;
            let shouldHide = false;
            
            // Hide Level 2 nodes if toggled off
            if (node.level === 2 && !this.showLevel2) {
                shouldHide = true;
            }
            
            // Hide Level 3 nodes if toggled off
            if (node.level === 3 && !this.showLevel3) {
                shouldHide = true;
            }
            
            // Update node attributes
            this.graph.setNodeAttribute(nodeId, 'hidden', shouldHide);
        });
        
        // Refresh the Sigma renderer
        this.sigma.refresh();
    }
    
    async load(objectType, objectId) {
        if (this.isLoading) return;
        
        this.options.objectType = objectType;
        this.options.objectId = objectId;
        
        this.showLoading();
        this.isLoading = true;
        
        try {
            // Build API URL - use milestone-specific endpoint for milestones
            let url;
            if (objectType === 'milestone') {
                url = new URL(`/api/milestones/${objectId}/semantic-network`, window.location.origin);
            } else {
                url = new URL(`/api/semantic-network/${objectType}/${objectId}`, window.location.origin);
            }
            url.searchParams.set('depth', this.options.depth);
            url.searchParams.set('summaries', this.options.generateSummaries);
            url.searchParams.set('include_hierarchy', this.options.includeHierarchy);
            
            console.log(`[SemanticNetwork] Loading network for ${objectType}/${objectId}`);
            console.log(`[SemanticNetwork] API URL: ${url.toString()}`);
            
            // Fetch network data
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            console.log(`[SemanticNetwork] Response status: ${response.status}`);
            
            if (!response.ok) {
                // Try to get error details from response
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    console.error('[SemanticNetwork] Error response:', errorData);
                    if (errorData.error) {
                        errorMessage = errorData.error;
                    }
                    if (errorData.details) {
                        console.error('[SemanticNetwork] Error details:', errorData.details);
                        errorMessage += ` - ${JSON.stringify(errorData.details)}`;
                    }
                } catch (e) {
                    console.error('[SemanticNetwork] Could not parse error response:', e);
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            console.log('[SemanticNetwork] Received data:', {
                success: data.success,
                nodeCount: data.nodes?.length,
                edgeCount: data.edges?.length,
                levels: Object.keys(data.levels || {})
            });
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load semantic network');
            }
            
            this.networkData = data;
            this.renderNetwork();
            this.renderSummaries();
            
            console.log('[SemanticNetwork] Network rendered successfully');
            
        } catch (error) {
            console.error('[SemanticNetwork] Error loading semantic network:', error);
            this.showError(error.message);
        } finally {
            this.hideLoading();
            this.isLoading = false;
        }
    }
    
    renderNetwork() {
        if (!this.networkData || !this.networkData.nodes) {
            console.warn('[SemanticNetwork] No network data to render');
            return;
        }
        
        console.log('[SemanticNetwork] Starting network render with', this.networkData.nodes.length, 'nodes');
        
        const graphContainer = document.getElementById('snGraph');
        if (!graphContainer) {
            console.error('[SemanticNetwork] Graph container not found');
            return;
        }
        
        // Ensure container is visible and has dimensions
        graphContainer.style.display = 'block';
        
        // Check if container has width
        const containerWidth = graphContainer.offsetWidth;
        const containerHeight = graphContainer.offsetHeight;
        
        console.log('[SemanticNetwork] Container dimensions:', containerWidth, 'x', containerHeight);
        
        if (containerWidth === 0 || containerHeight === 0) {
            console.warn('[SemanticNetwork] Container has no dimensions, retrying in 100ms...');
            setTimeout(() => this.renderNetwork(), 100);
            return;
        }
        
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
        
        const edges = this.networkData.edges.map((edge, idx) => {
            // Different styling for hierarchy vs similarity edges
            const isHierarchy = edge.type === 'hierarchy';
            const edgeAttributes = {
                size: isHierarchy ? 3 : edge.weight * 2,
                color: isHierarchy ? '#6366f1' : '#4b5563',
                type: isHierarchy ? 'line' : 'line',
                originalData: edge
            };
            
            // Add dashed style for hierarchy edges (handled in CSS)
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
        // Handle different possible graphology namespaces
        const GraphConstructor = typeof graphology !== 'undefined' && graphology.Graph ? graphology.Graph :
                                 (typeof window.graphology !== 'undefined' && window.graphology.Graph ? window.graphology.Graph : null);
        
        if (!GraphConstructor) {
            console.error('[SemanticNetwork] Graphology library not found. Cannot create graph.');
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
        // Handle different possible Sigma namespaces
        const SigmaConstructor = typeof Sigma !== 'undefined' ? Sigma : 
                                 (typeof window.Sigma !== 'undefined' ? window.Sigma : null);
        
        if (!SigmaConstructor) {
            console.error('[SemanticNetwork] Sigma.js library not found. Cannot render graph.');
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
            allowInvalidContainer: true  // Allow rendering even if container size is temporarily invalid
        });
        
        // Bind Sigma events
        this.bindSigmaEvents();
    }
    
    applyLayout() {
        // Use circular layout with ForceAtlas2 refinement
        // Access forceAtlas2 from the correct namespace based on UMD bundle
        let forceAtlas2;
        
        // Try different possible namespaces for the UMD bundle
        // The graphology-layout-forceatlas2 UMD build can be exposed under different names
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
            console.warn('[SemanticNetwork] ForceAtlas2 layout library not found. Skipping layout optimization.');
            console.warn('[SemanticNetwork] The network will still be displayed, but without force-directed layout.');
            console.warn('[SemanticNetwork] Available globals:', Object.keys(window).filter(k => k.toLowerCase().includes('graph')));
            return; // Skip layout if library not available - graph will still render with random positions
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
        // Color by type and role
        if (node.isSource) {
            return '#22c55e'; // Green for source
        }
        
        if (node.isParent) {
            return '#3b82f6'; // Blue for parent
        }
        
        if (node.isChild) {
            return '#f97316'; // Orange for child
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
        
        tooltip.innerHTML = `
            <div class="tooltip-title">${this.escapeHtml(title)}</div>
            <div class="tooltip-meta">Type: ${type}</div>
            <div class="tooltip-meta">Similarity: ${similarity}</div>
            ${hierarchyInfo}
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
