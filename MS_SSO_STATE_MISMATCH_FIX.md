# MS SSO State Mismatch Fix - Summary

## Problem Statement

The Microsoft Auth Single Sign-On (SSO) feature was experiencing a "state mismatch" error during the OAuth callback phase. The error message indicated:

```
Failed to acquire token: state mismatch
Expected state: 72jK2oQ-MozO95a9OPWjQKr2mWMCxR9oEiIVZbk1Ibo
Received state: None
```

This occurred on 2025-10-22 at 15:47:48 UTC.

## Root Cause Analysis

The issue was caused by incomplete data being passed to MSAL's `acquire_token_by_auth_code_flow()` method. 

### The Problem

In the OAuth 2.0 authorization code flow:
1. The application initiates login and generates a `state` parameter for CSRF protection
2. Microsoft redirects back to the callback URL with both `code` and `state` parameters
3. The application must validate the `state` matches what was stored in the session
4. The application exchanges the `code` for an access token

**The bug**: When calling MSAL's `acquire_token_by_auth_code_flow()`, we were only passing the authorization code:

```python
# BEFORE (INCORRECT)
result = self.msal_app.acquire_token_by_auth_code_flow(
    auth_code_flow=flow,
    auth_response={'code': authorization_code}  # Missing state!
)
```

MSAL internally validates that the `state` in the `auth_response` matches the `state` stored in the `flow` dictionary. When we only passed the `code`, MSAL received `None` for the state and validation failed with "state mismatch".

## Solution Implemented

### 1. Updated `ms_auth_service.py`

Changed the method signature to accept the full `auth_response` dictionary instead of just the authorization code:

**Before**:
```python
def acquire_token_by_authorization_code(
    self, 
    authorization_code: str,  # Only the code
    flow: Dict = None
) -> Dict:
```

**After**:
```python
def acquire_token_by_authorization_code(
    self, 
    auth_response: Dict,  # Full callback response
    flow: Dict = None
) -> Dict:
```

The method now properly passes all callback parameters to MSAL:

```python
# AFTER (CORRECT)
result = self.msal_app.acquire_token_by_auth_code_flow(
    auth_code_flow=flow,
    auth_response=auth_response  # Includes code, state, and any other params
)
```

### 2. Updated `auth_views.py` Callback Handler

Modified the callback view to pass the complete query string parameters:

**Before**:
```python
code = request.GET.get('code')
# ... state validation ...
token_response = ms_auth.acquire_token_by_authorization_code(code, flow)
```

**After**:
```python
code = request.GET.get('code')
# Build auth_response dict with all callback parameters
auth_response = dict(request.GET.items())
# ... state validation ...
token_response = ms_auth.acquire_token_by_authorization_code(auth_response, flow)
```

The `auth_response` dictionary now includes:
- `code`: The authorization code
- `state`: The state parameter for CSRF validation
- Any other parameters Microsoft might include

### 3. Enhanced Logging

Improved the state mismatch logging to show both expected and received values:

```python
logger.warning(f'MS SSO state mismatch - expected: {expected_state}, received: {state}')
```

This makes debugging future issues much easier.

### 4. Added Comprehensive Tests

Created new test cases to ensure the fix works correctly:

1. **`test_acquire_token_with_flow`**: Verifies token acquisition with full auth_response
2. **`test_acquire_token_without_flow`**: Tests fallback mode for backward compatibility
3. **`test_ms_sso_callback_with_state_validation`**: Validates callback passes full auth_response
4. **`test_ms_sso_callback_state_mismatch`**: Ensures mismatched state is properly rejected

## Security Considerations

### Dual-Layer State Validation

The implementation now provides two layers of state validation:

1. **Application-level validation** (in `auth_views.py`):
   ```python
   state = auth_response.get('state')
   expected_state = request.session.get('ms_auth_state')
   if not state or state != expected_state:
       logger.warning(f'MS SSO state mismatch - expected: {expected_state}, received: {state}')
       return redirect('main:login')
   ```

2. **MSAL-level validation** (automatic in MSAL library):
   - MSAL validates the state in `auth_response` against the state in the `flow` dictionary
   - Provides additional protection against state manipulation

### CSRF Protection Maintained

The fix maintains CSRF protection by:
- Generating a cryptographically secure random state (32 bytes using `secrets.token_urlsafe`)
- Storing it in the session
- Validating it matches on callback (both at app and MSAL level)
- Cleaning up the session state after validation

### No Security Vulnerabilities Introduced

CodeQL security scan completed with **0 vulnerabilities found**.

