# Zammad Integration - Quick Reference

## Configuration (Admin Settings)

```python
zammad_enabled = True
zammad_api_url = "https://support.example.com"
zammad_api_token = "your_api_token_here"
zammad_groups = "Support,Development,Sales"
zammad_sync_interval = 15  # minutes
```

## CLI Commands

```bash
# Test connection
python manage.py sync_zammad_tickets --test-connection

# Sync all configured groups
python manage.py sync_zammad_tickets

# Sync specific groups
python manage.py sync_zammad_tickets --groups "Support,Development"
```

## API Endpoints

All endpoints require Admin authentication.

### Test Connection
```bash
POST /api/zammad/test-connection
```

### Manual Sync
```bash
POST /api/zammad/sync
Content-Type: application/json

# Optional body for specific groups:
{"groups": ["Support", "Development"]}
```

### Get Status
```bash
GET /api/zammad/status
```

## Cron Setup

```cron
# Sync every 15 minutes
*/15 * * * * cd /path/to/ideagraph && python manage.py sync_zammad_tickets
```

## Task Fields

- **type**: task, feature, bug, ticket, maintenance
- **external_id**: Zammad ticket ID
- **external_url**: Link to Zammad ticket
- **section**: Auto-created "Zammad - {Group}"
- **tags**: Synced from Zammad
- **files**: Downloaded attachments

## Service Usage in Code

```python
from core.services.zammad_sync_service import ZammadSyncService

# Initialize
service = ZammadSyncService()

# Test connection
result = service.test_connection()

# Fetch tickets
tickets = service.fetch_open_tickets(['Support'])

# Sync specific ticket
ticket_result = service.sync_ticket_to_task(ticket_data)

# Sync all
sync_result = service.sync_all_tickets()
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check API URL and network |
| Auth failed | Verify API token |
| Missing tickets | Check group names (case-sensitive) |
| No attachments | Check disk space and permissions |

## File Locations

- **Service**: `core/services/zammad_sync_service.py`
- **Command**: `main/management/commands/sync_zammad_tickets.py`
- **Tests**: `main/test_zammad_sync.py`
- **Docs**: `ZAMMAD_INTEGRATION_GUIDE.md`
- **Attachments**: `zammad_attachments/`
- **Logs**: `logs/ideagraph.log`

## Example Response

```json
{
  "success": true,
  "total_tickets": 10,
  "created": 3,
  "updated": 7,
  "failed": 0,
  "duration_seconds": 12.5
}
```

## Migration

```bash
python manage.py migrate
# Applies migration 0022: Adds Zammad fields to Settings and Task models
```
