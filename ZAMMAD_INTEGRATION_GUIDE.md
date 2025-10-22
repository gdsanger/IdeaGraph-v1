# Zammad Integration Guide

## Overview

The Zammad Integration for IdeaGraph provides automatic synchronization of support tickets from Zammad into IdeaGraph as tasks. This creates a seamless connection between customer support and development workflows.

## Features

- ✅ **Automatic Ticket Synchronization**: Fetches open tickets from configured Zammad groups
- ✅ **Task Creation & Updates**: Creates new tasks or updates existing ones based on ticket changes
- ✅ **Attachment Management**: Downloads and stores ticket attachments locally and optionally in SharePoint
- ✅ **AI Classification**: Optional AI-powered task type classification (Bug, Feature, Ticket, Maintenance)
- ✅ **Status Updates**: Updates ticket status in Zammad after synchronization
- ✅ **Tag Synchronization**: Transfers ticket tags to IdeaGraph tasks
- ✅ **Section Mapping**: Automatically creates sections based on Zammad groups

## Configuration

### 1. Enable Zammad Integration

Navigate to Settings (Admin access required) and configure:

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `zammad_enabled` | Boolean | Enable/disable Zammad integration | Yes |
| `zammad_api_url` | String | Base URL of your Zammad instance (e.g., `https://support.example.com`) | Yes |
| `zammad_api_token` | String | Zammad API token for authentication | Yes |
| `zammad_groups` | String | Comma-separated list of group names to monitor (e.g., `Support,Development,Sales`) | Yes |
| `zammad_sync_interval` | Integer | Sync interval in minutes for periodic execution (default: 15) | No |

### 2. Generate Zammad API Token

1. Log into your Zammad instance as an administrator
2. Navigate to Settings → API
3. Create a new API token with read/write permissions for tickets
4. Copy the token and paste it into the `zammad_api_token` field

### 3. Test Connection

Test your connection using the management command:

```bash
python manage.py sync_zammad_tickets --test-connection
```

Or via API:

```bash
curl -X POST http://localhost:8000/api/zammad/test-connection \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

## Usage

### Manual Synchronization

#### Command Line

Sync all configured groups:

```bash
python manage.py sync_zammad_tickets
```

Sync specific groups:

```bash
python manage.py sync_zammad_tickets --groups "Support,Development"
```

#### API Endpoint

```bash
# Sync all configured groups
curl -X POST http://localhost:8000/api/zammad/sync \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# Sync specific groups
curl -X POST http://localhost:8000/api/zammad/sync \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"groups": ["Support", "Development"]}'
```

### Check Synchronization Status

```bash
curl -X GET http://localhost:8000/api/zammad/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:

```json
{
  "success": true,
  "enabled": true,
  "api_url": "https://support.example.com",
  "configured_groups": ["Support", "Development"],
  "sync_interval_minutes": 15,
  "statistics": {
    "total_tasks": 42,
    "new": 10,
    "working": 25,
    "done": 7,
    "last_sync": "2025-10-22T12:00:00Z"
  }
}
```

### Periodic Synchronization (Cron)

Add to your crontab for automatic synchronization every 15 minutes:

```cron
*/15 * * * * cd /path/to/ideagraph && /path/to/python manage.py sync_zammad_tickets >> /var/log/zammad_sync.log 2>&1
```

## Field Mapping

### Zammad Ticket → IdeaGraph Task

| Zammad Field | IdeaGraph Field | Description |
|--------------|-----------------|-------------|
| `ticket.title` | `task.title` | Ticket subject becomes task title |
| `ticket.article[0].body` | `task.description` | First article body becomes task description |
| `ticket.group` | `task.section` | Group mapped to section (auto-created as "Zammad - {Group}") |
| `ticket.tags` | `task.tags` | Tags are transferred and auto-created if needed |
| `ticket.id` | `task.external_id` | Ticket ID stored for reference |
| `ticket.url` | `task.external_url` | Direct link to ticket in Zammad |
| `ticket.attachments` | `task.files` | All attachments downloaded and linked to task |
| `ticket.state` | `task.status` | Initially set to "new", updated to "open" in Zammad after sync |
| `ticket.created_by` | `task.owner` | Optional: Can be mapped if user exists in IdeaGraph |

### Task Type Classification

Tasks are classified with the following types:

- **task**: General task (default)
- **feature**: Feature request
- **bug**: Bug report
- **ticket**: Support ticket
- **maintenance**: Maintenance work