## Testing Results

All 20 MS Auth tests pass successfully:

```
Ran 20 tests in 0.843s
OK
```

Key tests include:
- ✅ Service initialization
- ✅ Authorization URL generation
- ✅ Token acquisition with flow (with full auth_response)
- ✅ Token acquisition without flow (fallback)
- ✅ User profile retrieval
- ✅ Avatar retrieval
- ✅ State validation in callback
- ✅ State mismatch rejection
- ✅ User creation/update
- ✅ Password change restrictions for MS Auth users
- ✅ UI integration

## Benefits

### ✅ Fixes the State Mismatch Error
The primary issue is resolved - MSAL now receives the complete callback response and can properly validate the state parameter.

### ✅ Follows MSAL Best Practices
According to [MSAL Python documentation](https://msal-python.readthedocs.io/), when using `acquire_token_by_auth_code_flow()`, the `auth_response` parameter should contain the complete query string or form post data from the callback.

### ✅ Backward Compatibility
The fallback mode (when `flow=None`) still works for any code that might call the method without the flow parameter:

```python
if flow:
    result = self.msal_app.acquire_token_by_auth_code_flow(...)
else:
    result = self.msal_app.acquire_token_by_authorization_code(...)
```

### ✅ Better Error Messages
Enhanced logging makes it easier to diagnose authentication issues:
- Shows both expected and received state values
- Logs all callback parameters received

## Migration Guide

### For Existing Deployments

No action required! The fix is backward compatible:

1. ✅ No database changes needed
2. ✅ No configuration changes required
3. ✅ No Azure AD changes necessary
4. ✅ Existing MS SSO users can continue logging in
5. ✅ Session data is automatically managed

Simply deploy the updated code and the state mismatch error will be resolved.

### For New Implementations

If you're implementing MS SSO in a new project, follow this pattern:

```python
# 1. Initiate flow
auth_url, flow = ms_auth.get_authorization_url(redirect_uri, state)
request.session['ms_auth_flow'] = flow
request.session['ms_auth_state'] = state

# 2. In callback, pass complete response
auth_response = dict(request.GET.items())
flow = request.session.pop('ms_auth_flow', None)
token_response = ms_auth.acquire_token_by_authorization_code(auth_response, flow)
```

## Technical Details

### MSAL Flow-Based Authentication

MSAL's `initiate_auth_code_flow()` creates a flow dictionary containing:
- `auth_uri`: The authorization URL to redirect users to
- `state`: The CSRF protection state
- `nonce`: Additional security parameter for ID token validation
- Other internal MSAL parameters

This flow must be stored and passed back to `acquire_token_by_auth_code_flow()` along with the complete callback response for proper validation.

### Why Pass the Full auth_response?

MSAL needs the complete callback response to:
1. **Validate state**: Ensures the response came from our original request
2. **Validate nonce**: If using ID tokens, validates the nonce matches
3. **Handle errors**: Microsoft may return error parameters in the callback
4. **Future compatibility**: Any new parameters Microsoft adds will be handled

## Related Documentation

- [MS_SSO_GUIDE.md](MS_SSO_GUIDE.md) - Complete MS SSO configuration guide
- [MS_SSO_IMPLEMENTATION_SUMMARY.md](MS_SSO_IMPLEMENTATION_SUMMARY.md) - Implementation details
- [MS_SSO_FIX_SUMMARY.md](MS_SSO_FIX_SUMMARY.md) - Previous fix for reserved scopes
- [AUTHENTICATION_GUIDE.md](AUTHENTICATION_GUIDE.md) - General authentication guide

## Support

If you encounter issues with MS SSO:

1. **Check logs**: Review `auth_service.log` for detailed error messages
2. **Verify state**: Ensure session storage is working correctly
3. **Test flow**: Run the MS Auth test suite: `python manage.py test main.test_ms_auth`
4. **Check Azure AD**: Verify redirect URI matches exactly
5. **Review session**: Ensure cookies are enabled and session backend is configured

## Conclusion

The state mismatch error was caused by passing incomplete data to MSAL's token acquisition method. By passing the full OAuth callback response (including both `code` and `state`), MSAL can now properly validate the authorization flow and successfully exchange the authorization code for access tokens.

The fix is minimal, focused, and maintains backward compatibility while following MSAL best practices.

---

**Fix Version**: 1.2  
**Date**: 2025-10-22  
**Status**: Completed and Verified ✅  
**Security Scan**: Passed (0 vulnerabilities)  
**Tests**: 20/20 Passing
