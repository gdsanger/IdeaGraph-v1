# AI Features Implementation for Items

This document describes the AI features available for Items in IdeaGraph and their implementation.

## Overview

Three AI-powered features are now available for Items:

1. **AI Enhancer** - Enhances item title and description using AI
2. **Build Tasks** - Decomposes an item into actionable tasks using AI
3. **Check Similarity** - Finds similar items using semantic search

## Features

### 1. AI Enhancer

**Purpose**: Improves the quality of item titles and descriptions by:
- Optimizing text for clarity and conciseness
- Extracting relevant keywords/tags
- Improving overall readability

**Implementation**:
- **Backend**: `api_item_ai_enhance` in `main/api_views.py` (lines 1322-1416)
- **Frontend**: `detail.html` AI Enhance button handler (lines 400-447)
- **API Endpoint**: `POST /api/items/{item_id}/ai-enhance`
- **Service**: Uses KiGate service with `text-optimization-agent` and `text-keyword-extractor-de`

**Requirements**:
- KiGate API must be enabled and configured in Settings
- Item must have both title and description

**Response**:
```json
{
  "success": true,
  "title": "Enhanced title",
  "description": "Enhanced description with better formatting",
  "tags": ["keyword1", "keyword2", "keyword3"]
}
```

### 2. Build Tasks

**Purpose**: Automatically decomposes an item into multiple actionable tasks using AI.

**Implementation**:
- **Backend**: `api_item_build_tasks` in `main/api_views.py` (lines 1419-1535)
- **Frontend**: `detail.html` Build Tasks button handler (lines 449-486)
- **API Endpoint**: `POST /api/items/{item_id}/build-tasks`
- **Service**: Uses KiGate service with `task-decomposition-agent`

**Requirements**:
- KiGate API must be enabled and configured in Settings
- Item must have both title and description
- Item status must be "Ready" (enforced in UI)

**Response**:
```json
{
  "success": true,
  "tasks": [
    {
      "id": "task-uuid-1",
      "title": "Task 1 title",
      "description": "Task 1 description"
    },
    {
      "id": "task-uuid-2",
      "title": "Task 2 title",
      "description": "Task 2 description"
    }
  ],
  "count": 2
}
```

**Notes**:
- Maximum of 10 tasks will be created per request
- Created tasks are marked as `ai_generated=True`
- Tasks are assigned to the current user
- Tasks start with status "new"

### 3. Check Similarity

**Purpose**: Finds similar items using semantic search powered by ChromaDB.

**Implementation**:
- **Backend**: `api_item_check_similarity` in `main/api_views.py` (lines 1538-1600)
- **Frontend**: `detail.html` Check Similarity button handler (lines 488-566)
- **API Endpoint**: `POST /api/items/{item_id}/check-similarity`
- **Service**: Uses ChromaDB vector database for semantic search

**Requirements**:
- ChromaDB must be configured (either local or cloud)
- Item must have a description

**Response**:
```json
{
  "success": true,
  "similar_items": [
    {
      "id": "item-uuid-1",
      "distance": 0.15,
      "metadata": {
        "title": "Similar Item 1",
        "tags": ["tag1", "tag2"]
      },
      "document": "Description of similar item..."
    }
  ]
}
```

**Notes**:
- Returns up to 5 similar items
- Current item is filtered from results
- Lower distance = higher similarity
- Frontend converts distance to similarity percentage: `(1 - distance) * 100`

## Frontend Integration

All three features are integrated in the Item detail page (`main/templates/main/items/detail.html`):

### UI Elements
- Three buttons in the action button group:
  - 🌟 AI Enhancer (green button)
  - 🧠 Build Tasks (blue button, disabled unless status is "Ready")
  - 🔍 Check Similarity (yellow button)

### User Experience
1. **AI Enhancer**: Updates the form fields with enhanced content, allowing review before saving
2. **Build Tasks**: Creates tasks and reloads the page to show them in the Tasks tab
3. **Check Similarity**: Displays results in the "Similar Items" tab with similarity percentages

