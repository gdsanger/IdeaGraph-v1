# ChangeLog Recreation Feature

## Overview

Users can now recreate the ChangeLog in milestones at any time. When recreating, the system automatically cleans up old changelogs (from database, filesystem, and Weaviate) before generating a new one.

## Feature Details

### What Gets Cleaned Up

When you click "Recreate ChangeLog", the system removes:

1. **Database Field**: The `Milestone.changelog` text field is cleared
2. **File Records**: All `MilestoneFile` records with `content_type='text/markdown'`
3. **Physical Files**: Actual changelog files in `media/milestone_files/`
4. **Weaviate Entries**: KnowledgeObject entries with `object_type='milestone_changelog'`

### What's Preserved

- Other milestone files (PDFs, documents, etc.) are **NOT** deleted
- Only files with `content_type='text/markdown'` are removed
- The milestone itself and all other data remain intact

## User Experience

### Button Behavior

The button text changes based on context:
- **No changelog exists**: Shows "Generate ChangeLog" with robot icon
- **Changelog exists**: Shows "Recreate ChangeLog" with refresh icon

### Confirmation Dialog

When recreating an existing changelog, users see a confirmation:

```
This will replace the existing ChangeLog and all associated files. 
The old ChangeLog will be permanently deleted. Do you want to continue?
```

This ensures users don't accidentally delete their changelog.

## Technical Implementation

### API Endpoint

```
POST /api/milestones/<milestone_id>/generate-changelog
```

### Cleanup Process

The function now performs these steps in order:

1. **Identify old files**: Find all markdown MilestoneFile records
2. **Delete from Weaviate**: Remove each file's entry from Weaviate
3. **Delete physical files**: Remove files from filesystem
4. **Delete database records**: Remove MilestoneFile records
5. **Clear changelog field**: Empty the milestone.changelog field
6. **Generate new changelog**: Create fresh changelog using AI

### Error Handling

- Weaviate connection failures don't stop the recreation
- Filesystem errors are logged but don't fail the operation
- All cleanup steps are logged for debugging

## Testing

### Test Coverage

New tests verify:
- ✅ Old changelog field is cleared
- ✅ Old MilestoneFile records are deleted
- ✅ Multiple recreation cycles work correctly
- ✅ Only markdown files are deleted (others preserved)
- ✅ Weaviate sync flag works for new files

### Running Tests

```bash
python manage.py test main.test_milestone_changelog
```

## Usage Example

### Scenario: Updating Changelog After New Tasks

1. User completes additional tasks in a milestone
2. User navigates to milestone detail page
3. User clicks "Recreate ChangeLog" button
4. System confirms deletion of old changelog
5. System removes old files and Weaviate entries
6. AI generates new changelog with updated tasks
7. New changelog is stored in all locations

### Scenario: First-Time Generation

1. User has milestone with completed tasks
2. No changelog exists yet
3. User clicks "Generate ChangeLog" button
4. AI generates changelog from completed tasks
5. Changelog is stored in database, file, and Weaviate

## Files Modified

- `main/api_views.py`: Added cleanup logic
- `main/templates/main/milestones/detail.html`: Updated UI
- `main/test_milestone_changelog.py`: Added recreation tests

## Security

- ✅ CodeQL scan: 0 alerts
- ✅ Permission checks: Only admin or item owner can recreate
- ✅ No SQL injection risks
- ✅ Safe file deletion with proper path handling

## Future Enhancements

Possible future improvements:
- Keep changelog history/versions
- Allow manual editing of changelog before AI enhancement
- Export changelog in multiple formats
- Integration with release notes generation

## Related Documentation

- [Milestone Knowledge Hub](MILESTONE_KNOWLEDGE_HUB.md)
- [Milestone Interactive AI Analysis](MILESTONE_INTERACTIVE_AI_ANALYSIS.md)
- [Weaviate Milestones Fix](WEAVIATE_MILESTONES_FIX_SUMMARY.md)
