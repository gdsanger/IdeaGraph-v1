"""
Test Task views and API endpoints
"""
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, Tag, Section
import json


class TaskViewTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create another user
        self.other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='developer',
            is_active=True
        )
        self.other_user.set_password('testpass123')
        self.other_user.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test tag
        self.tag = Tag.objects.create(name='test-tag', color='#3b82f6')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description',
            github_repo='testuser/testrepo',
            status='new',
            section=self.section,
            created_by=self.user
        )
        self.item.tags.add(self.tag)
        
        # Create test tasks
        self.task1 = Task.objects.create(
            title='Test Task 1',
            description='Task 1 description',
            status='new',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        self.task1.tags.add(self.tag)
        
        self.task2 = Task.objects.create(
            title='Test Task 2',
            description='Task 2 description',
            status='ready',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        
        # Create client
        self.client = Client()
    
    def login(self):
        """Helper to log in the test user"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_task_list_view(self):
        """Test task list view"""
        self.login()
        url = reverse('main:task_list', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Task 1')
        self.assertContains(response, 'Test Task 2')
    
    def test_task_detail_view(self):
        """Test task detail view"""
        self.login()
        url = reverse('main:task_detail', args=[self.task1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Task 1')
        self.assertContains(response, 'Task 1 description')
    
    def test_task_create_view(self):
        """Test task creation"""
        self.login()
        url = reverse('main:task_create', args=[self.item.id])
        
        # GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # POST request
        response = self.client.post(url, {
            'title': 'New Test Task',
            'description': 'New task description',
            'status': 'new',
            'tags': [str(self.tag.id)]
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        
        # Verify task was created
        new_task = Task.objects.get(title='New Test Task')
        self.assertEqual(new_task.description, 'New task description')
        self.assertEqual(new_task.status, 'new')
        self.assertEqual(new_task.created_by, self.user)
    
    def test_task_edit_view(self):
        """Test task editing"""
        self.login()
        url = reverse('main:task_edit', args=[self.task1.id])
        
        # GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # POST request
        response = self.client.post(url, {
            'title': 'Updated Task 1',
            'description': 'Updated description',
            'status': 'working',
            'tags': [str(self.tag.id)]
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify task was updated
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.title, 'Updated Task 1')
        self.assertEqual(self.task1.description, 'Updated description')
        self.assertEqual(self.task1.status, 'working')
    
    def test_task_delete_view(self):
        """Test task deletion"""
        self.login()
        url = reverse('main:task_delete', args=[self.task1.id])
        
        # GET request (confirmation page)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Task 1')
        
        # POST request (actual deletion)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        
        # Verify task was deleted
        self.assertFalse(Task.objects.filter(id=self.task1.id).exists())
    
    def test_task_ownership_enforcement(self):
        """Test that users can only access their own tasks"""
        # Login as other user
        session = self.client.session
        session['user_id'] = str(self.other_user.id)
        session.save()
        
        # Try to access task detail
        url = reverse('main:task_detail', args=[self.task1.id])
        response = self.client.get(url)
        
        # Should redirect (access denied)
        self.assertEqual(response.status_code, 302)
    
    def test_task_status_ordering(self):
        """Test that tasks are ordered by status"""
        self.login()
        
        # Create tasks with different statuses
        Task.objects.create(
            title='Review Task',
            status='review',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        Task.objects.create(
            title='Done Task',
            status='done',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        
        url = reverse('main:task_list', args=[self.item.id])
        response = self.client.get(url)
        
        # All tasks should be visible
        self.assertContains(response, 'Test Task 1')
        self.assertContains(response, 'Test Task 2')
        self.assertContains(response, 'Review Task')
        self.assertContains(response, 'Done Task')


class TaskAPITest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description',
            github_repo='testuser/testrepo',
            status='new',
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        
        # Generate auth token
        from main.auth_utils import generate_jwt_token
        self.token = generate_jwt_token(self.user)
        
        self.client = Client()
    
    def test_api_task_list(self):
        """Test API task list endpoint"""
        url = reverse('main:api_tasks', args=[self.item.id])
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['tasks']), 1)
        self.assertEqual(data['tasks'][0]['title'], 'Test Task')
    
    def test_api_task_create(self):
        """Test API task creation endpoint"""
        url = reverse('main:api_tasks', args=[self.item.id])
        response = self.client.post(
            url,
            data=json.dumps({
                'title': 'New API Task',
                'description': 'Created via API',
                'status': 'new'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['task']['title'], 'New API Task')
        
        # Verify task was created
        new_task = Task.objects.get(title='New API Task')
        self.assertEqual(new_task.description, 'Created via API')
    
    def test_api_task_detail(self):
        """Test API task detail endpoint"""
        url = reverse('main:api_task_detail', args=[self.task.id])
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['task']['title'], 'Test Task')
    
    def test_api_task_update(self):
        """Test API task update endpoint"""
        url = reverse('main:api_task_detail', args=[self.task.id])
        response = self.client.put(
            url,
            data=json.dumps({
                'title': 'Updated Task',
                'description': 'Updated description',
                'status': 'working'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify task was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated Task')
        self.assertEqual(self.task.status, 'working')
    
    def test_api_task_delete(self):
        """Test API task delete endpoint"""
        url = reverse('main:api_task_detail', args=[self.task.id])
        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify task was deleted
        self.assertFalse(Task.objects.filter(id=self.task.id).exists())
    
    def test_api_authentication_required(self):
        """Test that API requires authentication"""
        url = reverse('main:api_tasks', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)
