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

    def test_task_edit_marks_done_and_sets_completed_at(self):
        """Status change to done should set completed_at via mark_as_done"""
        self.login()
        url = reverse('main:task_edit', args=[self.task1.id])

        self.task1.status = 'working'
        self.task1.completed_at = None
        self.task1.save()

        response = self.client.post(url, {
            'title': 'Task Done',
            'description': 'Completed description',
            'status': 'done',
            'tags': [str(self.tag.id)]
        })

        self.assertEqual(response.status_code, 302)

        self.task1.refresh_from_db()
        self.assertEqual(self.task1.status, 'done')
        self.assertIsNotNone(self.task1.completed_at)
        self.assertEqual(self.task1.description, 'Completed description')

    def test_task_edit_error_message_display(self):
        """Test that error messages are displayed when task edit fails"""
        self.login()
        url = reverse('main:task_edit', args=[self.task1.id])
        
        # POST request with missing required field (empty title)
        response = self.client.post(url, {
            'title': '',
            'description': 'Some description',
            'status': 'working',
        })
        
        # Should not redirect (stays on form page)
        self.assertEqual(response.status_code, 200)
        
        # Check that error message is in the response
        self.assertContains(response, 'Title is required')
        
        # Verify the messages template code is present
        self.assertContains(response, 'alert alert-')
    
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

    def test_api_task_update_marks_done(self):
        """Status change to done should set completed_at via mark_as_done"""
        url = reverse('main:api_task_detail', args=[self.task.id])

        self.task.status = 'working'
        self.task.completed_at = None
        self.task.save()

        response = self.client.put(
            url,
            data=json.dumps({
                'title': 'API Done Task',
                'description': 'API done description',
                'status': 'done'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )

        self.assertEqual(response.status_code, 200)

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'done')
        self.assertIsNotNone(self.task.completed_at)
        self.assertEqual(self.task.description, 'API done description')

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


class TaskOverviewTest(TestCase):
    """Tests for the task overview functionality"""
    
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
        
        # Create admin user
        self.admin = User.objects.create(
            username='adminuser',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin.set_password('testpass123')
        self.admin.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test tag
        self.tag = Tag.objects.create(name='test-tag', color='#3b82f6')
        
        # Create test items
        self.item1 = Item.objects.create(
            title='Test Item 1',
            description='Test item 1 description',
            github_repo='testuser/testrepo',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        self.item2 = Item.objects.create(
            title='Test Item 2',
            description='Test item 2 description',
            status='working',
            created_by=self.user
        )
        
        # Create test tasks with different statuses
        self.task1 = Task.objects.create(
            title='Task New',
            description='New task',
            status='new',
            item=self.item1,
            created_by=self.user,
            assigned_to=self.user
        )
        
        self.task2 = Task.objects.create(
            title='Task Working',
            description='Working task',
            status='working',
            item=self.item1,
            created_by=self.user,
            assigned_to=self.user,
            github_issue_id=123,
            github_issue_url='https://github.com/test/repo/issues/123'
        )
        
        self.task3 = Task.objects.create(
            title='Task Ready',
            description='Ready task',
            status='ready',
            item=self.item2,
            created_by=self.user,
            assigned_to=self.user
        )
        
        # Generate auth token
        from main.auth_utils import generate_jwt_token
        self.token = generate_jwt_token(self.user)
        self.admin_token = generate_jwt_token(self.admin)
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in the test user"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session['user_role'] = self.user.role
        session.save()
    
    def login_admin(self):
        """Helper to log in the admin user"""
        session = self.client.session
        session['user_id'] = str(self.admin.id)
        session['username'] = self.admin.username
        session['user_role'] = self.admin.role
        session.save()
    
    def test_task_overview_view(self):
        """Test task overview view"""
        self.login_user()
        url = reverse('main:task_overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Task Overview')
        self.assertContains(response, 'Task New')
        self.assertContains(response, 'Task Working')
        self.assertContains(response, 'Task Ready')
    
    def test_task_overview_status_filter(self):
        """Test filtering by status"""
        self.login_user()
        url = reverse('main:task_overview')
        response = self.client.get(url, {'status': 'working'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Task Working')
        self.assertNotContains(response, 'Task New')
        self.assertNotContains(response, 'Task Ready')
    
    def test_task_overview_item_filter(self):
        """Test filtering by item"""
        self.login_user()
        url = reverse('main:task_overview')
        response = self.client.get(url, {'item': str(self.item1.id)})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Task New')
        self.assertContains(response, 'Task Working')
        self.assertNotContains(response, 'Task Ready')
    
    def test_task_overview_github_filter(self):
        """Test filtering by GitHub issue presence"""
        self.login_user()
        url = reverse('main:task_overview')
        
        # Filter for tasks with GitHub issues
        response = self.client.get(url, {'has_github': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Task Working')
        self.assertNotContains(response, 'Task New')
        
        # Filter for tasks without GitHub issues
        response = self.client.get(url, {'has_github': 'false'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Task New')
        self.assertNotContains(response, 'Task Working')
    
    def test_task_overview_search(self):
        """Test search functionality"""
        self.login_user()
        url = reverse('main:task_overview')
        response = self.client.get(url, {'search': 'Working'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Task Working')
        self.assertNotContains(response, 'Task New')
    
    def test_task_overview_status_counts(self):
        """Test status counts are displayed"""
        self.login_user()
        url = reverse('main:task_overview')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that status counts are in context
        self.assertIn('status_counts', response.context)
        self.assertEqual(response.context['status_counts']['new'], 1)
        self.assertEqual(response.context['status_counts']['working'], 1)
        self.assertEqual(response.context['status_counts']['ready'], 1)
    
    def test_task_overview_requires_login(self):
        """Test that task overview requires login"""
        url = reverse('main:task_overview')
        response = self.client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_api_task_overview(self):
        """Test API task overview endpoint"""
        url = reverse('main:api_task_overview')
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['tasks']), 3)
        self.assertIn('status_counts', data)
        self.assertIn('pagination', data)
    
    def test_api_task_overview_filters(self):
        """Test API task overview with filters"""
        url = reverse('main:api_task_overview')
        
        # Filter by status
        response = self.client.get(
            url + '?status=working',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['tasks']), 1)
        self.assertEqual(data['tasks'][0]['title'], 'Task Working')
        
        # Filter by item
        response = self.client.get(
            url + f'?item={self.item1.id}',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['tasks']), 2)
        
        # Filter by GitHub issue
        response = self.client.get(
            url + '?has_github=true',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['tasks']), 1)
        self.assertEqual(data['tasks'][0]['github_issue_id'], 123)
    
    def test_api_task_overview_pagination(self):
        """Test API task overview pagination"""
        # Create more tasks to test pagination
        for i in range(25):
            Task.objects.create(
                title=f'Task {i}',
                description=f'Description {i}',
                status='new',
                item=self.item1,
                created_by=self.user,
                assigned_to=self.user
            )
        
        url = reverse('main:api_task_overview')
        response = self.client.get(
            url + '?limit=10&page=1',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['tasks']), 10)
        self.assertEqual(data['pagination']['page'], 1)
        self.assertTrue(data['pagination']['has_next'])
        self.assertFalse(data['pagination']['has_previous'])
