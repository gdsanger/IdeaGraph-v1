# Milestone Summary Optimization Feature

## Overview
This feature enables AI-powered optimization of milestone summary texts using the `summary-enhancer-agent` from KiGate. Users can review the AI-optimized version in a side-by-side comparison before deciding to accept or discard it.

## Features

### 1. AI Summary Optimization
- **One-click optimization**: Click the "AI-Optimize" button to send the current summary to the AI for enhancement
- **Preview mode**: View the optimized version alongside the original in a modal dialog
- **User control**: Accept or discard the optimized version - nothing changes without user confirmation
- **Version history**: All optimized summaries are stored with metadata for audit purposes

### 2. API Endpoints

#### Optimize Summary
```
POST /api/milestones/<milestone_id>/optimize-summary
```
**Description**: Generates an AI-optimized version of the milestone summary using the `summary-enhancer-agent`.

**Response**:
```json
{
  "success": true,
  "original_summary": "Original text...",
  "optimized_summary": "Optimized text...",
  "agent_name": "summary-enhancer-agent",
  "model": "gpt-4"
}
```

#### Save Optimized Summary
```
POST /api/milestones/<milestone_id>/save-optimized-summary
```
**Request Body**:
```json
{
  "optimized_summary": "The optimized text to save",
  "agent_name": "summary-enhancer-agent",
  "model_name": "gpt-4"
}
```

**Description**: Saves the optimized summary and creates a version history entry.

#### Get Summary History
```
GET /api/milestones/<milestone_id>/summary-history
```
**Description**: Retrieves the version history of all milestone summaries.

**Response**:
```json
{
  "success": true,
  "versions": [
    {
      "id": "uuid",
      "version_number": 2,
      "summary_text": "Version 2 text...",
      "optimized_by_ai": true,
      "agent_name": "summary-enhancer-agent",
      "model_name": "gpt-4",
      "created_by": "username",
      "created_at": "2025-10-23T10:30:00Z"
    },
    ...
  ],
  "total_versions": 2,
  "current_summary": "Current summary text..."
}
```

## User Interface

### Milestone Detail Page
On the milestone detail page, in the Summary tab:

1. **AI-Optimize Button**: Next to the "Regenerate Summary" button, available when a summary exists
2. **Comparison Modal**: Shows a side-by-side comparison of:
   - **Left**: Original summary (gray background)
   - **Right**: AI-optimized summary (green background)
3. **Action Buttons**:
   - **Accept & Save**: Saves the optimized version and creates a version history entry
   - **Discard**: Closes the modal without making changes

## Database Schema

### MilestoneSummaryVersion Model
Tracks version history of milestone summaries:

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| milestone | ForeignKey | Reference to Milestone |
| summary_text | TextField | Snapshot of the summary text |
| version_number | Integer | Sequential version number |
| optimized_by_ai | Boolean | Whether this version was AI-optimized |
| agent_name | CharField | Name of the AI agent used |
| model_name | CharField | AI model used for optimization |
| created_by | ForeignKey | User who created this version |
| created_at | DateTime | Timestamp of creation |

## Service Methods

### MilestoneKnowledgeService

#### `optimize_summary(milestone, user=None)`
Sends the current summary to the AI for optimization.

**Returns**: Dictionary with original and optimized summaries.

**Raises**: `MilestoneKnowledgeServiceError` if optimization fails.

#### `save_optimized_summary(milestone, optimized_summary, user=None, agent_name='summary-enhancer-agent', model_name='gpt-4')`
Saves the optimized summary and creates a version history entry.

**Returns**: Dictionary with success status.

#### `get_summary_history(milestone)`
Retrieves all version history entries for a milestone.

**Returns**: Dictionary with versions list and metadata.

## Testing

The feature includes comprehensive test coverage:

- **Service Tests** (6 tests):
  - Test optimize_summary method
  - Test handling of empty summaries
  - Test save_optimized_summary method
  - Test multiple version tracking
  - Test get_summary_history method

- **API Tests** (8 tests):
  - Test all three API endpoints
  - Test authentication and authorization
  - Test error handling (missing data, non-existent milestones)
  - Test permission checks

Run tests with:
```bash
python manage.py test main.test_milestone_summary_optimization
```

## Implementation Notes

### AI Agent
The feature uses the `summary-enhancer-agent` from KiGate, which is designed to:
- Remove redundancies
- Improve structure and clarity
- Unify language style
- Maintain the original content and meaning
- Create clear transitions between topics

### User Workflow
1. User navigates to Milestone Detail page
2. Clicks "AI-Optimize" button (only visible if summary exists)
3. Modal opens, showing loading state
4. AI processes the summary (via KiGate)
5. Comparison view displays original vs optimized
6. User reviews and either:
   - Clicks "Accept & Save" → Summary is updated, version history created, page reloads
   - Clicks "Discard" → Modal closes, nothing changes

### Error Handling
- No summary available: Button disabled, API returns 400
- KiGate service errors: Displayed in modal with error message
- Network errors: Toast notification shown
- Permission errors: 403 response if user doesn't own the item

## Configuration

Requires the following settings to be configured:
- `kigate_api_enabled`: Must be `True`
- `kigate_api_token`: Valid KiGate API token
- `kigate_api_base_url`: URL to KiGate service
- `openai_default_model`: Model to use (default: `gpt-4`)

## Security

- All endpoints require authentication
- Permission checks ensure only item owners (or admins) can optimize summaries
- Version history tracks who made each optimization
- CSRF protection on all POST requests

## Future Enhancements

Potential improvements:
1. **Re-optimize button**: Allow users to re-run optimization on the same text
2. **Rollback functionality**: Restore a previous version from history
3. **Diff view**: Show exact changes between versions with highlighting
4. **Batch optimization**: Optimize summaries for multiple milestones at once
5. **Custom prompts**: Allow users to specify optimization goals (shorter, more formal, etc.)
