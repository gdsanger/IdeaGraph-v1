# Google PSE Integration Migration - Implementation Summary

## Overview
This document summarizes the implementation of moving Google PSE (Programmable Search Engine) integration configuration from environment variables to the entity Settings model in IdeaGraph v1.0.

## Changes Made

### 1. Database Model Changes (`main/models.py`)
Added three new fields to the `Settings` model:

- **`google_pse_enabled`** (BooleanField): Toggle to enable/disable Google PSE integration
  - Default: `False`
  - When disabled, the external support analysis button is hidden from the UI

- **`google_search_api_key`** (CharField): Stores the Google Custom Search API Key
  - Max length: 255 characters
  - Can be blank/empty

- **`google_search_cx`** (CharField): Stores the Google Custom Search Engine ID (CX)
  - Max length: 255 characters
  - Can be blank/empty

### 2. Database Migration (`main/migrations/0027_add_google_pse_settings.py`)
Created a Django migration that adds the three new fields to the Settings table with appropriate defaults and help text.

### 3. Web Search Adapter (`core/services/web_search_adapter.py`)
Updated the `WebSearchAdapter` class to:
- Read Google PSE configuration from Settings model first
- Fall back to environment variables if Settings fields are empty
- This ensures backward compatibility with existing deployments

### 4. Settings Form Template (`main/templates/main/settings_form.html`)
Added a new "Google PSE Configuration" section containing:
- Enable/disable toggle switch for Google PSE
- Input field for Google Search API Key (password field for security)
- Input field for Google Search CX (Search Engine ID)
- Helpful descriptions for each field

### 5. Settings Views (`main/views.py`)
Updated both `settings_create` and `settings_update` views to:
- Handle the new Google PSE fields from POST requests
- Save the values to the database
- Pass settings to the task detail view for UI conditionals

### 6. Task Detail Template (`main/templates/main/tasks/detail.html`)
Modified the template to:
- Only show the "Support-Analyse (Extern)" button when `google_pse_enabled` is `True`
- Updated JavaScript to check if the button exists before attaching event listeners
- Prevents JavaScript errors when the button is hidden

### 7. Tests (`main/test_google_pse_settings.py`)
Created comprehensive tests covering:
- Model field creation and default values
- WebSearchAdapter reading from Settings
- Fallback to environment variables
- All tests pass successfully

## Security Analysis
- Ran CodeQL security checker: **No vulnerabilities found**
- API keys are stored as password fields in the UI
- Sensitive data is properly handled in the Settings model

## Benefits

1. **Centralized Configuration**: All API credentials now managed through the Settings UI
2. **No Environment Variable Changes Required**: Admins can configure without server restarts
3. **Better Control**: Enable/disable integration with a simple toggle
4. **Backward Compatible**: Falls back to environment variables if settings are empty
5. **UI Integration**: External support analysis button visibility controlled by settings

## Migration Path

### For New Installations
1. Access Settings page (Admin only)
2. Navigate to "Google PSE Configuration" section
3. Enable the toggle
4. Enter API Key and CX
5. Save settings
6. External support analysis becomes available in Task detail views

### For Existing Installations
1. Existing environment variables continue to work
2. Can gradually migrate to Settings-based configuration
3. Settings values take precedence over environment variables when set

## Testing Performed

1. **Unit Tests**: All 5 new tests pass
   - Model field validation
   - WebSearchAdapter configuration reading
   - Environment variable fallback

2. **Integration Tests**: Related settings tests continue to pass
   - 30 settings-related tests verified

3. **Security Scan**: CodeQL analysis passed with no alerts

## UI Changes

### Settings Form
- New section added: "Google PSE Configuration"
- Follows existing settings UI patterns
- Includes toggle switch and input fields

### Task Detail Page
- "Support-Analyse (Extern)" button conditionally shown
- No breaking changes to existing functionality
- JavaScript properly handles button absence

## Files Changed
1. `core/services/web_search_adapter.py` - Configuration reading logic
2. `main/models.py` - Added Google PSE fields
3. `main/migrations/0027_add_google_pse_settings.py` - Database migration
4. `main/templates/main/settings_form.html` - UI for configuration
5. `main/templates/main/tasks/detail.html` - Conditional button display
6. `main/views.py` - Form handling and context passing
7. `main/test_google_pse_settings.py` - Comprehensive tests

## Usage Example

```python
# In code (WebSearchAdapter automatically uses settings)
from core.services.web_search_adapter import WebSearchAdapter

adapter = WebSearchAdapter()  # Automatically loads from Settings
results = adapter.search("my query")
```

## Conclusion
The Google PSE integration has been successfully migrated to the Settings model, providing better control and user experience while maintaining backward compatibility with existing configurations.
