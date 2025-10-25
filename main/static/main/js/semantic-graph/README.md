# Semantic Graph Component

A reusable semantic graph visualization component for IdeaGraph that displays semantic relationships between KnowledgeObjects.

## Overview

The Semantic Graph component is a modular, reusable JavaScript component that can be integrated into any view to display semantic networks. It automatically fetches and visualizes relationships between KnowledgeObjects (Items, Tasks, Milestones, Files, Conversations, etc.) using the Weaviate vector database.

## Architecture

The component is split into several focused modules:

```
semantic-graph/
├── SemanticGraph.js           # Main component class
├── GraphToolbar.js            # Toolbar controls (zoom, reset, depth)
├── GraphNodeTooltip.js        # Hover information display
└── useSemanticGraphData.js    # Data fetching module
```

### Module Responsibilities

- **SemanticGraph.js**: Main orchestrator that coordinates all other modules
- **useSemanticGraphData.js**: Handles API communication and data fetching
- **GraphToolbar.js**: Manages toolbar UI and user interactions
- **GraphNodeTooltip.js**: Displays contextual information on hover

## Usage

### Basic Setup

1. Include the component files in your template:

```html
<!-- CSS -->
<link rel="stylesheet" href="{% static 'main/css/semantic-network.css' %}" />

<!-- Sigma.js and Graphology (required dependencies) -->
<script src="https://cdn.jsdelivr.net/npm/graphology@0.25.1/dist/graphology.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/sigma@2.4.0/build/sigma.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/graphology-layout-forceatlas2@0.10.1/build/graphology-layout-forceatlas2.umd.min.js"></script>

<!-- Semantic Graph Component -->
<script src="{% static 'main/js/semantic-graph/useSemanticGraphData.js' %}"></script>
<script src="{% static 'main/js/semantic-graph/GraphNodeTooltip.js' %}"></script>
<script src="{% static 'main/js/semantic-graph/GraphToolbar.js' %}"></script>
<script src="{% static 'main/js/semantic-graph/SemanticGraph.js' %}"></script>
```

2. Create a container element:

```html
<div id="semanticGraphContainer" style="width: 100%; height: 600px;"></div>
```

3. Initialize the component:

```javascript
const graph = new SemanticGraph('semanticGraphContainer', {
    objectType: 'item',           // Type: item, task, milestone, file, etc.
    objectId: 'uuid-here',        // KnowledgeObject UUID
    depth: 3,                     // Network depth (1-3)
    generateSummaries: true,      // Generate AI summaries
    includeHierarchy: false,      // Include parent/child relationships
    autoLoad: true                // Load automatically on init
});
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `objectType` | string | 'item' | Type of object (item, task, milestone, file, etc.) |
| `objectId` | string | null | UUID of the KnowledgeObject |
| `depth` | number | 3 | Network depth (1-3 levels) |
| `generateSummaries` | boolean | true | Generate AI summaries for each level |
| `includeHierarchy` | boolean | false | Include parent-child relationships |
| `autoLoad` | boolean | true | Automatically load network on initialization |
| `onNodeClick` | function | null | Custom node click handler |

### Examples

#### Item Detail View

```javascript
const itemGraph = new SemanticGraph('itemGraphContainer', {
    objectType: 'item',
    objectId: '{{ item.id }}',
    depth: 3,
    generateSummaries: true,
    includeHierarchy: true  // Show parent/child items
});
```

#### Task Detail View

```javascript
const taskGraph = new SemanticGraph('taskGraphContainer', {
    objectType: 'task',
    objectId: '{{ task.id }}',
    depth: 2,                // Shallower network for tasks
    generateSummaries: false // Skip summaries for faster loading
});
```

#### Milestone View

```javascript
const milestoneGraph = new SemanticGraph('milestoneGraphContainer', {
    objectType: 'milestone',
    objectId: '{{ milestone.id }}',
    depth: 3,
    generateSummaries: true,
    onNodeClick: function(nodeData) {
        // Custom click handler
        console.log('Clicked node:', nodeData);
        // Navigate or show modal
    }
});
```

#### Manual Loading

```javascript
// Initialize without auto-loading
const graph = new SemanticGraph('graphContainer', {
    autoLoad: false
});

