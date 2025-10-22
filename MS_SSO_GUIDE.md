# Microsoft Identity SSO Authentication - Implementation Guide

## Overview
IdeaGraph v1.0 now supports Microsoft Identity Single Sign-On (SSO) authentication alongside the existing local authentication. Users can log in using their Microsoft corporate accounts with automatic user provisioning.

## Features

✅ **Microsoft Identity SSO Integration**
- OAuth 2.0 authorization code flow
- Automatic user creation on first login
- User profile synchronization from Microsoft Graph
- Avatar/photo retrieval from Microsoft
- Seamless authentication experience

✅ **Dual Authentication Support**
- Local authentication (username/password)
- Microsoft SSO authentication
- Users tagged with auth_type (local/msauth)

✅ **Security Features**
- CSRF protection via state parameter
- Secure token exchange
- Role-based access control maintained
- Password management disabled for MS Auth users

✅ **User Management**
- Automatic user provisioning on first SSO login
- UPN (User Principal Name) used as username
- Last login timestamp updated on each login
- Default role: User (can be changed by admin)

## Azure AD Configuration

### 1. Register Application in Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Configure:
   - **Name**: IdeaGraph SSO
   - **Supported account types**: Accounts in this organizational directory only
   - **Redirect URI**: Web - `https://your-domain.com/login/microsoft/callback/`
5. Click **Register**

### 2. Configure Application

