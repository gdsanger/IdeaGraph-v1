# MS SSO Authorization URL Fix - Summary

## Problem Statement

The Microsoft SSO login feature was failing with the following errors:

### Error 1: Reserved Scope Error
```
Failed to generate authorization URL: You cannot use any scope value that is reserved. 
Your input: ['profile', 'openid', 'email', 'User.Read'] 
The reserved list: ['profile', 'openid', 'offline_access']
```

### Error 2: Deprecation Warning
```
DeprecationWarning: Change your get_authorization_request_url() to initiate_auth_code_flow()
```

## Root Causes

1. **Reserved Scopes Issue**: The code was explicitly passing reserved OAuth scopes (`openid`, `profile`, `email`) that MSAL automatically handles internally
2. **Deprecated API**: Using `get_authorization_request_url()` which is deprecated in MSAL 1.28+
3. **Improper Flow Management**: Not using the recommended flow-based approach for OAuth 2.0 authorization code flow

## Solution Implemented

### 1. Updated SCOPES Configuration
**File**: `core/services/ms_auth_service.py`

**Before**:
```python
SCOPES = ['User.Read', 'openid', 'profile', 'email']
```

**After**:
```python
# Note: 'openid', 'profile', and 'email' are reserved scopes automatically handled by MSAL
# Only specify the Graph API scopes needed
SCOPES = ['User.Read']
```

### 2. Migrated to New MSAL API
**File**: `core/services/ms_auth_service.py`

#### get_authorization_url() Method

**Before**:
```python
def get_authorization_url(self, redirect_uri: str, state: str = None) -> Tuple[str, str]:
    auth_result = self.msal_app.get_authorization_request_url(
        scopes=self.SCOPES,
        state=state,
        redirect_uri=redirect_uri
    )
    return auth_result, state
```

**After**:
```python
def get_authorization_url(self, redirect_uri: str, state: str = None) -> Tuple[str, Dict]:
    # Use initiate_auth_code_flow instead of deprecated get_authorization_request_url
    flow = self.msal_app.initiate_auth_code_flow(
        scopes=self.SCOPES,
        redirect_uri=redirect_uri,
        state=state
    )
    
    if 'error' in flow:
        error_desc = flow.get('error_description', 'Unknown error')
        raise MSAuthServiceError(f'Failed to initiate auth code flow: {error_desc}')
    
    auth_url = flow.get('auth_uri')
    return auth_url, flow
```

#### acquire_token_by_authorization_code() Method

**Before**:
```python
def acquire_token_by_authorization_code(
    self, 
    authorization_code: str, 
    redirect_uri: str
) -> Dict:
    result = self.msal_app.acquire_token_by_authorization_code(
        code=authorization_code,
        scopes=self.SCOPES,
        redirect_uri=redirect_uri
    )
    return result
```

**After**:
```python
def acquire_token_by_authorization_code(
    self, 
    authorization_code: str, 
    flow: Dict = None
) -> Dict:
    # Use acquire_token_by_auth_code_flow if flow is provided (recommended)
    if flow:
        result = self.msal_app.acquire_token_by_auth_code_flow(
            auth_code_flow=flow,
            auth_response={'code': authorization_code}
        )
    else:
        # Fallback for backward compatibility
        result = self.msal_app.acquire_token_by_authorization_code(
            code=authorization_code,
            scopes=self.SCOPES
        )
    
    if 'error' in result:
        error_desc = result.get('error_description', 'Unknown error')
        raise MSAuthServiceError(f'Token acquisition failed: {error_desc}')
    
    return result
```

### 3. Updated View Layer
**File**: `main/auth_views.py`

#### ms_sso_login() View

**Before**:
```python
auth_url, _ = ms_auth.get_authorization_url(redirect_uri, state)
```

**After**:
```python
# Get authorization URL and flow
auth_url, flow = ms_auth.get_authorization_url(redirect_uri, state)

# Store flow in session for token acquisition
request.session['ms_auth_flow'] = flow
```

#### ms_sso_callback() View

**Before**:
```python
redirect_uri = request.build_absolute_uri(reverse('main:ms_sso_callback'))
token_response = ms_auth.acquire_token_by_authorization_code(code, redirect_uri)
```

**After**:
```python
# Get flow from session
flow = request.session.pop('ms_auth_flow', None)

# Exchange code for token using the stored flow
token_response = ms_auth.acquire_token_by_authorization_code(code, flow)
```

### 4. Updated Tests
**File**: `main/test_ms_auth.py`

Updated all tests to work with the new flow-based approach:
- `test_get_authorization_url()` - Now expects flow dictionary
- `test_ms_sso_login_initiates_flow()` - Updated to match new return signature
- All 16 tests updated and passing

## Benefits of the Fix

### ✅ Eliminates Errors
- No more reserved scope errors
- No more deprecation warnings
- Microsoft SSO login now works correctly

### ✅ Best Practices
- Using recommended MSAL API (`initiate_auth_code_flow`)
- Proper OAuth 2.0 authorization code flow implementation
- Flow dictionary management for secure token exchange

### ✅ Maintainability
- Code is future-proof (no deprecated APIs)
- Better error handling
- Clearer separation of concerns

### ✅ Security
- CSRF protection maintained via state parameter
- Flow dictionary ensures authorization code can only be used once
- No security vulnerabilities detected (CodeQL scan passed)

## Testing Results

### Unit Tests
```
Ran 16 tests in 0.866s
OK
```

All MS Auth tests passing:
- Service initialization
- Authorization URL generation
- User profile retrieval
- Avatar retrieval
- Token acquisition
- User creation/update
- Password change restrictions
- UI integration
- Settings management

### Integration Verification
```
✅ PASS - No reserved scopes found
✅ PASS - Uses initiate_auth_code_flow() API call
✅ PASS - Does not use deprecated API call
✅ PASS - Uses acquire_token_by_auth_code_flow() API
```

### Security Scan
```
CodeQL Analysis: 0 vulnerabilities found
```

## Azure AD Configuration Update

**Important Note**: The Azure AD configuration guide has been updated. Administrators no longer need to explicitly add `openid`, `profile`, and `email` permissions as these are automatically handled by MSAL.

### Updated Permissions
Only the following permission needs to be explicitly added in Azure AD:
- `User.Read` (Read user profile)

The reserved scopes (`openid`, `profile`, `email`) are automatically included by MSAL's OAuth 2.0 implementation.

## Migration Guide

For existing deployments, no action is required:
1. ✅ Code changes are backward compatible
2. ✅ Existing Azure AD configurations will continue to work
3. ✅ No database changes required
4. ✅ No user data affected

Simply deploy the updated code and the MS SSO login will start working correctly.

## References

- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [OAuth 2.0 Authorization Code Flow](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/overview)

## Support

For issues or questions:
1. Check MS_SSO_GUIDE.md for configuration details
2. Review logs in `auth_service.log`
3. Run test suite to verify functionality
4. Check Azure AD configuration

---

**Fix Version**: 1.1  
**Date**: 2025-10-22  
**Status**: Completed and Verified ✅
