# Milestone Semantic Network Feature

## Overview

The Milestone Semantic Network feature enables semantic context visualization for Milestones in IdeaGraph. It allows teams to see and explore semantically related content (Items, Tasks, Files, etc.) within and across milestone boundaries.

## Features

- **Interactive Graph Visualization**: Uses Sigma.js to render an interactive semantic network
- **Multi-Level Similarity**: Shows connections at 3 levels of semantic similarity:
  - Level 1: >80% similarity (strong connections)
  - Level 2: >70% similarity (moderate connections)  
  - Level 3: >60% similarity (weak connections)
- **AI-Generated Summaries**: Optional KiGate-powered summaries for each network level
- **Node Interactions**: Click on nodes to navigate to related objects
- **Customizable Depth**: Control how many levels of relationships to explore

## Usage

### Accessing the Semantic Network

1. Navigate to a Milestone detail page
2. Click on the "Semantic Network" tab
3. The semantic network will automatically load and visualize connections

### Understanding the Visualization

#### Node Colors
- **Green**: Source milestone (center)
- **Orange**: Level 1 - Very similar objects (>80%)
- **Blue**: Level 2 - Similar objects (>70%)
- **Purple**: Level 3 - Somewhat similar objects (>60%)

#### Node Types
The network can show different types of objects:
- Milestones
- Items
- Tasks
- Files
- Emails
- GitHub Issues

#### Controls
- **Reset View**: Reset the graph to its default zoom and position
- **Labels**: Toggle node labels on/off
- **Ebene 2/3**: Toggle visibility of Level 2 and Level 3 nodes

### Clicking on Nodes

Click on any node in the graph to navigate to that object's detail page:
- Milestone nodes → Milestone detail page
- Item nodes → Item detail page
- Task nodes → Task detail page

## API Endpoint

The semantic network data is provided by the following API endpoint:

```
GET /api/milestones/<milestone_id>/semantic-network
```

### Query Parameters

- `depth` (integer, default: 3): Network depth (1-3)
- `threshold_1` (float, default: 0.8): Similarity threshold for level 1
- `threshold_2` (float, default: 0.7): Similarity threshold for level 2
- `threshold_3` (float, default: 0.6): Similarity threshold for level 3
- `summaries` (boolean, default: true): Generate AI summaries for each level

### Example Request

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/milestones/12345678-1234-1234-1234-123456789abc/semantic-network?depth=2&summaries=true"
```

### Example Response

```json
{
  "success": true,
  "source_id": "12345678-1234-1234-1234-123456789abc",
  "source_type": "milestone",
  "depth": 3,
  "nodes": [
    {
      "id": "12345678-1234-1234-1234-123456789abc",
      "type": "milestone",
      "level": 0,
      "properties": {
        "title": "Milestone A",
        "description": "..."
      },
      "isSource": true
    },
    {
      "id": "87654321-4321-4321-4321-cba987654321",
      "type": "item",
      "level": 1,
      "properties": {
        "title": "Item X",
        "description": "..."
      },
      "similarity": 0.82,
      "isSource": false
    }
  ],
  "edges": [
    {
      "source": "12345678-1234-1234-1234-123456789abc",
      "target": "87654321-4321-4321-4321-cba987654321",
      "weight": 0.82,
      "level": 1,
      "type": "similarity"
    }
  ],
  "levels": {
    "1": {
      "level": 1,
      "threshold": 0.8,
      "node_count": 1,
      "nodes": ["87654321-4321-4321-4321-cba987654321"],
      "summary": "Diese Ebene umfasst 1 Objekt mit Fokus auf..."
    }
  },
  "total_nodes": 2,
  "total_edges": 1,
  "include_hierarchy": false
}
```

## Technical Details

### Implementation

The feature is implemented using:
- **Backend**: Django REST API endpoint in `main/api_views.py`
- **Service**: `SemanticNetworkService` in `core/services/semantic_network_service.py`
- **Frontend**: Sigma.js graph visualization in `main/static/main/js/semantic-network.js`
- **Data**: Weaviate vector database for semantic similarity search

### Data Flow

1. User navigates to Milestone detail page and clicks "Semantic Network" tab
2. Frontend loads the `SemanticNetworkViewer` component
3. Component calls the API endpoint `/api/milestones/<id>/semantic-network`
4. Backend uses `SemanticNetworkService` to:
   - Retrieve the milestone from Weaviate
   - Find semantically similar objects using vector similarity
   - Generate AI summaries for each level (optional)
5. API returns the graph data as JSON
6. Frontend renders the interactive graph using Sigma.js

### Weaviate Integration

The milestone must be synced to Weaviate as a `KnowledgeObject` with type "Milestone" for the semantic network to work. The vector embeddings enable semantic similarity search.

## Testing

The feature includes comprehensive test coverage in:
- `main/test_milestone_semantic_network.py` - Integration tests for the API endpoint
- `main/test_semantic_network.py` - Unit tests for the semantic network service

Run tests with:
```bash
python manage.py test main.test_milestone_semantic_network
```

## Security

- **Authentication Required**: All API endpoints require valid JWT authentication
- **Error Handling**: Detailed error messages are logged but not exposed to clients
- **Input Validation**: All parameters are validated and sanitized

## Future Enhancements

Potential future improvements:
- Cross-type filtering (show only Items, only Tasks, etc.)
- Custom similarity thresholds per user
- Export graph as image or data
- Real-time updates when milestone context changes
- Integration with milestone knowledge hub for enhanced context
