# Teams Integration - Quick Reference

## Overview
Microsoft Teams integration for IdeaGraph allows automatic creation of Teams channels for items, enabling team communication and collaboration directly from the IdeaGraph interface.

## Quick Setup

### 1. Azure AD Permissions
Required Microsoft Graph permissions:
- `Channel.Create`
- `ChannelMessage.Send`
- `Group.Read.All`
- `TeamMember.Read.All` (optional)

### 2. Get Team ID
**Via Teams Web App:**
1. Open team in browser
2. Click "..." → "Get link to team"
3. Extract `groupId` from URL

**Via Graph Explorer:**
```
GET https://graph.microsoft.com/v1.0/me/joinedTeams
```

### 3. Configure IdeaGraph Settings
Admin → Settings → Microsoft Teams Integration:
- ✅ Enable Teams Integration
- Teams Team ID: `your-team-id`
- Welcome Post Template: `Welcome to {{Item}}!`

## Usage

### Create Channel
1. Go to Items → Tile View
2. Click red Teams icon on item card
3. Wait for success notification
4. Icon turns green

### Open Channel
1. Click green Teams icon
2. Teams opens in new tab

## API Endpoint

```
POST /api/items/<item_id>/create-teams-channel
```

**Success Response:**
```json
{
  "success": true,
  "channel_id": "19:abc...",
  "web_url": "https://teams.microsoft.com/..."
}
```

## Database Schema

**Settings:**
```python
teams_enabled: Boolean
teams_team_id: String
team_welcome_post: TextField
```

**Item:**
```python
channel_id: String
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Integration not configured | Check Graph API settings and Team ID |
| Channel exists error | Clear channel_id in Admin |
| Message not posted | Verify ChannelMessage.Send permission |
| Token error | Check credentials and clear cache |

## Testing

```bash
python manage.py test main.test_teams_integration
```

✅ 12 tests passing

## Security Notes

- No stack traces exposed to users
- All operations logged server-side
- Requires authentication
- Generic error messages for users

## Limitations

- Message pinning requires elevated permissions
- Auto-member management not supported
- Standard channels accessible to all team members

## Links

- [Full Documentation](TEAMS_INTEGRATION_GUIDE.md)
- [Microsoft Graph Teams API](https://docs.microsoft.com/graph/api/resources/teams-api-overview)
- [Azure AD Setup](https://portal.azure.com)
