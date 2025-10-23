# Task Move Feature

## Overview

The Task Move feature allows users to move tasks between different items, including automatically handling the relocation of associated SharePoint files.

## Features

- Move tasks from one item to another
- Automatically move task files in SharePoint
- Ensure target item folders exist before moving
- Handle tasks with or without files
- Maintain file structure and organization
- Comprehensive error handling and logging

## Architecture

### Components

1. **TaskMoveService** (`core/services/task_move_service.py`)
   - Core service handling task movement logic
   - Manages SharePoint folder operations
   - Validates task and item relationships
   - Handles file relocation

2. **GraphService Extensions** (`core/services/graph_service.py`)
   - `get_folder_by_path()` - Check if folder exists
   - `create_folder()` - Create new folders
   - `move_folder()` - Move folders between locations

3. **API Endpoint** (`main/api_views.py`)
   - `POST /api/tasks/<task_id>/move`
   - Authentication and permission checks
   - JSON-based request/response

## SharePoint Structure

Tasks can be stored in two locations:

1. **Item-based tasks**: `IdeaGraph/{item_title}/{task_uuid}/`
2. **Standalone tasks**: `IdeaGraph/Tasks/{task_uuid}/`

When moving a task:
- The entire task folder (with UUID) is moved
- Target item folder is created if it doesn't exist
- Folder names are normalized for SharePoint compatibility

## API Usage

### Request

```http
POST /api/tasks/{task_id}/move
Content-Type: application/json

{
  "target_item_id": "uuid-of-target-item"
}
```

### Response (Success)

```json
{
  "success": true,
  "message": "Task moved successfully to Item Title",
  "moved": true,
  "files_moved": true,
  "files_count": 2,
  "task_id": "task-uuid",
  "source_item_id": "source-item-uuid",
  "target_item_id": "target-item-uuid"
}
```

### Response (Already in Target)

```json
{
  "success": true,
  "message": "Task is already in the target item",
  "moved": false
}
```

### Response (Error)

```json
{
  "error": "Task not found"
}
```

## Security

- **Authentication**: User must be logged in
- **Authorization**: User must be task creator or admin
- **Stack Trace Protection**: No internal error details exposed to users
- **UUID Validation**: All IDs are validated before processing

## Error Handling

The service handles various error scenarios:

1. **Task not found**: Returns 404 with error message
2. **Target item not found**: Returns appropriate error
3. **Permission denied**: Returns 403 for unauthorized access
4. **SharePoint errors**: Logged internally, graceful degradation
5. **Database errors**: Transaction rollback, safe failure

## Testing

Comprehensive test suite in `main/test_task_move.py`:

- Task movement without files
- Task movement with files
- Moving to same item (no-op)
- Invalid task IDs
- Invalid target item IDs
- Permission checks
- API endpoint authentication
- Folder creation
- SharePoint operations (mocked)

Run tests:
```bash
python manage.py test main.test_task_move
```

## Usage Example

### Moving a Task via API

```python
import requests

# Authenticate first
session = requests.Session()
# ... login ...

# Move task
response = session.post(
    'http://localhost:8000/api/tasks/task-uuid/move',
    json={
        'target_item_id': 'target-item-uuid'
    }
)

result = response.json()
if result['success']:
    print(f"Task moved: {result['message']}")
    print(f"Files moved: {result['files_count']}")
```

### Using TaskMoveService Directly

```python
from main.models import Settings
from core.services.task_move_service import TaskMoveService

# Initialize service
settings = Settings.objects.first()
move_service = TaskMoveService(settings)

# Move task
result = move_service.move_task(
    task_id='task-uuid',
    target_item_id='target-item-uuid',
    user=current_user
)

if result['success']:
    print(f"Task moved successfully")
```

## Folder Name Normalization

SharePoint doesn't allow certain characters in folder names. The service normalizes folder names by:

1. Replacing invalid characters (`~"#%&*:<>?/\\{|}`) with underscores
2. Removing leading/trailing dots and spaces
3. Collapsing multiple underscores to single underscore
4. Limiting length to 255 characters
5. Using 'Untitled' as fallback for empty names

## Logging

The service provides detailed logging:

- **INFO**: Normal operations (task moved, folder created)
- **WARNING**: Non-critical issues (folder not found, continuing anyway)
- **ERROR**: Critical failures (GraphService errors, database errors)

All logs use the `task_move_service` logger.

## Future Enhancements

Potential improvements:

1. **Bulk Move**: Move multiple tasks at once
2. **Move History**: Track task movement history
3. **Undo**: Ability to undo recent moves
4. **UI Integration**: Add move button to task detail page
5. **Notifications**: Notify assigned users of task moves
6. **Cross-Item Dependencies**: Handle task dependencies during moves

## Related Documentation

- [File Upload Feature](FILE_UPLOAD_QUICK_REF.md)
- [SharePoint Integration](SHAREPOINT_UPLOAD_DEBUG_GUIDE.md)
- [Task Management](TASK_CLEANUP_GUIDE.md)
