"""
Test for the upload_file_to_sharepoint alias method in GraphService
"""

from unittest.mock import Mock, patch
from django.test import TestCase

from main.models import Settings
from core.services.graph_service import GraphService


class GraphServiceUploadAliasTestCase(TestCase):
    """Test suite for GraphService upload_file_to_sharepoint alias method"""
    
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
            sharepoint_site_id='test-site-id',
            default_mail_sender='test@example.com'
        )
    
    @patch('core.services.graph_service.requests.put')
    @patch('core.services.graph_service.requests.post')
    def test_upload_file_to_sharepoint_alias(self, mock_post, mock_put):
        """Test that upload_file_to_sharepoint alias works with alternative parameter names"""
        # Mock token request
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        # Mock upload request
        mock_put.return_value = Mock(
            status_code=201,
            json=lambda: {
                'id': 'new-file-123',
                'name': 'test.txt',
                'size': 100,
                'webUrl': 'https://sharepoint.example.com/test.txt'
            }
        )
        
        service = GraphService(self.settings)
        content = b'Test content'
        
        # Call the alias method with alternative parameter names
        result = service.upload_file_to_sharepoint(
            file_content=content,
            filename='test.txt',
            folder_path='Documents'
        )
        
        # Verify the result
        self.assertTrue(result['success'])
        self.assertEqual(result['file_name'], 'test.txt')
        self.assertEqual(result['file_id'], 'new-file-123')
        self.assertEqual(result['web_url'], 'https://sharepoint.example.com/test.txt')
        
    @patch('core.services.graph_service.requests.put')
    @patch('core.services.graph_service.requests.post')
    def test_upload_file_to_sharepoint_with_download_url_fallback(self, mock_post, mock_put):
        """Test that upload_file_to_sharepoint uses download URL as fallback for web_url"""
        # Mock token request
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'test-token', 'expires_in': 3600}
        )
        
        # Mock upload request without webUrl but with download URL
        mock_put.return_value = Mock(
            status_code=201,
            json=lambda: {
                'id': 'new-file-123',
                'name': 'test.txt',
                'size': 100,
                '@microsoft.graph.downloadUrl': 'https://download.example.com/test.txt'
            }
        )
        
        service = GraphService(self.settings)
        content = b'Test content'
        
        # Call the alias method
        result = service.upload_file_to_sharepoint(
            file_content=content,
            filename='test.txt',
            folder_path='Documents'
        )
        
        # Verify the result uses download URL as fallback
        self.assertTrue(result['success'])
        self.assertEqual(result['web_url'], 'https://download.example.com/test.txt')
