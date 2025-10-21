# Fix for Repository Assignment in sync_github_issues.py

## Problem Description

The `sync_github_issues.py` script was using a statically configured repository from settings (default owner/repo), which caused 404 errors when tasks were linked to items that belong to different repositories.

### Example Error
```
2025-10-21 20:58:30 [INFO] [github_service] - GET https://api.github.com/repos/eoe-university/IdeaGraph-v1/issues/261
2025-10-21 20:58:30 [INFO] [github_service] - Response: 404
2025-10-21 20:58:30 [ERROR] [github_service] - GitHub API error 404: Not Found
2025-10-21 20:58:30 [ERROR] [weaviate_github_issue_sync_service] - Error syncing task fb15c8cd-fbbd-401b-920f-4b2c39b22b9c: Not Found
```

## Root Cause

The `sync_tasks_with_github_issues` method in `WeaviateGitHubIssueSyncService` was passing the `repo` and `owner` parameters directly to the GitHub API calls without checking if the task's associated item has its own repository configured.

### Previous Flow
1. User runs `sync_github_issues.py` with optional `--owner` and `--repo` arguments
2. Script calls `sync_tasks_with_github_issues(repo, owner)`
3. For each task, the method uses the provided `repo` and `owner` (or None)
4. If None, `GitHubService` falls back to default settings
5. This causes issues when tasks belong to items in different repositories

## Solution

### Changes Made

1. **Added `_parse_github_repo` Helper Method**
   - Parses the `github_repo` field from the Item model
   - Supports various formats: `owner/repo`, `https://github.com/owner/repo`, etc.
   - Returns a tuple of `(owner, repo)` or `(None, None)` if parsing fails

2. **Updated `sync_tasks_with_github_issues` Method**
   - For each task, checks if the task has an associated item
   - If item exists and has `github_repo` configured, extracts owner/repo
   - Uses item's repository information when calling GitHub API
   - Command-line arguments still take precedence (for manual overrides)
   - Falls back to default settings if no repository information is available

### New Flow
1. User runs `sync_github_issues.py` with optional `--owner` and `--repo` arguments
2. Script calls `sync_tasks_with_github_issues(repo, owner)`
3. For each task:
   - Check if command-line `owner` and `repo` were provided (these override everything)
   - If not provided, check if task has an associated item
   - If item exists, extract `owner` and `repo` from item's `github_repo` field
   - Use the determined `owner` and `repo` for GitHub API calls
   - If still None, `GitHubService` falls back to default settings

## Code Changes

### File: `core/services/weaviate_github_issue_sync_service.py`

#### New Method: `_parse_github_repo`
```python
def _parse_github_repo(self, github_repo: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse github_repo field to extract owner and repo name
    
    Args:
        github_repo: Repository string in format "owner/repo" or full URL
    
    Returns:
        Tuple of (owner, repo) or (None, None) if parsing fails
    """
    if not github_repo:
        return None, None
    
    # Remove common GitHub URL prefixes
    repo_str = github_repo.strip()
    repo_str = repo_str.replace('https://github.com/', '')
    repo_str = repo_str.replace('http://github.com/', '')
    repo_str = repo_str.replace('github.com/', '')
    repo_str = repo_str.strip('/')
    
    # Split by '/' to get owner and repo
    parts = repo_str.split('/')
    if len(parts) >= 2:
        return parts[0], parts[1]
    
    return None, None
```

#### Updated Method: `sync_tasks_with_github_issues`
Key changes in the task iteration loop:
```python
for task in tasks_with_issues:
    results['tasks_checked'] += 1
    
    try:
        # Determine which repository to use
        task_owner = owner
        task_repo = repo
        
        # If not provided as arguments, try to get from task's item
        if not task_owner or not task_repo:
            if task.item and task.item.github_repo:
                item_owner, item_repo = self._parse_github_repo(task.item.github_repo)
                if not task_owner:
                    task_owner = item_owner
                if not task_repo:
                    task_repo = item_repo
                logger.debug(
                    f"Task {task.id} using repository from item: {task_owner}/{task_repo}"
                )
        
        # Log which repository we're using for this task
        if task_owner and task_repo:
            logger.info(
                f"Syncing task {task.id} (issue #{task.github_issue_id}) "
                f"from repository {task_owner}/{task_repo}"
            )
        else:
            logger.warning(
                f"Task {task.id} has no repository information in item, "
                f"falling back to default settings"
            )
        
        # Get issue from GitHub (now uses task-specific owner/repo)
        issue_result = github_service.get_issue(
            issue_number=task.github_issue_id,
            repo=task_repo,
            owner=task_owner
        )
```

## Usage Examples

### Scenario 1: Sync All Tasks Using Item Repositories
```bash
python sync_github_issues.py
```
- Each task will use its item's `github_repo` field
- Falls back to default settings if item has no repository configured

### Scenario 2: Override Repository for All Tasks
```bash
python sync_github_issues.py --owner gdsanger --repo IdeaGraph-v1
```
- Forces all tasks to sync with `gdsanger/IdeaGraph-v1`
- Ignores item's `github_repo` field

### Scenario 3: Mixed Approach (Partial Override)
```bash
python sync_github_issues.py --owner gdsanger
```
- Uses `gdsanger` as owner for all tasks
- Uses item's repository name if available
- Falls back to default repo if item has no repository configured

## Supported Repository Formats

The `_parse_github_repo` method supports various formats:

- ✓ `owner/repo`
- ✓ `https://github.com/owner/repo`
- ✓ `http://github.com/owner/repo`
- ✓ `github.com/owner/repo`
- ✓ `https://github.com/owner/repo/` (with trailing slash)
- ✓ `  owner/repo  ` (with whitespace)

## Testing

Comprehensive tests were created to verify:
1. Repository parsing from various formats
2. Priority of command-line arguments over item configuration
3. Fallback to None when no repository is available
4. Handling of tasks without items
5. Handling of items without github_repo configured

All tests passed successfully.

## Benefits

1. **Correct Repository Usage**: Tasks now sync with the correct repository based on their item configuration
2. **No More 404 Errors**: Eliminates 404 errors caused by incorrect repository assignment
3. **Backward Compatible**: Maintains existing behavior when command-line arguments are provided
4. **Flexible**: Supports various repository formats in the `github_repo` field
5. **Better Logging**: Enhanced logging to show which repository is being used for each task

## Migration Notes

No migration is required. The changes are backward compatible:
- Existing tasks with items that have `github_repo` will now use the correct repository
- Tasks without items or items without `github_repo` will continue to use default settings
- Command-line overrides still work as expected

## Verification

To verify the fix is working:

1. Check logs when running `sync_github_issues.py`:
   ```
   [INFO] Syncing task abc-123 (issue #261) from repository eoe-university/IdeaGraph-v1
   ```

2. Verify no 404 errors for tasks with valid item repositories

3. Check that tasks are synced with the correct GitHub repository
