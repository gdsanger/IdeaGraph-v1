# Task Templates & Task Cloning Feature

## Overview

This feature allows users to:
1. **Create Task Templates** from existing tasks for reuse
2. **Clone Tasks** to different items with selective field copying
3. **Use Templates** when creating new tasks to auto-fill common fields

## Features Implemented

### 1. Task Template Model

The `TaskTemplate` model stores reusable task configurations with:
- **Title** (required): Template name
- **Description**: Default task description in Markdown
- **Default Item**: Optional default item for tasks created from this template
- **Default Assignees**: Users who should be assigned by default
- **Tags**: Tags to apply to new tasks
- **Checklist JSON**: Placeholder for future checklist functionality
- **Created By**: User who created the template
- **Timestamps**: Creation and update times

### 2. Save Task as Template

From any task detail page, users can click **"Als Vorlage speichern"** to:
- Open a modal with field selection
- Choose which fields to include in the template:
  - Title (always included)
  - Description ✓
  - Tags ✓
  - Assignees ✓
  - Checklist (future)
- Save the template for future use

**Permissions**: Users must have at least read access to the task.

### 3. Create Task from Template

When creating a new task, users can:
- Select a template from the dropdown at the top of the form
- Auto-fill description, tags, and other fields from the template
- Override any pre-filled values before saving
- Templates are user-specific unless created by admin/developer

**Permissions**: Users can see:
- Their own templates
- Templates created by admin/developer users (shared templates)

### 4. Clone Task

From any task detail page, users can click **"Task klonen"** to:
- Open a modal to select a target item
- Choose which parts to copy:
  - Title (always copied with optional prefix)
  - Description ✓
  - Tags ✓
  - Assignees ✓
  - Comments (optional, default OFF)
- Create a new task in the target item

**Important**: 
- Cloned tasks always start with status "new"
- Mails and history are NOT copied
- The clone is created by the current user

**Permissions**: Users must have create permissions in the target item.

## API Endpoints

### Save Task as Template
```
POST /tasks/<task_id>/save-as-template/
```

Request body:
```json
{
  "title": "Template Name",
  "include_description": true,
  "include_tags": true,
  "include_assignees": false,
  "include_checklist": false
}
```

### Clone Task
```
POST /tasks/<task_id>/clone/
```

Request body:
```json
{
  "target_item_id": "uuid",
  "title_prefix": "Kopie von ",
  "include_description": true,
  "include_tags": true,
  "include_assignees": true,
  "include_comments": false
}
```

### List Templates (API)
```
GET /api/task-templates/list/
```

Returns:
```json
{
  "success": true,
  "templates": [
    {
      "id": "uuid",
      "title": "Template Name",
      "description": "...",
      "tag_ids": ["uuid1", "uuid2"],
      "default_assignee_ids": ["uuid3"],
      "checklist_json": []
    }
  ]
}
```

## Admin Interface

Templates can be managed via Django Admin:
- View all templates
- Filter by creator
- Edit template fields
- Delete templates

Access: `/admin/main/tasktemplate/`

## Template Management Views

### Template List
```
GET /admin/task-templates/
```
Shows all templates accessible to the user (own templates + admin/developer templates).

### Template Detail
```
GET /admin/task-templates/<template_id>/
```
Shows detailed information about a specific template.

## Usage Examples

### Creating a Template

1. Open any task
2. Click "Als Vorlage speichern"
3. Enter template name
4. Select fields to include
5. Click "Vorlage speichern"

### Using a Template

1. Go to an item
2. Click "Create Task"
3. Select template from dropdown
4. Fields auto-fill from template
5. Modify as needed
6. Click "Save Task"

### Cloning a Task

1. Open any task
2. Click "Task klonen"
3. Select target item
4. Choose fields to copy
5. Optionally change title prefix
6. Click "Task klonen"
7. Redirected to cloned task

## Database Schema

### TaskTemplate Table

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| title | VARCHAR(255) | Template name |
| description | TEXT | Default description |
| default_item | FK(Item) | Optional default item |
| default_assignees | M2M(User) | Default assignees |
| tags | M2M(Tag) | Template tags |
| checklist_json | JSON | Future checklist data |
| created_by | FK(User) | Creator |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Update timestamp |

## Tests

Comprehensive test suite in `main/test_task_templates.py`:

- ✅ Save task as template with fields
- ✅ Save template without tags
- ✅ Template title validation
- ✅ Clone task to another item
- ✅ Clone without description
- ✅ Target item requirement
- ✅ API template list endpoint
- ✅ Template permissions

Run tests:
```bash
python manage.py test main.test_task_templates
```

## Future Enhancements

Potential improvements for future versions:

1. **Checklist Support**: Add checklist functionality to Task model and templates
2. **Organization-wide Templates**: Shared templates visible to all users
3. **Template Categories**: Group templates by type (bug, feature, support, etc.)
4. **Template Preview**: Preview template before applying
5. **Bulk Template Application**: Apply template to multiple tasks at once
6. **Template Import/Export**: Share templates between instances
7. **Version History**: Track template changes over time
8. **Usage Analytics**: Track template usage statistics

## Security Considerations

- ✅ Permission checks for task access
- ✅ Permission checks for target item in cloning
- ✅ User-specific template visibility
- ✅ CSRF protection on all endpoints
- ✅ JSON request validation
- ✅ Input sanitization

## UI/UX Design

- Uses Bootstrap 5 modals for interactions
- HTMX for dynamic content updates
- Dark theme consistency with IdeaGraph design
- Clear visual feedback (toasts, alerts)
- Responsive design for mobile/desktop

## Migration

The feature adds one new database table (`TaskTemplate`) via migration `0049_tasktemplate.py`.

To apply:
```bash
python manage.py migrate
```

## Related Files

### Models
- `main/models.py` - TaskTemplate model

### Views
- `main/views.py` - Template and cloning views

### Templates
- `main/templates/main/tasks/_save_as_template_modal.html`
- `main/templates/main/tasks/_clone_modal.html`
- `main/templates/main/tasks/template_list.html`
- `main/templates/main/tasks/template_detail.html`
- `main/templates/main/tasks/form.html` - Updated with template selector
- `main/templates/main/tasks/detail.html` - Added buttons

### URLs
- `main/urls.py` - Added template and cloning routes

### Tests
- `main/test_task_templates.py` - Comprehensive test suite

### Admin
- `main/admin.py` - TaskTemplate admin registration
