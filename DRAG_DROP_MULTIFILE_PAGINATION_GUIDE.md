# Item DetailView: Drag-and-Drop Multi-File Upload & File Pagination

## Overview
This document describes the implementation of drag-and-drop multi-file upload functionality and file pagination in the Item DetailView.

## Features Implemented

### 1. Drag-and-Drop File Upload
**User Experience:**
- Users can drag one or more files from their file system
- Drop files directly into the designated drop zone
- Visual feedback when dragging files over the drop zone (border highlight, background change)
- Alternative: Click the drop zone to open file picker

**Technical Implementation:**
- Drop zone HTML element with visual styling
- JavaScript event handlers for drag events (dragenter, dragover, dragleave, drop)
- Prevents default browser behavior (opening file in new tab)
- CSS transitions for smooth visual feedback

**Location:** `/main/templates/main/items/detail.html`

### 2. Multi-File Upload
**User Experience:**
- Select and upload multiple files at once
- Progress indicator shows during upload
- Success message displays count of uploaded files
- Individual error handling for failed uploads

**Technical Implementation:**
- File input with `multiple` attribute
- API endpoint accepts both single file (`file`) and multiple files (`files`)
- Batch processing with error collection
- FormData API for multi-file submission

**Locations:**
- Frontend: `/main/templates/main/items/detail.html`
- Backend: `/main/api_views.py` - `api_item_file_upload()`

### 3. File Pagination
**User Experience:**
- 20 files displayed per page
- Pagination controls with first/previous/next/last buttons
- Current page indicator
- Total file count displayed
- Seamless page navigation without full page reload (HTMX)

**Technical Implementation:**
- Django Paginator for efficient pagination
- HTMX for seamless page transitions
- Bootstrap pagination components
- Query parameters: `page` and `per_page`

**Locations:**
- Frontend: `/main/templates/main/items/_files_list.html`
- Backend API: `/main/api_views.py` - `api_item_file_list()`
- Service: `/core/services/item_file_service.py` - `list_files()`

## Code Changes

### Frontend Changes

#### 1. Detail View Template (`detail.html`)
**Added:**
- Drop zone HTML structure with visual content
- CSS styles for drop zone (normal, hover, drag-over states)
- JavaScript for handling drag-and-drop events
- JavaScript `uploadFiles()` function for multi-file processing
- Modified file input to support `multiple` attribute
- Updated upload button text to "Upload Files" (plural)

#### 2. Files List Partial (`_files_list.html`)
**Added:**
- Pagination navigation controls
- Current page and total count display
- HTMX attributes for page navigation buttons
- Conditional rendering based on pagination state

### Backend Changes

#### 1. API Views (`api_views.py`)

**`api_item_file_upload()`:**
```python
# Changed from processing single file to handling multiple files
uploaded_files = []
if 'files' in request.FILES:
    uploaded_files = request.FILES.getlist('files')
elif 'file' in request.FILES:
    uploaded_files = [request.FILES['file']]

# Loop through all files and upload each one
for uploaded_file in uploaded_files:
    # Upload logic...
    
# Return updated file list with pagination
```

**`api_item_file_list()`:**
```python
# Extract pagination parameters from query string
page = request.GET.get('page', 1)
per_page = request.GET.get('per_page', 20)

# Pass to service
result = service.list_files(str(item_id), page=page, per_page=per_page)
```

#### 2. Service Layer (`item_file_service.py`)

**`ItemFileService.list_files()`:**
```python
def list_files(self, item_id: str, page: int = 1, per_page: int = 20):
    # Use Django Paginator
    paginator = Paginator(files, per_page)
    files_page = paginator.page(page_number)
    
    # Return with pagination metadata
    return {
        'files': files_data,
        'page': files_page.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
        'has_next': files_page.has_next(),
        'has_previous': files_page.has_previous(),
    }
```

## API Endpoints

### Upload Endpoint
**URL:** `/api/items/{item_id}/files/upload`
**Method:** POST
**Parameters:**
- `file` (single file) - Legacy support
- `files` (multiple files) - New multi-file support

**Response (HTMX):** Updated HTML file list with pagination
**Response (JSON):** 
```json
{
    "success": true,
    "uploaded": 3,
    "failed": 0,
    "results": [...],
    "errors": []
}
```

### List Endpoint
**URL:** `/api/items/{item_id}/files`
**Method:** GET
**Query Parameters:**
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 20) - Items per page

**Response (HTMX):** HTML file list with pagination controls
**Response (JSON):**
```json
{
    "success": true,
    "files": [...],
    "page": 1,
    "total_pages": 3,
    "total_count": 45,
    "has_next": true,
    "has_previous": false
}
```

## Testing

### Test Coverage
**File:** `/main/test_file_upload_multifile_pagination.py`

**Tests:**
1. `test_api_accepts_multiple_files` - Validates multi-file API structure
2. `test_pagination_parameters_passed_to_service` - Verifies pagination params
3. `test_pagination_defaults_applied` - Checks default values
4. `test_item_file_service_pagination` - Tests pagination logic ✅ PASSED

## Browser Compatibility
- Drag-and-drop: Modern browsers (Chrome, Firefox, Safari, Edge)
- Multi-file input: All modern browsers with HTML5 support
- HTMX pagination: All browsers with JavaScript enabled

## User Guide

### Uploading Files

**Method 1: Drag and Drop**
1. Navigate to Item DetailView
2. Click on "Files" tab
3. Drag one or more files from your file system
4. Drop them into the designated drop zone
5. Files will upload automatically

**Method 2: Click to Upload**
1. Navigate to Item DetailView
2. Click on "Files" tab
3. Click "Upload Files" button
4. Select one or more files from file picker
5. Files will upload automatically

**Method 3: Click Drop Zone**
1. Navigate to Item DetailView
2. Click on "Files" tab
3. Click anywhere in the drop zone
4. Select one or more files from file picker
5. Files will upload automatically

### Navigating Pages
- Click **First** (⏮️) to go to first page
- Click **Previous** (◀️) to go to previous page
- Click **Next** (▶️) to go to next page
- Click **Last** (⏭️) to go to last page
- Current page is highlighted
- Page indicator shows: "Showing page X of Y (Z files total)"

## Notes
- Maximum file size: 25 MB per file
- Files are uploaded to SharePoint
- Text content is extracted and stored in Weaviate for semantic search
- File metadata is tracked in the ItemFile model
- All uploads require authentication
- Users need appropriate permissions to upload files

## Future Enhancements
- Progress bar for individual files in multi-file upload
- Drag-and-drop sorting/reordering of files
- Batch delete functionality
- File preview/thumbnails
- Advanced filtering and sorting options
