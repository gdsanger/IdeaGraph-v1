# Milestone Interactive AI Analysis - Quick Reference

## Quick Start

### Adding Context with Auto-Analysis

```python
from core.services.milestone_knowledge_service import MilestoneKnowledgeService

service = MilestoneKnowledgeService()

# Add context object with automatic analysis
result = service.add_context_object(
    milestone=milestone,
    context_type='note',
    title='Team Meeting Q4',
    content='Discussion about launch strategy...',
    user=request.user,
    auto_analyze=True  # Triggers AI analysis automatically
)

# Result includes analysis data
print(result['analysis']['summary'])
print(result['analysis']['derived_tasks'])
```

### Enhancing Summary

```python
# Enhance an existing summary
result = service.enhance_summary(context_obj)
enhanced_text = result['enhanced_summary']
```

### Accepting Analysis Results

```python
# Accept with original analysis
result = service.accept_analysis_results(context_obj)

# Accept with edited data
result = service.accept_analysis_results(
    context_obj,
    summary='Edited summary text',
    derived_tasks=[
        {'Titel': 'Task 1', 'Beschreibung': 'Description 1'},
        {'Titel': 'Task 2', 'Beschreibung': 'Description 2'}
    ]
)
```

### Creating Tasks from Analysis

```python
# Create actual Task objects
result = service.create_tasks_from_context(
    context_obj,
    milestone,
    user=request.user
)

print(f"Created {result['tasks_created']} tasks")
```

## API Endpoints

### Analyze Context Object

```bash
# Get existing analysis
GET /api/milestones/context/<context_id>/analyze

# Run new analysis
POST /api/milestones/context/<context_id>/analyze
```

### Enhance Summary

```bash
POST /api/milestones/context/<context_id>/enhance-summary
```

**Example:**
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRFToken: <csrf>" \
  https://app.example.com/api/milestones/context/abc123/enhance-summary
```

### Accept Results

```bash
POST /api/milestones/context/<context_id>/accept-results
Content-Type: application/json

{
  "summary": "Edited summary",
  "derived_tasks": [
    {"Titel": "Task", "Beschreibung": "Description"}
  ]
}
```

### Create Tasks

```bash
POST /api/milestones/context/<context_id>/create-tasks
```

## JavaScript Functions

### Load and Display Results

```javascript
// Load context analysis data
loadContextResults(contextId);

// Display in modal
displayResultsInModal({
    id: contextId,
    title: 'Context Title',
    summary: 'Summary text',
    derived_tasks: [...]
});
```

### Enhance Summary

```javascript
// Enhance summary via AI
fetch(`/api/milestones/context/${contextId}/enhance-summary`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    }
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log(data.enhanced_summary);
    }
});
```

### Accept Results

```javascript
// Accept edited results
fetch(`/api/milestones/context/${contextId}/accept-results`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({
        summary: editedSummary,
        derived_tasks: editedTasks
    })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        location.reload();
    }
});
```

## Database Models

### MilestoneContextObject

```python
context_obj = MilestoneContextObject.objects.create(
    milestone=milestone,
    type='file',  # or 'email', 'transcript', 'note'
    title='Document.pdf',
    content='Text content...',
    source_id='sharepoint-guid',
    url='https://...',
    summary='AI summary',
    tags=['tag1', 'tag2'],
    derived_tasks=[
        {'Titel': 'Task', 'Beschreibung': 'Desc'}
    ],
    analyzed=True,
    uploaded_by=user
)
```

### Key Fields

| Field          | Type    | Description                          |
|----------------|---------|--------------------------------------|
| milestone      | FK      | Related milestone                    |
| type           | Char    | file, email, transcript, note        |
| title          | Char    | Display name                         |
| content        | Text    | Full text content                    |
| summary        | Text    | AI-generated summary                 |
| derived_tasks  | JSON    | List of task dictionaries            |
| analyzed       | Boolean | Has been analyzed by AI              |
| uploaded_by    | FK      | User who added the context           |

## KiGate Agents

### text-summary-agent

```python
kigate.execute_agent(
    agent_name='text-summary-agent',
    provider='openai',
    model='gpt-4',
    message=content,
    user_id='system',
    parameters={'max_length': 500}
)
```

**Returns:**
```json
{
  "success": true,
  "result": {
    "summary": "Concise summary text..."
  }
}
```

### text-analysis-task-derivation-agent

```python
kigate.execute_agent(
    agent_name='text-analysis-task-derivation-agent',
    provider='openai',
    model='gpt-4',
    message=f"Milestone: {milestone_name}\n\nContent:\n{content}",
    user_id='system'
)
```

**Returns:**
```json
{
  "success": true,
  "result": {
    "tasks": [
      {
        "Titel": "Task title",
        "Beschreibung": "Task description"
      }
    ]
  }
}
```

### summary-enhancer-agent (NEW)

```python
kigate.execute_agent(
    agent_name='summary-enhancer-agent',
    provider='openai',
    model='gpt-4',
    message=existing_summary,
    user_id='system',
    parameters={'context': f"Milestone: {milestone_name}"}
)
```

**Returns:**
```json
{
  "success": true,
  "result": {
    "enhanced_summary": "Improved and clarified summary..."
  }
}
```

## Error Handling

### Service Layer

```python
from core.services.milestone_knowledge_service import MilestoneKnowledgeServiceError