1. Note the **Application (client) ID** and **Directory (tenant) ID**
2. Go to **Certificates & secrets**
3. Create a new **Client secret**
4. Note the secret value (you won't be able to see it again)
5. Go to **API permissions**
6. Add the following Microsoft Graph permissions:
   - `User.Read` (Read user profile)
   - Note: `openid`, `profile`, and `email` are automatically included by MSAL and don't need to be explicitly added
7. Grant admin consent for the organization

### 3. Configure Redirect URIs

Add the following redirect URIs in Azure AD:
- Production: `https://your-production-domain.com/login/microsoft/callback/`
- Development: `http://localhost:8000/login/microsoft/callback/`

## IdeaGraph Configuration

### 1. Enable MS SSO in Settings

1. Login as admin
2. Navigate to **Admin** → **Settings**
3. Scroll to **SSO Microsoft Authentication** section
4. Configure:
   - ✅ **Enable Microsoft SSO**: Checked
   - **Client ID**: Your Azure AD Application (Client) ID
   - **Tenant ID**: Your Azure AD Directory (Tenant) ID
   - **Client Secret**: Your Azure AD Client Secret (optional)
5. Click **Update Settings**

### 2. Verify Configuration

1. Log out
2. Go to login page
3. You should see the "Sign in with Microsoft" button
4. Click the button to test SSO login

## User Experience

### First-Time Login
1. User clicks "Sign in with Microsoft" on login page
2. User is redirected to Microsoft login page
3. User authenticates with Microsoft credentials
4. User consents to app permissions (first time only)
5. User is redirected back to IdeaGraph
6. **New user account is automatically created** with:
   - Username: User's UPN (User Principal Name)
   - Email: User's email from Microsoft profile
   - Auth Type: msauth
   - Role: user (default)
   - Last Login: Current timestamp
   - Avatar URL: Link to user's Microsoft profile photo

### Subsequent Logins
1. User clicks "Sign in with Microsoft"
2. User is redirected to Microsoft (may auto-login if already signed in)
3. User is redirected back to IdeaGraph
4. User profile is updated:
   - Email (if changed)
   - Avatar URL (if changed)
   - Last Login timestamp

### User Management

#### For MS Auth Users:
- ❌ **Cannot change password** (managed by Microsoft)
- ❌ **No password reset** option available
- ✅ Can be managed by admin (role, status, etc.)
- ✅ Auth type displayed in user list and detail pages
- ✅ Avatar from Microsoft displayed (if available)

#### For Local Users:
- ✅ Can change password
- ✅ Can reset password via email
- ✅ Full password management capabilities

## Database Schema Changes

### User Model Extensions
```python
auth_type = models.CharField(
    max_length=20, 
    choices=[('local', 'Local'), ('msauth', 'Microsoft')],
    default='local'
)
ms_user_id = models.CharField(
    max_length=255, 
    blank=True, 
    help_text='Microsoft User ID (OID)'
)
avatar_url = models.URLField(
    max_length=500, 
    blank=True, 
    help_text='URL to user avatar image'
)
```

### Settings Model Extensions
```python
ms_sso_enabled = models.BooleanField(default=False)
ms_sso_client_id = models.CharField(max_length=255, blank=True)
ms_sso_tenant_id = models.CharField(max_length=255, blank=True)
ms_sso_client_secret = models.CharField(max_length=255, blank=True)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/login/microsoft/` | GET | Initiate MS SSO login |
| `/login/microsoft/callback/` | GET | MS SSO callback handler |
| `/login/` | GET/POST | Standard login (shows MS SSO button if enabled) |
| `/logout/` | POST | Logout (works for both auth types) |

## Security Considerations

### HTTPS Requirement
- **Production**: HTTPS is **required** for MS SSO
- **Development**: HTTP is acceptable for localhost only

### State Parameter
- CSRF protection via state parameter
- State is generated and validated on callback

### Token Handling
- Access tokens are never stored
- Tokens are only used during authentication flow
- User profile data is retrieved and stored

### Permissions
- Minimal permissions requested (User.Read)
- No write permissions to Microsoft Graph
- Read-only access to user profile

## Troubleshooting

### "Microsoft SSO is not enabled" Error
**Cause**: MS SSO is disabled in settings
**Solution**: Enable it in Admin → Settings → SSO Microsoft Authentication

### "Microsoft SSO is not properly configured" Error
**Cause**: Missing Client ID or Tenant ID
**Solution**: Verify configuration in Settings and Azure AD

### "Invalid authentication state" Error
**Cause**: State parameter mismatch (possible CSRF attempt)
**Solution**: Clear browser cookies and try again

### "Failed to get user profile" Error
**Cause**: Invalid access token or API permissions
**Solution**: 
1. Verify API permissions in Azure AD
2. Ensure admin consent is granted
3. Check Azure AD application is enabled

### User Cannot Login After SSO
**Cause**: User account may be inactive
**Solution**: Admin should verify user is active in User Management

### Redirect URI Mismatch Error
**Cause**: Redirect URI in Azure AD doesn't match application
**Solution**: 
1. Check redirect URI in Azure AD matches exactly
2. Include trailing slash: `/login/microsoft/callback/`
3. Ensure protocol matches (http vs https)

## Testing

### Run MS SSO Tests
```bash
python manage.py test main.test_ms_auth
```

### Test Coverage
- 16 comprehensive tests
- Service initialization
- Authorization flow
- User profile retrieval
- Avatar retrieval
- User auto-creation
- Password change restrictions
- UI integration
- Settings management

### Manual Testing Checklist
- [ ] MS SSO button appears when enabled
- [ ] MS SSO button hidden when disabled
- [ ] Login redirects to Microsoft
- [ ] New user is created on first login
- [ ] Existing user is updated on subsequent logins
- [ ] Last login timestamp is updated
- [ ] Auth type is displayed in user list
- [ ] Auth type is displayed in user detail
- [ ] Password change is blocked for MS Auth users
- [ ] Password reset button is hidden for MS Auth users
- [ ] Local users can still change password
- [ ] Settings form shows MS SSO configuration
- [ ] Admin can enable/disable MS SSO

## Migration Guide

### Existing Users
- Existing local users remain unchanged
- Local authentication continues to work
- Users can be manually converted to MS Auth by admin if needed

### New Users
- Can be created via local registration
- Can be auto-created via MS SSO
- Cannot have both auth types simultaneously

### Best Practices
1. **Enable MS SSO gradually**: Test with a small group first
2. **Keep local admin**: Maintain at least one local admin account
3. **Document for users**: Inform users about MS SSO availability
4. **Monitor logs**: Check auth_service.log for authentication events
5. **Regular security audits**: Review user access and permissions

## Files Changed

### Core Services
- `core/services/ms_auth_service.py` - MS Auth service implementation

### Views
- `main/auth_views.py` - Added MS SSO views (login, callback)

### Models
- `main/models.py` - Extended User and Settings models

### Templates
- `main/templates/main/auth/login.html` - Added MS SSO button
- `main/templates/main/users/user_list.html` - Added auth type column
- `main/templates/main/users/user_detail.html` - Added auth type display
- `main/templates/main/settings_form.html` - Added MS SSO configuration

### Configuration
- `requirements.txt` - Added msal>=1.28.0
- `main/urls.py` - Added MS SSO routes
- `main/migrations/0020_*.py` - Database migrations

### Tests
- `main/test_ms_auth.py` - Comprehensive test suite

## Dependencies

- `msal>=1.28.0` - Microsoft Authentication Library
- `requests>=2.31.0` - HTTP library (already present)
- `Django>=5.1.12` - Web framework (already present)

## Logging

All MS SSO events are logged to `auth_service.log`:
- Login initiation
- Callback processing
- User creation/update
- Errors and warnings

Example log entries:
```
[INFO] Redirecting to Microsoft SSO login
[INFO] User logged in via MS SSO: user@example.com
[INFO] Creating new MS Auth user: user@example.com
[WARNING] MS SSO login attempted but service is not configured
[ERROR] MS SSO callback error: Invalid authorization code
```

## Support

For issues or questions:
1. Check this guide and troubleshooting section
2. Review logs in `auth_service.log`
3. Run test suite to verify functionality
4. Check Azure AD configuration
5. Contact system administrator

## Changelog

### Version 1.1 (2025-10-22)
**Fix: Authorization URL Generation Error**

Fixed the MS SSO authorization URL generation issue that was causing login failures:

**Issues Resolved:**
1. ❌ **Reserved Scope Error**: Fixed error "You cannot use any scope value that is reserved"
   - Removed reserved scopes (`openid`, `profile`, `email`) from explicit scope list
   - These scopes are now automatically handled by MSAL
   - Only `User.Read` is explicitly specified

2. ❌ **Deprecation Warning**: Fixed "Change your get_authorization_request_url() to initiate_auth_code_flow()"
   - Migrated from deprecated `get_authorization_request_url()` to `initiate_auth_code_flow()`
   - Implemented proper OAuth 2.0 authorization code flow
   - Flow dictionary now stored in session for token acquisition

**Technical Changes:**
- Updated `MSAuthService.get_authorization_url()` to use `initiate_auth_code_flow()`
- Modified `MSAuthService.acquire_token_by_authorization_code()` to accept and use flow dictionary
- Updated `ms_sso_login()` view to store flow in session
- Updated `ms_sso_callback()` view to use stored flow for token acquisition
- Updated all tests to reflect new flow-based approach

**Benefits:**
- ✅ No more reserved scope errors
- ✅ No more deprecation warnings
- ✅ Using recommended MSAL API
- ✅ More secure and maintainable authentication flow
- ✅ All 16 tests passing

---

**Version**: 1.1  
**Date**: 2025-10-22  
**Status**: Production Ready ✅
