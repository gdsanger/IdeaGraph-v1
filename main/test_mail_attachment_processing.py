"""
Tests for Mail Attachment Processing in MailProcessingService
"""

import json
import base64
from unittest.mock import Mock, patch, MagicMock, call
from django.test import TestCase
from django.core.cache import cache

from main.models import Settings, User as AppUser, Item, Task, Section, TaskFile
from core.services.mail_processing_service import MailProcessingService, MailProcessingServiceError


# Patch Weaviate initialization for all tests in this module
@patch('core.services.weaviate_sync_service.WeaviateItemSyncService._initialize_client')
class MailAttachmentProcessingTestCase(TestCase):
    """Test suite for attachment processing in MailProcessingService"""
    
    def setUp(self):
        """Set up test data"""
        # Clear cache before each test
        cache.clear()
        
        # Create test user
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description for testing mail processing',
            status='working',
            section=self.section,
            created_by=self.user
        )
        
        # Create settings with all APIs enabled
        self.settings = Settings.objects.create(
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret',
            default_mail_sender='idea@angermeier.net',
            sharepoint_site_id='test-site-id',
            openai_api_enabled=True,
            openai_api_key='test-openai-key',
            openai_default_model='gpt-4',
            kigate_api_enabled=True,
            kigate_api_token='test-kigate-token',
            kigate_api_base_url='http://localhost:8000',
            weaviate_cloud_enabled=False
        )
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    @patch('core.services.graph_service.GraphService.get_message_attachments')
    @patch('core.services.graph_service.GraphService.download_attachment')
    @patch('core.services.task_file_service.TaskFileService.upload_file')
    def test_process_attachments_success(
        self,
        mock_upload,
        mock_download,
        mock_get_attachments,
        mock_weaviate_init
    ):
        """Test successful attachment processing"""
        # Create a test task
        task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            requester=self.user,
            created_by=self.user
        )
        
        # Mock attachment list
        mock_get_attachments.return_value = {
            'success': True,
            'attachments': [
                {
                    'id': 'attachment-1',
                    'name': 'test-document.pdf',
                    'size': 1024,
                    'contentType': 'application/pdf'
                }
            ],
            'count': 1
        }
        
        # Mock download
        test_content = b'Test PDF content'
        mock_download.return_value = {
            'success': True,
            'filename': 'test-document.pdf',
            'content_type': 'application/pdf',
            'content': test_content,
            'size': len(test_content)
        }
        
        # Mock upload
        mock_upload.return_value = {
            'success': True,
            'file_id': 'file-123',
            'filename': 'test-document.pdf',
            'file_size': len(test_content),
            'sharepoint_url': 'https://sharepoint.test/file',
            'weaviate_synced': True
        }
        
        # Create service and process attachments
        service = MailProcessingService(self.settings)
        result = service.process_attachments(
            message_id='test-message-id',
            task=task,
            user=self.user
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['processed'], 1)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(len(result['details']), 1)
        self.assertTrue(result['details'][0]['success'])
        self.assertEqual(result['details'][0]['filename'], 'test-document.pdf')
        self.assertTrue(result['details'][0]['weaviate_synced'])
        
        # Verify mocks were called correctly
        mock_get_attachments.assert_called_once_with('test-message-id')
        mock_download.assert_called_once_with(
            message_id='test-message-id',
            attachment_id='attachment-1'
        )
        mock_upload.assert_called_once()
    
    @patch('core.services.graph_service.GraphService.get_message_attachments')
    def test_process_attachments_no_attachments(
        self,
        mock_get_attachments,
        mock_weaviate_init
    ):
        """Test processing when message has no attachments"""
        # Create a test task
        task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            requester=self.user,
            created_by=self.user
        )
        
        # Mock empty attachment list
        mock_get_attachments.return_value = {
            'success': True,
            'attachments': [],
            'count': 0
        }
        
        # Create service and process attachments
        service = MailProcessingService(self.settings)
        result = service.process_attachments(
            message_id='test-message-id',
            task=task,
            user=self.user
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['processed'], 0)
        self.assertEqual(result['failed'], 0)
        self.assertEqual(len(result['details']), 0)
    
    @patch('core.services.graph_service.GraphService.get_message_attachments')
    @patch('core.services.graph_service.GraphService.download_attachment')
    @patch('core.services.task_file_service.TaskFileService.upload_file')
    def test_process_attachments_partial_failure(
        self,
        mock_upload,
        mock_download,
        mock_get_attachments,
        mock_weaviate_init
    ):
        """Test attachment processing with some failures"""
        # Create a test task
        task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            requester=self.user,
            created_by=self.user
        )
        
        # Mock attachment list with 2 attachments
        mock_get_attachments.return_value = {
            'success': True,
            'attachments': [
                {
                    'id': 'attachment-1',
                    'name': 'success.pdf',
                    'size': 1024,
                    'contentType': 'application/pdf'
                },
                {
                    'id': 'attachment-2',
                    'name': 'failure.pdf',
                    'size': 2048,
                    'contentType': 'application/pdf'
                }
            ],
            'count': 2
        }
        
        # Mock download - first succeeds, second fails
        def download_side_effect(*args, **kwargs):
            if kwargs.get('attachment_id') == 'attachment-1':
                return {
                    'success': True,
                    'filename': 'success.pdf',
                    'content_type': 'application/pdf',
                    'content': b'Success content',
                    'size': 15
                }
            else:
                return {
                    'success': False,
                    'error': 'Download failed'
                }
        
        mock_download.side_effect = download_side_effect
        
        # Mock upload - succeeds for the one that downloads
        mock_upload.return_value = {
            'success': True,
            'file_id': 'file-123',
            'filename': 'success.pdf',
            'file_size': 15,
            'sharepoint_url': 'https://sharepoint.test/file',
            'weaviate_synced': True
        }
        
        # Create service and process attachments
        service = MailProcessingService(self.settings)
        result = service.process_attachments(
            message_id='test-message-id',
            task=task,
            user=self.user
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['processed'], 1)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(len(result['details']), 2)
        
        # First attachment should succeed
        self.assertTrue(result['details'][0]['success'])
        self.assertEqual(result['details'][0]['filename'], 'success.pdf')
        
        # Second attachment should fail
        self.assertFalse(result['details'][1]['success'])
        self.assertEqual(result['details'][1]['filename'], 'failure.pdf')
    
    @patch('core.services.graph_service.GraphService._get_access_token')
    @patch('core.services.graph_service.GraphService._make_request')
    def test_get_message_attachments(
        self,
        mock_make_request,
        mock_token,
        mock_weaviate_init
    ):
        """Test GraphService.get_message_attachments method"""
        from core.services.graph_service import GraphService
        
        mock_token.return_value = 'test-token'
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'value': [
                {
                    'id': 'att-1',
                    'name': 'document.pdf',
                    'size': 1024,
                    'contentType': 'application/pdf'
                }
            ]
        }
        mock_make_request.return_value = mock_response
        
        # Test the method
        service = GraphService(self.settings)
        result = service.get_message_attachments('test-message-id')
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(len(result['attachments']), 1)
        self.assertEqual(result['attachments'][0]['name'], 'document.pdf')
    
    @patch('core.services.graph_service.GraphService._get_access_token')
    @patch('core.services.graph_service.GraphService._make_request')
    def test_download_attachment(
        self,
        mock_make_request,
        mock_token,
        mock_weaviate_init
    ):
        """Test GraphService.download_attachment method"""
        from core.services.graph_service import GraphService
        
        mock_token.return_value = 'test-token'
        
        # Create test content and encode it
        test_content = b'Test file content'
        test_content_b64 = base64.b64encode(test_content).decode('utf-8')
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'att-1',
            'name': 'test.txt',
            'contentType': 'text/plain',
            'contentBytes': test_content_b64
        }
        mock_make_request.return_value = mock_response
        
        # Test the method
        service = GraphService(self.settings)
        result = service.download_attachment(
            message_id='test-message-id',
            attachment_id='att-1'
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['filename'], 'test.txt')
        self.assertEqual(result['content_type'], 'text/plain')
        self.assertEqual(result['content'], test_content)
        self.assertEqual(result['size'], len(test_content))
