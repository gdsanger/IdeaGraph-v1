"""
Tests for Task Email UI feature in Comments section
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, TaskComment, Settings
from main.auth_utils import generate_jwt_token


class TaskEmailUITestCase(TestCase):
    """Test cases for Task Email UI functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test settings (required for email service)
        self.settings = Settings.objects.create(
            default_mail_sender='test@test.com',
            client_id='test-client-id',
            client_secret='test-client-secret',
            tenant_id='test-tenant-id'
        )
        
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
        
        # Generate JWT token
        self.token = generate_jwt_token(self.user)
        
        # Setup client
        self.client = Client()
    
    @patch('core.services.email_conversation_service.GraphService')
    def test_send_task_email_creates_comment(self, mock_graph_service_class):
        """Test that sending an email creates a comment with source='email'"""
        # Mock the GraphService class and instance
        mock_graph_service_instance = MagicMock()
        mock_graph_service_instance.send_mail.return_value = {
            'success': True,
            'message': 'Email sent successfully'
        }
        mock_graph_service_class.return_value = mock_graph_service_instance
        
        url = reverse('main:api_send_task_email', kwargs={'task_id': self.task.id})
        
        response = self.client.post(
            url,
            data=json.dumps({
                'email': 'recipient@example.com',
                'subject': 'Test Subject',
                'body': '<p>Test email body</p>'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify comment was created with source='email'
        email_comments = TaskComment.objects.filter(task=self.task, source='email')
        self.assertEqual(email_comments.count(), 1)
        
        comment = email_comments.first()
        self.assertEqual(comment.source, 'email')
        self.assertIn('recipient@example.com', comment.text)
    
    def test_comments_list_displays_email_comments(self):
        """Test that comments list properly displays email-sourced comments"""
        # Create an email comment
        email_comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            author_name='Test User',
            text='Email body content',
            source='email',
            email_message_id='<test@test.com>',
            email_from='sender@example.com',
            email_subject='Test Email Subject [IG-TASK:#ABC123]'
        )
        
        url = reverse('main:api_task_comments', kwargs={'task_id': self.task.id})
        
        # Make htmx request to get HTML partial
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
            HTTP_HX_REQUEST='true'  # Simulate htmx request
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check for email-specific styling and elements
        self.assertContains(response, 'comment-email')
        self.assertContains(response, 'bi-envelope')
        self.assertContains(response, 'sender@example.com')
        self.assertContains(response, 'Test Email Subject')
    
    def test_email_api_requires_authentication(self):
        """Test that email API requires authentication"""
        url = reverse('main:api_send_task_email', kwargs={'task_id': self.task.id})
        
        # Try without authentication
        response = self.client.post(
            url,
            data=json.dumps({
                'email': 'recipient@example.com',
                'subject': 'Test',
                'body': 'Test'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_css_styling_for_email_comments(self):
        """Test that CSS styling for email comments is included"""
        # Create an email comment
        TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Email content',
            source='email',
            email_from='sender@test.com'
        )
        
        url = reverse('main:api_task_comments', kwargs={'task_id': self.task.id})
        
        # Make htmx request to get HTML partial
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
            HTTP_HX_REQUEST='true'  # Simulate htmx request
        )
        
        # Check for email-specific CSS classes
        self.assertContains(response, '.comment-email')
        self.assertContains(response, 'border-left-color: #3b82f6')
        self.assertContains(response, '.comment-email-subject')
