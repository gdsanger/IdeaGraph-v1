"""
Tests for HTMX pagination functionality in item detail view (Tasks tab)
"""
from django.test import TestCase, Client
from main.models import User, Item, Task


class HTMXItemDetailPaginationTest(TestCase):
    """Test HTMX pagination in item detail view Tasks tab"""
    
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
        response = self.client.get(f'/items/{self.item.id}/')
        self.assertEqual(response.status_code, 200)
        
        # Check that full page is returned
        self.assertContains(response, '<html')
        self.assertContains(response, 'Item Details')
        self.assertContains(response, 'item-tasks-table-container')
    
    def test_htmx_request_returns_partial(self):
        """Test that HTMX request returns only the partial template"""
        self.login_user()
        response = self.client.get(
            f'/items/{self.item.id}/',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that only partial is returned (no full HTML structure)
        self.assertNotContains(response, '<html')
        self.assertNotContains(response, 'Item Details')
        
        # But should contain the task table
        self.assertContains(response, 'table-responsive')
    
    def test_htmx_pagination_second_page(self):
        """Test HTMX pagination to second page"""
        self.login_user()
        response = self.client.get(
            f'/items/{self.item.id}/?page=2',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should contain pagination controls
        self.assertContains(response, 'Seite 2 von')
        self.assertContains(response, 'pagination')
    
    def test_htmx_pagination_with_search(self):
        """Test HTMX pagination preserves search query"""
        self.login_user()
        response = self.client.get(
            f'/items/{self.item.id}/?search=Task&page=1',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should contain the search parameter in pagination links
        self.assertContains(response, 'search=Task')
    
    def test_htmx_pagination_with_show_completed(self):
        """Test HTMX pagination preserves show_completed filter"""
        # Create some completed tasks
        for i in range(5):
            Task.objects.create(
                title=f'Completed Task {i}',
                description='This task is done',
                status='done',
                item=self.item,
                created_by=self.user
            )
        
        self.login_user()
        response = self.client.get(
            f'/items/{self.item.id}/?show_completed=true&page=1',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should contain the show_completed parameter in pagination links
        self.assertContains(response, 'show_completed=true')
    
    def test_htmx_attributes_present(self):
        """Test that HTMX attributes are present in pagination links"""
        self.login_user()
        response = self.client.get(
            f'/items/{self.item.id}/',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check for HTMX attributes in pagination links
        self.assertContains(response, 'hx-get=')
        self.assertContains(response, 'hx-target="#item-tasks-table-container"')
        self.assertContains(response, 'hx-swap="innerHTML"')
        self.assertContains(response, 'hx-indicator="#tasks-loading-indicator"')
    
    def test_htmx_request_with_empty_results(self):
        """Test HTMX request with no tasks matching search"""
        self.login_user()
        response = self.client.get(
            f'/items/{self.item.id}/?search=NonexistentTask',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should show empty state message
        self.assertContains(response, 'Keine Tasks gefunden')
    
    def test_pagination_maintains_all_filters(self):
        """Test that pagination maintains all filter parameters"""
        self.login_user()
        response = self.client.get(
            f'/items/{self.item.id}/?show_completed=true&search=Task&page=2',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that all parameters are preserved in pagination links
        content = response.content.decode('utf-8')
        self.assertIn('show_completed=true', content)
        self.assertIn('search=Task', content)
        self.assertIn('page=', content)
    
    def test_htmx_script_reinitializes_tooltips(self):
        """Test that HTMX afterSwap script is present in partial template"""
        self.login_user()
        response = self.client.get(
            f'/items/{self.item.id}/',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should contain script to reinitialize tooltips
        self.assertContains(response, 'htmx:afterSwap')
        self.assertContains(response, 'item-tasks-table-container')
        self.assertContains(response, 'bootstrap.Tooltip')
    
    def test_htmx_request_without_tasks(self):
        """Test HTMX request when item has no tasks"""
        # Create new item without tasks
        empty_item = Item.objects.create(
            title='Empty Item',
            description='Item without tasks',
            status='new',
            created_by=self.user
        )
        
        self.login_user()
        response = self.client.get(
            f'/items/{empty_item.id}/',
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        
        # Should show empty state
        self.assertContains(response, 'No tasks yet')
        self.assertContains(response, 'Build Tasks')
