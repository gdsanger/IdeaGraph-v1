"""
Tests for Microsoft Graph API Service
"""

import json
import base64
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from main.models import Settings, User as AppUser
from core.services.graph_service import GraphService, GraphServiceError


class GraphServiceTestCase(TestCase):
    """Test suite for GraphService"""
    
    def setUp(self):
        """Set up test data"""
        # Clear cache before each test
        cache.clear()
        
        # Create settings with Graph API enabled
        self.settings = Settings.objects.create(
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret',
            graph_api_base_url='https://graph.microsoft.com/v1.0',
            graph_api_scopes='https://graph.microsoft.com/.default',
            sharepoint_site_id='test-site-id',
            default_mail_sender='test@example.com'
        )
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_init_without_settings(self):
        """Test GraphService initialization without settings object"""
        with patch('main.models.Settings') as mock_settings_model:
            mock_settings_model.objects.first.return_value = self.settings
            service = GraphService()
            self.assertIsNotNone(service.settings)
    
    def test_init_with_disabled_api(self):
        """Test GraphService raises error when API is disabled"""
        self.settings.graph_api_enabled = False
        self.settings.save()
        
        with self.assertRaises(GraphServiceError) as context:
            GraphService(self.settings)
        
        self.assertIn("not enabled", str(context.exception))
    
    def test_init_with_incomplete_config(self):
        """Test GraphService raises error with incomplete configuration"""
        self.settings.client_id = ''
        self.settings.save()
        
        with self.assertRaises(GraphServiceError) as context:
            GraphService(self.settings)
        
        self.assertIn("incomplete", str(context.exception))
    
    @patch('core.services.graph_service.requests.post')
    def test_get_access_token_success(self, mock_post):
        """Test successful token acquisition"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test-token-123',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        service = GraphService(self.settings)
        token = service._get_access_token()
        
        self.assertEqual(token, 'test-token-123')
        
        # Verify token is cached
        cached_token = service._get_token_from_cache()
        self.assertEqual(cached_token, 'test-token-123')
    
    @patch('core.services.graph_service.requests.post')
    def test_get_access_token_failure(self, mock_post):
        """Test token acquisition failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_post.return_value = mock_response
        
        service = GraphService(self.settings)
        
        with self.assertRaises(GraphServiceError) as context:
            service._get_access_token()
        
        self.assertIn("Failed to acquire access token", str(context.exception))
    
    @patch('core.services.graph_service.requests.post')
    def test_token_caching(self, mock_post):
        """Test that token is retrieved from cache on subsequent calls"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test-token-123',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        service = GraphService(self.settings)
        
        # First call - should hit the API
        token1 = service._get_access_token()
        self.assertEqual(mock_post.call_count, 1)
        
        # Second call - should use cache
        token2 = service._get_access_token()
        self.assertEqual(mock_post.call_count, 1)  # Still 1, no additional call
        self.assertEqual(token1, token2)
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_get_sharepoint_file_list(self, mock_post, mock_request):
        """Test listing SharePoint files"""
        # Mock token request
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        # Mock file list request
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'value': [
                    {'id': '1', 'name': 'file1.txt', 'size': 100},
                    {'id': '2', 'name': 'file2.pdf', 'size': 200}
                ]
            }
        )
        
        service = GraphService(self.settings)
        result = service.get_sharepoint_file_list('Documents')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['files']), 2)
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_get_sharepoint_file_list_error(self, mock_post, mock_request):
        """Test error handling when listing files"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(
            status_code=404,
            text='Folder not found'
        )
        
        service = GraphService(self.settings)
        
        with self.assertRaises(GraphServiceError) as context:
            service.get_sharepoint_file_list('NonExistent')
        
        self.assertIn("Failed to list files", str(context.exception))
    
    @patch('core.services.graph_service.requests.get')
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_get_sharepoint_file(self, mock_post, mock_request, mock_get):
        """Test downloading a SharePoint file"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'id': 'file-123',
                'name': 'test.txt',
                'size': 100,
                '@microsoft.graph.downloadUrl': 'https://download.url'
            }
        )
        
        mock_get.return_value = Mock(
            status_code=200,
            content=b'Test file content'
        )
        
        service = GraphService(self.settings)
        result = service.get_sharepoint_file('file-123')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['file_name'], 'test.txt')
        self.assertEqual(result['content'], b'Test file content')
    
    @patch('core.services.graph_service.requests.put')
    @patch('core.services.graph_service.requests.post')
    def test_upload_sharepoint_file(self, mock_post, mock_put):
        """Test uploading a file to SharePoint"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_put.return_value = Mock(
            status_code=201,
            json=lambda: {
                'id': 'new-file-123',
                'name': 'uploaded.txt',
                'size': 100
            }
        )
        
        service = GraphService(self.settings)
        content = b'Test content'
        result = service.upload_sharepoint_file('Documents', 'uploaded.txt', content)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['file_name'], 'uploaded.txt')
        self.assertEqual(result['file_id'], 'new-file-123')
    
    @patch('core.services.graph_service.requests.post')
    def test_upload_large_file_error(self, mock_post):
        """Test that large files are rejected"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        service = GraphService(self.settings)
        large_content = b'x' * (26 * 1024 * 1024)  # 26MB (exceeds 25MB limit)
        
        with self.assertRaises(GraphServiceError) as context:
            service.upload_sharepoint_file('Documents', 'large.txt', large_content)
        
        self.assertIn("File too large", str(context.exception))
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_delete_sharepoint_file(self, mock_post, mock_request):
        """Test deleting a SharePoint file"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(status_code=204)
        
        service = GraphService(self.settings)
        result = service.delete_sharepoint_file('file-123')
        
        self.assertTrue(result['success'])
        self.assertIn('deleted', result['message'].lower())
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_send_mail(self, mock_post, mock_request):
        """Test sending email via Graph API"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(status_code=202)
        
        service = GraphService(self.settings)
        result = service.send_mail(
            to=['user@example.com'],
            subject='Test Subject',
            body='Test Body'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('sent', result['message'].lower())
    
    @patch('core.services.graph_service.requests.post')
    def test_send_mail_no_recipients(self, mock_post):
        """Test that sending email without recipients raises error"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        service = GraphService(self.settings)
        
        with self.assertRaises(GraphServiceError) as context:
            service.send_mail(to=[], subject='Test', body='Test')
        
        self.assertIn("No recipients", str(context.exception))
    
    @patch('core.services.graph_service.requests.post')
    def test_send_mail_to_self_blocked(self, mock_post):
        """Test that sending email to default_mail_sender is blocked"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        service = GraphService(self.settings)
        
        # Attempt to send email to the default_mail_sender
        with self.assertRaises(GraphServiceError) as context:
            service.send_mail(
                to=['test@example.com'],  # This is the default_mail_sender
                subject='Test Self Send',
                body='This should be blocked'
            )
        
        self.assertIn("Self-sending not allowed", str(context.exception))
        self.assertIn("infinite loop", str(context.exception.details))
    
    @patch('core.services.graph_service.requests.post')
    def test_send_mail_to_self_case_insensitive(self, mock_post):
        """Test that self-send check is case-insensitive"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        service = GraphService(self.settings)
        
        # Test with uppercase
        with self.assertRaises(GraphServiceError) as context:
            service.send_mail(
                to=['TEST@EXAMPLE.COM'],
                subject='Test Self Send',
                body='This should be blocked'
            )
        
        self.assertIn("Self-sending not allowed", str(context.exception))
        
        # Test with mixed case
        with self.assertRaises(GraphServiceError) as context:
            service.send_mail(
                to=['Test@Example.Com'],
                subject='Test Self Send',
                body='This should be blocked'
            )
        
        self.assertIn("Self-sending not allowed", str(context.exception))
    
    @patch('core.services.graph_service.requests.post')
    def test_send_mail_cc_to_self_blocked(self, mock_post):
        """Test that CC'ing email to default_mail_sender is blocked"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        service = GraphService(self.settings)
        
        # Attempt to CC email to the default_mail_sender
        with self.assertRaises(GraphServiceError) as context:
            service.send_mail(
                to=['other@example.com'],
                cc=['test@example.com'],  # This is the default_mail_sender
                subject='Test Self CC',
                body='This should be blocked'
            )
        
        self.assertIn("Self-sending not allowed", str(context.exception))
        self.assertIn("infinite loop", str(context.exception.details))
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_send_mail_to_self_in_list_blocked(self, mock_post, mock_request):
        """Test that self-send is blocked even when mixed with other recipients"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        service = GraphService(self.settings)
        
        # Attempt to send to multiple recipients including self
        with self.assertRaises(GraphServiceError) as context:
            service.send_mail(
                to=['user1@example.com', 'test@example.com', 'user2@example.com'],
                subject='Test Self Send in List',
                body='This should be blocked'
            )
        
        self.assertIn("Self-sending not allowed", str(context.exception))
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_send_mail_to_others_allowed(self, mock_post, mock_request):
        """Test that sending to other addresses is still allowed"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(status_code=202)
        
        service = GraphService(self.settings)
        
        # This should succeed
        result = service.send_mail(
            to=['user@example.com', 'another@example.com'],
            subject='Test Normal Send',
            body='This should work'
        )
        
        self.assertTrue(result['success'])
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_send_system_mail(self, mock_post, mock_request):
        """Test sending system notification email"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(status_code=202)
        
        service = GraphService(self.settings)
        result = service.send_system_mail(
            template='user_created',
            context={
                'subject': 'New User Created',
                'recipients': ['admin@example.com'],
                'username': 'testuser',
                'email': 'testuser@example.com'
            }
        )
        
        self.assertTrue(result['success'])
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_retry_on_401(self, mock_post, mock_request):
        """Test that 401 errors trigger token refresh and retry"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        # First request returns 401, second returns 200
        mock_request.side_effect = [
            Mock(status_code=401),
            Mock(
                status_code=200,
                json=lambda: {'value': []}
            )
        ]
        
        service = GraphService(self.settings)
        result = service.get_sharepoint_file_list('')
        
        # Should have made 2 requests (initial + retry)
        self.assertEqual(mock_request.call_count, 2)
        self.assertTrue(result['success'])
    
    def test_graph_service_error_to_dict(self):
        """Test GraphServiceError to_dict method"""
        error = GraphServiceError(
            message="Test error",
            status_code=500,
            details="Test details"
        )
        
        error_dict = error.to_dict()
        
        self.assertFalse(error_dict['success'])
        self.assertEqual(error_dict['error'], "Test error")
        self.assertEqual(error_dict['details'], "Test details")


class GraphAPIEndpointsTestCase(TestCase):
    """Test suite for Graph API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Clear cache
        cache.clear()
        
        # Create admin user
        self.admin = AppUser(username='admin', email='admin@example.com', role='admin')
        self.admin.set_password('AdminPass123!')
        self.admin.save()
        
        # Create regular user
        self.user = AppUser(username='user', email='user@example.com', role='user')
        self.user.set_password('UserPass123!')
        self.user.save()
        
        # Create settings
        self.settings = Settings.objects.create(
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret',
            sharepoint_site_id='test-site-id',
            default_mail_sender='test@example.com'
        )
        
        # Get admin token
        response = self.client.post(
            reverse('main:api_login'),
            data=json.dumps({'username': 'admin', 'password': 'AdminPass123!'}),
            content_type='application/json'
        )
        self.admin_token = response.json()['token']
        
        # Get user token
        response = self.client.post(
            reverse('main:api_login'),
            data=json.dumps({'username': 'user', 'password': 'UserPass123!'}),
            content_type='application/json'
        )
        self.user_token = response.json()['token']
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_list_sharepoint_files_admin(self, mock_post, mock_request):
        """Test listing SharePoint files as admin"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'value': [
                    {'id': '1', 'name': 'file1.txt'}
                ]
            }
        )
        
        response = self.client.get(
            reverse('main:api_graph_sharepoint_files') + '?folder_path=Documents',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)
    
    def test_list_sharepoint_files_non_admin(self):
        """Test that non-admin users cannot list SharePoint files"""
        response = self.client.get(
            reverse('main:api_graph_sharepoint_files'),
            HTTP_AUTHORIZATION=f'Bearer {self.user_token}'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)
    
    @patch('core.services.graph_service.requests.put')
    @patch('core.services.graph_service.requests.post')
    def test_upload_file_admin(self, mock_post, mock_put):
        """Test uploading file as admin"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_put.return_value = Mock(
            status_code=201,
            json=lambda: {
                'id': 'new-file',
                'name': 'test.txt',
                'size': 100
            }
        )
        
        content = base64.b64encode(b'Test content').decode('utf-8')
        
        response = self.client.post(
            reverse('main:api_graph_sharepoint_upload'),
            data=json.dumps({
                'folder_path': 'Documents',
                'file_name': 'test.txt',
                'content': content
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_upload_file_missing_params(self):
        """Test upload with missing parameters"""
        response = self.client.post(
            reverse('main:api_graph_sharepoint_upload'),
            data=json.dumps({
                'folder_path': 'Documents'
                # Missing file_name and content
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 400)
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_send_mail_admin(self, mock_post, mock_request):
        """Test sending email as admin"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(status_code=202)
        
        response = self.client.post(
            reverse('main:api_graph_mail_send'),
            data=json.dumps({
                'to': ['user@example.com'],
                'subject': 'Test',
                'body': 'Test message'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_send_mail_missing_params(self):
        """Test send mail with missing parameters"""
        response = self.client.post(
            reverse('main:api_graph_mail_send'),
            data=json.dumps({
                'to': ['user@example.com']
                # Missing subject and body
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 400)
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_get_mailbox_messages_success(self, mock_post, mock_request):
        """Test retrieving mailbox messages successfully"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'value': [
                    {
                        'id': 'msg-1',
                        'subject': 'Test Email 1',
                        'bodyPreview': 'Preview 1',
                        'body': {'content': '<p>Content 1</p>', 'contentType': 'HTML'},
                        'from': {'emailAddress': {'address': 'sender@example.com'}},
                        'receivedDateTime': '2024-01-01T10:00:00Z',
                        'isRead': False
                    },
                    {
                        'id': 'msg-2',
                        'subject': 'Test Email 2',
                        'bodyPreview': 'Preview 2',
                        'body': {'content': '<p>Content 2</p>', 'contentType': 'HTML'},
                        'from': {'emailAddress': {'address': 'sender@example.com'}},
                        'receivedDateTime': '2024-01-01T11:00:00Z',
                        'isRead': False
                    }
                ]
            }
        )
        
        service = GraphService(self.settings)
        result = service.get_mailbox_messages(top=10, unread_only=True)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['messages']), 2)
        self.assertEqual(result['messages'][0]['subject'], 'Test Email 1')
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_get_mailbox_messages_custom_mailbox(self, mock_post, mock_request):
        """Test retrieving messages from custom mailbox"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {'value': []}
        )
        
        service = GraphService(self.settings)
        result = service.get_mailbox_messages(
            mailbox='custom@example.com',
            folder='inbox',
            top=5
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 0)
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_get_mailbox_messages_error(self, mock_post, mock_request):
        """Test error handling when retrieving messages"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(
            status_code=403,
            text='Access denied'
        )
        
        service = GraphService(self.settings)
        
        with self.assertRaises(GraphServiceError) as context:
            service.get_mailbox_messages()
        
        self.assertIn("Failed to retrieve messages", str(context.exception))
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_mark_message_as_read_success(self, mock_post, mock_request):
        """Test marking message as read successfully"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(status_code=200)
        
        service = GraphService(self.settings)
        result = service.mark_message_as_read('msg-123')
        
        self.assertTrue(result['success'])
        self.assertIn('marked as read', result['message'])
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_mark_message_as_read_error(self, mock_post, mock_request):
        """Test error handling when marking message as read"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(
            status_code=404,
            text='Message not found'
        )
        
        service = GraphService(self.settings)
        
        with self.assertRaises(GraphServiceError) as context:
            service.mark_message_as_read('invalid-msg-id')
        
        self.assertIn("Failed to mark message as read", str(context.exception))
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_move_message_success(self, mock_post, mock_request):
        """Test moving message to archive folder successfully"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(status_code=201)
        
        service = GraphService(self.settings)
        result = service.move_message('msg-123', destination_folder='archive')
        
        self.assertTrue(result['success'])
        self.assertIn('moved to archive', result['message'])
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_move_message_custom_folder(self, mock_post, mock_request):
        """Test moving message to custom folder"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(status_code=200)
        
        service = GraphService(self.settings)
        result = service.move_message('msg-123', destination_folder='processed')
        
        self.assertTrue(result['success'])
        self.assertIn('moved to processed', result['message'])
    
    @patch('core.services.graph_service.requests.request')
    @patch('core.services.graph_service.requests.post')
    def test_move_message_error(self, mock_post, mock_request):
        """Test error handling when moving message"""
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        mock_request.return_value = Mock(
            status_code=404,
            text='Message not found'
        )
        
        service = GraphService(self.settings)
        
        with self.assertRaises(GraphServiceError) as context:
            service.move_message('invalid-msg-id')
        
        self.assertIn("Failed to move message", str(context.exception))
