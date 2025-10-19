# Task ChromaDB Synchronization

## Overview

This document describes the implementation of automatic synchronization between Tasks and ChromaDB vector database in the IdeaGraph application.

## Purpose

Tasks are automatically synchronized with ChromaDB to enable semantic similarity search and AI-powered task recommendations. The task description is vectorized using OpenAI embeddings, while metadata is stored for filtering and retrieval.

## Implementation

### ChromaTaskSyncService

Located in `core/services/chroma_task_sync_service.py`, this service handles all ChromaDB operations for tasks.

#### Features

- **Automatic Synchronization**: Tasks are synced on create, update, and delete
- **Embedding Generation**: Task descriptions are vectorized using OpenAI's text-embedding-ada-002 model
- **Metadata Storage**: Task metadata is stored alongside embeddings
- **Error Handling**: Graceful error handling ensures task operations succeed even if ChromaDB sync fails
- **Cloud & Local Support**: Supports both cloud-hosted and local ChromaDB instances

#### Collection Structure

**Collection Name**: `tasks`

**Embedding Source**: Task description field

**Metadata Fields**:
- `id` (UUID) - Unique task identifier
- `title` (String) - Task title
- `item_id` (UUID) - Associated item identifier
- `status` (String) - Task status (new, working, review, ready, done)
- `github_issue_id` (Integer) - GitHub issue ID if linked
- `owner` (UUID) - Task creator's user ID
- `owner_username` (String) - Task creator's username
- `created_at` (ISO 8601) - Creation timestamp
- `updated_at` (ISO 8601) - Last update timestamp

### Integration Points

The synchronization is integrated at three key API endpoints:

1. **Task Creation** (`POST /api/tasks/{item_id}`)
   - Calls `sync_create()` after successful task creation
   - Generates embedding from description
   - Stores task in ChromaDB

2. **Task Update** (`PUT /api/tasks/{task_id}/detail`)
   - Calls `sync_update()` after successful task update
   - Regenerates embedding if description changed
   - Updates metadata in ChromaDB

3. **Task Delete** (`DELETE /api/tasks/{task_id}/detail`)
   - Calls `sync_delete()` after successful task deletion
   - Removes task from ChromaDB

### Error Handling

The synchronization is designed to be non-blocking:
- If ChromaDB is unavailable, task operations still succeed
- Errors are logged but don't interrupt the main operation
- Warnings are emitted for sync failures to aid debugging

### Configuration

ChromaDB synchronization uses the following settings from the `Settings` model:

**OpenAI Configuration** (for embeddings):
- `openai_api_enabled` - Enable/disable OpenAI API
- `openai_api_key` - OpenAI API key
- `openai_api_base_url` - OpenAI API endpoint

**ChromaDB Configuration**:
- `chroma_api_key` - ChromaDB cloud API key (optional)
- `chroma_database` - ChromaDB cloud database URL (optional)
- `chroma_tenant` - ChromaDB cloud tenant (optional)

If cloud settings are not provided, a local persistent ChromaDB instance is used at `./chroma_db`.

## Usage Examples

### Creating a Task with Sync

```python
from main.models import Task
from core.services.chroma_task_sync_service import ChromaTaskSyncService

# Create task
task = Task.objects.create(
    title="Implement feature X",
    description="Add new feature X to the system",
    status="new",
    item=item,
    created_by=user
)

# Sync to ChromaDB
service = ChromaTaskSyncService()
result = service.sync_create(task)
# Returns: {'success': True, 'message': 'Task ... synced to ChromaDB'}
```

### Searching for Similar Tasks

```python
from core.services.chroma_task_sync_service import ChromaTaskSyncService

service = ChromaTaskSyncService()
results = service.search_similar(
    "implement authentication system",
    n_results=5
)

for result in results['results']:
    print(f"Similar task: {result['metadata']['title']}")
    print(f"Distance: {result['distance']}")
```

## Testing

Comprehensive tests are provided in:

1. **`main/test_chroma_task_sync_service.py`**
   - Unit tests for ChromaTaskSyncService
   - Tests for initialization, embedding generation, metadata conversion
   - Tests for sync_create, sync_update, sync_delete operations
   - Error handling tests

2. **`main/test_task_chroma_integration.py`**
   - Integration tests for API endpoints
   - Tests sync behavior on task CRUD operations
   - Tests graceful error handling
   - Tests behavior without settings

All tests pass successfully (47 tests total for task synchronization).

## Performance Considerations

- **Embedding Generation**: Each task create/update makes an API call to OpenAI
- **Async Recommendation**: Consider moving sync operations to background tasks for better performance
- **Caching**: Embeddings could be cached if descriptions don't change frequently

## Future Enhancements

1. **Background Processing**: Move sync operations to Celery tasks
2. **Batch Operations**: Support batch sync for multiple tasks
3. **Similarity API**: Add API endpoint for task similarity search
4. **Smart Recommendations**: Use similarity search for task recommendations
5. **Partial Updates**: Only regenerate embeddings when description changes

## Related Documentation

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Item ChromaDB Sync](./ITEM_CHROMADB_SYNC.md) - Similar implementation for Items