#### AI-Powered Classification

If KiGate API is enabled, tasks are automatically classified using the `task-type-classifier` agent based on the title and description. The AI analyzes the content and determines the most appropriate type.

## Database Models

### Task Model Additions

```python
class Task(models.Model):
    # ... existing fields ...
    
    type = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        default='task'
    )
    external_id = models.CharField(
        max_length=255, 
        blank=True, 
        default=''
    )
    external_url = models.URLField(
        max_length=500, 
        blank=True, 
        default=''
    )
    section = models.ForeignKey(
        Section, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
```

### TaskFile Model

```python
class TaskFile(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    file_path = models.CharField(max_length=500)
    sharepoint_file_id = models.CharField(max_length=255, blank=True)
    sharepoint_url = models.URLField(max_length=1000, blank=True)
    content_type = models.CharField(max_length=100)
    # ... metadata fields ...
```

## API Reference

### POST /api/zammad/test-connection

Test connection to Zammad API.

**Authentication**: Admin required

**Response**:
```json
{
  "success": true,
  "message": "Connection successful",
  "user": "api_user",
  "api_url": "https://support.example.com"
}
```

### POST /api/zammad/sync

Manually trigger ticket synchronization.

**Authentication**: Admin required

**Request Body** (optional):
```json
{
  "groups": ["Support", "Development"]
}
```

**Response**:
```json
{
  "success": true,
  "started_at": "2025-10-22T12:00:00Z",
  "completed_at": "2025-10-22T12:00:45Z",
  "duration_seconds": 45.2,
  "total_tickets": 10,
  "created": 3,
  "updated": 7,
  "failed": 0,
  "errors": []
}
```

### GET /api/zammad/status

Get synchronization status and statistics.

**Authentication**: Admin required

**Response**: See "Check Synchronization Status" section above.

## Troubleshooting

### Connection Failures

**Problem**: "Request timeout" or "Connection refused"

**Solutions**:
- Verify `zammad_api_url` is correct and accessible
- Check firewall rules allow outbound connections to Zammad
- Ensure Zammad instance is running and accessible

### Authentication Errors

**Problem**: "Authentication failed" or 403 errors

**Solutions**:
- Verify API token is valid and not expired
- Ensure API token has sufficient permissions (tickets read/write)
- Regenerate API token if necessary

### Missing Tickets

**Problem**: Some tickets are not synced

**Solutions**:
- Verify group names in `zammad_groups` match exactly (case-sensitive)
- Check ticket states - only open/new tickets are synced by default
- Review logs for specific error messages: `/path/to/logs/ideagraph.log`

### Attachment Download Failures

**Problem**: Attachments not downloading

**Solutions**:
- Check disk space in attachment directory
- Verify file permissions for `zammad_attachments/` directory
- Check Zammad API token permissions include attachment access

## Security Considerations

- ✅ **Token Encryption**: API tokens should be encrypted at rest (recommended)
- ✅ **HTTPS Required**: Always use HTTPS for Zammad API URL in production
- ✅ **Access Control**: Only admin users can trigger synchronization or access status
- ✅ **File Validation**: Attachment downloads validate file types and sizes
- ✅ **Logging**: All synchronization activities are logged with rotation

## Performance

- **Typical sync time**: 1-5 seconds per ticket
- **Recommended interval**: 15-30 minutes
- **Concurrent requests**: Synchronization is sequential to avoid API rate limits
- **Attachment handling**: Downloads are throttled to prevent overwhelming the network

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Zammad    │   API   │  IdeaGraph   │  Store  │  Database   │
│   Server    │◄────────┤   Sync       ├────────►│  + Files    │
│             │         │   Service    │         │             │
└─────────────┘         └──────────────┘         └─────────────┘
                              │
                              │ Optional
                              ▼
                        ┌──────────────┐
                        │   KiGate     │
                        │   AI Agent   │
                        └──────────────┘
```

## Changelog

### Version 1.0.0 (2025-10-22)

- ✅ Initial release
- ✅ Basic ticket synchronization
- ✅ Attachment download support
- ✅ AI-powered classification
- ✅ Management commands
- ✅ API endpoints
- ✅ Comprehensive test coverage

## Support

For issues or questions:

1. Check logs: `/path/to/logs/ideagraph.log`
2. Review this documentation
3. Open an issue on GitHub
4. Contact support team

## License

See LICENSE file in repository root.
