# Quick Reference: Drag-Drop Multi-File Upload & Pagination

## 🎯 Feature Overview
Enhanced file management in Item DetailView with drag-and-drop upload, multi-file support, and pagination.

## 🚀 Quick Start

### For Users
1. **Drag & Drop Upload**
   - Go to Item DetailView → Files tab
   - Drag files from your computer
   - Drop into the designated zone
   - Files upload automatically

2. **Multi-File Upload**
   - Click "Upload Files" button
   - Select multiple files (Ctrl/Cmd + Click)
   - Files upload in one batch

3. **Navigate Pages**
   - Use ⏮️ ◀️ ▶️ ⏭️ buttons to navigate
   - 20 files shown per page
   - Current page highlighted

### For Developers

**Modified Files:**
```
main/templates/main/items/detail.html        - UI & JavaScript
main/templates/main/items/_files_list.html   - Pagination template
main/api_views.py                            - Multi-file & pagination APIs
core/services/item_file_service.py           - Pagination service
```

**Key API Endpoints:**
```python
# Upload (supports both single and multiple files)
POST /api/items/{item_id}/files/upload
- Parameters: 'file' (single) or 'files' (multiple)

# List with pagination
GET /api/items/{item_id}/files?page=1&per_page=20
```

**Key Functions:**
```javascript
// Frontend
uploadFiles(files)           // Handles multi-file upload
handleFileSelect(input)      // File input change handler
handleDrop(e)                // Drag-drop handler

// Backend
api_item_file_upload()       // Processes file uploads
api_item_file_list()         // Returns paginated file list
ItemFileService.list_files() // Service layer pagination
```

## 📋 Implementation Checklist

- [x] Drop zone with visual feedback
- [x] Multi-file selection support
- [x] Batch file upload processing
- [x] Pagination with Django Paginator
- [x] HTMX integration for seamless navigation
- [x] Error handling per file
- [x] Backward compatibility
- [x] Comprehensive tests
- [x] Documentation

## 🔧 Configuration

**Pagination Settings:**
- Default: 20 files per page
- Configurable via `per_page` query parameter
- Max: Controlled by Django Paginator

**File Upload Limits:**
- Max file size: 25 MB per file
- No limit on number of files per batch
- Limited by server configuration

## 🧪 Testing

**Run Tests:**
```bash
python manage.py test main.test_file_upload_multifile_pagination
```

**Key Test Cases:**
- Multi-file API acceptance
- Pagination parameters passing
- Default pagination values
- Service layer pagination logic ✅

## 💡 Tips

**For Best UX:**
- Show progress during upload
- Display file count after upload
- Highlight current page in pagination
- Disable navigation when at boundary
- Clear file input after successful upload

**For Performance:**
- Use pagination for large file lists
- HTMX prevents full page reloads
- Django Paginator optimizes DB queries

## 🐛 Troubleshooting

**Files not uploading:**
- Check file size (max 25 MB)
- Verify user authentication
- Check permissions on item
- Ensure SharePoint connection

**Pagination not showing:**
- Verify more than 20 files exist
- Check API response includes pagination metadata
- Ensure HTMX loaded correctly

**Drag-drop not working:**
- Check browser compatibility
- Verify JavaScript loaded
- Check for JS console errors
- Ensure drop zone element exists

## 📚 Documentation

**Full Guide:** `DRAG_DROP_MULTIFILE_PAGINATION_GUIDE.md`

**Related Docs:**
- `HTMX_FILE_LIST_IMPLEMENTATION.md`
- `FILE_UPLOAD_QUICK_REF.md`
- `DOKUMENTEN_UPLOAD_FEATURE.md`

## 🎨 UI Elements

**Drop Zone States:**
- Normal: Dashed border, dark background
- Hover: Accent color border, lighter background
- Drag Over: Thicker border, highlighted background

**Pagination Controls:**
- First (⏮️): Jump to page 1
- Previous (◀️): Go back one page
- Next (▶️): Go forward one page
- Last (⏭️): Jump to last page
- Current page badge

## ✅ Verification Checklist

Before deploying:
- [ ] Test single file upload
- [ ] Test multi-file upload (2-5 files)
- [ ] Test drag-and-drop with one file
- [ ] Test drag-and-drop with multiple files
- [ ] Test pagination navigation
- [ ] Test with 0 files (empty state)
- [ ] Test with exactly 20 files
- [ ] Test with 21+ files (pagination appears)
- [ ] Test error handling
- [ ] Test permissions

## 📞 Support

**Issues:** Report to GitHub issue tracker
**Questions:** Check documentation first
**Bugs:** Include browser info and console logs
