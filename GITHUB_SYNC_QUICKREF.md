# GitHub Sync - Quick Reference

## Quick Start

```bash
# 1. Install (if not already done)
pip install -r requirements.txt

# 2. Configure in Django admin
#    - GitHub API: Enable and add token
#    - ChromaDB: Add API key, database, tenant
#    - OpenAI: Enable and add API key

# 3. Run manually
python sync_github_issues.py

# 4. Set up cron (optional)
crontab -e
# Add: 0 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1
```

## Common Commands

```bash
# Show help
python sync_github_issues.py --help

# Run with verbose logging
python sync_github_issues.py --verbose

# Dry run (no changes)
python sync_github_issues.py --dry-run

# Specific repository
python sync_github_issues.py --owner USERNAME --repo REPONAME
```

## What It Does

1. ✅ Finds all tasks with GitHub issue links
2. ✅ Checks if the GitHub issue is closed
3. ✅ Updates task status to "Erledigt" if closed
4. ✅ Stores issue/PR data in ChromaDB with metadata
5. ✅ Creates embeddings for semantic search

## Required Settings

| Setting | Required | Description |
|---------|----------|-------------|
| `github_api_enabled` | Yes | Must be `True` |
| `github_token` | Yes | GitHub Personal Access Token |
| `chroma_api_key` | Yes | ChromaDB API key |
| `chroma_database` | Yes | ChromaDB database name |
| `chroma_tenant` | Yes | ChromaDB tenant |
| `openai_api_enabled` | Yes | Must be `True` |
| `openai_api_key` | Yes | OpenAI API key for embeddings |

## Troubleshooting

### "No settings found in database"
→ Create Settings entry in Django admin

### "GitHub API is not enabled"
→ Set `github_api_enabled = True` in Settings

### "OpenAI API is not enabled"
→ Set `openai_api_enabled = True` in Settings

### "Failed to initialize ChromaDB"
→ Check ChromaDB credentials (api_key, database, tenant)

## Output Example

```
================================================================================
GitHub Issues and Tasks Synchronization
Started at: 2025-10-19T19:17:23.897Z
================================================================================
Initializing GitHub Issue Sync Service...
Starting synchronization...
Syncing issue #42 to ChromaDB: Fix authentication bug
Task abc-123-def marked as done (GitHub issue #42 closed)
================================================================================
Synchronization Results:
  Tasks checked: 15
  Tasks updated: 3
  Issues synced to ChromaDB: 10
  Pull Requests synced to ChromaDB: 5
  No errors encountered
================================================================================
Synchronization completed successfully!
```

## Cron Examples

```cron
# Every hour
0 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1

# Every 15 minutes
*/15 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1

# Daily at 2 AM
0 2 * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1
```

## Files Location

- **Script**: `sync_github_issues.py`
- **Service**: `core/services/github_issue_sync_service.py`
- **Tests**: `main/test_github_issue_sync.py`
- **Logs**: `logs/github_sync.log`
- **Docs**: `GITHUB_SYNC_GUIDE.md`

## API Rate Limits

- GitHub: 5000 requests/hour (authenticated)
- Plan cron frequency accordingly
- Each task check = 1+ API calls

## Support

- Full documentation: `GITHUB_SYNC_GUIDE.md`
- Implementation details: `GITHUB_SYNC_IMPLEMENTATION.md`
- Cron examples: `cron_examples.txt`
- Issues: https://github.com/gdsanger/IdeaGraph-v1/issues
