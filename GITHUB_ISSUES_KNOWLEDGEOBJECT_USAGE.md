# GitHub Issues in KnowledgeObject Architecture

## Overview

This document clarifies how GitHub Issues and Pull Requests are stored in IdeaGraph's unified KnowledgeObject architecture.

## ✅ Correct Implementation: WeaviateGitHubIssueSyncService

**File:** `core/services/weaviate_github_issue_sync_service.py`

**Status:** ✅ ACTIVE - Used in production

### Architecture Compliance

This service correctly implements the KnowledgeObject architecture requirements:

1. **Single Collection:** All GitHub Issues stored in `KnowledgeObject` collection
2. **Type Discrimination:** Each issue has `type='GitHubIssue'` property
3. **Description Field:** Issue body/content stored in `description` field
4. **Item Linking:** When issue is linked to an Item, `itemId` is automatically populated
5. **Task Linking:** When issue is linked to a Task, `taskId` is automatically populated

### Usage Example

```python
from core.services.weaviate_github_issue_sync_service import WeaviateGitHubIssueSyncService

# Initialize service
service = WeaviateGitHubIssueSyncService()

# Sync issue with task and item linkage
service.sync_issue_to_weaviate(
    issue=github_issue_data,
    task=task_instance,      # Optional: Links issue to task
    item=item_instance       # Optional: Links issue to item (populates itemId)
)

# Close connection
service.close()
```

### Production Usage

- **Script:** `sync_github_issues.py` - Production GitHub sync script
- **Service:** `github_task_sync_service.py` - Uses Weaviate service for issue sync
- **API Views:** `main/api_views.py` - Similarity search endpoints

## ❌ Deprecated: GitHubIssueSyncService (ChromaDB)

**File:** `core/services/github_issue_sync_service.py`

**Status:** ⚠️ DEPRECATED - Legacy code kept for reference only

### Why Deprecated

This service violates the KnowledgeObject architecture:

1. **Separate Collection:** Uses `GitHubIssues` collection instead of `KnowledgeObject`
2. **ChromaDB:** Uses ChromaDB instead of Weaviate
3. **Not Exported:** Removed from `core/services/__init__.py`
4. **Not Used:** No production code imports this service

### Migration

The system migrated from ChromaDB to Weaviate. See:
- `CHROMADB_TO_WEAVIATE_MIGRATION.md` - Migration documentation
- `KNOWLEDGEOBJECT_SCHEMA_MIGRATION.md` - Schema changes

## KnowledgeObject Schema for GitHub Issues

### Properties

| Property | Type | Description | Required |
|----------|------|-------------|----------|
| `type` | string | Always 'GitHubIssue' for issues/PRs | ✅ |
| `title` | string | Issue title | ✅ |
| `description` | string | Issue body/content | ✅ |
| `status` | string | Issue state (open/closed) | ✅ |
| `createdAt` | date | Issue creation timestamp | ✅ |
| `githubIssueId` | integer | GitHub issue number | ✅ |
| `url` | string | GitHub issue URL | ✅ |
| `tags` | string[] | Tags (empty for GitHub issues) | ✅ |
| `taskId` | string | UUID of linked Task | Optional |
| `itemId` | string | UUID of linked Item | Optional |

### Example Object

```json
{
  "type": "GitHubIssue",
  "title": "Fix login bug",
  "description": "Users cannot login after password reset...",
  "status": "open",
  "createdAt": "2024-01-15T10:30:00Z",
  "githubIssueId": 123,
  "url": "https://github.com/org/repo/issues/123",
  "tags": [],
  "taskId": "550e8400-e29b-41d4-a716-446655440000",
  "itemId": "660e8400-e29b-41d4-a716-446655440001"
}
```

## Architecture Benefits

### Why Single KnowledgeObject Collection?

1. **Unified Search:** Semantic search across all knowledge types (Items, Tasks, Issues, etc.)
2. **Complete Context:** Get all related information in one query
3. **Better Similarities:** More accurate similarity matching across all content
4. **Simplified Schema:** One schema to maintain instead of multiple collections
5. **Consistent API:** Same query interface for all knowledge types

### Type Discrimination

The `type` property allows querying specific knowledge types:

```python
# Query only GitHub Issues
collection.query.hybrid(
    query=search_text,
    filters=Filter.by_property("type").equal("GitHubIssue")
)

# Query across all types (Items, Tasks, Issues, etc.)
collection.query.hybrid(query=search_text)
```

## Testing

### Syntax Validation

```bash
python -m py_compile core/services/weaviate_github_issue_sync_service.py
```

### Integration Tests

```bash
# Run Weaviate integration tests
python manage.py test main.test_weaviate_github_issue_sync_upsert
```

### Manual Testing

```bash
# Run GitHub sync script
python sync_github_issues.py --verbose
```

## Troubleshooting

### Issue: "GitHub Issues stored in wrong collection"

**Symptom:** Confusion about where GitHub Issues are stored

**Solution:** 
- Verify you're looking at `WeaviateGitHubIssueSyncService`, not the deprecated `GitHubIssueSyncService`
- Check that production code imports from `core.services.weaviate_github_issue_sync_service`
- Confirm Weaviate is configured and running

### Issue: "itemId not populated"

**Symptom:** GitHub Issues don't have itemId property

**Cause:** Issue not linked to an Item when synced

**Solution:**
```python
# Always pass item parameter when syncing
service.sync_issue_to_weaviate(
    issue=github_data,
    task=task,
    item=task.item  # ✅ Ensures itemId is populated
)
```

## References

- **KnowledgeObject Schema:** `KNOWLEDGEOBJECT_SCHEMA_MIGRATION.md`
- **Migration Guide:** `CHROMADB_TO_WEAVIATE_MIGRATION.md`
- **Weaviate Service:** `core/services/weaviate_github_issue_sync_service.py`
- **Sync Script:** `sync_github_issues.py`
- **Django Models:** `main/models.py`

## Conclusion

✅ GitHub Issues are correctly stored in the KnowledgeObject collection using `WeaviateGitHubIssueSyncService`

✅ All architecture requirements are met:
- Single collection (KnowledgeObject)
- Type discrimination (type='GitHubIssue')
- Content in description field
- Automatic itemId population when linked to Item

⚠️ Legacy ChromaDB service is deprecated and should not be used
