"""
Tests for GitHub Doc Sync Service Error Handling

This test verifies that error details are properly logged when SharePoint upload fails.
"""

import uuid
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase

from main.models import User, Item, Settings
from core.services.github_doc_sync_service import GitHubDocSyncService, GitHubDocSyncServiceError


class GitHubDocSyncErrorHandlingTest(TestCase):
    """Test cases for GitHubDocSyncService error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        
        # Create test settings
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='test_token',
            client_id='test_client_id',
            client_secret='test_client_secret',
            tenant_id='test_tenant_id'
        )
        
        # Create test item with GitHub repo
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            github_repo='testowner/testrepo'
        )
    
    @patch('core.services.github_doc_sync_service.GitHubService')
    @patch('core.services.github_doc_sync_service.GraphService')
    @patch('core.services.github_doc_sync_service.WeaviateItemSyncService')
    def test_sharepoint_upload_error_includes_details(self, mock_weaviate, mock_graph, mock_github):
        """Test that SharePoint upload errors include detailed error information"""
        
        # Setup mock GitHub service to return a markdown file
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        
        mock_github_instance.get_repository_contents.return_value = {
            'success': True,
            'contents': [{
                'type': 'file',
                'name': 'TEST.md',
                'path': 'TEST.md',
                'download_url': 'https://raw.githubusercontent.com/test/test/TEST.md',
                'size': 100,
                'sha': 'abc123'
            }]
        }
        
        mock_github_instance.get_file_raw.return_value = {
            'success': True,
            'content': '# Test Document\nThis is a test.',
            'size': 30
        }
        
        # Setup mock GraphService to raise an error with details
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        
        # Simulate a SharePoint error with specific details
        from core.services.graph_service import GraphServiceError
        mock_graph_instance.upload_file_to_sharepoint.side_effect = GraphServiceError(
            message="Upload failed",
            status_code=403,
            details="Insufficient permissions to access SharePoint folder"
        )
        
        # Initialize service and sync
        service = GitHubDocSyncService(self.settings)
        result = service.sync_item(item_id=str(self.item.id), uploaded_by=self.user)
        
        # Verify the result includes error information
        self.assertTrue(result.get('success'))  # sync_item returns True even with file errors
        self.assertEqual(result.get('files_processed'), 1)
        self.assertEqual(result.get('files_synced'), 0)
        self.assertGreater(len(result.get('errors', [])), 0)
        
        # Verify the error message includes details
        errors = result.get('errors', [])
        self.assertTrue(any('Details:' in error for error in errors), 
                       f"Error message should include 'Details:' section. Errors: {errors}")
        self.assertTrue(any('Insufficient permissions' in error for error in errors),
                       f"Error message should include specific error details. Errors: {errors}")
    
    @patch('core.services.github_doc_sync_service.GitHubService')
    @patch('core.services.github_doc_sync_service.GraphService')
    @patch('core.services.github_doc_sync_service.WeaviateItemSyncService')
    def test_generic_exception_handling(self, mock_weaviate, mock_graph, mock_github):
        """Test that generic exceptions are still caught and logged"""
        
        # Setup mock GitHub service to return a markdown file
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        
        mock_github_instance.get_repository_contents.return_value = {
            'success': True,
            'contents': [{
                'type': 'file',
                'name': 'TEST.md',
                'path': 'TEST.md',
                'download_url': 'https://raw.githubusercontent.com/test/test/TEST.md',
                'size': 100,
                'sha': 'abc123'
            }]
        }
        
        # Setup GitHub service to raise a generic exception
        mock_github_instance.get_file_raw.side_effect = RuntimeError("Unexpected network error")
        
        # Initialize service and sync
        service = GitHubDocSyncService(self.settings)
        result = service.sync_item(item_id=str(self.item.id), uploaded_by=self.user)
        
        # Verify the result includes error information
        self.assertTrue(result.get('success'))  # sync_item returns True even with file errors
        self.assertEqual(result.get('files_processed'), 1)
        self.assertEqual(result.get('files_synced'), 0)
        self.assertGreater(len(result.get('errors', [])), 0)
        
        # Verify the error message includes the exception message
        errors = result.get('errors', [])
        self.assertTrue(any('Unexpected network error' in error for error in errors),
                       f"Error message should include exception text. Errors: {errors}")
    
    @patch('core.services.github_doc_sync_service.GitHubService')
    def test_sync_all_items_error_handling(self, mock_github):
        """Test that sync_all_items properly handles and reports errors with details"""
        
        # Create another item
        item2 = Item.objects.create(
            title='Test Item 2',
            description='Test Description 2',
            github_repo='testowner/testrepo2'
        )
        
        # Setup mock GitHub service to raise an error
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        
        mock_github_instance.get_repository_contents.side_effect = GitHubDocSyncServiceError(
            message="Repository not found",
            details="The repository testowner/testrepo does not exist or is private"
        )
        
        # Initialize service and sync all items
        service = GitHubDocSyncService(self.settings)
        result = service.sync_all_items(uploaded_by=self.user)
        
        # Verify the result includes error information
        self.assertTrue(result.get('success'))  # Overall success flag is True even with errors
        self.assertEqual(result.get('items_processed'), 2)
        self.assertEqual(result.get('items_synced'), 0)
        self.assertGreater(len(result.get('errors', [])), 0)
        
        # Verify error messages include details
        errors = result.get('errors', [])
        self.assertTrue(any('Details:' in error for error in errors),
                       f"Error messages should include 'Details:' section. Errors: {errors}")
        self.assertTrue(any('Repository not found' in error for error in errors),
                       f"Error messages should include specific error details. Errors: {errors}")
