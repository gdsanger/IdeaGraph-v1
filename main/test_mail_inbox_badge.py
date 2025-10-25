"""
Tests for the mail inbox badge context processor.
"""
from django.test import TestCase, RequestFactory
from main.models import Item, Task, User, Section
from main.context_processors import mail_inbox_badge


class MailInboxBadgeContextProcessorTest(TestCase):
    """Test the mail inbox badge context processor"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        
        # Create the Mail-Eingang item
        self.mail_inbox = Item.objects.create(
            title='Mail-Eingang',
            description='Test mail inbox',
            created_by=self.user
        )
        
    def test_context_processor_with_new_tasks(self):
        """Test that context processor returns correct count with new tasks"""
        # Create some new tasks
        Task.objects.create(
            title='Task 1',
            item=self.mail_inbox,
            status='new',
            created_by=self.user
        )
        Task.objects.create(
            title='Task 2',
            item=self.mail_inbox,
            status='new',
            created_by=self.user
        )
        
        # Create a task with different status (should not be counted)
        Task.objects.create(
            title='Task 3',
            item=self.mail_inbox,
            status='done',
            created_by=self.user
        )
        
        request = self.factory.get('/')
        context = mail_inbox_badge(request)
        
        self.assertEqual(context['mail_inbox_new_tasks'], 2)
        self.assertEqual(context['mail_inbox_id'], self.mail_inbox.id)
        
    def test_context_processor_without_new_tasks(self):
        """Test that context processor returns zero when no new tasks"""
        # Create only completed tasks
        Task.objects.create(
            title='Task 1',
            item=self.mail_inbox,
            status='done',
            created_by=self.user
        )
        
        request = self.factory.get('/')
        context = mail_inbox_badge(request)
        
        self.assertEqual(context['mail_inbox_new_tasks'], 0)
        self.assertEqual(context['mail_inbox_id'], self.mail_inbox.id)
        
    def test_context_processor_without_mail_inbox_item(self):
        """Test that context processor handles missing Mail-Eingang item"""
        # Delete the Mail-Eingang item
        self.mail_inbox.delete()
        
        request = self.factory.get('/')
        context = mail_inbox_badge(request)
        
        self.assertEqual(context['mail_inbox_new_tasks'], 0)
        self.assertIsNone(context['mail_inbox_id'])
        
    def test_context_processor_with_other_item_tasks(self):
        """Test that context processor only counts tasks from Mail-Eingang"""
        # Create another item
        other_item = Item.objects.create(
            title='Other Item',
            description='Another item',
            created_by=self.user
        )
        
        # Create new tasks in Mail-Eingang
        Task.objects.create(
            title='Mail Task',
            item=self.mail_inbox,
            status='new',
            created_by=self.user
        )
        
        # Create new tasks in other item (should not be counted)
        Task.objects.create(
            title='Other Task',
            item=other_item,
            status='new',
            created_by=self.user
        )
        
        request = self.factory.get('/')
        context = mail_inbox_badge(request)
        
        self.assertEqual(context['mail_inbox_new_tasks'], 1)
        self.assertEqual(context['mail_inbox_id'], self.mail_inbox.id)
