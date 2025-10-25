# Global Semantic Search - Implementation Summary

## Overview
Implemented a global semantic search feature for IdeaGraph that allows users to search across all objects stored in the Weaviate KnowledgeObject collection using AI-powered semantic similarity.

## Features Implemented

### 🔍 1. Global Search Service
**File:** `core/services/weaviate_search_service.py`

- **WeaviateSearchService** class with semantic search functionality
- Searches across all KnowledgeObject types (Items, Tasks, Files, Milestones, Conversations, Issues, etc.)
- Returns top N results with relevance scores (0-1, higher = more relevant)
- Supports filtering by object type
- Configurable result limit (default: 10, max: 50)

**Key Methods:**
- `search(query, limit=10, object_types=None)` - Main search method
- Returns results with: id, type, title, description, url, relevance, metadata

### 🔌 2. REST API Endpoint
**Endpoint:** `GET /api/search`

**Query Parameters:**
- `query` (required) - Search query text (natural language)
- `limit` (optional) - Maximum results to return (1-50, default: 10)
- `types` (optional) - Comma-separated object types to filter (e.g., "Item,Task")

**Authentication:** Supports both JWT Bearer token and Django session authentication

For API clients using JWT:
- Include `Authorization: Bearer YOUR_TOKEN` header

For web browsers using sessions:
- Session cookies are automatically included
- No additional authentication headers needed

**Response Format:**
```json
{
  "success": true,
  "results": [
    {
      "id": "uuid",
      "type": "Item",
      "title": "Title",
      "description": "Description preview...",
      "url": "/items/uuid/",
      "relevance": 0.87,
      "metadata": {
        "owner": "username",
        "section": "Section Name",
        "status": "new",
        "tags": ["tag1", "tag2"]
      }
    }
  ],
  "total": 10,
  "query": "original query"
}
```

### 🎨 3. User Interface
**URL:** `/search/`

**Components:**
- Global search page with prominent search input
- Real-time search via API (AJAX)
- Beautiful result cards with:
  - Type badges (color-coded by object type)
  - Relevance score with visual progress bar
  - Title (clickable link to object)
  - Description preview (truncated to 200 chars)
  - Metadata (owner, section, status, tags)
- Empty states for no query/no results
- Loading spinner during search
- Responsive design matching IdeaGraph corporate identity

**Navigation:**
- Added "Search" link in main navigation menu (between Settings and Mail-Eingang)
- Accessible from any page in the application

### 🧪 4. Testing
**File:** `main/test_global_search.py`

**Test Coverage:**
- Authentication requirement (JWT and session-based)
- Query parameter validation
- Search with results
- Search with type filters
- Search with custom limits
- Empty result handling
- View URL and context
- Session authentication (verifies fix for "Please login" error)
- Search with custom limits
- Empty result handling
- View URL and context

**Test Results:** ✅ All 7 API tests passing (including session auth test)

## Technical Details

### Architecture
1. **Service Layer** - `WeaviateSearchService` handles Weaviate client initialization and search logic
2. **API Layer** - `api_global_search` endpoint handles HTTP requests, authentication, and response formatting
3. **View Layer** - `global_search_view` renders the search page
4. **Template Layer** - Beautiful, interactive search UI with JavaScript for API calls

### Weaviate Integration
- Uses `near_text` query for semantic search
- Leverages existing KnowledgeObject collection
- Supports both local Weaviate (localhost:8081) and Weaviate Cloud
- Returns distance and certainty metrics for relevance scoring
- Automatic client connection management (open/close)

### Security
- **Dual Authentication Support**: API accepts both JWT tokens and Django session cookies
  - JWT tokens for programmatic API access
  - Session cookies for web browser access
- User must be logged in to access search page
- Input validation on query parameters
- XSS protection via HTML escaping

## Usage Examples

### Via API
```bash
# Search using JWT authentication
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/search?query=authentication&limit=5"

# Search using session authentication (from browser)
# Session cookies are automatically included by the browser
curl -b cookies.txt \
  "http://localhost:8000/api/search?query=authentication&limit=5"

# Search only in Items and Tasks
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/search?query=token&types=Item,Task"
```

### Via UI
1. Click "Search" in navigation menu
2. Enter natural language query (e.g., "How does token authentication work?")
3. Press Enter or click Search button
4. View results with relevance scores
5. Click on result to navigate to object

## Files Modified/Created

### Created:
- `core/services/weaviate_search_service.py` (267 lines) - Search service
- `main/templates/main/search/results.html` (393 lines) - Search UI
- `main/test_global_search.py` (236 lines) - Tests

### Modified:
- `main/api_views.py` - Added `api_global_search` endpoint
- `main/views.py` - Added `global_search_view` view
- `main/urls.py` - Added routes for search view and API
- `main/templates/main/base.html` - Added Search link to navbar

## Performance Considerations
- Search limited to 50 results maximum
- Client connections properly closed after each request
- Efficient Weaviate near_text queries
- Description truncated to 200 chars for preview

## Future Enhancements (Not Implemented)
- Date range filtering
- Advanced filters (status, section, owner)
- Search result pagination
- Search history
- Saved searches
- Search suggestions/autocomplete
- Export search results

## Dependencies
- weaviate-client>=4.9.0 (already in requirements.txt)
- Django>=5.1.12 (already in requirements.txt)
- requests>=2.31.0 (already in requirements.txt)

## Configuration
No additional configuration required. Uses existing Weaviate settings from Settings model:
- `weaviate_cloud_enabled`
- `weaviate_url`
- `weaviate_api_key`

## Testing Instructions
```bash
# Run all search tests
python manage.py test main.test_global_search -v 2

# Run specific test
python manage.py test main.test_global_search.GlobalSearchAPITest.test_search_returns_results -v 2
```

## Deployment Notes
1. Ensure Weaviate is running (local or cloud)
2. Ensure KnowledgeObject collection exists and is populated
3. No database migrations required
4. Static files are inline in template (no collectstatic needed)
5. Works with existing authentication system

## Summary
✅ Fully functional global semantic search
✅ Beautiful, intuitive UI
✅ Comprehensive API
✅ Well tested
✅ Production-ready

## Bug Fixes

### Authentication Error Fix (2025-10-25)
**Issue:** Users encountered "Please login" and "No authentication token found" errors when using Global Search, even when logged in via the web interface.

**Root Cause:** The search page JavaScript incorrectly required JWT tokens from sessionStorage, but web users authenticate via Django session cookies, not JWT tokens.

**Solution:**
- Updated `main/templates/main/search/results.html` to use session-based authentication
- Removed JWT token requirement from JavaScript
- Added `credentials: 'same-origin'` to fetch requests to include session cookies
- Improved error handling for 401 responses with login redirect link
- Added test case `test_search_with_session_authentication` to verify fix

**Files Modified:**
- `main/templates/main/search/results.html` - Fixed authentication method
- `main/test_global_search.py` - Added session auth test
- `GLOBAL_SEARCH_IMPLEMENTATION.md` - Updated documentation
