# Milestone Knowledge Hub - Feature Documentation

## Overview

The Milestone Knowledge Hub transforms milestones from simple deadline trackers into intelligent knowledge containers that collect, analyze, and derive actionable tasks from various context sources.

## Key Features

### 1. Extended Milestone Model

Milestones now include:
- **Description**: Manual or AI-generated description
- **Status**: Planning stage tracking (Planned, In Progress, Completed)
- **Summary**: AI-generated summary from all context objects
- **Weaviate Integration**: Vector database storage for semantic search

### 2. Context Objects

Milestones can contain multiple context sources:
- **Files** (📄): Documents, PDFs, etc.
- **Emails** (✉️): Email communications
- **Transcripts** (🎙️): Meeting transcripts
- **Notes** (🗒️): Manual notes

Each context object includes:
- Title and content
- Source ID and URL
- AI-generated summary
- Automatically derived tasks
- Tags for categorization

### 3. AI-Powered Analysis

**KiGate Integration**:
- **text-summary-agent**: Generates concise summaries of context
- **text-analysis-task-derivation-agent**: Derives actionable tasks from content

**Automatic Processing**:
1. User adds context object
2. AI analyzes content
3. Summary generated
4. Tasks derived and can be created automatically
5. Milestone summary updated

## API Endpoints

### Add Context Object
```http
POST /api/milestones/<milestone_id>/context/add
Content-Type: application/json

{
  "type": "file|email|transcript|note",
  "title": "Meeting Protocol Q4",
  "content": "Discussion about project goals...",
  "source_id": "optional-guid",
  "url": "optional-url",
  "auto_analyze": true
}
```

### List Context Objects
```http
GET /api/milestones/<milestone_id>/context
```

### Analyze Context Object
```http
POST /api/milestones/context/<context_id>/analyze
```

### Generate Milestone Summary
```http
POST /api/milestones/<milestone_id>/context/summarize
```

### Create Tasks from Context
```http
POST /api/milestones/context/<context_id>/create-tasks
```

### Remove Context Object
```http
DELETE /api/milestones/context/<context_id>/remove
```

## Usage Examples

### Example 1: Adding a Meeting Transcript

```python
import requests

# Add transcript to milestone
response = requests.post(
    'http://localhost:8000/api/milestones/<milestone-id>/context/add',
    json={
        'type': 'transcript',
        'title': 'Jour Fixe KW42',
        'content': 'Discussed automation features for IdeaGraph...',
        'auto_analyze': True
    },
    headers={'Authorization': 'Bearer <token>'}
)

result = response.json()
# {
#   'success': True,
#   'context_object_id': 'uuid',
#   'analysis': {
#     'summary': 'Meeting about automation...',
#     'derived_tasks': [
#       {'title': 'Implement auto-tagging', 'description': '...'},
#       ...
#     ]
#   }
# }
```

### Example 2: Creating Tasks from Derived Tasks

```python
# Create actual Task objects from derived tasks
response = requests.post(
    f'http://localhost:8000/api/milestones/context/{context_id}/create-tasks',
    headers={'Authorization': 'Bearer <token>'}
)

result = response.json()
# {
#   'success': True,
#   'tasks_created': 3,
#   'tasks': [
#     {'id': 'task-uuid-1', 'title': 'Task 1'},
#     ...
#   ]
# }
```

## UI Features

### Milestone Form
- Name and description fields
- Due date picker
- Status dropdown (Planned, In Progress, Completed)

### Item Detail View - Milestones Tab
- Accordion view for each milestone
- Shows milestone status badge
- Displays context objects with icons
- Shows AI summaries
- Lists associated tasks
- Edit/delete actions

### Context Object Display
- Type indicator icons
- Analysis status badge
- Summary preview
- Number of derived tasks
- Creation date

## Database Schema

### Milestone Table Extensions
```sql
-- New fields added to existing Milestone table
description TEXT DEFAULT '',
status VARCHAR(20) DEFAULT 'planned',
summary TEXT DEFAULT '',
weaviate_id UUID NULL
```

### MilestoneContextObject Table
```sql
CREATE TABLE milestone_context_object (
    id UUID PRIMARY KEY,
    milestone_id UUID REFERENCES milestone(id),
    type VARCHAR(20),  -- file, email, transcript, note
    title VARCHAR(255),
    source_id VARCHAR(255),
    url VARCHAR(1000),
    content TEXT,
    summary TEXT,
    tags JSONB DEFAULT '[]',
    derived_tasks JSONB DEFAULT '[]',
    analyzed BOOLEAN DEFAULT FALSE,
    uploaded_by_id UUID REFERENCES user(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

## Service Layer

### MilestoneKnowledgeService

Key methods:
- `add_context_object()`: Add and optionally analyze context
- `analyze_context_object()`: Run AI analysis on context
- `generate_milestone_summary()`: Create overall milestone summary
- `create_tasks_from_context()`: Convert derived tasks to actual tasks
- `sync_to_weaviate()`: Sync to vector database

## Testing

Comprehensive test suite includes:
- Model creation and relationships
- Context object lifecycle
- AI analysis mocking
- API endpoint testing
- Permission and authentication checks

Run tests:
```bash
python manage.py test main.test_milestones main.test_milestone_knowledge_hub
```

## Security

- All API endpoints require authentication
- Permission checks verify user owns the milestone's item or is admin
- Stack trace exposure prevented in error responses
- CodeQL security scan: 0 vulnerabilities

## Future Enhancements

Potential improvements:
1. **Weaviate Integration**: Full vector search implementation
2. **File Upload**: Direct file upload for context objects
3. **Email Integration**: Automatic email import from Outlook/Graph API
4. **Batch Operations**: Analyze multiple contexts at once
5. **Context Templates**: Predefined templates for common scenarios
6. **Version History**: Track changes to context objects
7. **Collaborative Features**: Multiple users can contribute context

## Related Documentation

- [KiGate API Integration](KI_FUNCTIONS_IMPLEMENTATION.md)
- [Weaviate Integration](WEAVIATE_MIGRATION_SUMMARY.md)
- [API Documentation](README.md)

## Support

For issues or questions:
1. Check existing tests for usage examples
2. Review API endpoint documentation
3. Consult service layer code for business logic details
