# Teams Message Posting Authentication Fix

## Problem

Posting messages to Microsoft Teams channels was failing with the following error:

```
Error: Unauthorized
Message: Message POST is allowed in application-only context only for import purposes.
```

This error indicates that the code was using **app-only authentication** (client credentials flow with "roles" claim) instead of **delegated user authentication** (with "scp" claim) when posting messages to Teams channels.

## Root Cause

Microsoft Graph API has specific requirements for Teams channel message posting:
- **Reading messages**: Can use app-only authentication (Application permissions)
- **Posting messages**: Requires delegated user authentication (Delegated permissions)

The `GraphResponseService` was initializing `GraphService` without passing the `use_delegated_auth` parameter:

```python
# BEFORE (Incorrect)
self.graph_service = GraphService(settings=settings)  # Defaults to app-only auth
```

This caused it to default to app-only authentication, which is not allowed for posting messages to Teams channels (except for import purposes).

## Solution

The fix ensures that `GraphResponseService` uses delegated authentication when initializing `GraphService`:

```python
# AFTER (Correct)
use_delegated = getattr(self.settings, 'teams_use_delegated_auth', True)
self.graph_service = GraphService(settings=settings, use_delegated_auth=use_delegated)
```

## Implementation Details

### Services Analysis

1. **GraphResponseService** ❌ → ✅ FIXED
   - **Purpose**: Posts AI-generated responses to Teams channels
   - **Issue**: Was not using delegated auth
   - **Fix**: Now reads `teams_use_delegated_auth` setting and passes it to GraphService

2. **TeamsService** ✅ Already Correct
   - **Purpose**: Creates channels and posts welcome messages
   - **Status**: Already correctly using delegated auth

3. **TeamsListenerService** ✅ Correct (No Change Needed)
   - **Purpose**: Reads messages from Teams channels
   - **Status**: Uses app-only auth (which is fine for reading)

### Authentication Flow

The application supports two authentication flows:

#### App-Only Authentication (Client Credentials)
- Uses: `client_id`, `client_secret`, `tenant_id`
- Grants: Application permissions (roles)
- Use cases: Reading data, background operations
- Token claim: `"roles": ["ChannelMessage.Read.All"]`

#### Delegated Authentication (Device Code Flow)
- Uses: `client_id`, `tenant_id`, user consent via device code
- Grants: Delegated permissions (scp)
- Use cases: Acting on behalf of a user (posting messages)
- Token claim: `"scp": "ChannelMessage.Send Channel.ReadBasic.All"`
- Setup: Run `python manage.py auth_teams`

## Configuration

### Settings Model

The `teams_use_delegated_auth` field in the Settings model controls which authentication method to use:

```python
teams_use_delegated_auth = models.BooleanField(
    default=True,
    verbose_name='Use Delegated Auth for Teams',
    help_text='Use delegated user authentication (device code flow) for Teams channel posting. Required for posting messages.'
)
```

### Required Permissions

#### Application Permissions (App-Only)
- `ChannelMessage.Read.All` - Read channel messages
- `Channel.ReadBasic.All` - Read basic channel info
- `Team.ReadBasic.All` - Read basic team info

#### Delegated Permissions (User)
- `ChannelMessage.Send` - Send messages to channels
- `Channel.ReadBasic.All` - Read basic channel info
- `Team.ReadBasic.All` - Read basic team info

## Setup Instructions

### 1. Azure AD App Registration

Ensure your Azure AD app registration has the correct permissions configured:

1. Go to Azure Portal → Azure Active Directory → App Registrations
2. Select your application
3. Go to "API permissions"
4. Verify both Application and Delegated permissions are granted
5. Grant admin consent for the organization

### 2. Enable Delegated Authentication

In IdeaGraph settings:
1. Set `teams_use_delegated_auth` to `True` (default)
2. Ensure `teams_enabled` is `True`
3. Configure `teams_team_id` with your Teams team ID

