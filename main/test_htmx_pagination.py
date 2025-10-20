"""
Tests for HTMX pagination functionality in task overview
"""
from django.test import TestCase, Client
from main.models import User, Item, Task


class HTMXPaginationTest(TestCase):
    """Test HTMX pagination in task overview"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            created_by=self.user
        )
        
        # Create 25 tasks for pagination testing
        for i in range(25):
            Task.objects.create(
                title=f'Task {i+1}',
                description=f'Description for task {i+1}',
                status='new',
                item=self.item,
                created_by=self.user
            )
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in the test user"""
        self.client.post('/login/', {
            'username': self.user.username,
            'password': 'Test@123'
        })
    
    def test_regular_request_returns_full_page(self):
        """Test that regular request returns full HTML page"""
        self.login_user()
        response = self.client.get('/admin/tasks/overview/')
        self.assertEqual(response.status_code, 200)
        
        # Check that full page is returned
        self.assertContains(response, '<html')
        self.assertContains(response, 'Task Overview')
        self.assertContains(response, 'task-table-container')
    
    def test_htmx_request_returns_partial(self):
        """Test that HTMX request returns only the partial template"""
        self.login_user()
        response = self.client.get(
            '/admin/tasks/overview/',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that only partial is returned (no full HTML structure)
        self.assertNotContains(response, '<html')
        self.assertNotContains(response, 'Task Overview')
        
        # But should contain the task table
        self.assertContains(response, 'table-responsive')
    
    def test_htmx_pagination_second_page(self):
        """Test HTMX pagination to second page"""
        self.login_user()
        response = self.client.get(
            '/admin/tasks/overview/?page=2',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should contain pagination controls
        self.assertContains(response, 'Page 2 of')
        self.assertContains(response, 'pagination')
    
    def test_htmx_pagination_with_filters(self):
        """Test HTMX pagination preserves filters"""
        # Create multiple tasks with 'done' status to ensure pagination
        for i in range(25):
            Task.objects.create(
                title=f'Completed Task {i}',
                description='This task is done',
                status='done',
                item=self.item,
                created_by=self.user
            )
        
        self.login_user()
        response = self.client.get(
            '/admin/tasks/overview/?status=done&page=1',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should contain the filter parameters in pagination links
        self.assertContains(response, 'status=done')
    
    def test_htmx_pagination_with_search(self):
        """Test HTMX pagination preserves search query"""
        self.login_user()
        response = self.client.get(
            '/admin/tasks/overview/?search=Task&page=1',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should contain the search parameter in pagination links
        self.assertContains(response, 'search=Task')
    
    def test_htmx_attributes_present(self):
        """Test that HTMX attributes are present in pagination links"""
        self.login_user()
        response = self.client.get(
            '/admin/tasks/overview/',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check for HTMX attributes in pagination links
        self.assertContains(response, 'hx-get=')
        self.assertContains(response, 'hx-target="#task-table-container"')
        self.assertContains(response, 'hx-swap="innerHTML"')
        self.assertContains(response, 'hx-indicator="#loading-indicator"')
    
    def test_htmx_request_with_empty_results(self):
        """Test HTMX request with no tasks"""
        self.login_user()
        response = self.client.get(
            '/admin/tasks/overview/?search=NonexistentTask',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should show empty state message
        self.assertContains(response, 'No tasks found')
    
    def test_pagination_maintains_all_filters(self):
        """Test that pagination maintains all filter parameters"""
        self.login_user()
        response = self.client.get(
            '/admin/tasks/overview/?status=new&item=' + str(self.item.id) + '&has_github=false&search=Task&page=2',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that all parameters are preserved in pagination links
        content = response.content.decode('utf-8')
        self.assertIn('status=new', content)
        self.assertIn('item=' + str(self.item.id), content)
        self.assertIn('has_github=false', content)
        self.assertIn('search=Task', content)
