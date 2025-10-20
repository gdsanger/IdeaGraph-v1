"""
Tests for Task pagination and search functionality in Item detail view
"""
from django.test import TestCase, Client
from main.models import User, Item, Task, Section


class TaskPaginationSearchTest(TestCase):
    """Test Task pagination and search in item detail view"""
    
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
        
        # Create multiple tasks for pagination testing
        for i in range(25):
            Task.objects.create(
                title=f'Task {i+1}',
                description=f'Description for task {i+1}',
                status='new' if i < 20 else 'done',
                item=self.item,
                created_by=self.user
            )
        
        # Create tasks with specific titles for search testing
        Task.objects.create(
            title='Python Implementation',
            description='Implement feature in Python',
            status='new',
            item=self.item,
            created_by=self.user
        )
        
        Task.objects.create(
            title='Bootstrap UI Update',
            description='Update UI using Bootstrap components',
            status='new',
            item=self.item,
            created_by=self.user
        )
        
        Task.objects.create(
            title='Database Migration',
            description='Create migration for new Python models',
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
    
    def test_item_detail_displays_paginated_tasks(self):
        """Test that item detail view shows paginated tasks"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/')
        self.assertEqual(response.status_code, 200)
        
        # Check that pagination is working (should show 10 tasks per page by default)
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 10)
        
        # Check that paginator has correct total count (excluding 5 done tasks)
        # 25 original + 3 new = 28 total, 5 are done, so 23 non-done
        self.assertEqual(tasks.paginator.count, 23)
    
    def test_pagination_page_2(self):
        """Test that page 2 of pagination works"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?page=2')
        self.assertEqual(response.status_code, 200)
        
        tasks = response.context['tasks']
        self.assertEqual(len(tasks), 10)
        self.assertEqual(tasks.number, 2)
    
    def test_pagination_last_page(self):
        """Test that last page shows remaining tasks"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?page=3')
        self.assertEqual(response.status_code, 200)
        
        tasks = response.context['tasks']
        self.assertEqual(tasks.number, 3)
        # 23 total non-done tasks, page 1 and 2 have 10 each, so page 3 has 3
        self.assertEqual(len(tasks), 3)
    
    def test_search_by_title(self):
        """Test that search works for task titles"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?search=Python')
        self.assertEqual(response.status_code, 200)
        
        tasks = response.context['tasks']
        # Should find "Python Implementation" and "Database Migration" (has Python in description)
        self.assertGreaterEqual(tasks.paginator.count, 1)
        
        # Check that the search query is in context
        self.assertEqual(response.context['search_query'], 'Python')
    
    def test_search_by_description(self):
        """Test that search works for task descriptions"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?search=Bootstrap')
        self.assertEqual(response.status_code, 200)
        
        tasks = response.context['tasks']
        # Should find "Bootstrap UI Update"
        self.assertGreaterEqual(tasks.paginator.count, 1)
    
    def test_search_case_insensitive(self):
        """Test that search is case insensitive"""
        self.login_user()
        response1 = self.client.get(f'/items/{self.item.id}/?search=python')
        response2 = self.client.get(f'/items/{self.item.id}/?search=PYTHON')
        
        tasks1 = response1.context['tasks']
        tasks2 = response2.context['tasks']
        
        # Both searches should return the same count
        self.assertEqual(tasks1.paginator.count, tasks2.paginator.count)
    
    def test_search_no_results(self):
        """Test search with no matching results"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?search=NonexistentTask')
        self.assertEqual(response.status_code, 200)
        
        tasks = response.context['tasks']
        self.assertEqual(tasks.paginator.count, 0)
        self.assertContains(response, 'Keine Tasks gefunden')
    
    def test_show_completed_with_search(self):
        """Test that show_completed works with search"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?search=Task&show_completed=true')
        self.assertEqual(response.status_code, 200)
        
        tasks = response.context['tasks']
        # Should include completed tasks when show_completed=true
        # We have 25 tasks with "Task" in title (Task 1-25)
        self.assertEqual(tasks.paginator.count, 25)
    
    def test_pagination_with_search(self):
        """Test that pagination works with search"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?search=Task&page=2')
        self.assertEqual(response.status_code, 200)
        
        tasks = response.context['tasks']
        self.assertEqual(tasks.number, 2)
    
    def test_search_preserves_show_completed(self):
        """Test that search form preserves show_completed parameter"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?show_completed=true')
        self.assertEqual(response.status_code, 200)
        
        # Check that the hidden input for show_completed exists
        self.assertContains(response, 'name="show_completed" value="true"')
    
    def test_invalid_page_number(self):
        """Test that invalid page number defaults to last page"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?page=999')
        self.assertEqual(response.status_code, 200)
        
        tasks = response.context['tasks']
        # Django's Paginator.get_page() returns the last page for out-of-range values
        self.assertEqual(tasks.number, tasks.paginator.num_pages)
    
    def test_empty_search_query(self):
        """Test that empty search query shows all tasks"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?search=')
        self.assertEqual(response.status_code, 200)
        
        tasks = response.context['tasks']
        # Should show all non-completed tasks (23 total)
        self.assertEqual(tasks.paginator.count, 23)
    
    def test_search_query_in_context(self):
        """Test that search query is passed to template context"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/?search=TestQuery')
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context['search_query'], 'TestQuery')
        # Check that search input has the value
        self.assertContains(response, 'value="TestQuery"')
