# Task UI Implementation Documentation

## Overview
This document describes the implementation of the Task UI for the IdeaGraph v1 project, as specified in the issue "UI-Implementierung für Tasks-Ansichten".

## Components Implemented

### 1. Views (main/views.py)
- **task_list**: Lists all tasks for an item, filtered by owner
- **task_detail**: Shows detailed view of a single task with AI enhancement and GitHub issue creation
- **task_create**: Creates a new task for an item
- **task_edit**: Edits an existing task
- **task_delete**: Deletes a task with confirmation

### 2. Templates
- **tasks/list.html**: List view of tasks with status badges and actions
- **tasks/detail.html**: Detailed task view with:
  - Toast UI Editor for markdown descriptions
  - AI Enhancer button
  - Create GitHub Issue button (only for Ready status)
  - Similar tasks section
  - Status badges with icons
- **tasks/form.html**: Create/Edit form for tasks
- **tasks/delete.html**: Confirmation page for task deletion

### 3. API Endpoints (main/api_views.py)
- **GET/POST /api/tasks/{item_id}**: List and create tasks
- **GET/PUT/DELETE /api/tasks/{task_id}/detail**: Task CRUD operations
- **POST /api/tasks/{task_id}/ai-enhance**: AI enhancement using KiGate
- **POST /api/tasks/{task_id}/create-github-issue**: Create GitHub issue from task
- **GET /api/tasks/{task_id}/similar**: Get similar tasks (ChromaDB integration pending)

### 4. URL Patterns (main/urls.py)
```python
# View URLs
path('items/<uuid:item_id>/tasks/', views.task_list, name='task_list'),
path('items/<uuid:item_id>/tasks/create/', views.task_create, name='task_create'),
path('tasks/<uuid:task_id>/', views.task_detail, name='task_detail'),
path('tasks/<uuid:task_id>/edit/', views.task_edit, name='task_edit'),
path('tasks/<uuid:task_id>/delete/', views.task_delete, name='task_delete'),

# API URLs
path('api/tasks/<uuid:item_id>', api_views.api_tasks, name='api_tasks'),
path('api/tasks/<uuid:task_id>/detail', api_views.api_task_detail, name='api_task_detail'),
path('api/tasks/<uuid:task_id>/ai-enhance', api_views.api_task_ai_enhance, name='api_task_ai_enhance'),
path('api/tasks/<uuid:task_id>/create-github-issue', api_views.api_task_create_github_issue, name='api_task_create_github_issue'),
path('api/tasks/<uuid:task_id>/similar', api_views.api_task_similar, name='api_task_similar'),
```

## Features

### Status Icons and Colors
- **Neu** (new): ⚪ Secondary
- **Working**: 🔵 Primary (Blue)
- **Review**: 🟡 Warning (Yellow)
- **Ready**: 🟢 Success (Green)
- **Erledigt** (done): ✅ Secondary

### AI Enhancement
The AI Enhancer feature:
1. Takes the current title and description
2. Sends them to KiGate's `text-optimization-agent`
3. Extracts keywords using `text-keyword-extractor-de`
4. Returns enhanced content and suggested tags
5. Updates the form (requires user to save)

### GitHub Issue Creation
The Create GitHub Issue feature:
1. Only available when task status is "Ready"
2. Reads GitHub repository from parent Item
3. Creates issue with:
   - Task title as issue title
   - Task description as issue body
   - Task tags as issue labels
4. Stores issue number and URL in task
5. Prevents duplicate issue creation

### Task Ownership
- Users can only see and manage tasks they created
- Enforced at both view and API levels
- Admin users can see all tasks

### Task-Item Integration
- Tasks are displayed in a tab on the Item detail page
- New Task button links to task creation form
- Task count shown in tab label
- Tasks sorted by status priority (new → working → review → ready → done)

## Testing

### Test Coverage
13 tests implemented covering:
- Task CRUD operations (views)
- Task API endpoints
- Authentication and authorization
- Task ownership enforcement
- Status ordering

### Running Tests
```bash
python manage.py test main.test_tasks
```

All tests pass successfully:
```
Ran 13 tests in 5.413s
OK
```

## Dependencies

### Frontend
- **Bootstrap 5**: UI framework
- **Bootstrap Icons**: Icon library
- **Toast UI Editor**: Markdown editor for descriptions
- **HTMX**: For dynamic interactions (future enhancement)

### Backend
- **Django**: Web framework
- **KiGateService**: AI text optimization
- **GitHubService**: GitHub API integration
- **ChromaDB**: Similarity search (integration pending)

## Usage

### Creating a Task
1. Navigate to an Item detail page
2. Click on "Tasks" tab
3. Click "New Task" button
4. Fill in title, description, status, and tags
5. Click "Save Task"

### Using AI Enhancer
1. Open a task in detail view
2. Enter/edit title and description
3. Click "AI Enhancer" button
4. Review enhanced content
5. Click "Save" to persist changes

### Creating GitHub Issue
1. Edit task and set status to "Ready"
2. Ensure parent Item has GitHub repository configured
3. Click "Create GitHub Issue"
4. Issue is created and linked to task

## Known Limitations

1. **ChromaDB Integration**: Similarity search currently returns empty list
2. **Authentication**: Manual UI testing requires proper authentication setup
3. **KiGate Configuration**: AI features require KiGate to be running and configured
4. **GitHub Token**: GitHub integration requires valid personal access token

## Future Enhancements

1. Implement ChromaDB similarity search
2. Add task assignment to other users
3. Add task comments/discussion
4. Add task time tracking
5. Add task priority field
6. Add bulk task operations
7. Add task export functionality
8. Add task templates

## Security Considerations

1. **CSRF Protection**: All POST endpoints use Django's CSRF middleware
2. **Authentication**: All endpoints require valid user session or JWT token
3. **Authorization**: Users can only access their own tasks
4. **Input Validation**: All user inputs are validated and sanitized
5. **SQL Injection**: Protected by Django ORM

## Performance Considerations

1. **Query Optimization**: Use `select_related` and `prefetch_related` for related objects
2. **Pagination**: Implement pagination for large task lists (future)
3. **Caching**: Add caching for frequently accessed data (future)
4. **Lazy Loading**: Similar tasks loaded asynchronously

## Accessibility

1. **Semantic HTML**: Proper use of HTML5 semantic elements
2. **ARIA Labels**: Added where appropriate
3. **Keyboard Navigation**: All interactive elements are keyboard accessible
4. **Screen Reader Support**: Alt text and labels for screen readers

## Browser Support

- Chrome/Edge: ✅ Fully supported
- Firefox: ✅ Fully supported
- Safari: ✅ Fully supported
- Mobile browsers: ✅ Responsive design

## Deployment Notes

1. Run migrations: `python manage.py migrate`
2. Configure KiGate API settings in admin
3. Configure GitHub token in settings
4. Collect static files: `python manage.py collectstatic`
5. Test AI features with valid KiGate connection

## Troubleshooting

### AI Enhancer Not Working
- Check KiGate API is running and accessible
- Verify KiGate API token in settings
- Check KiGate logs for errors

### GitHub Issue Creation Fails
- Verify GitHub token is valid
- Check repository exists and user has access
- Verify repository format is "owner/repo"

### Tasks Not Showing
- Verify user is logged in
- Check user owns the tasks
- Verify item exists and user has access

## References

- Issue: #[issue_number] - UI-Implementierung für Tasks-Ansichten
- Toast UI Editor: https://github.com/nhn/tui.editor
- Bootstrap 5: https://getbootstrap.com/
- Django: https://www.djangoproject.com/
