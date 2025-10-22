# Weaviate Availability Indicator Guide

## Overview

The Weaviate Availability Indicator is an interactive feature that displays whether Items, Tasks, and Files exist in the Weaviate vector database. It provides visual feedback and allows users to sync objects to Weaviate or view their stored data.

## Features

### Visual Indicators

- **Green Indicator (✓)**: Object exists in Weaviate
- **Red Indicator (✗)**: Object doesn't exist in Weaviate
- **Loading Spinner**: Checking status

### Interactive Functionality

#### When Object Doesn't Exist (Red Indicator)
- **Click Action**: Adds the object to Weaviate
- **Feedback**: Shows success toast notification
- **Auto-Update**: Indicator changes to green after successful sync

#### When Object Exists (Green Indicator)
- **Click Action**: Displays object dump in a modal
- **Content**: Shows JSON representation of the object in Weaviate
- **Format**: Pretty-printed JSON with syntax highlighting

## Where Indicators Appear

### 1. Item Detail Page
- **Location**: Top-right corner of the Item Details card header
- **Label**: "Weaviate:"
- **Object Type**: `item`

### 2. Task Detail Page
- **Location**: Top-right corner of the Task Details card header
- **Label**: "Weaviate:"
- **Object Type**: `task`

### 3. Item Files List
- **Location**: "Weaviate Status" column in the files table
- **Object Type**: `item_file`
- **Note**: Automatically initializes after HTMX content updates

### 4. Task Files List
- **Location**: "Weaviate Status" column in the files table
- **Object Type**: `task_file`
- **Note**: Automatically initializes after HTMX content updates

## Technical Implementation

### API Endpoints

#### Check Status
```
GET /api/weaviate/<object_type>/<object_id>/status
```
- **Response**: `{ success: true, exists: boolean, data?: {...} }`
- **Authentication**: Required

#### Add to Weaviate
```
POST /api/weaviate/<object_type>/<object_id>/add
```
- **Response**: `{ success: true, message: string }`
- **Authentication**: Required

#### Get Dump
```
GET /api/weaviate/<object_type>/<object_id>/dump
```
- **Response**: `{ success: true, dump: {...} }`
- **Authentication**: Required

### Object Types

- `item` - For Item objects
- `task` - For Task objects
- `item_file` - For ItemFile objects
- `task_file` - For TaskFile objects

### JavaScript Integration

#### Automatic Initialization
```javascript
// Indicators auto-initialize on page load
document.addEventListener('DOMContentLoaded', initAllWeaviateIndicators);
```

#### Manual Initialization
```javascript
// Initialize a specific indicator
const indicator = initWeaviateIndicator('item', itemId, containerElement);
```

#### HTMX Integration
```javascript
// Re-initialize after HTMX content swap
document.addEventListener('htmx:afterSwap', function(event) {
    initAllWeaviateIndicators();
});
```

### HTML Usage

```html
<!-- Add indicator container -->
<div data-weaviate-indicator 
     data-weaviate-type="item" 
     data-weaviate-id="{{ item.id }}">
</div>

<!-- Include required assets -->
<link rel="stylesheet" href="{% static 'main/css/weaviate-indicator.css' %}">
<script src="{% static 'main/js/weaviate-indicator.js' %}"></script>
```

## Styling

### CSS Classes

- `.weaviate-indicator` - Base indicator button
- `.weaviate-indicator-exists` - Green indicator for existing objects
- `.weaviate-indicator-missing` - Red indicator for missing objects
- `.weaviate-indicator.loading` - Loading state
- `.weaviate-indicator-container` - Container wrapper
- `.weaviate-indicator-label` - Label text

### Customization

Modify `/main/static/main/css/weaviate-indicator.css` to customize:
- Colors
- Sizes
- Animations
- Hover effects

## Error Handling

### Scenarios

1. **Authentication Error**: Returns 401 Unauthorized
2. **Object Not Found**: Returns 404 Not Found
3. **Weaviate Connection Error**: Shows error indicator (⚠)
4. **Sync Failure**: Displays error toast with details

### User Feedback

All actions provide visual feedback via:
- Toast notifications (success/error)
- Indicator state changes
- Modal dialogs

## Testing

Run the test suite:
```bash
python manage.py test main.test_weaviate_indicator
```

### Test Coverage

- Status checking (exists/not exists)
- Adding objects to Weaviate
- Getting object dumps
- Authentication requirements
- Error handling
- File sync operations

## Dependencies

### Backend
- Django 5.1+
- Weaviate Python Client
- `core.services.weaviate_sync_service`
- `core.services.weaviate_task_sync_service`

### Frontend
- Bootstrap 5 (for styling)
- Bootstrap Icons (for icons)
- HTMX (for dynamic updates)

## Troubleshooting

### Indicator Doesn't Appear
- Check that CSS and JS files are loaded
- Verify `data-weaviate-indicator` attributes are set correctly
- Check browser console for JavaScript errors

### Status Check Fails
- Verify Weaviate connection settings
- Check user authentication
- Review server logs for errors

### Objects Not Syncing
- Ensure Weaviate service is running
- Check object permissions
- Verify Weaviate collection schema

## Future Enhancements

- Batch sync multiple objects
- Sync status progress indicator
- Last sync timestamp display
- Automatic sync on object create/update
- Sync conflict resolution
- Bulk operations from list views
