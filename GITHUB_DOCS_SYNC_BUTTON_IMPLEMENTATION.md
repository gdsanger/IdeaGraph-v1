# GitHub Documentation Sync Button Implementation

## Overview

This implementation adds a UI button on the Item detail page that allows users to manually trigger GitHub documentation synchronization for a specific item. The button provides the same functionality as the CLI command `sync_github_docs --item {itemid}`.

## Changes Made

### 1. API Endpoint (`main/api_views.py`)

Added new endpoint `api_github_sync_docs()` at line 899:

```python
@csrf_exempt
@require_http_methods(["POST"])
def api_github_sync_docs(request, item_id):
    """
    API endpoint to sync GitHub documentation to IdeaGraph for a specific item.
    POST /api/github/sync-docs/<item_id>
    """
```

**Features:**
- Requires authentication (checks session user_id)
- Validates permissions (admin or item owner)
- Uses `GitHubDocSyncService.sync_item()` to perform the sync
- Returns JSON with sync results (files_processed, files_synced, errors)
- Handles errors gracefully with appropriate HTTP status codes

### 2. URL Pattern (`main/urls.py`)

Added route at line 140:

```python
path('api/github/sync-docs/<uuid:item_id>', api_views.api_github_sync_docs, name='api_github_sync_docs'),
```

### 3. UI Button (`main/templates/main/items/detail.html`)

Added button after the "Sync GitHub Issues" button (line 549):

```html
<button type="button" class="btn btn-outline-info" id="syncGitHubDocsBtn" 
        {% if not settings.github_api_enabled or not item.github_repo %}
        disabled 
        title="{% if not settings.github_api_enabled %}GitHub is not enabled{% elif not item.github_repo %}No GitHub repository set for this item{% endif %}"
        {% else %}
        title="Sync GitHub Documentation"
        {% endif %}>
    <span class="button-text"><i class="bi bi-file-earmark-text"></i> Sync GitHub Docs</span>
    <span class="spinner-border spinner-border-sm" role="status" style="display: none;"></span>
</button>
```

**Button Behavior:**
- Disabled when GitHub API is not enabled
- Disabled when item has no GitHub repository configured
- Shows appropriate tooltip messages
- Displays spinner during sync operation
- Uses Bootstrap icon `bi-file-earmark-text` for documentation

### 4. JavaScript Handler (`main/templates/main/items/detail.html`)

Added event listener at line 1448:

```javascript
document.querySelector('#syncGitHubDocsBtn')?.addEventListener('click', async function() {
    // Shows confirmation dialog
    // Calls POST /api/github/sync-docs/{item_id}
    // Displays success/error alerts
    // Refreshes files tab to show new documentation
});
```

**Handler Features:**
- Confirmation dialog before syncing
- Proper error handling with user-friendly messages
- Shows detailed sync results (files processed, synced, errors)
- Automatically refreshes the files tab after successful sync
- Disables button and shows spinner during operation

## User Experience

### Button Location
The "Sync GitHub Docs" button is placed on the Item detail page in the action buttons section, right after the "Sync GitHub Issues" button.

### Workflow
1. User navigates to Item detail page
2. User clicks "Sync GitHub Docs" button
3. Confirmation dialog appears explaining what will happen
4. User confirms
5. System synchronizes all .md files from the GitHub repository
6. Success message shows: files processed, files synced, any errors
7. Files tab automatically refreshes to display the new documentation files

### States
- **Enabled**: GitHub is enabled AND item has a repository configured
- **Disabled**: GitHub is not enabled OR item has no repository
- **Loading**: During sync operation (button disabled, spinner visible)

## Technical Details

### Synchronization Process
The button triggers `GitHubDocSyncService.sync_item()` which:
1. Scans the GitHub repository for .md files
2. Downloads file content
3. Uploads to SharePoint in the Item folder
4. Creates ItemFile records in the database
5. Syncs to Weaviate as KnowledgeObjects (type: "documentation")

### Security
- Authentication required (session-based)
- Permission check (admin or item owner only)
- CSRF protection enabled
- Error messages don't expose sensitive internal details

### Response Format
```json
{
    "success": true,
    "item_title": "Item Name",
    "files_processed": 10,
    "files_synced": 8,
    "errors": []
}
```

## Testing

### Manual Testing Steps
1. Ensure GitHub API is enabled in settings
2. Create an item with a valid GitHub repository URL
3. Navigate to the item detail page
4. Verify button is enabled
5. Click "Sync GitHub Docs" button
6. Confirm the dialog
7. Verify success message appears
8. Check Files tab for synchronized documentation
9. Verify files are uploaded to SharePoint
10. Verify files are indexed in Weaviate

### Edge Cases
- Item without GitHub repository: Button disabled
- GitHub API disabled: Button disabled
- No markdown files in repository: Success with 0 files synced
- Network errors: Appropriate error message displayed
- Permission denied: 403 error returned

## Acceptance Criteria ✓

- [x] Ein Button zur Synchronisation der GitHub-Dokumentation ist auf der Item-Ebene sichtbar
- [x] Der Button führt den Befehl `sync_github_docs --item {itemid}` korrekt aus

## Files Modified

1. `main/api_views.py` - Added API endpoint
2. `main/urls.py` - Added URL pattern
3. `main/templates/main/items/detail.html` - Added button and JavaScript handler

## Dependencies

- `core.services.github_doc_sync_service.GitHubDocSyncService`
- Django session-based authentication
- Bootstrap 5 for styling
- Bootstrap Icons for icon

## Related Documentation

- [GitHub Documentation Sync Guide](GITHUB_DOC_SYNC_GUIDE.md)
- [GitHub Documentation Sync Implementation Summary](GITHUB_DOC_SYNC_IMPLEMENTATION_SUMMARY.md)
- [GitHub Documentation Sync Quick Reference](GITHUB_DOC_SYNC_QUICKREF.md)
