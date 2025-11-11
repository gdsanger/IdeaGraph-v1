# Sentry Project Slug Auto-Fetch Implementation

## Overview

This document describes the implementation of automatic Sentry project slug detection, which eliminates the need for users to manually enter the project slug when configuring Sentry integration.

## Problem Statement

### Original Issue
When adding a Sentry DSN to an Item, users were required to manually enter both:
1. **Sentry DSN**: Contains organization and project ID (numeric)
2. **Sentry Project Slug**: The string name of the project

This was confusing because:
- The DSN already contains project information (project ID)
- The Sentry API requires the project slug (not project ID)
- Users had to look up the project slug separately in Sentry settings

### Solution
Implemented automatic project slug detection that:
1. Extracts the project ID from the DSN
2. Queries the Sentry API to fetch the project slug
3. Automatically saves it to the Item

## Technical Implementation

### Architecture

```
User provides DSN → System extracts Project ID → Query Sentry API → 
Fetch Project Slug → Save to Item → Use for error fetching
```

### Components Modified

#### 1. SentryService (`core/services/sentry_service.py`)

**New Method**: `get_project_slug_from_id(project_id: str) -> Optional[str]`
- Queries Sentry API for all projects in the organization
- Matches the project ID from the DSN with the project list
- Returns the corresponding project slug

```python
def get_project_slug_from_id(self, project_id: str) -> Optional[str]:
    projects = self.get_projects()
    for project in projects:
        if str(project.get('id')) == str(project_id):
            return project.get('slug')
    return None
```

#### 2. SentryTaskSyncService (`core/services/sentry_task_sync_service.py`)

**New Method**: `auto_fetch_project_slug(item: Item) -> Optional[str]`
- Validates that DSN and auth token are configured
- Parses the DSN to extract organization and project ID
- Uses SentryService to fetch the project slug
- Handles errors gracefully

**Modified Method**: `fetch_and_create_tasks()`
- Checks if project slug is missing or empty
- Automatically fetches the slug using the new method
- Saves the fetched slug to the Item
- Continues with error fetching using the slug

#### 3. Views (`main/views.py`)

**New Helper Function**: `_auto_fetch_sentry_project_slug(sentry_dsn, current_slug)`
- Called when creating or updating an Item
- Only fetches if DSN is provided and slug is empty
- Returns the fetched slug or the current one if fetch fails

**Modified Views**:
- `item_create()`: Auto-fetches project slug before saving new Item
- `item_edit()`: Auto-fetches project slug before updating Item
- Both views show an info message when slug is auto-detected

#### 4. Templates

**Updated `main/templates/main/items/form.html`**:
- Changed placeholder from "my-project" to "auto-detected"
- Updated help text to "Auto-filled from DSN if left empty"

**Updated `main/templates/main/items/detail.html`**:
- Added help text explaining auto-detection
- Changed placeholder to indicate auto-detection

### Data Flow

#### Creating a New Item
```
1. User enters Sentry DSN in form
2. User leaves Project Slug empty (or enters manually)
3. Form submitted to item_create()
4. _auto_fetch_sentry_project_slug() called
5. If slug empty: Query Sentry API
6. Item saved with auto-fetched slug
7. User sees info message: "Auto-detected Sentry project slug: [slug]"
```

#### Syncing Sentry Errors
```
1. sync_sentry_errors.py or API endpoint triggered
2. fetch_and_create_tasks() called
3. Checks if project slug exists
4. If empty: auto_fetch_project_slug() called
5. Fetched slug saved to Item
6. Continues with error fetching
```

## API Changes

### No Breaking Changes
- All existing functionality preserved
- Project slug can still be manually entered
- Manual entries override auto-fetch

### New Behavior
- Empty project slug → Auto-fetch from Sentry API
- Existing project slug → Keep as-is (no override)

## Error Handling

### Graceful Degradation
The implementation handles various error scenarios:

1. **No Sentry Auth Token**:
   - Returns None, logs error
   - User must configure token in Settings

2. **Invalid DSN Format**:
   - Returns None, logs warning
   - User sees validation error

