# Teams Message Posting Auth Fix - Quick Reference

## Quick Summary

**Problem:** Teams message posting failed with "Unauthorized" error  
**Root Cause:** Using app-only authentication instead of delegated user authentication  
**Solution:** Fixed `GraphResponseService` to use delegated authentication  

## Quick Setup

1. **Authenticate Once:**
   ```bash
   python manage.py auth_teams
   ```

2. **Follow Browser Prompts:**
   - Open: https://microsoft.com/devicelogin
   - Enter the code shown
   - Sign in with your Microsoft account
   - Grant permissions

3. **Done!** Token is cached for 90 days and auto-refreshes.

## Quick Commands

```bash
# Authenticate with Microsoft
python manage.py auth_teams

# Check authentication status
python manage.py auth_teams --check

# Clear tokens and re-authenticate
python manage.py auth_teams --clear
```

## What Changed

### Before (Broken)
```python
# GraphResponseService
self.graph_service = GraphService(settings=settings)  # ❌ App-only auth
```

### After (Fixed)
```python
# GraphResponseService
use_delegated = getattr(self.settings, 'teams_use_delegated_auth', True)
self.graph_service = GraphService(settings=settings, use_delegated_auth=use_delegated)  # ✅ Delegated auth
```

## Authentication Types

| Type | Use Case | Permissions | Token Claim |
|------|----------|-------------|-------------|
| **App-Only** | Reading messages, background tasks | Application | `roles` |
| **Delegated** | Posting messages, user actions | Delegated | `scp` |

## Troubleshooting

| Error | Solution |
|-------|----------|
| "Unauthorized" | Run `python manage.py auth_teams` |
| "Token not available" | Run `python manage.py auth_teams` |
| "teams_use_delegated_auth not enabled" | Set to `True` in Settings |
| Token expired | Re-run `python manage.py auth_teams` |

## Services Status

| Service | Posts Messages? | Auth Type | Status |
|---------|----------------|-----------|--------|
| GraphResponseService | ✅ Yes | Delegated | ✅ Fixed |
| TeamsService | ✅ Yes | Delegated | ✅ OK |
| TeamsListenerService | ❌ No (reads only) | App-Only | ✅ OK |

## Required Azure AD Permissions

### Delegated (User) - Required for Posting
- ✅ `ChannelMessage.Send`
- ✅ `Channel.ReadBasic.All`
- ✅ `Team.ReadBasic.All`

### Application - For Reading
- ✅ `ChannelMessage.Read.All`
- ✅ `Channel.ReadBasic.All`
- ✅ `Team.ReadBasic.All`

## Files Changed

- ✅ `core/services/graph_response_service.py` - Added delegated auth support

## Documentation

- 📖 Full Guide: `TEAMS_MESSAGE_POSTING_AUTH_FIX.md`
- 📖 Teams Integration: `TEAMS_INTEGRATION_GUIDE.md`
- 📖 Teams Device Code: `TEAMS_DEVICE_CODE_AUTH_GUIDE.md`
