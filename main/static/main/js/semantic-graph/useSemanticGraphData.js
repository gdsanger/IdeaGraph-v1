/**
 * Semantic Graph Data Manager
 * 
 * Module for fetching and managing semantic graph data from the API.
 * This module provides a clean interface for loading semantic networks
 * based on KnowledgeObject IDs.
 */

class SemanticGraphDataManager {
    constructor(options = {}) {
        this.options = {
            depth: options.depth || 3,
            generateSummaries: options.generateSummaries !== false,
            includeHierarchy: options.includeHierarchy || false,
            ...options
        };
        
        this.isLoading = false;
        this.lastError = null;
        this.networkData = null;
    }
    
    /**
     * Load semantic network data for a KnowledgeObject
     * 
     * @param {string} objectType - Type of object (item, task, milestone, etc.)
     * @param {string} objectId - UUID of the object
     * @returns {Promise<Object>} Network data with nodes and edges
     */
    async load(objectType, objectId) {
        if (this.isLoading) {
            console.warn('[SemanticGraphData] Already loading data');
            return null;
        }
        
        this.isLoading = true;
        this.lastError = null;
        
        try {
            // Build API URL - use milestone-specific endpoint for milestones
            let url;
            if (objectType === 'milestone') {
                url = new URL(`/api/milestones/${objectId}/semantic-network`, window.location.origin);
            } else {
                url = new URL(`/api/semantic-network/${objectType}/${objectId}`, window.location.origin);
            }
            
            // Add query parameters
            url.searchParams.set('depth', this.options.depth);
            url.searchParams.set('summaries', this.options.generateSummaries);
            url.searchParams.set('include_hierarchy', this.options.includeHierarchy);
            
            console.log(`[SemanticGraphData] Loading network for ${objectType}/${objectId}`);
            console.log(`[SemanticGraphData] API URL: ${url.toString()}`);
            
            // Fetch network data
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            console.log(`[SemanticGraphData] Response status: ${response.status}`);
            
            if (!response.ok) {
                // Try to get error details from response
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorData = await response.json();
                    console.error('[SemanticGraphData] Error response:', errorData);
                    if (errorData.error) {
                        errorMessage = errorData.error;
                    }
                    if (errorData.details) {
                        console.error('[SemanticGraphData] Error details:', errorData.details);
                        errorMessage += ` - ${JSON.stringify(errorData.details)}`;
                    }
                } catch (e) {
                    console.error('[SemanticGraphData] Could not parse error response:', e);
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            console.log('[SemanticGraphData] Received data:', {
                success: data.success,
                nodeCount: data.nodes?.length,
                edgeCount: data.edges?.length,
                levels: Object.keys(data.levels || {})
            });
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load semantic network');
            }
            
            this.networkData = data;
            return data;
            
        } catch (error) {
            console.error('[SemanticGraphData] Error loading semantic network:', error);
            this.lastError = error.message;
            throw error;
        } finally {
            this.isLoading = false;
        }
    }
    
    /**
     * Get cached network data
     */
    getData() {
        return this.networkData;
    }
    
    /**
     * Update options and reload if data was already loaded
     */
    updateOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
    }
    
    /**
     * Clear cached data
     */
    clear() {
        this.networkData = null;
        this.lastError = null;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SemanticGraphDataManager;
}