3. **Project Not Found**:
   - Returns None, logs warning
   - User must enter slug manually

4. **Network/API Error**:
   - Returns None, logs error with traceback
   - User can retry or enter manually

5. **No Internet Access**:
   - Returns None, logs error
   - User must enter slug manually

### User Feedback
- Success: "Auto-detected Sentry project slug: [slug]"
- Failure: Field remains empty, user must enter manually

## Testing

### Test Coverage
Created comprehensive test suite in `main/test_sentry_integration.py`:

1. **`test_auto_fetch_project_slug_success`**:
   - Mocks Sentry API response
   - Verifies correct slug is returned

2. **`test_auto_fetch_project_slug_not_found`**:
   - Tests when project ID not in API response
   - Verifies None is returned

3. **`test_auto_fetch_project_slug_no_dsn`**:
   - Tests when Item has no DSN
   - Verifies None is returned

4. **`test_auto_fetch_project_slug_no_auth_token`**:
   - Tests when auth token not configured
   - Verifies None is returned

5. **`test_fetch_and_create_tasks_auto_fills_slug`**:
   - Integration test with full sync flow
   - Verifies slug is fetched and saved to Item

6. **`test_get_project_slug_from_id`**:
   - Tests SentryService method directly
   - Verifies correct matching logic

### Test Results
```
Ran 6 tests in 1.626s
OK
```

All tests passing ✅

## Security

### Security Analysis
- **CodeQL**: No vulnerabilities found ✅
- **Dependency Check**: No vulnerabilities in requests library ✅

### Security Considerations
1. **API Token Storage**: Stored securely in Settings model (admin only)
2. **No Token Exposure**: Token never sent to client
3. **HTTPS Only**: All Sentry API calls use HTTPS
4. **Input Validation**: DSN parsed and validated before use
5. **Error Information**: Errors logged server-side, not exposed to users

## Benefits

### User Experience
- ✅ Simpler configuration process
- ✅ Reduced confusion about DSN vs Project Slug
- ✅ Fewer configuration errors
- ✅ No need to look up project slug in Sentry

### Developer Experience
- ✅ Less support burden
- ✅ Clearer error messages
- ✅ Better logging
- ✅ Comprehensive test coverage

### System Reliability
- ✅ Graceful error handling
- ✅ No breaking changes
- ✅ Backward compatible
- ✅ Automatic recovery (auto-fill on first sync)

## Documentation

Updated `SENTRY_INTEGRATION_GUIDE.md`:
- Added "Automatic Project Slug Detection" section
- Updated configuration instructions
- Added troubleshooting for auto-fetch issues
- Clarified requirements (auth token permissions)

## Migration Path

### Existing Items
No migration needed. For existing Items:
1. If project slug already set → No change
2. If project slug empty → Auto-fetched on next sync or edit
3. Manual entry still works if needed

### New Items
- Users can leave project slug empty
- Auto-filled when DSN is provided
- Manual entry still available as fallback

## Future Enhancements

### Potential Improvements
1. **Cache Project Slugs**: Cache org → project mapping to reduce API calls
2. **Batch Validation**: Validate all Sentry configs in background job
3. **UI Indication**: Show loading spinner while fetching slug
4. **Pre-validation**: Check Sentry connectivity before saving
5. **Alternative to Project Slug**: Consider using Sentry Auth Token + DSN only

### Not Implemented (Out of Scope)
- Using API key instead of project slug (would require API restructure)
- Real-time validation in form (would need AJAX)
- Project slug dropdown (would need to fetch all projects)

## Conclusion

This implementation successfully addresses the original issue by:
1. ✅ Eliminating manual project slug entry requirement
2. ✅ Maintaining backward compatibility
3. ✅ Providing graceful error handling
4. ✅ Including comprehensive testing
5. ✅ Ensuring security best practices
6. ✅ Updating documentation

The solution is production-ready and improves the user experience for Sentry integration configuration.

---

**Implementation Date**: 2025-11-11  
**Version**: v1.0  
**Status**: Complete ✅
