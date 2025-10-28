# GitHub PR Sync - Quick Reference

## Quick Start

```bash
# Sync PRs for specific item (incremental)
python manage.py sync_github_prs --item <item_id>

# Initial load all PRs
python manage.py sync_github_prs --item <item_id> --initial

# Sync all items
python manage.py sync_github_prs --all
```

## Command Options

| Option | Description |
|--------|-------------|
| `--item <uuid>` | Sync specific item by UUID |
| `--all` | Sync all items with GitHub repos |
| `--initial` | Fetch all PRs (default: last hour) |
| `--export-sharepoint` | Export PR data to SharePoint as JSON |
| `--verbose` | Enable verbose output |

## Sync Modes

### Incremental Sync (Default)
- Fetches PRs updated in last hour
- Use for regular scheduled updates
- Lower API usage

### Initial Load
- Fetches all PRs from repository
- Use for first-time setup or rebuild
- Higher API usage

## Cron Job Examples

```bash
# Hourly incremental sync
0 * * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_prs --all >> logs/sync_github_prs.log 2>&1

# Daily full sync at 3 AM
0 3 * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_prs --all --initial >> logs/sync_github_prs.log 2>&1
```

## Prerequisites

✅ GitHub API enabled in Settings  
✅ GitHub token configured (PAT with `repo` scope)  
✅ Item has `github_repo` field set (e.g., "owner/repo")  

## What Gets Synced

- PR number, title, body
- State: open, closed, merged
- Author (login, avatar)
- Branches (head, base)
- Timestamps (created, updated, closed, merged)
- Draft status

## Storage Locations

1. **SQLite Database**: `GitHubPullRequest` model
2. **Weaviate**: `KnowledgeObject` (type: "pull_request")
3. **SharePoint** (optional): JSON files in `{item_id}/github_prs/`

## Usage in Code

```python
from main.models import Item, GitHubPullRequest
from core.services.github_pr_sync_service import GitHubPRSyncService

# Sync PRs for an item
service = GitHubPRSyncService()
item = Item.objects.get(id='<uuid>')
result = service.sync_pull_requests(item, initial_load=False)

# Query PRs from database
prs = GitHubPullRequest.objects.filter(item=item, state='open')
for pr in prs:
    print(f"PR #{pr.pr_number}: {pr.title}")
```

## Common Use Cases

### 1. First-Time Setup
```bash
python manage.py sync_github_prs --item <uuid> --initial --verbose
```

### 2. Regular Updates
```bash
python manage.py sync_github_prs --all
```

### 3. Single Item Update
```bash
python manage.py sync_github_prs --item <uuid>
```

### 4. Debugging
```bash
python manage.py sync_github_prs --item <uuid> --verbose
```

## Troubleshooting

| Error | Solution |
|-------|----------|
| "GitHub API not enabled" | Enable in Settings → GitHub API |
| "No GitHub repo configured" | Set `github_repo` field on Item |
| "Rate limit exceeded" | Wait or use token with higher limits |
| "Failed to sync to Weaviate" | Check Weaviate connection settings |

## Output Example

```
Sync mode: Incremental Sync (last hour)

Syncing PRs for item: 7d6b9aee-2e6f-4e7a-bae4-28face017a97

✓ Sync completed successfully!
Item: IdeaGraph v1
PRs checked: 5
PRs created: 2
PRs updated: 1
PRs synced to Weaviate: 3
```

## Key Files

- **Model**: `main/models.py` → `GitHubPullRequest`
- **Service**: `core/services/github_pr_sync_service.py`
- **Command**: `main/management/commands/sync_github_prs.py`
- **Tests**: `main/test_github_pr_sync.py`
- **Guide**: `GITHUB_PR_SYNC_GUIDE.md`

## Related Commands

```bash
# GitHub issues sync
python manage.py sync_github_docs --item <uuid>

# Weaviate maintenance
python manage.py sync_tags_to_weaviate
```

## API Rate Limits

GitHub API rate limits:
- **Authenticated**: 5,000 requests/hour
- **Unauthenticated**: 60 requests/hour

Each sync operation uses approximately:
- 1 request per page of PRs (100 PRs per page)
- Example: 250 PRs = 3 requests

## Best Practices

1. **Use incremental sync** for regular updates (hourly/daily)
2. **Use initial load** only for setup or rebuild
3. **Monitor logs** for sync status and errors
4. **Set up cron jobs** for automated synchronization
5. **Enable verbose mode** when debugging issues
