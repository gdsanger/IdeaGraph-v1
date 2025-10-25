# KnowledgeObject Schema Migration - Implementation Summary

## Overview

This document summarizes the implementation of the unified "KnowledgeObject" schema in Weaviate, replacing the separate Item, Task, and GitHubIssue collections. This schema also includes Milestones and context objects (Mails, Notes, Files, Transcripts) to ensure complete and accurate semantic similarity matching.

## Changes Made

### 1. Service Updates

All Weaviate synchronization services now use the unified `KnowledgeObject` collection:

#### WeaviateItemSyncService (`core/services/weaviate_sync_service.py`)
- **Collection Name**: Changed from `'Item'` to `'KnowledgeObject'`
- **Properties Mapping**:
  - Added `type: 'Item'` field to identify object type
  - Added `url: '/items/{item.id}/'` for direct link to item
  - Changed `tags` from references to text array (list of tag names)
  - Removed tag reference handling code
  - All other fields mapped directly: `title`, `description`, `section`, `owner`, `status`, `createdAt`
- **Search**: Updated to filter by `type='Item'` when searching for items

#### WeaviateTaskSyncService (`core/services/weaviate_task_sync_service.py`)
- **Collection Name**: Changed from `'Task'` to `'KnowledgeObject'`
- **Properties Mapping**:
  - Added `type: 'Task'` field to identify object type
  - Added `url: '/tasks/{task.id}/'` for direct link to task
  - Added `itemId: str(task.item.id)` when task belongs to an item
  - Added `githubIssueId: task.github_issue_id` when task has a linked GitHub issue
  - Changed `tags` from references to text array (list of tag names)
  - Removed item and tag reference handling code
  - All other fields mapped directly: `title`, `description`, `status`, `owner`, `createdAt`
- **Search**: Updated to filter by `type='Task'` when searching for tasks

