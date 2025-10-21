# ChromaDB to Weaviate Migration

## Overview
This document describes the migration from ChromaDB to Weaviate for the GitHub issue synchronization service and similarity search functionality.

## Changes Made

### 1. GitHub Issue Sync Service Migration

**Files Changed:**
- `main/api_views.py` (line 2339, 2395, 2469)
- `sync_github_issues.py` (line 44, 140, 173)
- `core/services/weaviate_github_issue_sync_service.py` (added `sync_tasks_with_github_issues` method)

**What Changed:**
- Replaced all uses of `GitHubIssueSyncService` (ChromaDB) with `WeaviateGitHubIssueSyncService`
- Updated import statements to use the Weaviate version
- Updated exception handling to use `WeaviateGitHubIssueSyncServiceError`
- Updated metadata field names to match Weaviate schema:
  - `github_issue_id` → `issue_number`
  - `github_issue_url` → `issue_url`
  - `github_issue_state` → `issue_state`
  - `github_issue_title` → `issue_title`

### 2. Added sync_tasks_with_github_issues Method

**File:** `core/services/weaviate_github_issue_sync_service.py`

**What Changed:**
- Added the comprehensive `sync_tasks_with_github_issues()` method to WeaviateGitHubIssueSyncService
- This method mirrors the functionality of the ChromaDB version but stores data in Weaviate instead
- Syncs GitHub issues and pull requests to Weaviate
- Updates task status when GitHub issues are closed

### 3. Updated Service Exports

**File:** `core/services/__init__.py`

**What Changed:**
- Removed exports of ChromaDB services (`ChromaItemSyncService`, `ChromaItemSyncServiceError`)
- Added exports of Weaviate services:
  - `WeaviateItemSyncService`, `WeaviateItemSyncServiceError`
  - `WeaviateTaskSyncService`, `WeaviateTaskSyncServiceError`
  - `WeaviateGitHubIssueSyncService`, `WeaviateGitHubIssueSyncServiceError`

### 4. Similarity Search Endpoints

**Status:** Already using Weaviate

The following endpoints were already using Weaviate services (no changes needed):
- `/api/items/<item_id>/check-similarity` - uses `WeaviateItemSyncService`
- `/api/tasks/<task_id>/similar` - uses `WeaviateTaskSyncService` (for tasks) and now `WeaviateGitHubIssueSyncService` (for GitHub issues)

## Backward Compatibility

### ChromaDB Services Still Available
The old ChromaDB services are still present in the codebase:
- `core/services/github_issue_sync_service.py`
- `core/services/chroma_sync_service.py`
- `core/services/chroma_task_sync_service.py`

However, they are:
1. No longer used in production code
2. No longer exported from `core/services/__init__.py`
3. Will fail to import if ChromaDB is not installed (which is expected since it's not in `requirements.txt`)

### Settings Model
The Settings model still contains ChromaDB configuration fields (`chroma_api_key`, `chroma_database`, `chroma_tenant`). These fields are retained for:
- Backward compatibility
- Potential data migration needs
- Historical reference

These fields are not used by the active codebase.

## Testing

### Import Tests
All imports were verified to work correctly:
```bash
✓ All Weaviate service imports successful
✓ Weaviate services exported from core.services
✓ WeaviateGitHubIssueSyncService.sync_tasks_with_github_issues method exists
✓ API views imported successfully
✓ api_task_similar function exists
✓ api_item_check_similarity function exists
✓ sync_github_issues.py imports successfully
```

### Unit Tests
Existing tests in `main/test_github_issue_sync.py` still test the old ChromaDB service. These tests are left unchanged because:
1. They test the old implementation which is kept for reference
2. They require ChromaDB to be installed, which is no longer a dependency
3. New tests should be created for the Weaviate services

## Usage Examples

### Sync GitHub Issues
```bash
# Run the sync script
python sync_github_issues.py

# With specific repository
python sync_github_issues.py --owner myorg --repo myrepo

# With verbose logging
python sync_github_issues.py --verbose
```

### API Endpoints
```bash
# Get similar tasks and GitHub issues
GET /api/tasks/{task_id}/similar

# Check item similarity
POST /api/items/{item_id}/check-similarity
Body: {"title": "...", "description": "..."}
```

## Migration Checklist

- [x] Replace GitHubIssueSyncService with WeaviateGitHubIssueSyncService in api_views.py
- [x] Update sync_github_issues.py to use WeaviateGitHubIssueSyncService
- [x] Add sync_tasks_with_github_issues method to WeaviateGitHubIssueSyncService
- [x] Update metadata field names to match Weaviate schema
- [x] Update core/services/__init__.py to export Weaviate services
- [x] Verify all similarity search endpoints use Weaviate services
- [x] Verify imports work correctly
- [x] Document migration changes

## Next Steps

### For Production Deployment
1. Ensure Weaviate is running and accessible (either local at localhost:8081 or cloud)
2. Configure Weaviate settings in the admin panel:
   - Set `weaviate_cloud_enabled` if using Weaviate Cloud
   - Set `weaviate_url` (cluster URL for cloud or localhost:8081 for local)
   - Set `weaviate_api_key` (for cloud only)
3. Run initial GitHub issue sync: `python sync_github_issues.py`
4. Verify similarity search works in the UI (Tasks → Similar tab)

### For Development
1. Start local Weaviate instance: `docker run -p 8081:8080 semitechnologies/weaviate:latest`
2. Or configure Weaviate Cloud credentials in settings
3. Run migrations if needed: `python manage.py migrate`
4. Test similarity search functionality

### Optional: ChromaDB Data Migration
If you have existing data in ChromaDB that needs to be migrated to Weaviate:
1. The old ChromaDB services are still available (but require installing `chromadb` package)
2. Create a migration script that:
   - Reads data from ChromaDB using old services
   - Writes data to Weaviate using new services
3. This is left as a manual task since data requirements vary

## Notes

- **No functional changes**: The migration maintains the same functionality, just using Weaviate instead of ChromaDB
- **Performance**: Weaviate may have different performance characteristics than ChromaDB
- **Schema differences**: Metadata field names were updated to match Weaviate's schema
- **Error handling**: Error types changed from `*ChromaDB*Error` to `*Weaviate*Error`
