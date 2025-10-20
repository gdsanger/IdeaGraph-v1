"""
Tests for home page view with dynamic data
"""
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, Section, Tag


class HomeViewTest(TestCase):
    """Test cases for the home page view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test items
        self.item1 = Item.objects.create(
            title='Test Item 1',
            description='Test description 1',
            created_by=self.user
        )
        self.item2 = Item.objects.create(
            title='Test Item 2',
            description='Test description 2',
            created_by=self.user
        )
        
        # Create test tasks
        self.task1 = Task.objects.create(
            title='Test Task 1',
            description='Task description 1',
            status='new',
            created_by=self.user,
            item=self.item1
        )
        self.task2 = Task.objects.create(
            title='Test Task 2',
            description='Task description 2',
            status='done',
            created_by=self.user,
            item=self.item1
        )
        self.task3 = Task.objects.create(
            title='Test Task 3',
            description='Task description 3',
            status='working',
            github_issue_id=123,
            github_issue_url='https://github.com/test/repo/issues/123',
            created_by=self.user,
            item=self.item2
        )

    def login_user(self):
        """Helper to log in the test user"""
        self.client.post('/login/', {
            'username': self.user.username,
            'password': 'testpass123'
        })

    def test_home_view_status_code(self):
        """Test that home page returns 200 status code"""
        self.login_user()
        response = self.client.get(reverse('main:home'))
        self.assertEqual(response.status_code, 200)

    def test_home_view_uses_correct_template(self):
        """Test that home page uses the correct template"""
        self.login_user()
        response = self.client.get(reverse('main:home'))
        self.assertTemplateUsed(response, 'main/home.html')

    def test_home_view_context_contains_statistics(self):
        """Test that home page context contains all required statistics"""
        self.login_user()
        response = self.client.get(reverse('main:home'))
        
        # Check that all statistics are in context
        self.assertIn('total_items', response.context)
        self.assertIn('total_tasks', response.context)
        self.assertIn('github_issues', response.context)
        self.assertIn('completed_tasks', response.context)

    def test_home_view_total_items_count(self):
        """Test that total_items shows correct count"""
        self.login_user()
        response = self.client.get(reverse('main:home'))
        self.assertEqual(response.context['total_items'], 2)

    def test_home_view_total_tasks_count(self):
        """Test that total_tasks shows correct count"""
        self.login_user()
        response = self.client.get(reverse('main:home'))
        self.assertEqual(response.context['total_tasks'], 3)

    def test_home_view_github_issues_count(self):
        """Test that github_issues shows correct count"""
        self.login_user()
        response = self.client.get(reverse('main:home'))
        self.assertEqual(response.context['github_issues'], 1)

    def test_home_view_completed_tasks_count(self):
        """Test that completed_tasks shows correct count"""
        self.login_user()
        response = self.client.get(reverse('main:home'))
        self.assertEqual(response.context['completed_tasks'], 1)

    def test_home_view_with_no_data(self):
        """Test home page with no items or tasks"""
        # Delete all test data
        Item.objects.all().delete()
        Task.objects.all().delete()
        
        self.login_user()
        response = self.client.get(reverse('main:home'))
        
        # All counts should be 0
        self.assertEqual(response.context['total_items'], 0)
        self.assertEqual(response.context['total_tasks'], 0)
        self.assertEqual(response.context['github_issues'], 0)
        self.assertEqual(response.context['completed_tasks'], 0)

    def test_home_view_renders_statistics_in_html(self):
        """Test that statistics are rendered in the HTML"""
        self.login_user()
        response = self.client.get(reverse('main:home'))
        
        # Check that counts are present in the HTML
        self.assertContains(response, 'Ideas Created')
        self.assertContains(response, 'Tasks Generated')
        self.assertContains(response, 'Issues Created')
        self.assertContains(response, 'Completed')

    def test_home_view_with_multiple_completed_tasks(self):
        """Test completed count with multiple completed tasks"""
        # Create more completed tasks
        Task.objects.create(
            title='Completed Task 2',
            description='Another completed task',
            status='done',
            created_by=self.user
        )
        Task.objects.create(
            title='Completed Task 3',
            description='Yet another completed task',
            status='done',
            created_by=self.user
        )
        
        self.login_user()
        response = self.client.get(reverse('main:home'))
        self.assertEqual(response.context['completed_tasks'], 3)

    def test_home_view_with_multiple_github_issues(self):
        """Test github issues count with multiple synced tasks"""
        # Create more tasks with GitHub issues
        Task.objects.create(
            title='GitHub Task 2',
            description='Task synced to GitHub',
            github_issue_id=456,
            github_issue_url='https://github.com/test/repo/issues/456',
            created_by=self.user
        )
        
        self.login_user()
        response = self.client.get(reverse('main:home'))
        self.assertEqual(response.context['github_issues'], 2)
