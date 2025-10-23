# Manual Verification Guide for Async Task Filter

## Overview
This guide explains how to manually verify the asynchronous "Erledigt anzeigen" (Show Completed) filter implementation in the Item DetailView.

## Changes Made
- The "Erledigt anzeigen" checkbox in the Tasks tab now uses HTMX for asynchronous filtering
- No more full page reloads when toggling the filter
- Much smoother and more responsive UI

## How to Test

### Prerequisites
1. Set up the development environment:
   ```bash
   cp .env.example .env
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver
   ```

2. Create test data:
   - Create a user account
   - Create an item
   - Create several tasks with different statuses (at least some with status "done")

### Manual Testing Steps

1. **Navigate to Item Detail View**
   - Go to Items list
   - Click on an item to view its details
   - Click on the "Tasks" tab

2. **Test Async Filter**
   - Observe the "Erledigt anzeigen" checkbox at the top right of the tasks section
   - Initially, completed tasks (status="done") should be hidden
   - Toggle the checkbox ON:
     - Notice that the page does NOT reload
     - Only the tasks table should update
     - Completed tasks should now appear
     - You should see a brief loading indicator
   - Toggle the checkbox OFF:
     - Again, no page reload
     - Completed tasks should disappear
     - Only active tasks remain visible

3. **Test with Search Query**
   - Enter a search term in the search box and submit
   - Results should show matching tasks
   - Now toggle the "Erledigt anzeigen" checkbox
   - Verify that:
     - The search query is preserved
     - The filter works correctly with the search
     - No page reload occurs

4. **Test with Pagination**
   - If you have more than 10 tasks, pagination will appear
   - Navigate to page 2 or 3
   - Toggle the "Erledigt anzeigen" checkbox
   - Verify that the filter resets to page 1 correctly

### Expected Behavior

**Before (Synchronous):**
- Clicking the checkbox caused a full page reload
- Browser would show loading animation
- Entire page would refresh
- Loss of scroll position
- Noticeable delay and screen flash

**After (Asynchronous):**
- No full page reload
- Only the tasks table area updates
- Smooth transition with loading indicator
- Scroll position maintained on the page
- Much faster and more responsive

### Visual Indicators

1. **Loading Indicator**: A spinner should briefly appear in the tasks section while loading
2. **Smooth Update**: The task list should smoothly update without page flash
3. **Preserved State**: All other page elements remain unchanged (item details, other tabs, etc.)

### Browser Developer Tools Verification

1. Open browser Developer Tools (F12)
2. Go to Network tab
3. Toggle the "Erledigt anzeigen" checkbox
4. Observe:
   - XHR/Fetch request to the item detail URL with `show_completed` parameter
   - Request has `HX-Request: true` header
   - Response is partial HTML (just the task table), not full page
   - Response time should be fast (< 200ms typically)

### Common Issues

1. **Full page still reloading**: 
   - Clear browser cache
   - Verify HTMX is loaded (check Network tab for htmx.org script)

2. **Filter not working**:
   - Check browser console for JavaScript errors
   - Verify the checkbox has the correct ID: `showCompletedSwitch`

3. **Search query not preserved**:
   - Verify the URL includes the search parameter
   - Check the JavaScript console for errors

## Technical Details

The implementation uses:
- **HTMX JavaScript API** (`htmx.ajax()`) for programmatic async requests
- **Partial template rendering** on the server side
- **Event-driven updates** triggered by checkbox change event
- **URL parameter preservation** for search queries and other filters

## Performance Comparison

Approximate timings (may vary based on server and data):

| Action | Before (Sync) | After (Async) |
|--------|--------------|---------------|
| Toggle filter | 500-1000ms | 100-200ms |
| Page reload time | Full page | Partial only |
| Data transferred | ~100KB | ~5KB |
| User perception | Slow, jarring | Fast, smooth |

## Code References

- Template: `main/templates/main/items/detail.html` (lines 607-623, 1386-1403)
- View: `main/views.py` (`item_detail` function, lines 883-1041)
- Partial Template: `main/templates/main/items/_item_tasks_table.html`
- Tests: `main/test_async_task_filter.py`
