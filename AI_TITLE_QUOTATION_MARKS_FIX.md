# AI Enhancer Title Generation - Quotation Marks Fix

## Problem Statement

The AI Enhancer in Task Title Generation was always generating titles with quotation marks at the beginning and end. For example:
- Input: `"Implement new feature for user authentication"`
- Previous Output: `"Implement new feature for user authentication"`
- Expected Output: `Implement new feature for user authentication`

## Solution

### Changes Made

1. **Added Helper Function**: Created `strip_quotes_from_title()` in `main/api_views.py`
   - Removes both single (`'`) and double (`"`) quotation marks from the beginning and end of titles
   - Preserves quotation marks that appear inside the title text
   - Handles edge cases (None, empty strings, whitespace)

2. **Updated 4 API Endpoints** to use the new helper function:
   - `api_task_generate_title()` - Generates titles for tasks from descriptions
   - `api_task_ai_enhance()` - AI enhancement for tasks (includes title generation)
   - `api_item_generate_title()` - Generates titles for items from descriptions
   - `api_item_ai_enhance()` - AI enhancement for items (includes title generation)

### Implementation Details

The `strip_quotes_from_title()` function:

```python
def strip_quotes_from_title(title_text):
    """
    Remove quotation marks from the beginning and end of AI-generated titles.
    
    The text-to-title-generator agent often returns titles wrapped in quotation marks.
    This function removes both single and double quotation marks from the start and end
    of the title string.
    
    Args:
        title_text: Raw title text from AI response
        
    Returns:
        Title without surrounding quotation marks
    """
    if not title_text:
        return title_text
    
    cleaned = title_text.strip()
    
    # Remove leading and trailing quotation marks (both single and double)
    if cleaned and cleaned[0] in '"\'':
        cleaned = cleaned[1:]
    if cleaned and cleaned[-1] in '"\'':
        cleaned = cleaned[:-1]
    
    # Final cleanup: strip any whitespace that was inside the quotes
    return cleaned.strip()
```

### Example Usage

**Before the fix:**
```python
# AI agent returns: '"Implement authentication feature"'
# API response: {"title": "\"Implement authentication feature\""}
```

**After the fix:**
```python
# AI agent returns: '"Implement authentication feature"'
# API response: {"title": "Implement authentication feature"}
```

### Test Coverage

1. **Unit Tests** (`main/test_strip_quotes.py`):
   - Test stripping double quotes
   - Test stripping single quotes
   - Test handling mixed quotes
   - Test preserving internal quotes
   - Test handling titles without quotes
   - Test handling empty strings
   - Test handling None values
   - Test handling internal whitespace

2. **Integration Test** (`main/test_task_ai_enhance.py`):
   - Test that the API endpoints correctly strip quotation marks from AI-generated titles

### API Endpoints Affected

All endpoints using the `text-to-title-generator` agent now strip quotation marks:

1. **POST** `/api/tasks/{task_id}/generate-title`
   - Generates a title from a task description
   
2. **POST** `/api/tasks/{task_id}/ai-enhance`
   - Enhances task with AI (includes title generation, text normalization, and tag extraction)
   
3. **POST** `/api/items/{item_id}/generate-title`
   - Generates a title from an item description
   
4. **POST** `/api/items/{item_id}/ai-enhance`
   - Enhances item with AI (includes title generation, text normalization, and tag extraction)

## Testing

To verify the fix works:

1. Run the unit tests:
   ```bash
   python manage.py test main.test_strip_quotes
   ```

2. Run the integration test:
   ```bash
   python manage.py test main.test_task_ai_enhance.TaskAIEnhanceTest.test_api_task_ai_enhance_strips_quotation_marks_from_title
   ```

3. Manual testing:
   - Create a task or item
   - Use the AI Enhancer to generate a title
   - Verify that the title no longer has quotation marks at the beginning and end

## Files Modified

- `main/api_views.py` - Added helper function and updated 4 API endpoints
- `main/test_task_ai_enhance.py` - Added integration test
- `main/test_strip_quotes.py` - New file with comprehensive unit tests

## Notes

- The fix is minimal and surgical - only the necessary code was changed
- Existing functionality is preserved - titles without quotes are unchanged
- Internal quotation marks are preserved (e.g., `Test "Quoted" Title` remains as-is)
- The solution is consistent across all title generation endpoints
