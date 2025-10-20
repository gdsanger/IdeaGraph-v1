# GitHub Issue Display Fix

## Problem Statement

The display of similar GitHub Issues in the Task Detail view had several issues:

1. **Incorrect Title**: The title was showing "Untitled Issue" instead of the actual GitHub issue title
2. **Missing GitHub Issue ID**: The title was not formatted with the repository and issue number (e.g., `owner/repo#123`)
3. **Wrong URL Field**: The system was looking for `html_url` field instead of `github_issue_url`
4. **Outdated Status**: The status was not being refreshed from the GitHub API, showing stale data

## Solution

### 1. Corrected Metadata Field Names

Updated the API view to use the correct metadata field names stored in ChromaDB:
- `github_issue_id` instead of `number`
- `github_issue_title` instead of `title`
- `github_issue_url` instead of `html_url`
- `github_issue_state` instead of `state`

### 2. Title Formatting

The title is now formatted as: `owner/repo#issue_number Issue Title`

Example: `gdsanger/IdeaGraph-v1#1 Das ist das erste Issue`

### 3. Real-time Status Updates

The system now:
- Fetches the current issue state from GitHub API when displaying similar issues
- Updates the ChromaDB metadata if the state has changed
- Displays the current status (Open/Closed) to users

### 4. Security Improvements

Fixed a security vulnerability by implementing proper URL validation:
- Uses Python's `urlparse` to validate GitHub URLs
- Checks that the hostname is exactly `github.com`
- Prevents URL injection attacks

## Technical Details

### Modified Files

- `main/api_views.py`: Updated the `api_task_similar` function (lines 2353-2425)
- `main/test_github_issue_display.py`: Added comprehensive tests for the fixes

### Code Flow

1. Search for similar GitHub issues in ChromaDB
2. Extract metadata with corrected field names
3. Parse GitHub URL using `urlparse` to extract owner/repo
4. Format title with owner/repo#issue_number prefix
5. Fetch current state from GitHub API
6. Update ChromaDB if state changed
7. Return formatted data to frontend

### Error Handling

The implementation includes graceful error handling:
- If URL parsing fails, uses the original title without formatting
- If GitHub API is unavailable, uses the cached state from ChromaDB
- Logs warnings for debugging without breaking functionality

## Testing

Added two test cases:
1. `test_github_issue_metadata_fields`: Validates correct metadata usage and state updates
2. `test_github_issue_without_state_update`: Ensures functionality works even if GitHub API fails

All tests pass successfully, including existing tests for authentication and access control.

## Security

CodeQL analysis confirms no security vulnerabilities in the updated code.

The fix addresses CVE-class issues related to:
- Incomplete URL substring sanitization
- Proper input validation
- Secure API integration

## Impact

Users will now see:
- Accurate GitHub issue titles with proper formatting
- Current issue status (not stale data)
- Clickable links that work correctly
- Better context with owner/repo#number format

## Future Improvements

Potential enhancements for consideration:
1. Cache GitHub API responses to reduce API calls
2. Add rate limit handling for GitHub API
3. Display more metadata (labels, assignees, etc.)
4. Add visual indicators for PRs vs Issues
