# Weaviate Synchronization for Items, Tasks, and GitHub Issues

## Overview

This document describes the Weaviate synchronization feature that automatically keeps Items, Tasks, GitHub Issues, and Tags synchronized with a Weaviate vector database for semantic search and similarity analysis.

## Architecture

### Components

1. **WeaviateItemSyncService** (`core/services/weaviate_sync_service.py`)
   - Main service class for handling Weaviate synchronization of Items
   - Implements sync_create, sync_update, sync_delete, and search_similar methods

2. **WeaviateTaskSyncService** (`core/services/weaviate_task_sync_service.py`)
   - Service class for handling Weaviate synchronization of Tasks
   - Implements sync_create, sync_update, sync_delete, and search_similar methods

3. **WeaviateGitHubIssueSyncService** (`core/services/weaviate_github_issue_sync_service.py`)
   - Service class for handling Weaviate synchronization of GitHub Issues/PRs
   - Implements sync_issue_to_weaviate, sync_pull_request_to_weaviate, delete_issue, and search_similar_issues methods

4. **WeaviateTagSyncService** (`core/services/weaviate_tag_sync_service.py`)
   - Service class for handling Weaviate synchronization of Tags
   - Implements sync_create, sync_update, sync_delete, sync_all_tags, and search_similar methods

5. **View Integration** (`main/views.py`)
   - Item and Task CRUD operations automatically trigger Weaviate sync
   - Integrated into: `item_create`, `item_edit`, `item_delete`, `task_create`, `task_edit`, `task_delete` views
   - Gracefully handles sync failures without blocking operations

6. **API Integration** (`main/api_views.py`)
   - API endpoints for item and task operations trigger Weaviate sync
   - Similarity search endpoints use Weaviate for semantic search

7. **Management Command** (`main/management/commands/sync_tags_to_weaviate.py`)
   - CLI command to sync all tags to Weaviate
   - Can be run as a cron job for automatic synchronization
   - Usage: `python manage.py sync_tags_to_weaviate`

## Weaviate Configuration

### Connection Details

- **Host**: `localhost`
- **Port**: `8081`
- **Authentication**: None (local instance)

### Schema

The Weaviate schema is pre-configured and includes the following collections:

#### Tag Collection
```json
{
  "class": "Tag",
  "description": "Tags aus Entität Tags",
  "vectorizer": "text2vec-transformers",
  "properties": [
    { "name": "name", "dataType": ["string"] },
    { "name": "description", "dataType": ["text"] }
  ]
}
```

#### Item Collection
```json
{
  "class": "Item",
  "description": "Wissensitem, Projekt, Themengebiet",
  "vectorizer": "text2vec-transformers",
  "properties": [
    { "name": "title", "dataType": ["text"] },
    { "name": "description", "dataType": ["text"] },
    { "name": "section", "dataType": ["string"] },
    { "name": "owner", "dataType": ["string"] },
    { "name": "tagRefs", "dataType": ["Tag"] },
    { "name": "status", "dataType": ["string"] },
    { "name": "createdAt", "dataType": ["date"] }
  ]
}
```

#### Task Collection
```json
{
  "class": "Task",
  "description": "Konkrete Aufgabe, die zu einem Item gehört",
  "vectorizer": "text2vec-transformers",
  "properties": [
    { "name": "title", "dataType": ["text"] },
    { "name": "description", "dataType": ["text"] },
    { "name": "status", "dataType": ["string"] },
    { "name": "owner", "dataType": ["string"] },
    { "name": "item", "dataType": ["Item"] },
    { "name": "tagRefs", "dataType": ["Tag"] },
    { "name": "createdAt", "dataType": ["date"] },
    { "name": "githubIssue", "dataType": ["GitHubIssue"] }
  ]
}
```

#### GitHubIssue Collection
```json
{
  "class": "GitHubIssue",
  "description": "Synchronisierter GitHub-Issue (optional)",
  "vectorizer": "text2vec-transformers",
  "properties": [
    { "name": "issue_title", "dataType": ["text"] },
    { "name": "issue_description", "dataType": ["text"] },
    { "name": "issue_state", "dataType": ["string"] },
    { "name": "issue_url", "dataType": ["string"] },
    { "name": "issue_number", "dataType": ["int"] },
    { "name": "task", "dataType": ["Task"] },
    { "name": "item", "dataType": ["Item"] },
    { "name": "createdAt", "dataType": ["date"] }
  ]
}
```

## Embedding Strategy

Weaviate uses **text2vec-transformers** for automatic vectorization. This means:

1. **No OpenAI API required**: Embeddings are generated locally by Weaviate
2. **Automatic vectorization**: All text fields are automatically vectorized
3. **Consistent embeddings**: Same text always produces same vector
4. **Language support**: Supports multiple languages including German

The `text2vec-transformers` vectorizer automatically processes:
- Item titles and descriptions
- Task titles and descriptions
- Tag names and descriptions
- GitHub issue titles and descriptions

## Usage

### Automatic Synchronization

Weaviate sync happens automatically during Item and Task operations:

```python
# Creating an item
item = Item.objects.create(
    title="My Item",
    description="Description text for embedding",
    created_by=user
)
# Weaviate sync_create is called automatically

# Updating an item
item.description = "Updated description"
item.save()
# Weaviate sync_update is called automatically

# Deleting an item
item.delete()
# Weaviate sync_delete is called automatically
```

