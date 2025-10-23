# GitHub Issue Creation Feature

## Overview
When creating a GitHub issue from a task in IdeaGraph v1.0, the system now automatically:
1. Assigns the issue to GitHub Copilot (or any configured GitHub user)
2. Adds a comment with a reference link back to the task in IdeaGraph

## Configuration

### Setting up GitHub Copilot Assignment

1. Navigate to the **Settings** page in the Django admin interface
2. Locate the **GitHub Copilot Username** field under the GitHub configuration section
3. Enter the GitHub username you want issues to be assigned to (e.g., "copilot")
4. Save the settings

The field is optional. If left empty, issues will be created without automatic assignment.

## How It Works

### Creating an Issue

1. Navigate to a task in IdeaGraph
2. Ensure the task status is set to **Ready**
3. Ensure the item has a GitHub repository configured (format: `owner/repo`)
4. Click the **"Create GitHub Issue"** button

### What Happens

1. **Issue Creation**: A new issue is created in the configured GitHub repository with:
   - The task's title as the issue title
   - The task's description as the issue body
   - All task tags as issue labels
   - Automatic assignment to the configured GitHub user (if set)

2. **Comment Addition**: A comment is automatically added to the issue:
   ```
   Created with IdeaGraph v1.0

   Task: https://your-ideagraph-domain.com/tasks/{task-id}
   ```
   The URL is automatically constructed from your deployment's host context.

3. **Task Update**: The task is updated with:
   - The GitHub issue number
   - The GitHub issue URL
   - A sync timestamp

### Error Handling

- If issue creation fails, an error message is displayed to the user
- If the comment creation fails, the issue is still created and a warning is logged
- This ensures that even if the comment addition fails, the primary operation (issue creation) succeeds

## URL Construction

The IdeaGraph task URL is constructed dynamically based on the request context:
- **Scheme**: Automatically detects HTTP or HTTPS based on the request
- **Host**: Uses the actual host from the request (supports multiple deployment URLs)
- **Path**: Follows the pattern `/tasks/{task-id}`

Example URLs:
- Development: `http://localhost:8000/tasks/abc123...`
- Staging: `https://staging.ideagraph.com/tasks/abc123...`
- Production: `https://ideagraph.com/tasks/abc123...`

## Testing

Comprehensive test coverage includes:
- Unit tests for the `create_issue_comment()` method
- Integration tests for the full issue creation flow
- Tests for both assigned and unassigned scenarios

Run tests with:
```bash
python manage.py test main.test_github_service
python manage.py test main.test_github_issue_creation_integration
```

## API Details

### GitHub Service Method
```python
def create_issue_comment(
    self,
    issue_number: int,
    body: str,
    repo: Optional[str] = None,
    owner: Optional[str] = None
) -> Dict[str, Any]:
    """Create a comment on an issue"""
```

### Settings Model Field
```python
github_copilot_username = models.CharField(
    max_length=255,
    blank=True,
    default='',
    verbose_name='GitHub Copilot Username',
    help_text='GitHub username to assign issues to (e.g., copilot)'
)
```

## Migration

The feature requires a database migration:
```bash
python manage.py migrate main 0027_settings_github_copilot_username
```

This migration adds the `github_copilot_username` field to the Settings model.
