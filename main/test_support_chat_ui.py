"""
Test Support Chat UI Changes

Tests for the support chat UI improvements and email-like processing.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from main.models import Item, Task
from core.services.support_submit_service import SupportSubmitService


User = get_user_model()


class SupportChatUITest(TestCase):
    """Test support chat UI improvements"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            created_by=self.user
        )
    
    def test_support_view_accessible(self):
        """Test that support embed view is accessible"""
        response = self.client.get(
            f'/embed/support?itemId={self.item.id}&key=test-key'
        )
        # Should render or redirect, not 404
        self.assertIn(response.status_code, [200, 400, 401])
    
    def test_support_view_requires_item_id(self):
        """Test that support view requires itemId parameter"""
        response = self.client.get('/embed/support')
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Missing itemId', response.content)


class SupportSubmitServiceTest(TestCase):
    """Test support submit service for email-like processing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = SupportSubmitService()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            created_by=self.user
        )
    
    def test_get_or_create_user_by_email_existing(self):
        """Test finding existing user by email"""
        # User already exists
        found_user = self.service._get_or_create_user_by_email('test@example.com')
        
        self.assertEqual(found_user.id, self.user.id)
        self.assertEqual(found_user.email, 'test@example.com')
    
    def test_get_or_create_user_by_email_new(self):
        """Test creating new user by email"""
        # New email
        new_user = self.service._get_or_create_user_by_email('newuser@example.com')
        
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.email, 'newuser@example.com')
        self.assertTrue(new_user.username.startswith('newuser'))
        self.assertTrue(new_user.is_active)
    
    def test_get_or_create_user_handles_duplicate_username(self):
        """Test that duplicate usernames are handled"""
        # Create user with username 'support'
        User.objects.create_user(
            username='support',
            email='support1@example.com'
        )
        
        # Try to create another user with same email prefix
        new_user = self.service._get_or_create_user_by_email('support@example.com')
        
        self.assertIsNotNone(new_user)
        self.assertNotEqual(new_user.username, 'support')
        self.assertTrue(new_user.username.startswith('support'))
    
    @patch('core.services.support_submit_service.EmailConversationService')
    def test_submit_creates_task_with_requester(self, mock_email_service):
        """Test that submit creates task with requester linked"""
        # Mock email service
        mock_email_service.return_value.send_task_reply_email.return_value = {
            'success': True
        }
        
        result = self.service.submit(
            item_id=str(self.item.id),
            title='Test Support Request',
            description='Need help with something',
            task_type='support',
            reporter_email='requester@example.com'
        )
        
        # Check result
        self.assertTrue(result['success'])
        self.assertIn('task_id', result)
        
        # Check task was created
        task = Task.objects.get(id=result['task_id'])
        self.assertEqual(task.title, 'Test Support Request')
        self.assertEqual(task.source, 'support')
        self.assertEqual(task.reporter_email, 'requester@example.com')
        
        # Check requester was linked
        self.assertIsNotNone(task.requester)
        self.assertEqual(task.requester.email, 'requester@example.com')
    
    @patch('core.services.support_submit_service.EmailConversationService')
    def test_submit_sends_confirmation_email(self, mock_email_service):
        """Test that submit sends confirmation email"""
        # Mock email service
        mock_instance = MagicMock()
        mock_instance.send_task_reply_email.return_value = {'success': True}
        mock_email_service.return_value = mock_instance
        
        result = self.service.submit(
            item_id=str(self.item.id),
            title='Test Support Request',
            description='Need help',
            reporter_email='requester@example.com'
        )
        
        # Check email was sent
        self.assertTrue(result['success'])
        mock_instance.send_task_reply_email.assert_called_once()
        
        # Check email parameters
        call_args = mock_instance.send_task_reply_email.call_args
        self.assertIn('task', call_args[1])
        self.assertIn('recipient_email', call_args[1])
        self.assertEqual(call_args[1]['recipient_email'], 'requester@example.com')
    
    def test_enrich_description_includes_metadata(self):
        """Test that description enrichment includes metadata"""
        enriched = self.service._enrich_description(
            description='Original description',
            chat_history=[
                {'role': 'user', 'content': 'Question 1'},
                {'role': 'assistant', 'content': 'Answer 1'}
            ],
            auto_answer={
                'offered': True,
                'accepted': False,
                'summary': 'Auto answer text'
            }
        )
        
        # Check components are included
        self.assertIn('Original description', enriched)
        self.assertIn('Chat-Verlauf', enriched)
        self.assertIn('Question 1', enriched)
        self.assertIn('Automatische Antwort', enriched)
        self.assertIn('Auto answer text', enriched)
        self.assertIn('Abgelehnt', enriched)
        self.assertIn('Erstellt via Support-Formular', enriched)


if __name__ == '__main__':
    unittest.main()
