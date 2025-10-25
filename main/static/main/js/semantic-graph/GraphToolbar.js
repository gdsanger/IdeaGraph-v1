/**
 * Graph Toolbar
 * 
 * Module for graph toolbar controls including zoom, reset, depth control,
 * and visibility toggles.
 */

class GraphToolbar {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            onReset: options.onReset || null,
            onToggleLabels: options.onToggleLabels || null,
            onToggleHierarchy: options.onToggleHierarchy || null,
            onToggleLevel: options.onToggleLevel || null,
            showHierarchyToggle: options.showHierarchyToggle !== false,
            showLevelToggles: options.showLevelToggles !== false,
            ...options
        };
        
        this.state = {
            includeHierarchy: false,
            showLevel2: false,
            showLevel3: false
        };
        
        this.init();
    }
    
    init() {
        // Create toolbar HTML
        const toolbarHtml = `
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
                    ${this.options.showHierarchyToggle ? `
                        <button class="btn btn-sm btn-outline-info" id="snToggleHierarchy">
                            <i class="bi bi-diagram-2"></i> Hierarchie
                        </button>
                    ` : ''}
                    ${this.options.showLevelToggles ? `
                        <button class="btn btn-sm btn-outline-warning" id="snToggleLevel2">
                            <i class="bi bi-eye-slash"></i> Ebene 2
                        </button>
                        <button class="btn btn-sm btn-outline-warning" id="snToggleLevel3">
                            <i class="bi bi-eye-slash"></i> Ebene 3
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
        
        // Insert toolbar at the beginning of container
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = toolbarHtml;
        while (tempDiv.firstChild) {
            this.container.insertBefore(tempDiv.firstChild, this.container.firstChild);
        }
        
        // Bind events
        this.bindEvents();
        
        // Update button states to reflect initial state
        this.updateLevelButton(2);
        this.updateLevelButton(3);
    }
    
    bindEvents() {
        // Reset view button
        const resetBtn = document.getElementById('snResetView');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                if (this.options.onReset) {
                    this.options.onReset();
                }
            });
        }
        
        // Toggle labels button
        const toggleLabelsBtn = document.getElementById('snToggleLabels');
        if (toggleLabelsBtn) {
            toggleLabelsBtn.addEventListener('click', () => {
                if (this.options.onToggleLabels) {
                    this.options.onToggleLabels();
                }
            });
        }
        
        // Toggle hierarchy button
        const toggleHierarchyBtn = document.getElementById('snToggleHierarchy');
        if (toggleHierarchyBtn) {
            toggleHierarchyBtn.addEventListener('click', () => {
                this.state.includeHierarchy = !this.state.includeHierarchy;
                this.updateHierarchyButton();
                if (this.options.onToggleHierarchy) {
                    this.options.onToggleHierarchy(this.state.includeHierarchy);
                }
            });
        }
        
        // Toggle level 2 button
        const toggleLevel2Btn = document.getElementById('snToggleLevel2');
        if (toggleLevel2Btn) {
            toggleLevel2Btn.addEventListener('click', () => {
                this.state.showLevel2 = !this.state.showLevel2;
                this.updateLevelButton(2);
                if (this.options.onToggleLevel) {
                    this.options.onToggleLevel(2, this.state.showLevel2);
                }
            });
        }
        
        // Toggle level 3 button
        const toggleLevel3Btn = document.getElementById('snToggleLevel3');
        if (toggleLevel3Btn) {
            toggleLevel3Btn.addEventListener('click', () => {
                this.state.showLevel3 = !this.state.showLevel3;
                this.updateLevelButton(3);
                if (this.options.onToggleLevel) {
                    this.options.onToggleLevel(3, this.state.showLevel3);
                }
            });
        }
    }
    
    updateHierarchyButton() {
        const btn = document.getElementById('snToggleHierarchy');
        if (btn) {
            if (this.state.includeHierarchy) {
                btn.classList.remove('btn-outline-info');
                btn.classList.add('btn-info');
            } else {
                btn.classList.remove('btn-info');
                btn.classList.add('btn-outline-info');
            }
        }
    }
    
    updateLevelButton(level) {
        const btnId = `snToggleLevel${level}`;
        const btn = document.getElementById(btnId);
        if (btn) {
            const isVisible = level === 2 ? this.state.showLevel2 : this.state.showLevel3;
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
    }
    
    /**
     * Get current state
     */
    getState() {
        return { ...this.state };
    }
    
    /**
     * Set state
     */
    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.updateHierarchyButton();
        this.updateLevelButton(2);
        this.updateLevelButton(3);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GraphToolbar;
}