// Load later with different object
graph.load('item', 'some-uuid');

// Load another object
graph.load('task', 'another-uuid');
```

### API Methods

#### `load(objectType, objectId)`
Load semantic network for a specific object.

```javascript
graph.load('item', 'uuid-here');
```

#### `resetView()`
Reset camera to default position.

```javascript
graph.resetView();
```

#### `destroy()`
Clean up and destroy the component.

```javascript
graph.destroy();
```

## Features

### Multi-Level Semantic Network
- **Level 1**: High similarity (≥80%)
- **Level 2**: Medium similarity (≥70%)
- **Level 3**: Lower similarity (≥60%)

### Interactive Toolbar
- **Reset View**: Return camera to default position
- **Toggle Labels**: Show/hide node labels
- **Toggle Hierarchy**: Include/exclude parent-child relationships
- **Toggle Levels**: Show/hide individual similarity levels

### Node Tooltips
Hover over nodes to see:
- Object title
- Object type
- Similarity percentage
- Hierarchical relationships

### Visual Legend
Color-coded legend showing:
- Source object (green)
- Items by level (amber, blue, violet)
- Tasks by level (pink, purple, indigo)
- Hierarchical relationships (dashed lines)

## Integration Examples

### Django Template Integration

```html
{% block extra_css %}
<link rel="stylesheet" href="{% static 'main/css/semantic-network.css' %}" />
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-md-6">
        <!-- Main content -->
    </div>
    <div class="col-md-6">
        <div id="semanticGraphContainer"></div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/graphology@0.25.1/dist/graphology.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/sigma@2.4.0/build/sigma.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/graphology-layout-forceatlas2@0.10.1/build/graphology-layout-forceatlas2.umd.min.js"></script>

<script src="{% static 'main/js/semantic-graph/useSemanticGraphData.js' %}"></script>
<script src="{% static 'main/js/semantic-graph/GraphNodeTooltip.js' %}"></script>
<script src="{% static 'main/js/semantic-graph/GraphToolbar.js' %}"></script>
<script src="{% static 'main/js/semantic-graph/SemanticGraph.js' %}"></script>

<script>
document.addEventListener('DOMContentLoaded', function() {
    const graph = new SemanticGraph('semanticGraphContainer', {
        objectType: '{{ object_type }}',
        objectId: '{{ object_id }}',
        depth: 3
    });
});
</script>
{% endblock %}
```

## API Endpoints

The component uses the following API endpoints:

- **Generic objects**: `/api/semantic-network/{objectType}/{objectId}`
- **Milestones**: `/api/milestones/{milestoneId}/semantic-network`

Query parameters:
- `depth`: Network depth (1-3)
- `summaries`: Generate AI summaries (true/false)
- `include_hierarchy`: Include parent/child relationships (true/false)

## Dependencies

- **Sigma.js** (v2.4.0+): Graph rendering
- **Graphology** (v0.25.1+): Graph data structure
- **ForceAtlas2** (v0.10.1+): Force-directed layout algorithm
- **Bootstrap** (v5.x): UI styling
- **Bootstrap Icons**: Icon set

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Migration from Old Component

If you're using the old `SemanticNetworkViewer` class, migration is simple:

**Old code:**
```javascript
const viewer = new SemanticNetworkViewer('container', {
    objectType: 'item',
    objectId: 'uuid'
});
viewer.load('item', 'uuid');
```

**New code:**
```javascript
const graph = new SemanticGraph('container', {
    objectType: 'item',
    objectId: 'uuid'
});
// Auto-loads by default, no need to call load()
```

## Troubleshooting

### Graph not displaying
- Check browser console for errors
- Ensure container has explicit width and height
- Verify Sigma.js and Graphology are loaded before component

### No data showing
- Check API endpoint is accessible
- Verify object exists in Weaviate
- Check network tab for API errors

### Performance issues
- Reduce `depth` parameter (use 1 or 2)
- Disable `generateSummaries` for faster loading
- Limit container size

## Future Enhancements

- Support for more object types (Conversations, Emails, Notes)
- Real-time updates via WebSocket
- Export graph as image
- Advanced filtering and search
- Graph snapshots and history
