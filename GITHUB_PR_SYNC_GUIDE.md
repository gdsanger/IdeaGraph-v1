# GitHub Pull Request Synchronization Feature

## Overview

IdeaGraph now supports automatic synchronization of GitHub Pull Requests from linked repositories. This feature stores PRs in the local SQLite database and synchronizes them to Weaviate for AI-powered semantic search.

## Features

- **Automatic PR Sync**: Fetch pull requests from GitHub repositories linked to Items
- **Two Sync Modes**:
  - **Initial Load**: Fetch all PRs from repository (for first-time setup)
  - **Incremental Sync**: Fetch only PRs updated in the last hour (for regular updates)
- **Database Storage**: Store PRs locally in SQLite for fast access
- **Weaviate Integration**: Sync PRs to Weaviate as `KnowledgeObject` (type: "pull_request")
- **Optional SharePoint Export**: Export PR data as JSON to SharePoint folders

## Database Schema

The new `GitHubPullRequest` model stores:
- PR number, title, description (body)
- State: open, closed, or merged
- Author information (login, avatar URL)
- Branch information (head/base branches)
- Timestamps (created, updated, closed, merged)
- Repository information (owner, name)
- Link to IdeaGraph Item

## Usage

### Command Line Interface

```bash
# Sync PRs for a specific item (incremental - last hour)
python manage.py sync_github_prs --item <item_id>

# Initial load - fetch all PRs for an item
python manage.py sync_github_prs --item <item_id> --initial

# Sync PRs for all items with GitHub repositories
python manage.py sync_github_prs --all

# Sync with SharePoint export
python manage.py sync_github_prs --item <item_id> --export-sharepoint

# Verbose output for debugging
python manage.py sync_github_prs --item <item_id> --verbose
```

### Cron Job Setup

For automatic hourly synchronization:

```bash
# Add to crontab
0 * * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_prs --all >> logs/sync_github_prs.log 2>&1
```

For daily full synchronization:

```bash
# Add to crontab - runs at 3 AM daily
0 3 * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_prs --all --initial >> logs/sync_github_prs.log 2>&1
```

## Configuration

### Prerequisites

1. **GitHub API Token**: Set in Settings
   - Navigate to Settings → GitHub API
   - Enable GitHub API
   - Configure GitHub Token (PAT with `repo` scope)

2. **Item Configuration**: Link GitHub repository to Item
   - Edit Item
   - Set `github_repo` field to repository (e.g., "owner/repo" or "https://github.com/owner/repo")

### Settings

The following settings are used by the PR sync:
- `github_api_enabled`: Must be True
- `github_token`: GitHub Personal Access Token
- `github_api_base_url`: Default is "https://api.github.com"
- `github_default_owner`: Optional default repository owner

## Weaviate Integration

Pull Requests are stored in Weaviate as `KnowledgeObject` with:
- `type`: "pull_request" (discriminator)
- `title`: PR title
- `description`: PR body/description
- `status`: PR state (open/closed/merged)
- `githubIssueId`: PR number
- `url`: GitHub PR URL
- `itemId`: Associated Item UUID

This allows semantic search across PR descriptions and integration with the IdeaGraph AI features.

## SharePoint Export (Optional)

When enabled with `--export-sharepoint`, PR data is exported as JSON files to:

```
{sharepoint_base_path}/{item_id}/github_prs/pr_{pr_number}.json
```

Each JSON file contains complete PR metadata including:
- PR number, title, body
- State, draft status, merged status
- Author information
- Branch information
- Timestamps
- Repository information

## Examples

### Example 1: Initial Sync for Specific Item

```bash
# First-time setup: fetch all PRs
python manage.py sync_github_prs --item 7d6b9aee-2e6f-4e7a-bae4-28face017a97 --initial --verbose
```

