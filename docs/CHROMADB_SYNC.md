# ChromaDB Synchronization for Items

## Overview

This document describes the ChromaDB synchronization feature that automatically keeps Items synchronized with a ChromaDB vector database for semantic search and similarity analysis.

## Architecture

### Components

1. **ChromaItemSyncService** (`core/services/chroma_sync_service.py`)
   - Main service class for handling ChromaDB synchronization
   - Located in: `core/services/chroma_sync_service.py`
   - Implements sync_create, sync_update, and sync_delete methods

2. **View Integration** (`main/views.py`)
   - Item CRUD operations automatically trigger ChromaDB sync
   - Integrated into: `item_create`, `item_edit`, `item_delete` views
   - Gracefully handles sync failures without blocking item operations

### Data Storage

#### Embedding
- **Source**: Item `description` field
- **Method**: OpenAI text-embedding-ada-002 model
- **Dimension**: 1536-dimensional vector
- **Fallback**: Zero vector if API is unavailable

#### Metadata
The following Item fields are stored as metadata in ChromaDB:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique item identifier (primary key) |
| `title` | String | Item title |
| `section` | UUID | Section ID reference |
| `section_name` | String | Section name for display |
| `tags` | String | Comma-separated tag names |
| `status` | String | Item status (new, working, done, etc.) |
| `owner` | UUID | Creator's user ID |
| `owner_username` | String | Creator's username |
| `created_at` | DateTime | Creation timestamp (ISO format) |
| `updated_at` | DateTime | Last update timestamp (ISO format) |

## Configuration

### Settings Model

ChromaDB sync requires configuration in the Settings model:

```python
# OpenAI API (for embeddings)
openai_api_enabled = True
openai_api_key = "your-api-key"
openai_api_base_url = "https://api.openai.com/v1"

# ChromaDB (optional cloud configuration)
chroma_api_key = ""        # For cloud deployment
chroma_database = ""       # For cloud deployment  
chroma_tenant = ""         # For cloud deployment
```

### Local vs. Cloud

- **Local Mode**: If ChromaDB cloud settings are empty, uses `PersistentClient` with local storage at `./chroma_db/`
- **Cloud Mode**: If cloud settings are provided, connects to ChromaDB cloud instance

## Usage

### Automatic Synchronization

ChromaDB sync happens automatically during Item operations:

```python
# Creating an item
item = Item.objects.create(
    title="My Item",
    description="Description text for embedding",
    created_by=user
)
# ChromaDB sync_create is called automatically

# Updating an item
item.description = "Updated description"
item.save()
# ChromaDB sync_update is called automatically

# Deleting an item
item.delete()
# ChromaDB sync_delete is called automatically
```

### Manual Sync

You can also manually sync items:

```python
from core.services.chroma_sync_service import ChromaItemSyncService

service = ChromaItemSyncService()

# Sync a new item
result = service.sync_create(item)

# Update an existing item
result = service.sync_update(item)

# Delete an item from ChromaDB
result = service.sync_delete(item_id)
```

### Similarity Search

Search for similar items using semantic similarity:

```python
from core.services.chroma_sync_service import ChromaItemSyncService

service = ChromaItemSyncService()
results = service.search_similar(
    query_text="description of what to search",
    n_results=5
)

for item in results['results']:
    print(f"Item {item['id']}: {item['metadata']['title']}")
    print(f"Distance: {item['distance']}")
```

## Error Handling

The synchronization is designed to be **non-blocking**:

- If ChromaDB sync fails, the Item operation still succeeds
- Errors are logged as warnings
- Zero vectors are used if embedding generation fails
- This ensures the application remains functional even if ChromaDB is unavailable

Example from logs:
```
ChromaDB sync failed for item <uuid>: <error message>
```

## Testing

### Unit Tests
Run ChromaItemSyncService unit tests:
```bash
python manage.py test main.test_chroma_sync_service
```

### Integration Tests
Run end-to-end integration tests:
```bash
python manage.py test main.test_chroma_integration
```

### All Item Tests
Run all Item-related tests including sync:
```bash
python manage.py test main.test_items main.test_chroma_sync_service main.test_chroma_integration
```

## Security

- API keys are stored in the Settings model (admin access only)
- No security vulnerabilities detected by CodeQL analysis
- ChromaDB local storage directory (`chroma_db/`) is gitignored
- Embedding generation is isolated and error-handled

## Dependencies

```
chromadb>=0.4.0
```

Added to `requirements.txt` and verified for security vulnerabilities.

## Collection Details

- **Collection Name**: `items`
- **Primary Key**: `id` (Item UUID)
- **Indexed Fields**: id, tags, section, status, owner

## Performance Considerations

1. **Embedding Generation**: Each create/update triggers an OpenAI API call (if enabled)
2. **Batch Operations**: Consider implementing batch sync for bulk operations
3. **Async Processing**: Current implementation is synchronous; consider async for production
4. **Caching**: Zero vectors are used as fallback to maintain performance

## Future Enhancements

- [ ] Batch synchronization API
- [ ] Async embedding generation using Celery
- [ ] Automatic similarity detection on item creation
- [ ] UI for viewing similar items
- [ ] Embedding model selection in settings
- [ ] Periodic re-sync of all items

## Troubleshooting

### ChromaDB Not Initializing
- Check Settings model configuration
- Verify ChromaDB installation: `pip show chromadb`
- Check logs for initialization errors

### Embeddings Not Generated
- Verify OpenAI API key in Settings
- Check `openai_api_enabled` is True
- Review API usage/quota on OpenAI dashboard

### Items Not Syncing
- Check application logs for sync warnings
- Verify ChromaDB collection exists
- Test manual sync with ChromaItemSyncService

## Example Use Cases

### Finding Similar Items
```python
# After creating several items, find similar ones
service = ChromaItemSyncService()
similar = service.search_similar(
    "web application with user authentication",
    n_results=5
)
```

### Semantic Search
```python
# Search across all items semantically
results = service.search_similar(
    query_text=user_search_query,
    n_results=10
)
```

### Content Recommendation
```python
# Recommend related items based on current item
current_item = Item.objects.get(id=item_id)
recommendations = service.search_similar(
    current_item.description,
    n_results=3
)
```