### 3. Authenticate via Device Code Flow

Run the authentication command:

```bash
python manage.py auth_teams
```

This will:
1. Display a device code and verification URL
2. Wait for you to authenticate in a browser
3. Store the access token and refresh token
4. Token is valid for 90 days with regular use (automatic refresh)

To check authentication status:

```bash
python manage.py auth_teams --check
```

To clear tokens and re-authenticate:

```bash
python manage.py auth_teams --clear
```

### 4. Token Storage

Tokens are stored in:
- File: `data/msal_token_cache.bin`
- Format: MSAL serializable token cache
- Security: Contains sensitive tokens, ensure proper file permissions
- Auto-refresh: MSAL automatically refreshes tokens using refresh token

## Testing

### Manual Testing

1. Authenticate:
   ```bash
   python manage.py auth_teams
   ```

2. Try posting a message via the API or trigger Teams integration

3. Check logs for authentication method:
   ```
   [graph_service] - Using delegated user access token
   ```

### Unit Tests

Existing tests in `main/test_teams_message_integration.py` cover the Teams integration functionality. The tests mock the authentication layer, so they don't require actual Microsoft authentication.

## Troubleshooting

### Error: "Delegated authentication token not available"

**Cause**: Token not available or expired
**Solution**: Run `python manage.py auth_teams` to authenticate

### Error: "teams_use_delegated_auth is not enabled in Settings"

**Cause**: Delegated auth is disabled in settings
**Solution**: Set `teams_use_delegated_auth = True` in Settings model

### Error: "Failed to acquire access token"

**Cause**: Network issue or invalid credentials
**Solution**: 
1. Check internet connectivity
2. Verify Azure AD app credentials
3. Ensure app permissions are granted
4. Try clearing cache: `python manage.py auth_teams --clear`

### Token Expired After 90 Days

**Cause**: Refresh token expired due to inactivity
**Solution**: Re-authenticate with `python manage.py auth_teams`

## Technical Notes

### Why Delegated Auth is Required

Microsoft's security model distinguishes between:
- **Application context**: The app acts on its own behalf
- **User context**: The app acts on behalf of a specific user

For Teams message posting, Microsoft requires user context to:
1. Track who posted the message (for audit logs)
2. Apply user-specific permissions and policies
3. Maintain conversation threading and notifications
4. Prevent automated spam/abuse

### Token Claims Comparison

**App-Only Token:**
```json
{
  "aud": "https://graph.microsoft.com",
  "roles": ["ChannelMessage.Read.All", "Channel.ReadBasic.All"],
  "sub": "<app-object-id>",
  ...
}
```

**Delegated Token:**
```json
{
  "aud": "https://graph.microsoft.com",
  "scp": "ChannelMessage.Send Channel.ReadBasic.All Team.ReadBasic.All",
  "upn": "user@domain.com",
  "sub": "<user-object-id>",
  ...
}
```

### MSAL Token Cache

The application uses MSAL (Microsoft Authentication Library) which:
- Automatically handles token refresh using refresh tokens
- Maintains a sliding 90-day window (refreshed on each use)
- Stores tokens securely in serialized cache
- Handles concurrent access and token expiration

## Related Files

- `core/services/graph_response_service.py` - Fixed to use delegated auth
- `core/services/graph_service.py` - Base service with auth support
- `core/services/delegated_auth_service.py` - Handles device code flow
- `core/services/teams_service.py` - Already using delegated auth
- `main/management/commands/auth_teams.py` - Authentication command
- `main/models.py` - Settings model with `teams_use_delegated_auth` field

## References

- [Microsoft Teams Graph API Documentation](https://docs.microsoft.com/microsoftteams/platform/graph-api/import-messages/import-external-messages-to-teams)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [OAuth 2.0 Device Code Flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code)
- [Microsoft Graph Permissions Reference](https://docs.microsoft.com/en-us/graph/permissions-reference)
