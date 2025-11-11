# Sentry Integration Guide

## Overview

The Sentry Integration feature allows IdeaGraph to automatically fetch errors from Sentry and create Bug tasks for Items that have Sentry monitoring configured. This enables automated error tracking and task creation for development teams.

## Features

- **Automatic Error Fetching**: Automatically fetch errors from Sentry API
- **Regional Sentry Support**: Automatically detects and uses correct API endpoints for regional Sentry instances (EU, US, etc.)
- **Bug Task Creation**: Create Bug-type tasks from Sentry errors
- **Duplicate Detection**: Prevent creating duplicate tasks for the same error
- **Time-based Filtering**: Only fetch errors from the last 24 hours (configurable)
- **Manual and Automated Sync**: Support for both user-triggered and cron-based synchronization
- **Multi-Item Support**: Configure Sentry for multiple Items independently

## Configuration

### 1. Settings Configuration

First, configure the global Sentry API token in Settings (Admin access required):

1. Navigate to **Settings** → **Admin Settings**
2. Add or edit the Settings record
3. Set the **Sentry Auth Token** field with your Sentry API token

To get a Sentry Auth Token:
1. Go to your Sentry dashboard
2. Navigate to **Settings** → **Account** → **API** → **Auth Tokens**
3. Create a new token with the following permissions:
   - `project:read`
   - `org:read`
   - `event:read`

### 2. Item Configuration

For each Item that should fetch Sentry errors:

1. Navigate to the Item detail page
2. Click **Edit**
3. Configure the following Sentry fields:
   - **Sentry DSN**: The Data Source Name from your Sentry project
     - Format: `https://<key>@<org>.ingest[.region].sentry.io/<project_id>`
     - Example (default): `https://abc123@o123456.ingest.sentry.io/789012`
     - Example (EU/DE): `https://abc123@o123456.ingest.de.sentry.io/789012`
     - Example (US): `https://abc123@o123456.ingest.us.sentry.io/789012`
     - **Required**: This is the primary identifier for your Sentry project
     - **Note**: The system automatically detects the region from the DSN and uses the appropriate API endpoint
   - **Sentry Project Slug**: The project slug from Sentry
     - Example: `ideagraph-v1`, `my-app`
     - **Auto-detected**: Leave empty to automatically fetch from Sentry API
     - **Optional**: Only needed if auto-detection fails or you want to override
   - **Enable Auto-Fetch**: Check this box to enable automatic error fetching

4. Save the Item

**Note**: When you provide a Sentry DSN but leave the Project Slug empty, the system will automatically query the Sentry API to fetch and save the correct project slug. This eliminates the need to manually look up the project slug in your Sentry settings.

## Usage

### Manual Error Fetch (User-Triggered)

#### Via API

Make a POST request to fetch Sentry errors for a specific Item:

```bash
POST /api/items/<item_id>/fetch-sentry-errors
Content-Type: application/json

{
  "hours_back": 24  // Optional, defaults to 24
}
```

**Response:**
```json
{
  "success": true,
  "issues_fetched": 5,
  "tasks_created": 3,
  "duplicates_skipped": 2,
  "message": "Successfully fetched 5 issues and created 3 tasks"
}
```

### Automated Error Fetch (CLI/Cron)

#### CLI Script

The `sync_sentry_errors.py` script can be run manually or scheduled via cron:

**Sync errors for a specific Item:**
```bash
python sync_sentry_errors.py --item-id <uuid>
```

**Sync errors for all Items with Sentry enabled:**
```bash
python sync_sentry_errors.py --all-items
```

**Sync errors from last 48 hours:**
```bash
python sync_sentry_errors.py --all-items --hours 48
```

**Dry run (no changes):**
```bash
python sync_sentry_errors.py --all-items --dry-run
```

**Verbose logging:**
```bash
python sync_sentry_errors.py --all-items --verbose
```

#### Cron Job Setup

To automatically fetch Sentry errors on a schedule, add a cron job:

**Example: Sync all items every hour**
```bash
0 * * * * cd /path/to/IdeaGraph-v1 && python sync_sentry_errors.py --all-items >> logs/sync_sentry.log 2>&1
```

**Example: Sync all items daily at 3 AM**
```bash
0 3 * * * cd /path/to/IdeaGraph-v1 && python sync_sentry_errors.py --all-items >> logs/sync_sentry.log 2>&1
```

**Example: Sync specific item every 30 minutes**
```bash
*/30 * * * * cd /path/to/IdeaGraph-v1 && python sync_sentry_errors.py --item-id abc-123-def --hours 1 >> logs/sync_sentry.log 2>&1
```

## How It Works

### Automatic Project Slug Detection

