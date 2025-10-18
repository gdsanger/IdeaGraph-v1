# GitHub API Integration - Usage Examples

## Overview

The GitHub API integration provides direct access to GitHub repositories and issues through the IdeaGraph system. This integration is designed for admins and developers to manage GitHub resources.

## Configuration

Before using the GitHub API integration, configure the following settings in the database (Settings model):

- `github_api_enabled`: Set to `true` to enable the integration
- `github_token`: Personal Access Token (PAT) from GitHub
- `github_api_base_url`: GitHub API base URL (default: `https://api.github.com`)
- `github_default_owner`: Default repository owner (optional)
- `github_default_repo`: Default repository name (optional)

## Python API Usage

### Import the Service

```python
from core.services.github_service import GitHubService
```

### List Repositories

```python
# Initialize service
gh = GitHubService()

# Get repositories for authenticated user
repos = gh.get_repositories()
print(f"Found {repos['count']} repositories")

# Get repositories for specific owner
repos = gh.get_repositories(owner='ca-angermeier')

# With pagination
repos = gh.get_repositories(per_page=50, page=2)
```

### Create an Issue

```python
# Create issue with full details
result = gh.create_issue(
    owner='ca-angermeier',
    repo='ideagraph',
    title='Add Graph API integration',
    body='Implementiere Microsoft Graph API Service mit SharePoint und Mail Support.',
    labels=['enhancement', 'backend'],
    assignees=['ca-angermeier']
)

print(f"Created issue #{result['issue_number']}")
print(f"URL: {result['url']}")

# Create issue using default owner/repo from settings
result = gh.create_issue(
    title='Fix bug in user authentication',
    body='Users cannot log in when...',
    labels=['bug']
)
```

### Get Issue Details

```python
# Get specific issue
issue = gh.get_issue(
    owner='ca-angermeier',
    repo='ideagraph',
    issue_number=102
)

print(f"Issue: {issue['issue']['title']}")
print(f"State: {issue['issue']['state']}")
print(f"Labels: {[label['name'] for label in issue['issue']['labels']]}")
```

### List Issues

```python
# List open issues
issues = gh.list_issues(
    owner='ca-angermeier',
    repo='ideagraph',
    state='open'
)

print(f"Found {issues['count']} open issues")

# List closed issues with label filter
issues = gh.list_issues(
    owner='ca-angermeier',
    repo='ideagraph',
    state='closed',
    labels=['bug', 'critical']
)

# With pagination
issues = gh.list_issues(
    owner='ca-angermeier',
    repo='ideagraph',
    per_page=30,
    page=1
)
```

## REST API Usage

### Authentication

All endpoints require authentication with a JWT token. Only users with `admin` or `developer` roles can access these endpoints.

```bash
# Login first
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Use the returned token in subsequent requests
TOKEN="your-jwt-token-here"
```

### List Repositories

```bash
# GET /api/github/repos
curl -X GET "http://localhost:8000/api/github/repos" \
  -H "Authorization: Bearer $TOKEN"

# With parameters
curl -X GET "http://localhost:8000/api/github/repos?owner=ca-angermeier&per_page=50&page=1" \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "success": true,
  "repositories": [
    {
      "id": 123456,
      "name": "ideagraph",
      "full_name": "ca-angermeier/ideagraph",
      "description": "IdeaGraph project",
      "html_url": "https://github.com/ca-angermeier/ideagraph"
    }
  ],
  "count": 1
}
```

### Create an Issue

```bash
# POST /api/github/create-issue
curl -X POST "http://localhost:8000/api/github/create-issue" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "ca-angermeier",
    "repo": "ideagraph",
    "title": "Add Graph API integration",
    "body": "Implementiere Microsoft Graph API Service mit SharePoint und Mail Support.",
    "labels": ["enhancement", "backend"],
    "assignees": ["ca-angermeier"]
  }'
```

Response:
```json
{
  "success": true,
  "issue": {
    "number": 102,
    "title": "Add Graph API integration",
    "state": "open",
    "html_url": "https://github.com/ca-angermeier/ideagraph/issues/102"
  },
  "issue_number": 102,
  "url": "https://github.com/ca-angermeier/ideagraph/issues/102"
}
```

### Get Issue Details

```bash
# GET /api/github/issue/{owner}/{repo}/{issue_number}
curl -X GET "http://localhost:8000/api/github/issue/ca-angermeier/ideagraph/102" \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "success": true,
  "issue": {
    "number": 102,
    "title": "Add Graph API integration",
    "body": "Implementiere Microsoft Graph API Service...",
    "state": "open",
    "labels": [
      {"name": "enhancement"},
      {"name": "backend"}
    ],
    "assignees": [
      {"login": "ca-angermeier"}
    ],
    "created_at": "2025-10-17T10:00:00Z",
    "updated_at": "2025-10-17T10:00:00Z"
  }
}
```

### List Issues

```bash
# GET /api/github/issues/{owner}/{repo}
curl -X GET "http://localhost:8000/api/github/issues/ca-angermeier/ideagraph?state=open" \
  -H "Authorization: Bearer $TOKEN"

# With filters
curl -X GET "http://localhost:8000/api/github/issues/ca-angermeier/ideagraph?state=closed&labels=bug,critical&per_page=30&page=1" \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "success": true,
  "issues": [
    {
      "number": 102,
      "title": "Add Graph API integration",
      "state": "open",
      "labels": [{"name": "enhancement"}]
    }
  ],
  "count": 1
}
```

## Error Handling

All endpoints return structured error responses:

```json
{
  "success": false,
  "error": "Not Found",
  "details": "Repository 'example' not found or unauthorized."
}
```

Common HTTP status codes:
- `200`: Success (GET requests)
- `201`: Created (POST requests)
- `400`: Bad Request (missing or invalid parameters)
- `401`: Unauthorized (invalid or expired GitHub token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found (resource does not exist)
- `422`: Unprocessable Entity (validation failed)
- `500`: Internal Server Error

## Rate Limits

GitHub API has rate limits:
- **5000 requests per hour** for authenticated requests

The service logs all requests with method, endpoint, and response code for monitoring.

## Security Considerations

1. **Token Storage**: The GitHub PAT is stored in the database (Settings model) and should be encrypted in production
2. **Access Control**: Only users with `admin` or `developer` roles can access GitHub API endpoints
3. **Token Permissions**: Configure the GitHub PAT with minimal required scopes (repo, issues)
4. **Logging**: All API calls are logged for audit purposes
5. **Error Messages**: Internal error details are logged but not exposed to clients

## Testing

Run the test suite:

```bash
python manage.py test main.test_github_service
```

The test suite includes 26 comprehensive tests covering:
- Service initialization and configuration
- Repository operations
- Issue creation, retrieval, and listing
- Error handling and edge cases
- API endpoint authentication and authorization
