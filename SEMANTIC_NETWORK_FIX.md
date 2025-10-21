# Semantic Network HTTP 400 Error Fix

## Problem
Users were experiencing HTTP 400 (Bad Request) errors when trying to load the semantic network feature in Tasks and Items detail pages. The error occurred when the JavaScript code attempted to fetch data from the API endpoint:

```
GET /api/semantic-network/task/{uuid}?depth=3&summaries=true
```

## Root Cause
The `fetch()` request in `semantic-network.js` was not explicitly including credentials (session cookies) when making the API request. While the Django backend's `get_user_from_request()` function supports both JWT token authentication and session-based authentication, the API middleware marks `/api/` endpoints as "public" (bypassing the session check middleware).

The fetch request needed to explicitly include `credentials: 'same-origin'` to ensure that session cookies are sent with the request, allowing the backend to authenticate the user via the session fallback mechanism.

## Solution
Added `credentials: 'same-origin'` to the fetch options in the `load()` method of `SemanticNetworkViewer` class.

### Changes Made

**File: `main/static/main/js/semantic-network.js`**
- Line 117: Added `credentials: 'same-origin'` to fetch options

**File: `main/test_semantic_network.py`**
- Line 6: Removed unused `pytest` import that was causing test failures

### Code Change
```javascript
// Before
const response = await fetch(url, {
    method: 'GET',
    headers: {
        'Content-Type': 'application/json'
    }
});

// After
const response = await fetch(url, {
    method: 'GET',
    headers: {
        'Content-Type': 'application/json'
    },
    credentials: 'same-origin'  // Ensure session cookies are sent
});
```

## Testing
- Ran existing unit tests: 7 out of 8 tests passing (1 unrelated test failure pre-existed)
- CodeQL security analysis: No vulnerabilities detected
- The fix follows the Fetch API standard for same-origin requests requiring credentials

## Impact
This fix ensures that:
1. Session cookies are explicitly sent with the semantic network API request
2. Users authenticated via Django session can successfully load semantic networks
3. The authentication fallback mechanism in `get_user_from_request()` works correctly
4. No breaking changes to existing functionality

## Notes
- The `credentials: 'same-origin'` option is the standard way to include cookies for same-origin requests
- This aligns with Django's session-based authentication model
- The fix is minimal and focused on the specific issue reported
