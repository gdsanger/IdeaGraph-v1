"""
Tests for Actions API Tasks endpoints
"""
import json
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from main.models import User, ApiKey, Item, Task, Tag, Milestone
from datetime import date


@override_settings(
    ACTIONS_API_ENABLED=True,
    ACTIONS_API_KEY_HEADER='X-IG-API-Key'
)
class TasksAPITest(TestCase):
    """Test Tasks API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            is_active=True
        )
        
        # Create API key
        self.api_key = ApiKey.generate_key(
            user=self.user,
            name='Test API Key'
        )
        
        # Create item
        self.item = Item.objects.create(
            title='Test Item',
            created_by=self.user
        )
        
        # Create milestone
        self.milestone = Milestone.objects.create(
            name='Test Milestone',
            item=self.item,
            due_date=date.today()
        )
        
        # Create tags
        self.tag1 = Tag.objects.create(name='bug')
        self.tag2 = Tag.objects.create(name='urgent')
        
        # Create test tasks
        self.task1 = Task.objects.create(
            title='Test Task 1',
            description='Description 1',
            status='new',
            type='bug',
            item=self.item,
            created_by=self.user
        )
        self.task1.tags.add(self.tag1)
        
        self.task2 = Task.objects.create(
            title='Test Task 2',
            description='Description 2',
            status='working',
            type='feature',
            item=self.item,
            milestone=self.milestone,
            created_by=self.user
        )
        self.task2.tags.add(self.tag1, self.tag2)
    
    def _set_api_key(self):
        """Set API key header for requests"""
        self.client.credentials(HTTP_X_IG_API_KEY=self.api_key.key)
    
    def test_list_tasks_requires_auth(self):
        """Test that listing tasks requires authentication"""
        response = self.client.get('/api/ideagraph/tasks/')
        
        self.assertEqual(response.status_code, 403)
    
    def test_list_tasks_success(self):
        """Test listing tasks with valid API key"""
        self._set_api_key()
        
        response = self.client.get('/api/ideagraph/tasks/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('tasks', data)
        self.assertEqual(data['count'], 2)
    
    def test_list_tasks_filter_by_item(self):
        """Test filtering tasks by item ID"""
        self._set_api_key()
        
        response = self.client.get(f'/api/ideagraph/tasks/?itemId={self.item.id}')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['tasks']), 2)
    
    def test_list_tasks_filter_by_status(self):
        """Test filtering tasks by status"""
        self._set_api_key()
        
        response = self.client.get('/api/ideagraph/tasks/?status=new')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['tasks']), 1)
        self.assertEqual(data['tasks'][0]['status'], 'new')
    
    def test_list_tasks_with_query(self):
        """Test searching tasks with query"""
        self._set_api_key()
        
        response = self.client.get('/api/ideagraph/tasks/?query=Task 1')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['tasks']), 1)
        self.assertEqual(data['tasks'][0]['title'], 'Test Task 1')
    
    def test_get_task_detail(self):
        """Test getting task detail"""
        self._set_api_key()
        
        response = self.client.get(f'/api/ideagraph/tasks/{self.task1.id}/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('task', data)
        
        task = data['task']
        self.assertEqual(task['title'], 'Test Task 1')
        self.assertEqual(task['status'], 'new')
        self.assertEqual(task['type'], 'bug')
        self.assertIn('tags', task)
    
    def test_create_task_success(self):
        """Test creating a new task"""
        self._set_api_key()
        
        task_data = {
            'title': 'New Task',
            'description': 'New task description',
            'status': 'new',
            'type': 'feature',
            'item_id': str(self.item.id)
        }
        
        response = self.client.post(
            '/api/ideagraph/tasks/',
            data=json.dumps(task_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('task', data)
        
        task = data['task']
        self.assertEqual(task['title'], 'New Task')
        self.assertEqual(task['status'], 'new')
        self.assertEqual(task['type'], 'feature')
        
        # Verify task was created in database
        self.assertTrue(Task.objects.filter(title='New Task').exists())
    
    def test_create_task_with_tags(self):
        """Test creating task with tags"""
        self._set_api_key()
        
        task_data = {
            'title': 'Task with Tags',
            'description': 'Description',
            'status': 'new',
            'type': 'bug',
            'tag_ids': [str(self.tag1.id), str(self.tag2.id)]
        }
        
        response = self.client.post(
            '/api/ideagraph/tasks/',
            data=json.dumps(task_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        task = data['task']
        self.assertEqual(len(task['tags']), 2)
    
    def test_create_task_sets_created_by(self):
        """Test that created_by is set to authenticated user"""
        self._set_api_key()
        
        task_data = {
            'title': 'User Task',
            'description': 'Description',
            'status': 'new',
            'type': 'feature'
        }
        
        response = self.client.post(
            '/api/ideagraph/tasks/',
            data=json.dumps(task_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        
        # Get task from database
        task = Task.objects.get(id=data['task']['id'])
        self.assertEqual(task.created_by, self.user)
    
    def test_create_task_validation_error(self):
        """Test creating task with invalid data"""
        self._set_api_key()
        
        task_data = {
            'description': 'Missing title'
        }
        
        response = self.client.post(
            '/api/ideagraph/tasks/',
            data=json.dumps(task_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_update_task_success(self):
        """Test updating a task"""
        self._set_api_key()
        
        update_data = {
            'title': 'Updated Title',
            'status': 'done'
        }
        
        response = self.client.patch(
            f'/api/ideagraph/tasks/{self.task1.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        task = data['task']
        self.assertEqual(task['title'], 'Updated Title')
        self.assertEqual(task['status'], 'done')
        
        # Verify in database
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.title, 'Updated Title')
        self.assertEqual(self.task1.status, 'done')
    
    def test_update_task_tags(self):
        """Test updating task tags"""
        self._set_api_key()
        
        update_data = {
            'tag_ids': [str(self.tag2.id)]
        }
        
        response = self.client.patch(
            f'/api/ideagraph/tasks/{self.task1.id}/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        task = data['task']
        self.assertEqual(len(task['tags']), 1)
        self.assertEqual(task['tags'][0]['name'], 'urgent')
    
    def test_task_includes_milestone(self):
        """Test that task includes milestone information"""
        self._set_api_key()
        
        response = self.client.get(f'/api/ideagraph/tasks/{self.task2.id}/')
        
        data = response.json()
        task = data['task']
        self.assertEqual(task['milestone_id'], str(self.milestone.id))


@override_settings(
    ACTIONS_API_ENABLED=True,
    ACTIONS_API_KEY_HEADER='X-IG-API-Key',
    REST_FRAMEWORK={
        'DEFAULT_THROTTLE_RATES': {
            'actions_api': '2/minute',
            'actions_api_burst': '1/minute',
        }
    }
)
class TasksAPIRateLimitTest(TestCase):
    """Test rate limiting for Tasks API"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        
        self.api_key = ApiKey.generate_key(
            user=self.user,
            name='Test Key'
        )
        
        self.client.credentials(HTTP_X_IG_API_KEY=self.api_key.key)
    
    def test_rate_limit_exceeded(self):
        """Test that rate limiting works"""
        # Make multiple requests
        for i in range(3):
            response = self.client.get('/api/ideagraph/tasks/')
        
        # Should get 429 Too Many Requests
        self.assertEqual(response.status_code, 429)