#### WeaviateGitHubIssueSyncService (`core/services/weaviate_github_issue_sync_service.py`)
- **Collection Name**: Changed from `'GitHubIssue'` to `'KnowledgeObject'`
- **Properties Mapping**:
  - Added `type: 'GitHubIssue'` field to identify object type
  - Changed property names to match KnowledgeObject schema:
    - `issue_title` → `title`
    - `issue_description` → `description`
    - `issue_state` → `status`
    - `issue_url` → `url`
    - `issue_number` → `githubIssueId`
  - Added `taskId: str(task.id)` when issue is linked to a task
  - Added `itemId: str(item.id)` when issue is linked to an item
  - Added empty `tags: []` array (GitHub issues don't have tags in our system)
  - Removed task and item reference handling code
  - Field `createdAt` mapped directly
- **Search**: Updated to filter by `type='GitHubIssue'` when searching for GitHub issues

#### MilestoneKnowledgeService (`core/services/milestone_knowledge_service.py`)
- **Collection Name**: Uses `'KnowledgeObject'` for both Milestones and context objects
- **Milestone Properties Mapping**:
  - Added `type: 'Milestone'` field to identify object type
  - Added `url: '/milestones/{milestone.id}/'` for direct link to milestone
  - Added `owner` extracted from milestone's item creator
  - Added `tags` extracted from milestone's item tags
  - All other fields: `title`, `description`, `status`, `createdAt`, `itemId`, `dueDate`
- **Context Object Properties Mapping** (Mails, Notes, Files, Transcripts):
  - Added `type` field: `'Email'`, `'Note'`, `'File'`, or `'Transcript'`
  - Added `owner` extracted from context object uploader or milestone's item creator
  - Added `tags` extracted from context object tags or milestone's item tags
  - Added `url` for context object URL
  - All other fields: `title`, `description`, `status` (empty string), `createdAt`, `milestoneId`, `sourceId`

### 2. Key Schema Changes

**Before (Old Schema - Separate Collections)**:
- Separate collections: `Item`, `Task`, `GitHubIssue`
- Milestones and context objects (Mails, Notes, Files, Transcripts) may not have been consistently stored or were missing standard properties
- Tags stored as references (`tagRefs` property pointing to Tag UUIDs)
- Items and Tasks linked through references
- GitHub Issues linked to Tasks/Items through references
- Each collection had its own property schema

**After (New Schema - Unified KnowledgeObject)**:
- Single unified collection: `KnowledgeObject`
- Type discrimination through `type` property: `'Item'`, `'Task'`, `'GitHubIssue'`, `'Milestone'`, `'Email'`, `'Note'`, `'File'`, `'Transcript'`
- Tags stored as text array (list of tag names)
- Items linked to Tasks through `itemId` string property
- Tasks linked to GitHub Issues through `githubIssueId` integer property
- GitHub Issues linked to Tasks through `taskId` string property
- Milestones linked to Items through `itemId` string property
- Context objects linked to Milestones through `milestoneId` string property
- Consistent property names across all object types
- All objects now have standard properties: `type`, `title`, `description`, `owner`, `tags`, `status`, `createdAt`, `url`

### 3. Property Mapping Rules

According to the requirements, properties are filled conditionally based on object type:

| Property | Item | Task | GitHubIssue | Milestone | Email/Note/File/Transcript | Type |
|----------|------|------|-------------|-----------|---------------------------|------|
| `type` | ✓ ('Item') | ✓ ('Task') | ✓ ('GitHubIssue') | ✓ ('Milestone') | ✓ ('Email'/'Note'/'File'/'Transcript') | text |
| `title` | ✓ | ✓ | ✓ | ✓ | ✓ | text |
| `description` | ✓ | ✓ | ✓ | ✓ | ✓ | text |
| `section` | ✓ | - | - | - | - | text |
| `owner` | ✓ | ✓ | - | ✓ (from item) | ✓ (from uploader or item) | text |
| `tags` | ✓ (tag names) | ✓ (tag names) | ✓ (empty array) | ✓ (from item) | ✓ (from object or item) | text[] |
| `status` | ✓ | ✓ | ✓ (issue state) | ✓ | ✓ (empty string) | text |
| `createdAt` | ✓ | ✓ | ✓ | ✓ | ✓ | date |
| `githubIssueId` | - | ✓ (if linked) | ✓ (issue number) | - | - | int |
| `url` | ✓ | ✓ | ✓ | ✓ | ✓ | string |
| `itemId` | - | ✓ (if has item) | ✓ (if linked) | ✓ (if has item) | - | string |
| `taskId` | - | - | ✓ (if linked) | - | - | string |
| `milestoneId` | - | - | - | - | ✓ (if has milestone) | string |
| `dueDate` | - | - | - | ✓ | - | date |
| `sourceId` | - | - | - | - | ✓ (optional) | string |
| `taskId` | - | - | ✓ (if linked) | string |

### 4. Breaking Changes

⚠️ **Important**: These changes require a schema migration in Weaviate:

1. **Schema Creation**: The `KnowledgeObject` collection must be created in Weaviate with the exact schema specified in the issue
2. **Data Migration**: Existing data in `Item`, `Task`, and `GitHubIssue` collections must be migrated to `KnowledgeObject`
3. **Reference Removal**: Tag references are no longer used; tags are stored as text arrays
4. **Item/Task References**: Item and Task relationships are now stored as string IDs, not references

### 5. Test Updates

- Updated `test_weaviate_github_issue_sync_upsert.py` to reflect new schema
- Removed tests for reference handling (`reference_add` calls)
- Added tests for property-based relationships (taskId, itemId in properties)

### 6. Backward Compatibility

⚠️ **No backward compatibility**: This is a breaking change that requires:
- Weaviate schema to be updated/created with the KnowledgeObject collection
- Existing data to be migrated
- Old collections (Item, Task, GitHubIssue) can be removed after migration

## Migration Steps Required

To deploy these changes, the following steps must be performed:

1. **Create KnowledgeObject Schema in Weaviate**:
   - Use the schema definition from the issue description
   - Ensure all properties match the specification

2. **Migrate Existing Data**:
   - Export data from old `Item`, `Task`, and `GitHubIssue` collections
   - Transform to KnowledgeObject format with appropriate `type` field
   - Import into new `KnowledgeObject` collection

3. **Deploy Code Changes**:
   - Deploy updated service files
   - Verify all sync operations work correctly

4. **Cleanup**:
   - Remove old collection schemas (optional, after verifying migration)
   - Update any documentation referencing old schemas

## Testing

All code changes pass syntax validation. Full integration testing requires:
- A running Weaviate instance with the KnowledgeObject schema
- Django application configured with proper Weaviate connection settings
- Sample data to verify CRUD operations work correctly

## Files Changed

1. `core/services/weaviate_sync_service.py` - Item sync service
2. `core/services/weaviate_task_sync_service.py` - Task sync service
3. `core/services/weaviate_github_issue_sync_service.py` - GitHub Issue sync service
4. `core/services/milestone_knowledge_service.py` - Milestone and context object sync service (updated to include standard properties)
5. `main/test_weaviate_github_issue_sync_upsert.py` - Updated tests
6. `KNOWLEDGEOBJECT_SCHEMA_MIGRATION.md` - This documentation file

## Summary

The implementation successfully migrates all Weaviate operations from separate collection schemas to a unified KnowledgeObject schema. The changes follow the requirements exactly:
- ✅ Type field identifies object type (Item, Task, GitHubIssue, Milestone, Email, Note, File, Transcript)
- ✅ GitHubIssueID only for Tasks and GitHub Issues
- ✅ TaskID only for GitHub Issues
- ✅ ItemID for Tasks, GitHub Issues, and Milestones
- ✅ MilestoneID for context objects (Emails, Notes, Files, Transcripts)
- ✅ All objects include standard properties: type, title, description, owner, tags, status, createdAt, url
- ✅ All operations (POST/PATCH) updated to use new schema
- ✅ Consistent property mapping ensures proper semantic similarity matching across all object types
