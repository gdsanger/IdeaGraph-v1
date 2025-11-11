"""
Tests for the all new tasks badge context processor.
"""
from django.test import TestCase, RequestFactory
from main.models import Item, Task, User
from main.context_processors import all_new_tasks_badge


class AllNewTasksBadgeContextProcessorTest(TestCase):
    """Test the all new tasks badge context processor"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create test users
        self.user1 = User.objects.create(
            username='testuser1',
            email='test1@example.com'
        )
        self.user2 = User.objects.create(
            username='testuser2',
            email='test2@example.com'
        )
        
        # Create test items
        self.item1 = Item.objects.create(
            title='Item 1',
            description='Test item 1',
            created_by=self.user1
        )
        self.item2 = Item.objects.create(
            title='Item 2',
            description='Test item 2',
            created_by=self.user1
        )
        
    def test_context_processor_with_new_tasks(self):
        """Test that context processor returns correct count with new tasks"""
        # Create new tasks across different items
        Task.objects.create(
            title='Task 1',
            item=self.item1,
            status='new',
            created_by=self.user1
        )
        Task.objects.create(
            title='Task 2',
            item=self.item1,
            status='new',
            created_by=self.user1
        )
        Task.objects.create(
            title='Task 3',
            item=self.item2,
            status='new',
            created_by=self.user2
        )
        
        # Create tasks with different statuses (should not be counted)
        Task.objects.create(
            title='Task 4',
            item=self.item1,
            status='done',
            created_by=self.user1
        )
        Task.objects.create(
            title='Task 5',
            item=self.item2,
            status='working',
            created_by=self.user1
        )
        
        request = self.factory.get('/')
        context = all_new_tasks_badge(request)
        
        self.assertEqual(context['all_new_tasks_count'], 3)
        
    def test_context_processor_without_new_tasks(self):
        """Test that context processor returns zero when no new tasks"""
        # Create only completed/working tasks
        Task.objects.create(
            title='Task 1',
            item=self.item1,
            status='done',
            created_by=self.user1
        )
        Task.objects.create(
            title='Task 2',
            item=self.item2,
            status='working',
            created_by=self.user1
        )
        
        request = self.factory.get('/')
        context = all_new_tasks_badge(request)
        
        self.assertEqual(context['all_new_tasks_count'], 0)
        
    def test_context_processor_without_tasks(self):
        """Test that context processor returns zero when no tasks exist"""
        request = self.factory.get('/')
        context = all_new_tasks_badge(request)
        
        self.assertEqual(context['all_new_tasks_count'], 0)
        
    def test_context_processor_counts_all_items(self):
        """Test that context processor counts new tasks across all items"""
        # Create third item
        item3 = Item.objects.create(
            title='Item 3',
            description='Test item 3',
            created_by=self.user2
        )
        
        # Create new tasks in all items
        Task.objects.create(
            title='Task in Item 1',
            item=self.item1,
            status='new',
            created_by=self.user1
        )
        Task.objects.create(
            title='Task in Item 2',
            item=self.item2,
            status='new',
            created_by=self.user1
        )
        Task.objects.create(
            title='Task in Item 3',
            item=item3,
            status='new',
            created_by=self.user2
        )
        
        request = self.factory.get('/')
        context = all_new_tasks_badge(request)
        
        # Should count tasks from all items
        self.assertEqual(context['all_new_tasks_count'], 3)
        
    def test_context_processor_with_orphaned_tasks(self):
        """Test that context processor counts new tasks without items"""
        # Create new tasks with and without items
        Task.objects.create(
            title='Task with Item',
            item=self.item1,
            status='new',
            created_by=self.user1
        )
        Task.objects.create(
            title='Task without Item',
            item=None,
            status='new',
            created_by=self.user1
        )
        
        request = self.factory.get('/')
        context = all_new_tasks_badge(request)
        
        # Should count both tasks (including orphaned one)
        self.assertEqual(context['all_new_tasks_count'], 2)