### Error Handling
- Shows user-friendly alerts for errors
- Handles authentication and permission errors gracefully
- Displays service configuration errors (KiGate/ChromaDB not configured)

## Configuration

### KiGate Setup (Required for AI Enhancer and Build Tasks)

1. Create Settings entry via Django admin or programmatically
2. Enable KiGate API: `kigate_api_enabled = True`
3. Set KiGate API token: `kigate_api_token = "your-token"`
4. Set KiGate API URL: `kigate_api_base_url = "http://your-kigate-server:8000"`

### ChromaDB Setup (Required for Check Similarity)

**Option 1: Local ChromaDB**
- No configuration needed
- Data stored in `./chroma_db` directory

**Option 2: Cloud ChromaDB**
- Set `chroma_api_key` in Settings
- Set `chroma_database` in Settings
- Set `chroma_tenant` in Settings

## Testing

Test file: `main/test_item_ai_features.py`

Tests cover:
- Authentication requirements for all endpoints
- Session-based authentication
- Ownership checks (users can only access their own items)
- Error handling when services are not configured

Run tests:
```bash
python manage.py test main.test_item_ai_features
```

## Security

- All endpoints require authentication
- Users can only access their own items (ownership check)
- CSRF protection enabled
- Supports both JWT token and session authentication

## Error Messages

Common error scenarios:

1. **"Authentication required"** (401)
   - User is not logged in
   - Solution: Log in to the system

2. **"Access denied"** (403)
   - User trying to access another user's item
   - Solution: Only access your own items

3. **"KiGate API is not enabled in settings"** (500)
   - KiGate service not configured
   - Solution: Enable and configure KiGate in Settings

4. **"Settings not configured"** (500)
   - No Settings entry exists in database
   - Solution: Create a Settings entry

5. **"Failed to enhance/build/search"** (500)
   - General service error
   - Check logs for detailed error message

## Future Enhancements

Potential improvements:

1. **Build Tasks**:
   - Add option to specify number of tasks to generate
   - Support task dependencies
   - Automatically link related tasks

2. **Check Similarity**:
   - Add similarity threshold filter
   - Support filtering by tags/section
   - Show similarity based on different criteria (tags only, description only, etc.)

3. **AI Enhancer**:
   - Support multiple languages
   - Add option to preserve original formatting
   - Provide diff view to show changes

## API Documentation

### POST /api/items/{item_id}/ai-enhance

Enhance item with AI.

**Request Body**:
```json
{
  "title": "Item title",
  "description": "Item description"
}
```

**Response**: See "AI Enhancer" section above

### POST /api/items/{item_id}/build-tasks

Build tasks from item using AI.

**Request Body**:
```json
{
  "title": "Item title",
  "description": "Item description"
}
```

**Response**: See "Build Tasks" section above

### POST /api/items/{item_id}/check-similarity

Check similarity for item.

**Request Body**:
```json
{
  "title": "Item title",
  "description": "Item description"
}
```

**Response**: See "Check Similarity" section above

## Troubleshooting

### KiGate Connection Issues

1. Verify KiGate server is running
2. Check `kigate_api_base_url` is correct
3. Verify `kigate_api_token` is valid
4. Check firewall/network connectivity

### ChromaDB Issues

1. For local: Ensure write permissions to `./chroma_db` directory
2. For cloud: Verify API key, database, and tenant settings
3. Check ChromaDB service status

### No Results in Similarity Search

1. Ensure items have been synced to ChromaDB (check `chroma_synced_at` field)
2. Try with different/longer descriptions
3. Check if ChromaDB collection has data

## Changelog

### 2025-10-19
- ✅ Implemented Build Tasks feature
- ✅ Implemented Check Similarity feature
- ✅ Updated frontend to remove placeholder alerts
- ✅ Added comprehensive tests
- ✅ Created documentation
