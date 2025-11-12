# IdeaGraph Actions API

The IdeaGraph Actions API provides RESTful endpoints for interacting with Items, Tasks, semantic search, files, and milestones. It's designed for integration with CustomGPT and other AI agents.

## Table of Contents

- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
  - [Items](#items)
  - [Tasks](#tasks)
  - [Semantic Search](#semantic-search)
  - [Files](#files)
  - [Milestones](#milestones)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Configuration](#configuration)

## Authentication

All API endpoints require authentication using an API key.

### API Key Setup

1. Generate an API key for a user:
```python
from main.models import User, ApiKey

user = User.objects.get(username='your_username')
api_key = ApiKey.generate_key(
    user=user,
    name='My API Key',
    expires_at=None  # Optional expiration
)

# Save the key value - it won't be shown again
print(f"API Key: {api_key.key}")
```

2. Include the API key in all requests:
```bash
curl -H "X-IG-API-Key: YOUR_API_KEY" \
     https://idea.angermeier.net/api/ideagraph/items/
```

### API Key Management

- API keys can be rotated by creating new keys and deactivating old ones
- Keys can have optional expiration dates
- Last used timestamp is tracked for security auditing

## Rate Limiting

- **Default rate**: 100 requests per hour per user
- **Burst rate**: 10 requests per minute per user

When rate limit is exceeded, you'll receive a `429 Too Many Requests` response.

## Endpoints

### Items

#### List Items
```http
GET /api/ideagraph/items/
```

**Query Parameters:**
- `query` (string): Search in title or description
- `tag` (string): Filter by tag name
- `limit` (integer, max 100): Number of results

**Response:**
```json
{
  "success": true,
  "items": [
    {
      "id": "uuid",
      "title": "Item Title",
      "description": "Item description...",
      "status": "new",
      "github_repo": "owner/repo",
      "section_name": "Section Name",
      "tags": [{"id": "uuid", "name": "python", "color": "#3b82f6"}],
      "created_by": {"id": "uuid", "username": "user"},
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

#### Get Item Detail
```http
GET /api/ideagraph/items/{id}/
```

**Response:** Item object with additional `file_count`, `task_count`, and `milestone_count` fields.

#### Get Item Files
```http
GET /api/ideagraph/items/{id}/files/
```

**Response:**
```json
{
  "success": true,
  "files": [
    {
      "id": "uuid",
      "filename": "document.pdf",
      "file_id": "file-id-for-weaviate",
      "file_size": 1024,
      "content_type": "application/pdf",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

### Tasks

#### List Tasks
```http
GET /api/ideagraph/tasks/
```

**Query Parameters:**
- `itemId` (uuid): Filter by item
- `status` (string): Filter by status (new, review, ready, working, testing, done)
- `query` (string): Search in title or description
- `limit` (integer, max 100): Number of results

**Response:**
```json
{
  "success": true,
  "tasks": [
    {
      "id": "uuid",
      "title": "Task Title",
      "description": "Task description...",
      "status": "new",
      "type": "bug",
      "item_id": "uuid",
      "milestone_id": "uuid",
      "tags": [{"id": "uuid", "name": "urgent", "color": "#ef4444"}],
      "assigned_to": {"id": "uuid", "username": "user"},
      "created_by": {"id": "uuid", "username": "creator"},
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

#### Create Task
```http
POST /api/ideagraph/tasks/
Content-Type: application/json
```

**Request Body:**
```json
{
  "title": "New Task",
  "description": "Task description",
  "status": "new",
  "type": "feature",
  "item_id": "uuid",
  "milestone_id": "uuid",
  "tag_ids": ["uuid1", "uuid2"]
}
```

**Response:** Task object with `201 Created` status.

#### Get Task Detail
```http
GET /api/ideagraph/tasks/{id}/
```

**Response:** Task object.

#### Update Task
```http
PATCH /api/ideagraph/tasks/{id}/
Content-Type: application/json
```

**Request Body:** (all fields optional)
```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "status": "done",
  "tag_ids": ["uuid1", "uuid2"]
}
```

**Response:** Updated task object.

### Semantic Search

Perform semantic search across all knowledge objects (Items, Tasks, Files, Issues, PRs, etc.) using Weaviate.

```http
GET /api/ideagraph/search/semantic/
```

**Query Parameters:**
- `query` (string, required): Search query
- `types` (string): Comma-separated list of types (Item, Task, File, GitHubIssue, PullRequest, Email, Note, Transcript, Milestone)
- `limit` (integer, max 50): Number of results

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "id": "uuid",
      "type": "Task",
      "title": "Relevant Task",
      "excerpt": "This is an excerpt of the content...",
      "score": 0.95,
      "metadata": {"status": "new"}
    }
  ],
  "count": 1
}
```

Results are sorted by relevance score (0-1, higher is better).

### Files

Retrieve file content from Weaviate by file ID.

```http
GET /api/ideagraph/files/{fileId}/
```

**Response:**
```json
{
  "success": true,
  "file": {
    "file_id": "file-id",
    "filename": "document.pdf",
    "content_type": "application/pdf",
    "content": "Full file content...",
    "size": 1024,
    "excerpt": "First 350 characters...",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### Milestones

#### List Milestones
```http
GET /api/ideagraph/milestones/
```

**Query Parameters:**
- `itemId` (uuid): Filter by item
- `status` (string): Filter by status (planned, in_progress, completed)

**Response:**
```json
{
  "success": true,
  "milestones": [
    {
      "id": "uuid",
      "name": "Milestone Name",
      "description": "Description",
      "due_date": "2024-12-31",
      "status": "in_progress",
      "item_id": "uuid",
      "item_title": "Item Title",
      "task_count": 5,
      "summary": "AI-generated summary...",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

#### Get Milestone Detail
```http
GET /api/ideagraph/milestones/{id}/
```

**Response:** Milestone object.

#### Get Milestone Changelog
```http
GET /api/ideagraph/milestones/{id}/changelog/
```

Generates or retrieves AI-powered markdown changelog.

**Response:**
```json
{
  "success": true,
  "changelog": "# Changelog\n\n## Features\n- Feature 1\n- Feature 2\n\n## Fixes\n- Bug fix 1",
  "metadata": {
    "task_count": 10,
    "agent_used": "changelog-generator"
  }
}
```

#### Generate Milestone Summary
```http
POST /api/ideagraph/milestones/{id}/summarize/
```

Generates AI summary from context objects (files, emails, notes, transcripts).

**Response:**
```json
{
  "success": true,
  "summary": "AI-generated summary of the milestone based on all context...",
  "metadata": {
    "context_count": 5,
    "agent_used": "milestone-summarizer"
  }
}
```

## Error Handling

All errors follow a consistent format:

```json
{
  "success": false,
  "error": "Error message",
  "details": "Additional details about the error"
}
```

### Common HTTP Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `403 Forbidden`: Authentication failed or API disabled
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Examples

### CustomGPT Action Configuration

To use the API with CustomGPT, configure an action with:

1. **Authentication:** API Key in header
   - Header name: `X-IG-API-Key`
   - API key value: Your generated key

2. **Optional Headers:**
   - `X-IG-Actor`: Identifier for the actor (e.g., `gpt/customgpt-id`)
   - `X-IG-User`: User identifier

3. **OpenAPI Schema:** Import from `docs/openapi/ideagraph_actions.yaml`

### Example Workflow: Search and Create Task

1. **Search for relevant information:**
```bash
curl -H "X-IG-API-Key: YOUR_KEY" \
     "https://idea.angermeier.net/api/ideagraph/search/semantic/?query=bug+authentication&types=Task,Item&limit=5"
```

2. **Create a task based on findings:**
```bash
curl -X POST \
     -H "X-IG-API-Key: YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Fix authentication bug",
       "description": "Based on search results...",
       "status": "new",
       "type": "bug",
       "item_id": "item-uuid-from-search"
     }' \
     https://idea.angermeier.net/api/ideagraph/search/semantic/
```

### Example: Get File Content for Context

```bash
# Get item files
curl -H "X-IG-API-Key: YOUR_KEY" \
     https://idea.angermeier.net/api/ideagraph/items/ITEM_UUID/files/

# Get file content
curl -H "X-IG-API-Key: YOUR_KEY" \
     https://idea.angermeier.net/api/ideagraph/files/FILE_ID/
```

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# Actions API Configuration
ACTIONS_API_ENABLED=true
ACTIONS_API_KEY_HEADER=X-IG-API-Key
ACTIONS_API_ACTOR_HEADER=X-IG-Actor
ACTIONS_API_USER_HEADER=X-IG-User

# Weaviate Configuration (required for semantic search and files)
WEAVIATE_URL=http://localhost:8081
WEAVIATE_TIMEOUT=6

# KiGate Configuration (required for milestone summaries/changelogs)
KIGATE_API_URL=http://kigate:8000
KIGATE_API_KEY=your-kigate-key
```

### Django Settings

The API is automatically configured when `ACTIONS_API_ENABLED=true`. Additional configuration:

```python
# REST Framework throttling
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'actions_api': '100/hour',
        'actions_api_burst': '10/minute',
    }
}
```

## Security Considerations

1. **API Keys**: Treat API keys like passwords. Never commit them to version control.
2. **HTTPS**: Always use HTTPS in production to protect API keys in transit.
3. **Key Rotation**: Regularly rotate API keys for security.
4. **Rate Limiting**: Respect rate limits to avoid service disruption.
5. **User Permissions**: API keys inherit the permissions of the associated user.
6. **Audit Logs**: All API requests are logged with user and actor information.

## Testing

Run the test suite:

```bash
# All Actions API tests
python manage.py test main.test_actions_api_*

# Specific test modules
python manage.py test main.test_actions_api_auth
python manage.py test main.test_actions_api_items
python manage.py test main.test_actions_api_tasks
python manage.py test main.test_actions_api_semantic_search
```

## Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/gdsanger/IdeaGraph-v1/issues
- Documentation: See `/docs/` directory

## License

See LICENSE file in the repository root.
