# Comment Template Fixes - Summary

## Issues Fixed

### 1. MAX_LINES_COLLAPSED JavaScript Redeclaration Error

**Problem:**
When the comments list template was loaded via htmx, JavaScript variables (`MAX_LINES_COLLAPSED`, `HEIGHT_TOLERANCE`) and functions (`shouldShowExpandButton`, `updateExpandButton`, etc.) were being redeclared in the global scope, causing the error:
```
Uncaught SyntaxError: Failed to execute 'insertBefore' on 'Node': 
Identifier 'MAX_LINES_COLLAPSED' has already been declared
```

**Solution:**
Wrapped all JavaScript code in an Immediately Invoked Function Expression (IIFE):
```javascript
(function() {
    // All variables and functions are now scoped to this function
    const MAX_LINES_COLLAPSED = 5;
    // ... rest of the code
})();
```

This creates a new scope for each template load, preventing variable redeclaration errors.

**Files Changed:**
- `main/templates/main/tasks/_comments_list.html` - Lines 184-372

### 2. Comment Timestamp Not Displaying

**Problem:**
Comment timestamps were not visible because the view was passing ISO format strings (`comment.created_at.isoformat()`) to the template, but the Django template filter `|date:"d.m.Y H:i"` requires datetime objects.

**Solution:**
Modified the `api_task_comments` view to differentiate between htmx and JSON API requests:
- **htmx requests**: Pass datetime objects directly for proper template rendering
- **JSON API requests**: Pass ISO strings for API compatibility

```python
# For htmx requests, keep datetime objects
if request.headers.get('HX-Request'):
    comment_data = {
        'created_at': comment.created_at,  # Keep as datetime object
        'updated_at': comment.updated_at,  # Keep as datetime object
        # ...
    }

# For JSON API requests, use ISO strings
else:
    comment_data = {
        'created_at': comment.created_at.isoformat(),
        'updated_at': comment.updated_at.isoformat(),
        # ...
    }
```

**Files Changed:**
- `main/api_views.py` - Lines 6060-6105

## Expected Behavior After Fix

### Comment Timestamps
- Timestamps now display in format: `DD.MM.YYYY HH:MM` (e.g., "25.10.2025 14:59")
- If a comment has been edited, it shows "(bearbeitet)" next to the timestamp

### MAX_LINES_COLLAPSED Functionality
- Comments longer than 5 lines are automatically collapsed
- An "Mehr anzeigen" (Show more) button appears for collapsed comments
- Clicking toggles between collapsed and expanded state
- No more JavaScript errors when comments are reloaded via htmx

## Testing

### Automated Verification
Created `main/test_comment_template_fixes.py` with tests for:
- ✓ htmx requests receive datetime objects
- ✓ JSON API requests receive ISO strings
- ✓ JavaScript is wrapped in IIFE
- ✓ MAX_LINES_COLLAPSED is scoped within IIFE

### Manual Verification Checklist
1. Open a task detail page with comments
2. Verify timestamps are visible in format "DD.MM.YYYY HH:MM"
3. Add a long comment (more than 5 lines)
4. Verify "Mehr anzeigen" button appears
5. Click to expand/collapse and verify it works
6. Reload the comments (e.g., by editing a comment)
7. Verify no JavaScript errors in browser console
8. Verify timestamps remain visible after reload

## Technical Implementation Details

### IIFE Pattern Benefits
- Prevents variable pollution of global scope
- Allows multiple htmx loads without conflicts
- Maintains event handlers without duplication
- Used `cloneNode()` to remove old event listeners before adding new ones

### Backward Compatibility
- JSON API responses unchanged (still return ISO strings)
- Template markup unchanged (still uses Django date filter)
- No breaking changes to existing API consumers

## Related Files
- `main/templates/main/tasks/_comments_list.html` - Comment list template
- `main/api_views.py` - API endpoint for fetching comments
- `main/models.py` - TaskComment model (lines 599-636)
- `main/test_comment_template_fixes.py` - Test cases for fixes
