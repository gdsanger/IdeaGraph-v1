"""
Tests for item email functionality
"""

import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse

from main.models import Item, Task, User, Tag, Section, Settings
from main.mail_utils import send_item_email


class SendItemEmailTestCase(TestCase):
    """Test suite for send_item_email functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with Graph API enabled
        self.settings = Settings.objects.create(
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret',
            graph_api_base_url='https://graph.microsoft.com/v1.0',
            graph_api_scopes='https://graph.microsoft.com/.default',
            default_mail_sender='test@example.com'
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='testuser@example.com',
            role='user'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create admin user
        self.admin = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        self.admin.set_password('adminpass123')
        self.admin.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test tags
        self.tag1 = Tag.objects.create(name='Tag1', color='#ff0000')
        self.tag2 = Tag.objects.create(name='Tag2', color='#00ff00')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='This is a test item description',
            status='working',
            section=self.section,
            created_by=self.user,
            github_repo='owner/repo'
        )
        self.item.tags.add(self.tag1, self.tag2)
        
        # Create test tasks
        self.task1 = Task.objects.create(
            title='Task 1',
            description='First task',
            status='new',
            item=self.item,
            created_by=self.user
        )
        
        self.task2 = Task.objects.create(
            title='Task 2',
            description='Second task',
            status='working',
            item=self.item,
            assigned_to=self.user,
            created_by=self.user
        )
        
        # Create a completed task (should not be included in email)
        self.task3 = Task.objects.create(
            title='Task 3',
            description='Completed task',
            status='done',
            item=self.item,
            created_by=self.user
        )
        
        self.client = Client()
    
    @patch('main.mail_utils.GraphService')
    def test_send_item_email_success(self, mock_graph_service):
        """Test sending item email successfully"""
        # Mock GraphService
        mock_service = Mock()
        mock_service.send_mail.return_value = {'success': True, 'message': 'Email sent'}
        mock_graph_service.return_value = mock_service
        
        # Send email
        success, message = send_item_email(self.item.id, 'recipient@example.com')
        
        # Verify success
        self.assertTrue(success)
        self.assertEqual(message, 'Item email sent successfully')
        
        # Verify send_mail was called with correct parameters
        mock_service.send_mail.assert_called_once()
        call_args = mock_service.send_mail.call_args
        self.assertEqual(call_args[1]['to'], ['recipient@example.com'])
        self.assertEqual(call_args[1]['subject'], 'Test Item')
        self.assertIn('Test Item', call_args[1]['body'])
        self.assertIn('Task 1', call_args[1]['body'])
        self.assertIn('Task 2', call_args[1]['body'])
        # Verify completed task is NOT in the email
        self.assertNotIn('Task 3', call_args[1]['body'])
    
    @patch('main.mail_utils.GraphService')
    def test_send_item_email_with_no_tasks(self, mock_graph_service):
        """Test sending item email when there are no open tasks"""
        # Create item without tasks
        item = Item.objects.create(
            title='Item Without Tasks',
            description='No tasks',
            status='new',
            created_by=self.user
        )
        
        # Mock GraphService
        mock_service = Mock()
        mock_service.send_mail.return_value = {'success': True}
        mock_graph_service.return_value = mock_service
        
        # Send email
        success, message = send_item_email(item.id, 'recipient@example.com')
        
        # Verify success
        self.assertTrue(success)
        
        # Verify email content includes "no tasks" message
        call_args = mock_service.send_mail.call_args
        self.assertIn('Keine offenen Aufgaben', call_args[1]['body'])
    
    def test_send_item_email_item_not_found(self):
        """Test sending email for non-existent item"""
        import uuid
        fake_id = uuid.uuid4()
        
        success, message = send_item_email(fake_id, 'recipient@example.com')
        
        self.assertFalse(success)
        self.assertEqual(message, 'Item not found')
    
    @patch('main.mail_utils.GraphService')
    def test_send_item_email_graph_service_error(self, mock_graph_service):
        """Test error handling when GraphService fails"""
        from core.services.graph_service import GraphServiceError
        
        # Mock GraphService to raise error
        mock_service = Mock()
        mock_service.send_mail.side_effect = GraphServiceError('Service unavailable')
        mock_graph_service.return_value = mock_service
        
        # Send email
        success, message = send_item_email(self.item.id, 'recipient@example.com')
        
        # Verify failure
        self.assertFalse(success)
        self.assertIn('Email service error', message)


class SendItemEmailAPITestCase(TestCase):
    """Test suite for send item email API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings
        self.settings = Settings.objects.create(
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret',
            default_mail_sender='test@example.com'
        )
        
        # Create users
        self.user = User.objects.create(
            username='testuser',
            email='testuser@example.com',
            role='user'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        self.other_user = User.objects.create(
            username='otheruser',
            email='otheruser@example.com',
            role='user'
        )
        self.other_user.set_password('otherpass123')
        self.other_user.save()
        
        self.admin = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        self.admin.set_password('adminpass123')
        self.admin.save()
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            created_by=self.user
        )
        
        self.client = Client()
    
    @patch('main.mail_utils.send_item_email')
    def test_send_item_email_as_owner(self, mock_send):
        """Test sending item email as the owner"""
        # Mock send_item_email
        mock_send.return_value = (True, 'Email sent successfully')
        
        # Login as owner
        self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Send request
        response = self.client.post(
            reverse('main:api_send_item_email', args=[self.item.id]),
            data=json.dumps({'email': 'recipient@example.com'}),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify mock was called
        mock_send.assert_called_once_with(self.item.id, 'recipient@example.com')
    
    @patch('main.mail_utils.send_item_email')
    def test_send_item_email_as_admin(self, mock_send):
        """Test sending item email as admin"""
        # Mock send_item_email
        mock_send.return_value = (True, 'Email sent successfully')
        
        # Login as admin
        self.client.post(reverse('main:login'), {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        # Send request
        response = self.client.post(
            reverse('main:api_send_item_email', args=[self.item.id]),
            data=json.dumps({'email': 'recipient@example.com'}),
            content_type='application/json'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_send_item_email_as_non_owner(self):
        """Test that non-owner cannot send item email"""
        # Login as other user
        self.client.post(reverse('main:login'), {
            'username': 'otheruser',
            'password': 'otherpass123'
        })
        
        # Send request
        response = self.client.post(
            reverse('main:api_send_item_email', args=[self.item.id]),
            data=json.dumps({'email': 'recipient@example.com'}),
            content_type='application/json'
        )
        
        # Verify access denied
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data['error'], 'Access denied')
    
    def test_send_item_email_unauthenticated(self):
        """Test that unauthenticated users cannot send item email"""
        response = self.client.post(
            reverse('main:api_send_item_email', args=[self.item.id]),
            data=json.dumps({'email': 'recipient@example.com'}),
            content_type='application/json'
        )
        
        # Verify authentication required
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['error'], 'Authentication required')
    
    def test_send_item_email_missing_email(self):
        """Test error when email is missing"""
        # Login
        self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Send request without email
        response = self.client.post(
            reverse('main:api_send_item_email', args=[self.item.id]),
            data=json.dumps({}),
            content_type='application/json'
        )
        
        # Verify error
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'Email address is required')
    
    def test_send_item_email_invalid_email(self):
        """Test error when email format is invalid"""
        # Login
        self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Send request with invalid email
        response = self.client.post(
            reverse('main:api_send_item_email', args=[self.item.id]),
            data=json.dumps({'email': 'invalid-email'}),
            content_type='application/json'
        )
        
        # Verify error
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'Invalid email address format')
    
    def test_send_item_email_item_not_found(self):
        """Test error when item doesn't exist"""
        import uuid
        
        # Login
        self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Send request with non-existent item
        fake_id = uuid.uuid4()
        response = self.client.post(
            reverse('main:api_send_item_email', args=[fake_id]),
            data=json.dumps({'email': 'recipient@example.com'}),
            content_type='application/json'
        )
        
        # Verify error
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['error'], 'Item not found')