Output:
```
Sync mode: Initial Load (all PRs)

Syncing PRs for item: 7d6b9aee-2e6f-4e7a-bae4-28face017a97

Item: IdeaGraph v1
Repository: gdsanger/IdeaGraph-v1

✓ Sync completed successfully!
Item: IdeaGraph v1
PRs checked: 42
PRs created: 42
PRs updated: 0
PRs synced to Weaviate: 42
```

### Example 2: Incremental Sync for All Items

```bash
# Regular update: fetch only recent PRs (last hour)
python manage.py sync_github_prs --all
```

Output:
```
Sync mode: Incremental Sync (last hour)

Syncing PRs for all items with GitHub repositories

Found 3 items with GitHub repositories

✓ IdeaGraph v1: 1 created, 0 updated
✓ Project Alpha: 0 created, 2 updated
✓ Project Beta: 0 created, 0 updated

================================================================================
Synchronization Results:
Items processed: 3
Items succeeded: 3
Items failed: 0
Total PRs checked: 3
Total PRs created: 1
Total PRs updated: 2
Total PRs synced to Weaviate: 3

No errors encountered
================================================================================
```

### Example 3: Using in Python Code

```python
from main.models import Item
from core.services.github_pr_sync_service import GitHubPRSyncService

# Initialize service
service = GitHubPRSyncService()

# Get item
item = Item.objects.get(id='7d6b9aee-2e6f-4e7a-bae4-28face017a97')

# Sync PRs (incremental)
result = service.sync_pull_requests(item, initial_load=False)

print(f"PRs created: {result['prs_created']}")
print(f"PRs updated: {result['prs_updated']}")
print(f"Synced to Weaviate: {result['prs_synced_to_weaviate']}")
```

## Monitoring & Troubleshooting

### Logs

The sync service logs to:
- Standard output (when run from command line)
- Django log files (configured in `logger_config.py`)

Enable verbose logging for debugging:

```bash
python manage.py sync_github_prs --item <item_id> --verbose
```

### Common Issues

**Issue**: "GitHub API is not enabled in settings"
- **Solution**: Navigate to Settings and enable GitHub API integration

**Issue**: "Item has no GitHub repository configured"
- **Solution**: Edit the Item and set the `github_repo` field

**Issue**: "GitHub API rate limit exceeded"
- **Solution**: Wait for rate limit to reset, or use a GitHub token with higher rate limits

**Issue**: "Failed to sync to Weaviate"
- **Solution**: Check Weaviate connection settings and ensure Weaviate is running

## Architecture

### Data Flow

```
GitHub API → GitHubPRSyncService → SQLite Database (GitHubPullRequest)
                                 → Weaviate (KnowledgeObject)
                                 → SharePoint (JSON export, optional)
```

### Service Components

1. **GitHubPRSyncService**: Main service class
   - `sync_pull_requests()`: Main sync method
   - `_store_pr_in_database()`: Store PR in SQLite
   - `_sync_pr_to_weaviate()`: Sync PR to Weaviate
   - `_export_pr_to_sharepoint()`: Export PR to SharePoint (optional)

2. **Management Command**: `sync_github_prs`
   - Command-line interface
   - Argument parsing
   - Progress reporting

3. **Database Model**: `GitHubPullRequest`
   - Stores PR data locally
   - Unique constraint on (item, pr_number, repo_owner, repo_name)
   - Indexed for fast lookups

## Testing

Run tests:

```bash
# Run PR sync tests
python manage.py test main.test_github_pr_sync

# Run all GitHub-related tests
python manage.py test main.test_github*
```

## Future Enhancements

Possible future improvements:
- Sync PR comments
- Sync PR reviews
- Sync PR files changed
- Auto-create tasks from PRs
- PR status tracking in Item detail view
- PR analytics dashboard

## Related Features

- **GitHub Issues Sync**: See `GITHUB_ISSUES_TO_TASKS_SYNC_GUIDE.md`
- **GitHub Documentation Sync**: See `GITHUB_DOC_SYNC_GUIDE.md`
- **Weaviate Integration**: See `WEAVIATE_MIGRATION_SUMMARY.md`