try:
    result = service.enhance_summary(context_obj)
except MilestoneKnowledgeServiceError as e:
    print(f"Error: {e.message}")
    print(f"Details: {e.details}")
    error_dict = e.to_dict()  # For API responses
```

### API Responses

```python
# Success
{
    "success": true,
    "data": {...}
}

# Error
{
    "success": false,
    "error": "Human-readable error message",
    "details": "Technical details (not shown to users)"
}
```

### JavaScript Error Handling

```javascript
fetch(url, options)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Handle success
        } else {
            showToast(`Error: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        showToast(`Network error: ${error}`, 'error');
    });
```

## Permissions

All endpoints check:
1. User is authenticated
2. User owns the item (milestone.item.created_by) OR
3. User has 'admin' role

```python
# Permission check pattern
if user.role != 'admin' and milestone.item.created_by != user:
    return JsonResponse({
        'success': False,
        'error': 'Permission denied'
    }, status=403)
```

## Common Patterns

### Full Analysis Workflow

```python
# 1. Add context
result = service.add_context_object(
    milestone, 'note', 'Title', 'Content', user=user, auto_analyze=True
)
context_id = result['context_object_id']

# 2. Get context object
context = MilestoneContextObject.objects.get(id=context_id)

# 3. Optionally enhance summary
if context.summary:
    service.enhance_summary(context)
    context.refresh_from_db()

# 4. Accept results
service.accept_analysis_results(context)

# 5. Create tasks
service.create_tasks_from_context(context, milestone, user)
```

### Batch Processing

```python
# Process multiple context objects
for context in milestone.context_objects.filter(analyzed=False):
    try:
        service.analyze_context_object(context)
    except MilestoneKnowledgeServiceError as e:
        logger.error(f"Analysis failed for {context.id}: {e}")
```

### Custom Task Processing

```python
# Filter/modify derived tasks before creation
context = MilestoneContextObject.objects.get(id=context_id)
filtered_tasks = [
    task for task in context.derived_tasks
    if 'urgent' in task.get('Titel', '').lower()
]

# Accept with filtered tasks
service.accept_analysis_results(
    context,
    derived_tasks=filtered_tasks
)
```

## Testing

### Unit Test Example

```python
from unittest.mock import patch, MagicMock

@patch('core.services.milestone_knowledge_service.KiGateService')
def test_enhance_summary(self, mock_kigate):
    # Setup mock
    mock_instance = MagicMock()
    mock_instance.execute_agent.return_value = {
        'success': True,
        'result': {'enhanced_summary': 'Enhanced text'}
    }
    mock_kigate.return_value = mock_instance
    
    # Create context
    context = MilestoneContextObject.objects.create(
        milestone=self.milestone,
        type='note',
        title='Test',
        summary='Original'
    )
    
    # Test
    service = MilestoneKnowledgeService()
    result = service.enhance_summary(context)
    
    # Assert
    self.assertTrue(result['success'])
    context.refresh_from_db()
    self.assertEqual(context.summary, 'Enhanced text')
```

### API Test Example

```python
def test_api_accept_results(self):
    # Login
    session = self.client.session
    session['user_id'] = str(self.user.id)
    session.save()
    
    # Make request
    url = reverse('main:api_milestone_context_accept_results', 
                  kwargs={'context_id': context.id})
    response = self.client.post(
        url,
        data=json.dumps({
            'summary': 'Edited',
            'derived_tasks': [...]
        }),
        content_type='application/json'
    )
    
    # Assert
    self.assertEqual(response.status_code, 200)
    data = json.loads(response.content)
    self.assertTrue(data['success'])
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "Cannot enhance empty summary" | Run analysis first to generate summary |
| "Context object not found" | Verify context_id is valid UUID |
| "Permission denied" | Check user owns item or is admin |
| "AI analysis failed" | Check KiGate API availability and settings |
| Summary not showing source | Ensure accept_analysis_results was called |

### Debug Mode

```python
import logging
logging.getLogger('milestone_knowledge_service').setLevel(logging.DEBUG)
```

### Check Analysis Status

```python
# Check what needs analysis
unanalyzed = milestone.context_objects.filter(analyzed=False)
print(f"{unanalyzed.count()} context objects need analysis")

# Check for derived tasks
with_tasks = milestone.context_objects.exclude(derived_tasks=[])
print(f"{with_tasks.count()} context objects have derived tasks")
```

---

**Last Updated:** 2025-10-23  
**For detailed documentation, see:** [MILESTONE_INTERACTIVE_AI_ANALYSIS.md](MILESTONE_INTERACTIVE_AI_ANALYSIS.md)