When you configure a Sentry DSN without specifying a project slug, the system automatically:

1. **Parse the DSN**: Extracts the organization and project ID from the DSN
2. **Query Sentry API**: Fetches the list of projects from your Sentry organization
3. **Match Project**: Finds the project matching the ID from the DSN
4. **Save Slug**: Automatically saves the project slug to the Item

This automation happens:
- When creating a new Item with a Sentry DSN
- When updating an Item's Sentry DSN
- When running the sync script for the first time on an Item without a project slug

**Benefits**:
- No need to manually look up the project slug in Sentry settings
- Reduces configuration errors
- Simplifies the setup process

**Requirements**:
- A valid Sentry Auth Token must be configured in Settings
- The auth token must have `project:read` and `org:read` permissions

### Error Fetching Process

1. **Query Sentry API**: The service queries the Sentry API for issues in the configured project
2. **Time Filtering**: Only issues from the last N hours (default 24) are fetched
3. **Duplicate Detection**: Each issue is checked against existing tasks to prevent duplicates:
   - By Sentry Issue ID (stored in `external_id` field)
   - By exact title match
4. **Task Creation**: For each unique error, a Bug task is created with:
   - **Title**: From the Sentry issue title
   - **Description**: Formatted markdown with error details
   - **Type**: Bug
   - **Status**: New
   - **Item**: Linked to the configured Item
   - **External ID**: `sentry-<issue_id>` for duplicate detection
   - **External URL**: Link to the Sentry issue
   - **Tags**: Inherited from the parent Item

### Task Description Format

Tasks created from Sentry errors include:

- Error title and message
- Sentry Issue ID and URL
- Severity level
- Number of occurrences
- Number of affected users
- Error type and value
- Timeline (first seen, last seen)
- Code location (culprit)

Example:
```markdown
# ValueError in user authentication

**Sentry Issue ID:** 123456789
**Sentry URL:** [https://sentry.io/issues/123456789](https://sentry.io/issues/123456789)
**Severity:** ERROR
**Occurrences:** 15
**Affected Users:** 8

## Error Details

**Type:** `ValueError`
**Message:** Cannot authenticate user with invalid credentials

## Timeline

**First Seen:** 2024-01-15T10:30:00Z
**Last Seen:** 2024-01-15T14:45:00Z

## Location

```
app.auth.authenticate_user
```

---
*This task was automatically created from a Sentry error.*
```

## Duplicate Detection

The system prevents creating duplicate tasks through two mechanisms:

1. **Sentry Issue ID**: Each task stores the Sentry issue ID in the `external_id` field with format `sentry-<issue_id>`. Before creating a new task, the system checks if a task with the same external_id already exists.

2. **Title Matching**: If the external_id doesn't match, the system also checks for exact title matches to catch cases where the Sentry issue ID might have changed.

If a duplicate is detected, the sync process skips creating a new task and logs it in the statistics.

## Troubleshooting

### Error 404 - Issues not found

If you're getting a 404 error when fetching issues:

1. **Check Regional Endpoint (Most Common)**:
   - The system now automatically detects regional Sentry instances from the DSN
   - Verify your DSN is correct and includes the proper regional domain:
     - Default: `https://key@org.ingest.sentry.io/project`
     - EU/DE: `https://key@org.ingest.de.sentry.io/project`
     - US: `https://key@org.ingest.us.sentry.io/project`
   - The system will automatically use:
     - `https://sentry.io/api/0` for default instances
     - `https://de.sentry.io/api/0` for EU/DE instances
     - `https://us.sentry.io/api/0` for US instances

2. **Check Project Slug**:
   - Ensure the project slug is correctly set or can be auto-detected
   - The project slug must match exactly with your Sentry project
   
3. **Check Organization ID**:
   - Ensure the organization ID in the DSN is correct
   - For Sentry SaaS, this usually starts with 'o' followed by numbers (e.g., `o4510215672365056`)

4. **Check Auth Token Permissions**:
   - Token must have `project:read`, `org:read`, and `event:read` permissions
   - Token must be valid for the specific Sentry organization

### Project Slug is not auto-detected

If the project slug is not automatically filled in:

1. **Check Sentry Auth Token**:
   - Ensure the Sentry Auth Token is configured in Settings or per-Item
   - Verify the token has `project:read` and `org:read` permissions
   
2. **Check DSN Format**:
   - Ensure the DSN follows the format: `https://<key>@<org>.ingest[.region].sentry.io/<project_id>`
   - Verify the organization and project ID are correct
   
3. **Check Network Access**:
   - Ensure the server can reach the appropriate Sentry API endpoint
   - For regional instances, ensure access to `de.sentry.io`, `us.sentry.io`, etc.
   - Check for firewall or proxy restrictions
   
