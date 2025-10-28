"""
Tests for Email Conversation Recognition and Task Assignment Feature
"""
import uuid
from django.test import TestCase
from main.models import User, Item, Task, TaskComment, Settings
from core.services.email_conversation_service import EmailConversationService


class EmailConversationTestCase(TestCase):
    """Test cases for Email Conversation functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with Graph API enabled for testing
        self.settings = Settings.objects.create(
            openai_api_enabled=False,
            kigate_api_enabled=False,
            graph_api_enabled=True,  # Enable Graph API for tests
            default_mail_sender='test@example.com',
            client_id='test-client-id',
            client_secret='test-client-secret',
            tenant_id='test-tenant-id'
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            item=self.item,
            created_by=self.user,
            status='new'
        )
    
    def test_task_short_id_generation(self):
        """Test that Task generates a 6-character Short-ID from UUID"""
        short_id = self.task.short_id
        
        # Should be 6 characters
        self.assertEqual(len(short_id), 6)
        
        # Should be uppercase hexadecimal
        self.assertTrue(all(c in '0123456789ABCDEF' for c in short_id))
        
        # Should be first 6 characters of UUID hex
        expected = self.task.id.hex[:6].upper()
        self.assertEqual(short_id, expected)
    
    def test_format_subject_with_short_id(self):
        """Test formatting email subject with Short-ID"""
        service = EmailConversationService(self.settings)
        
        original_subject = "Test Email Subject"
        formatted = service.format_subject_with_short_id(self.task, original_subject)
        
        # Should contain original subject
        self.assertIn(original_subject, formatted)
        
        # Should contain Short-ID in correct format
        short_id = self.task.short_id
        self.assertIn(f'[IG-TASK:#{short_id}]', formatted)
    
    def test_extract_short_id_from_subject(self):
        """Test extracting Short-ID from email subject"""
        service = EmailConversationService(self.settings)
        
        # Test with Short-ID present
        subject = "Re: Bug Report [IG-TASK:#ABC123]"
        extracted = service.extract_short_id_from_subject(subject)
        self.assertEqual(extracted, 'ABC123')
        
        # Test with lowercase Short-ID
        subject = "Re: Feature Request [ig-task:#def456]"
        extracted = service.extract_short_id_from_subject(subject)
        self.assertEqual(extracted, 'DEF456')
        
        # Test without Short-ID
        subject = "Some random email"
        extracted = service.extract_short_id_from_subject(subject)
        self.assertIsNone(extracted)
    
    def test_find_task_by_short_id(self):
        """Test finding task by Short-ID"""
        service = EmailConversationService(self.settings)
        
        short_id = self.task.short_id
        
        # Should find the task
        found_task = service.find_task_by_short_id(short_id)
        self.assertIsNotNone(found_task)
        self.assertEqual(found_task.id, self.task.id)
        
        # Test with lowercase
        found_task = service.find_task_by_short_id(short_id.lower())
        self.assertIsNotNone(found_task)
        self.assertEqual(found_task.id, self.task.id)
        
        # Test with non-existent Short-ID
        found_task = service.find_task_by_short_id('ZZZZZZ')
        self.assertIsNone(found_task)
    
    def test_generate_message_id(self):
        """Test Message-ID generation"""
        service = EmailConversationService(self.settings)
        
        message_id = service.generate_message_id(self.task)
        
        # Should be in correct format: <uuid@domain>
        self.assertTrue(message_id.startswith('<'))
        self.assertTrue(message_id.endswith('>'))
        self.assertIn('@', message_id)
        
        # Should contain domain
        self.assertIn('ideagraph.local', message_id)
    
    def test_task_comment_email_fields(self):
        """Test TaskComment email-specific fields"""
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Test email comment',
            source='email',
            email_message_id='<test@example.com>',
            email_in_reply_to='<previous@example.com>',
            email_references='<ref1@example.com> <ref2@example.com>',
            email_from='sender@example.com',
            email_subject='Test Subject [IG-TASK:#ABC123]'
        )
        
        # Verify all fields are saved correctly
        saved_comment = TaskComment.objects.get(id=comment.id)
        self.assertEqual(saved_comment.source, 'email')
        self.assertEqual(saved_comment.email_message_id, '<test@example.com>')
        self.assertEqual(saved_comment.email_in_reply_to, '<previous@example.com>')
        self.assertEqual(saved_comment.email_references, '<ref1@example.com> <ref2@example.com>')
        self.assertEqual(saved_comment.email_from, 'sender@example.com')
        self.assertEqual(saved_comment.email_subject, 'Test Subject [IG-TASK:#ABC123]')
    
    def test_process_incoming_email_structure(self):
        """Test processing incoming email structure (without actual Graph API call)"""
        service = EmailConversationService(self.settings)
        
        # Create a mock incoming email message
        message = {
            'id': 'test-message-id',
            'subject': f'Re: Test Task [IG-TASK:#{self.task.short_id}]',
            'body': {
                'content': '<p>This is a test reply</p>'
            },
            'from': {
                'emailAddress': {
                    'address': 'sender@example.com',
                    'name': 'Test Sender'
                }
            },
            'internetMessageHeaders': [
                {'name': 'Message-ID', 'value': '<incoming@example.com>'},
                {'name': 'In-Reply-To', 'value': '<original@example.com>'},
                {'name': 'References', 'value': '<ref1@example.com> <original@example.com>'}
            ]
        }
        
        # Process the email (this will work because it doesn't call Graph API)
        result = service.process_incoming_email(message)
        
        # Should succeed
        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('task_id'), str(self.task.id))
        self.assertEqual(result.get('short_id'), self.task.short_id)
        
        # Should create a comment
        comments = self.task.comments.filter(source='email')
        self.assertEqual(comments.count(), 1)
        
        comment = comments.first()
        self.assertEqual(comment.email_from, 'sender@example.com')
        self.assertEqual(comment.email_message_id, '<incoming@example.com>')
        self.assertEqual(comment.email_in_reply_to, '<original@example.com>')
    
    def test_process_incoming_email_without_short_id(self):
        """Test processing email without Short-ID"""
        service = EmailConversationService(self.settings)
        
        message = {
            'id': 'test-message-id',
            'subject': 'Random email without Short-ID',
            'body': {'content': '<p>Random content</p>'},
            'from': {
                'emailAddress': {
                    'address': 'sender@example.com',
                    'name': 'Test Sender'
                }
            },
            'internetMessageHeaders': []
        }
        
        result = service.process_incoming_email(message)
        
        # Should fail
        self.assertFalse(result.get('success'))
        self.assertIn('No Short-ID found', result.get('message'))
        
        # Should not create a comment
        comments = self.task.comments.filter(source='email')
        self.assertEqual(comments.count(), 0)
    
    def test_process_incoming_email_with_invalid_short_id(self):
        """Test processing email with invalid Short-ID"""
        service = EmailConversationService(self.settings)
        
        # Use a valid hexadecimal Short-ID that doesn't match any task
        message = {
            'id': 'test-message-id',
            'subject': 'Email with invalid Short-ID [IG-TASK:#FFFFFF]',
            'body': {'content': '<p>Test content</p>'},
            'from': {
                'emailAddress': {
                    'address': 'sender@example.com',
                    'name': 'Test Sender'
                }
            },
            'internetMessageHeaders': []
        }
        
        result = service.process_incoming_email(message)
        
        # Should fail
        self.assertFalse(result.get('success'))
        self.assertIn('Task not found', result.get('message'))
        
        # Should not create a comment
        comments = self.task.comments.filter(source='email')
        self.assertEqual(comments.count(), 0)
    
    def test_multiple_tasks_different_short_ids(self):
        """Test that different tasks have different Short-IDs"""
        task2 = Task.objects.create(
            title='Another Task',
            description='Another description',
            item=self.item,
            created_by=self.user,
            status='new'
        )
        
        short_id1 = self.task.short_id
        short_id2 = task2.short_id
        
        # Should be different
        self.assertNotEqual(short_id1, short_id2)
        
        # Both should be valid
        self.assertEqual(len(short_id1), 6)
        self.assertEqual(len(short_id2), 6)
    
    def test_subject_replacement_when_short_id_exists(self):
        """Test that existing Short-ID in subject is replaced"""
        service = EmailConversationService(self.settings)
        
        # Subject already has a different Short-ID
        subject = "Re: Test [IG-TASK:#ABCDEF]"
        formatted = service.format_subject_with_short_id(self.task, subject)
        
        # Should replace with correct Short-ID
        self.assertIn(f'[IG-TASK:#{self.task.short_id}]', formatted)
        
        # Should not contain old Short-ID
        self.assertNotIn('[IG-TASK:#ABCDEF]', formatted)
