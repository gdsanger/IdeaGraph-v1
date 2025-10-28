# GitHub Issues KnowledgeObject Migration

## Summary

This document describes the migration from the old ChromaDB-based GitHub Issues storage to the unified Weaviate KnowledgeObject schema.

## Problem Statement

**Issue**: GitHub issues were being stored in a separate ChromaDB collection called `GitHubIssues` instead of the unified Weaviate `KnowledgeObject` collection that is used for all other object types (Items, Tasks, Milestones, etc.).

**Translation of Original Issue** (German):
> Wir benutzen nur das Objekt KnowledgeObject, sonst nichts. Es ist wichtig dass alle Informationen in diesem Objekt gespeichert werden. Ich habe gesehen dass GitHubIssues nicht darin gespeichert werden sondern im Objekt GitHubIssues. Das muss umgestellt werden.

Translation:
> We only use the KnowledgeObject, nothing else. It is important that all information is stored in this object. I saw that GitHubIssues are not stored in it but in a GitHubIssues object. This must be changed.

## Changes Made

### 1. Removed Old ChromaDB Service

**Deleted File**: `core/services/github_issue_sync_service.py`
- This service used ChromaDB with a separate `GitHubIssues` collection
- It was an older implementation that didn't align with the unified KnowledgeObject architecture

### 2. Updated Weaviate GitHub Issue Sync Service

**Modified File**: `core/services/weaviate_github_issue_sync_service.py`

Added the `owner` field to align with other KnowledgeObject types:

```python
# Extract owner from GitHub user data
issue_user = issue.get('user', {})
issue_owner = issue_user.get('login', '') if issue_user else ''

properties = {
    'type': 'GitHubIssue',
    'title': issue_title,
    'description': issue_body or '',  # Content stored in description field
    'status': issue_state,
    'owner': issue_owner,  # NEW: Added owner field
    'createdAt': created_at,
    'githubIssueId': issue_number,
    'url': issue_url,
    'tags': [],
}

# Add itemId if linked to an item (requirement from issue)
if item:
    properties['itemId'] = str(item.id)

# Add taskId if linked to a task
if task:
    properties['taskId'] = str(task.id)
```

The same changes were applied to the `sync_pull_request_to_weaviate` method.

### 3. Updated Tests

**Modified File**: `main/test_weaviate_github_issue_sync_upsert.py`
- Updated test data to include the `user` field with `login` property
- Tests now properly validate the extraction of the `owner` field

**Deleted File**: `main/test_github_issue_sync.py`
- Removed tests for the old ChromaDB service as it no longer exists

## KnowledgeObject Schema for GitHub Issues

GitHub Issues are now stored in the `KnowledgeObject` collection with the following properties:

| Property | Type | Description | Required |
|----------|------|-------------|----------|
| `type` | string | Always "GitHubIssue" | Yes |
| `title` | string | Issue/PR title | Yes |
| `description` | string | Issue/PR body content | Yes |
| `status` | string | Issue state (open/closed) | Yes |
| `owner` | string | GitHub username of issue creator | Yes |
| `createdAt` | string | ISO timestamp of creation | Yes |
| `githubIssueId` | integer | GitHub issue number | Yes |
| `url` | string | URL to the GitHub issue | Yes |
| `tags` | array | Tag names (empty for GitHub issues) | Yes |
| `itemId` | string | UUID of linked Item (if any) | Optional |
| `taskId` | string | UUID of linked Task (if any) | Optional |

## Benefits

1. **Unified Storage**: All knowledge objects (Items, Tasks, GitHub Issues, Milestones, etc.) are now stored in a single KnowledgeObject collection
2. **Better Semantic Search**: GitHub Issues can now be found alongside other knowledge objects in semantic searches
3. **Consistent Schema**: All objects follow the same property structure, making queries and integrations simpler
4. **Proper Relationships**: GitHub Issues maintain proper relationships to Items and Tasks through `itemId` and `taskId` fields

## Migration Notes

### For Existing Deployments

If you have existing GitHub Issues stored in the old ChromaDB collection:

1. The old `GitHubIssues` collection in ChromaDB is no longer used
2. Re-run the GitHub sync to populate Weaviate with existing issues:
   ```bash
   python sync_github_issues.py
   ```
3. The sync service will automatically use the new Weaviate-based implementation

### Code That Uses GitHub Issue Sync

The following code already uses the correct service:
- `sync_github_issues.py` - CLI script for syncing
- `core/services/github_task_sync_service.py` - Task synchronization
- All existing views and controllers

No changes needed in consuming code.

## Technical Details

### Service Location
- **Active Service**: `core/services/weaviate_github_issue_sync_service.py`
- **Collection**: `KnowledgeObject` in Weaviate
- **Type Identifier**: `type='GitHubIssue'`

### How to Use

```python
from core.services import WeaviateGitHubIssueSyncService

# Initialize service
service = WeaviateGitHubIssueSyncService()

# Sync a GitHub issue
issue = {
    'number': 123,
    'title': 'Fix bug',
    'body': 'Bug description',
    'state': 'open',
    'html_url': 'https://github.com/owner/repo/issues/123',
    'created_at': '2025-10-28T10:00:00Z',
    'user': {'login': 'developer'}
}

result = service.sync_issue_to_weaviate(issue, task=task_obj, item=item_obj)
```

## Compliance with Requirements

✅ **All information stored in KnowledgeObject**: GitHub Issues now use the `KnowledgeObject` collection

✅ **Descriptions/Content in description field**: GitHub issue body is stored in the `description` property

✅ **ItemID populated when linked**: When a GitHub issue is linked to an Item, the `itemId` field is populated with the Item's UUID

✅ **Owner field added**: GitHub issue creator is stored in the `owner` field (GitHub user's login)

✅ **Consistent schema**: Follows the same property structure as Items and Tasks

## See Also

- [KNOWLEDGEOBJECT_SCHEMA_MIGRATION.md](./KNOWLEDGEOBJECT_SCHEMA_MIGRATION.md) - Original KnowledgeObject schema migration
- [WEAVIATE_MILESTONES_FIX_SUMMARY.md](./WEAVIATE_MILESTONES_FIX_SUMMARY.md) - Similar fix for Milestones
- [SEMANTIC_NETWORK_KNOWLEDGEOBJECT_FIX.md](./SEMANTIC_NETWORK_KNOWLEDGEOBJECT_FIX.md) - Semantic network integration