4. **Manual Override**:
   - If auto-detection fails, you can manually enter the project slug
   - Find it in Sentry: Settings → Projects → [Your Project] → Project Slug

### No errors are being fetched

1. **Check Sentry Configuration**:
   - Verify the Sentry Auth Token is set in Settings
   - Verify the Sentry DSN is correct for the Item
   - Verify the Sentry Project Slug is present (should be auto-filled or manually entered)
   - Verify "Enable Auto-Fetch" is checked

2. **Check Sentry API Token Permissions**:
   - Token must have `project:read`, `org:read`, and `event:read` permissions

3. **Check Time Range**:
   - By default, only errors from the last 24 hours are fetched
   - Try increasing the `--hours` parameter

4. **Check Logs**:
   ```bash
   # View sync logs
   tail -f logs/sync_sentry.log
   
   # Run with verbose logging
   python sync_sentry_errors.py --item-id <uuid> --verbose
   ```

### Tasks are being duplicated

This shouldn't happen due to the duplicate detection mechanism. If it does:

1. Check if the `external_id` field is being set correctly
2. Check if the Sentry issue ID format has changed
3. Review the logs for duplicate detection messages

### API endpoint returns error

1. **401 Unauthorized**: Ensure you're authenticated (logged in or using JWT token)
2. **404 Not Found**: Verify the Item ID is correct
3. **400 Bad Request**: Check error message for specific configuration issues
4. **500 Internal Server Error**: Check application logs for detailed error information

## Database Schema

### Item Model Fields

- `sentry_dsn` (CharField, max_length=500): Sentry DSN for error tracking
- `sentry_project_slug` (CharField, max_length=255): Sentry project slug
- `enable_sentry_fetch` (BooleanField): Enable automatic error fetching

### Settings Model Fields

- `sentry_auth_token` (CharField, max_length=255): Sentry API authentication token

### Task Fields Used

- `external_id`: Stores `sentry-<issue_id>` for duplicate detection
- `external_url`: Stores the Sentry issue URL
- `type`: Set to `bug` for Sentry-created tasks
- `ai_generated`: Set to `True` to indicate automated creation

## API Reference

### Fetch Sentry Errors

**Endpoint**: `POST /api/items/<item_id>/fetch-sentry-errors`

**Authentication**: Required (Session or JWT)

**Request Body**:
```json
{
  "hours_back": 24  // Optional, number of hours to look back
}
```

**Success Response** (200):
```json
{
  "success": true,
  "issues_fetched": 5,
  "tasks_created": 3,
  "duplicates_skipped": 2,
  "message": "Successfully fetched 5 issues and created 3 tasks"
}
```

**Error Responses**:

- **401 Unauthorized**:
  ```json
  {
    "success": false,
    "error": "Authentication required"
  }
  ```

- **404 Not Found**:
  ```json
  {
    "success": false,
    "error": "Item not found"
  }
  ```

- **400 Bad Request**:
  ```json
  {
    "success": false,
    "error": "Sentry DSN not configured for this item"
  }
  ```

## Best Practices

1. **Configure Sentry for Critical Items**: Enable Sentry integration only for Items where automated error tracking is valuable

2. **Set Appropriate Sync Frequency**: 
   - For production systems: Every hour or every 30 minutes
   - For development systems: Every 4-6 hours

3. **Monitor Sync Logs**: Regularly check sync logs to ensure errors are being fetched successfully

4. **Review Created Tasks**: Periodically review auto-created Bug tasks to ensure they're actionable

5. **Use Dry Run for Testing**: When setting up or troubleshooting, use `--dry-run` to preview what would happen without actually creating tasks

6. **Tag Management**: Since tasks inherit tags from their parent Item, ensure Items have appropriate tags for organization

## Security Considerations

1. **Sentry Auth Token**: Store the Sentry auth token securely in the Settings. Only admin users should have access to Settings.

2. **API Access**: The Sentry fetch API endpoint requires authentication. Ensure proper session or JWT authentication is in place.

3. **Rate Limiting**: Be mindful of Sentry API rate limits when configuring sync frequency.

4. **Error Information**: Sentry errors may contain sensitive information. Ensure that task descriptions don't expose sensitive data inappropriately.

## Related Documentation

- [Sentry API Documentation](https://docs.sentry.io/api/)
- [Task Management Guide](./TASK_MANAGEMENT.md) (if available)
- [CLI Scripts Documentation](./CLI_SCRIPTS_DOCUMENTATION.md)

## Support

For issues or questions regarding the Sentry integration, please:

1. Check the Troubleshooting section above
2. Review the application logs
3. Check the Sentry API documentation
4. Contact the development team

---

*Last updated: 2024-11-10*
