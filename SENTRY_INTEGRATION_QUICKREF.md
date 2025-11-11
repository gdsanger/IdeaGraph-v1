# Sentry Integration Quick Reference

## 📋 Quick Setup Checklist

- [ ] Set Sentry Auth Token in Settings
- [ ] Configure Item with Sentry DSN
- [ ] Set Sentry Project Slug
- [ ] Enable Auto-Fetch checkbox
- [ ] Test manual fetch via API or CLI
- [ ] Set up cron job (optional)

## 🔧 Configuration

### Settings (Admin Only)
```
Settings → Sentry Auth Token
```
Example: `sntrys_abc123def456...`

### Item Configuration
```
Item Edit → Sentry Integration Section
```

| Field | Example | Required | Notes |
|-------|---------|----------|-------|
| Sentry DSN | `https://key@org.ingest.sentry.io/12345` | Yes | Regional domains auto-detected (`.de`, `.us`, etc.) |
| Sentry Auth Token | `sntrys_abc123...` | Yes | Per-item token (optional if set in Settings) |
| Project Slug | `ideagraph-v1` | Auto* | Auto-detected from API if left empty |
| Enable Auto-Fetch | ☑ | Yes | Must be checked to enable sync |

*Project Slug is automatically fetched if not provided

## 🚀 Usage

### Manual Fetch (API)
```bash
curl -X POST http://localhost:8000/api/items/<ITEM_ID>/fetch-sentry-errors \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=<SESSION>" \
  -d '{"hours_back": 24}'
```

### CLI - Single Item
```bash
python sync_sentry_errors.py --item-id <UUID>
```

### CLI - All Items
```bash
python sync_sentry_errors.py --all-items
```

### CLI - Options
```bash
--hours 48           # Look back 48 hours
--dry-run            # Preview without creating tasks
--verbose            # Detailed logging
```

## ⏰ Cron Job Examples

### Every Hour
```cron
0 * * * * cd /path/to/IdeaGraph-v1 && python sync_sentry_errors.py --all-items >> logs/sentry.log 2>&1
```

### Every 30 Minutes
```cron
*/30 * * * * cd /path/to/IdeaGraph-v1 && python sync_sentry_errors.py --all-items >> logs/sentry.log 2>&1
```

### Daily at 3 AM
```cron
0 3 * * * cd /path/to/IdeaGraph-v1 && python sync_sentry_errors.py --all-items >> logs/sentry.log 2>&1
```

## 📊 What Gets Created

Each Sentry error becomes a **Bug Task** with:

- ✅ **Title**: Sentry error title
- ✅ **Type**: Bug
- ✅ **Status**: New
- ✅ **Description**: Formatted markdown with error details
- ✅ **External ID**: `sentry-<issue_id>` (for duplicate detection)
- ✅ **External URL**: Link to Sentry issue
- ✅ **Tags**: Inherited from parent Item

## 🔍 Duplicate Detection

Tasks are **NOT created** if:
1. A task already exists with same `external_id` (`sentry-<issue_id>`)
2. A task already exists with exact same title and type=bug

## 🐛 Troubleshooting

### Error 404 - Issues not found?
1. ✅ **Regional endpoint**: DSN with `.ingest.de.sentry.io` now auto-detects EU endpoint
2. ✅ Check Sentry Auth Token (per-item or in Settings)
3. ✅ Check DSN format includes region: `https://key@org.ingest[.region].sentry.io/project`
4. ✅ Check Project Slug matches Sentry (or leave empty for auto-detect)
5. ✅ Check organization ID in DSN is correct

### No errors fetched?
1. ✅ Check Sentry Auth Token in Settings or per-Item
2. ✅ Check DSN format is correct
3. ✅ Check Project Slug matches Sentry (or auto-detected)
4. ✅ Check "Enable Auto-Fetch" is checked
5. ✅ Check errors exist in last 24 hours

### Check logs:
```bash
# View sync output
tail -f logs/sync_sentry.log

# Run with verbose logging
python sync_sentry_errors.py --item-id <UUID> --verbose
```

### Test connection:
```bash
# Dry run - no changes
python sync_sentry_errors.py --item-id <UUID> --dry-run --verbose
```

## 📈 Response Format

### Success
```json
{
  "success": true,
  "issues_fetched": 5,
  "tasks_created": 3,
  "duplicates_skipped": 2,
  "message": "Successfully fetched 5 issues and created 3 tasks"
}
```

### Error
```json
{
  "success": false,
  "error": "Sentry DSN not configured for this item"
}
```

## 🔐 Sentry Token Permissions

Required Sentry API permissions:
- ✅ `project:read`
- ✅ `org:read`
- ✅ `event:read`

Create token at: `Sentry → Settings → Account → API → Auth Tokens`

## 📖 Flow Diagram

```
┌─────────────────┐
│   Sentry API    │
│   (Errors)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fetch Issues    │
│ (Last 24h)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check Duplicate │◄─── external_id
│                 │◄─── title match
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Create Task    │
│  (Type: Bug)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Link to Item   │
└─────────────────┘
```

## 🎯 Best Practices

1. **Start with one Item**: Configure and test with one Item before enabling for all
2. **Use dry-run**: Always test with `--dry-run` first
3. **Monitor logs**: Keep an eye on sync logs initially
4. **Set reasonable hours**: Don't go too far back (24-48h is usually enough)
5. **Review tasks**: Check auto-created tasks to ensure quality
6. **Tag appropriately**: Items with good tags = tasks with good tags

## 📚 Full Documentation

See [SENTRY_INTEGRATION_GUIDE.md](./SENTRY_INTEGRATION_GUIDE.md) for complete documentation.

---

*Quick Reference v1.0*