### Manual Sync

You can also manually sync items, tasks, or tags:

```python
from core.services.weaviate_sync_service import WeaviateItemSyncService
from core.services.weaviate_task_sync_service import WeaviateTaskSyncService
from core.services.weaviate_tag_sync_service import WeaviateTagSyncService

# Sync an item
item_service = WeaviateItemSyncService()
result = item_service.sync_create(item)
item_service.close()

# Sync a task
task_service = WeaviateTaskSyncService()
result = task_service.sync_update(task)
task_service.close()

# Sync all tags
tag_service = WeaviateTagSyncService()
result = tag_service.sync_all_tags()
tag_service.close()
```

### Tag Synchronization

Tags can be synchronized using the management command:

```bash
# Sync all tags
python manage.py sync_tags_to_weaviate

# Sync a specific tag
python manage.py sync_tags_to_weaviate --tag-id <UUID>

# Verbose output
python manage.py sync_tags_to_weaviate --verbose
```

### Cron Job Setup

To automatically sync tags on a schedule, add a cron job:

```bash
# Edit crontab
crontab -e

# Add this line to sync tags every hour
0 * * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_tags_to_weaviate >> /var/log/tag_sync.log 2>&1
```

### Similarity Search

Search for similar items, tasks, or tags using semantic similarity:

```python
from core.services.weaviate_sync_service import WeaviateItemSyncService

service = WeaviateItemSyncService()
results = service.search_similar(
    query_text="description of what to search",
    n_results=5
)

for item in results['results']:
    print(f"Item {item['id']}: {item['metadata']['title']}")
    print(f"Distance: {item['distance']}")

service.close()
```

## UUID Management

**Important**: We always use our internal UUIDs as IDs in Weaviate. This ensures:

1. Consistency between our database and Weaviate
2. Easy mapping of Weaviate results to our database records
3. No duplicate entries when re-syncing

When creating objects in Weaviate:
```python
collection.data.insert(
    properties=properties,
    uuid=str(object.id)  # Always use our internal UUID
)
```

## Error Handling

The synchronization is designed to be **non-blocking**:

- If Weaviate sync fails, the Item/Task operation still succeeds
- Errors are logged as warnings
- Connection issues are handled gracefully
- This ensures the application remains functional even if Weaviate is unavailable

Example from logs:
```
Weaviate sync failed for item <uuid>: <error message>
```

## Testing

### Unit Tests
Run Weaviate service unit tests:
```bash
python manage.py test main.test_weaviate_sync_service
python manage.py test main.test_weaviate_task_sync_service
```

### Integration Tests
Run end-to-end integration tests:
```bash
python manage.py test main.test_weaviate_integration
python manage.py test main.test_weaviate_task_integration
```

### All Tests
Run all Weaviate-related tests:
```bash
python manage.py test main.test_weaviate*
```

## Security

- No authentication required for local Weaviate instance
- Connection to localhost:8081 only
- No API keys or credentials stored
- Internal UUIDs protect data integrity
- No security vulnerabilities detected by CodeQL analysis

## Dependencies

```
weaviate-client>=4.9.0
```

Added to `requirements.txt` and verified for security vulnerabilities.

## Performance Considerations

1. **Vectorization**: Handled automatically by Weaviate's text2vec-transformers
2. **Batch Operations**: Consider implementing batch sync for bulk operations
3. **Async Processing**: Current implementation is synchronous; consider async for production
4. **Connection Pooling**: Weaviate client manages connections efficiently

## Migration from ChromaDB

This system replaces the previous ChromaDB implementation. Key differences:

1. **No OpenAI dependency**: Weaviate uses text2vec-transformers locally
2. **Better schema support**: Native support for cross-references between collections
3. **Local vectorization**: No external API calls for embeddings
4. **Consistent UUIDs**: Always use internal UUIDs for consistency

## Future Enhancements

- [ ] Batch synchronization API
- [ ] Async synchronization using Celery
- [ ] Automatic similarity detection on item/task creation
- [ ] UI for viewing similar items/tasks
- [ ] Periodic re-sync of all items/tasks
- [ ] Advanced filtering and search options

## Troubleshooting

### Weaviate Not Running
- Check if Weaviate is running: `curl http://localhost:8081/v1/.well-known/ready`
- Start Weaviate if needed
- Check logs for connection errors

### Items Not Syncing
- Check application logs for sync warnings
- Verify Weaviate collections exist
- Test manual sync with service classes

### Search Not Working
- Verify vectorization is enabled
- Check if items/tasks have been synced
- Review Weaviate logs for errors

## Example Use Cases

### Finding Similar Items
```python
# After creating several items, find similar ones
service = WeaviateItemSyncService()
similar = service.search_similar(
    "web application with user authentication",
    n_results=5
)
service.close()
```

### Semantic Search Across Tasks
```python
# Search across all tasks semantically
service = WeaviateTaskSyncService()
results = service.search_similar(
    query_text=user_search_query,
    n_results=10
)
service.close()
```

### Content Recommendation
```python
# Recommend related items based on current item
current_item = Item.objects.get(id=item_id)
service = WeaviateItemSyncService()
recommendations = service.search_similar(
    current_item.description,
    n_results=3
)
service.close()
```
