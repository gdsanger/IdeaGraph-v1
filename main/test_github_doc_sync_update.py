"""
Tests for GitHub Doc Sync Service - Update/Create behavior

This test verifies that:
1. The service properly creates new objects when they don't exist
2. The service properly updates existing objects
3. No duplicate object errors occur
"""

import uuid
from unittest.mock import Mock, patch, MagicMock, call
from django.test import TestCase

from main.models import User, Item, Settings
from core.services.github_doc_sync_service import GitHubDocSyncService, GitHubDocSyncServiceError


class GitHubDocSyncUpdateTest(TestCase):
    """Test cases for GitHubDocSyncService update/create behavior"""
    
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
    def test_creates_new_object_when_not_exists(self, mock_weaviate, mock_graph, mock_github):
        """Test that service creates new object when it doesn't exist"""
        
        # Setup mock GitHub service
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        
        test_content = '# Test Document\n\nThis is test content.'
        
        mock_github_instance.get_repository_contents.return_value = {
            'success': True,
            'contents': [{
                'type': 'file',
                'name': 'TEST.md',
                'path': 'TEST.md',
                'download_url': 'https://raw.githubusercontent.com/test/test/TEST.md',
                'size': len(test_content),
                'sha': 'abc123'
            }]
        }
        
        mock_github_instance.get_file_raw.return_value = {
            'success': True,
            'content': test_content,
            'size': len(test_content)
        }
        
        # Setup mock GraphService
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.upload_file_to_sharepoint.return_value = {
            'success': True,
            'file_id': 'test_file_id',
            'web_url': 'https://sharepoint.test/file',
            'size': len(test_content)
        }
        
        # Setup mock Weaviate service
        mock_weaviate_instance = MagicMock()
        mock_weaviate.return_value = mock_weaviate_instance
        
        # Mock the collection object - object doesn't exist
        mock_collection = MagicMock()
        mock_weaviate_instance._client.collections.get.return_value = mock_collection
        mock_collection.query.fetch_object_by_id.return_value = None
        
        # Initialize service and sync
        service = GitHubDocSyncService(self.settings)
        result = service.sync_item(item_id=str(self.item.id), uploaded_by=self.user)
        
        # Verify sync was successful
        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('files_synced'), 1)
        
        # Verify insert was called (not update)
        mock_collection.data.insert.assert_called_once()
        mock_collection.data.update.assert_not_called()
    
    @patch('core.services.github_doc_sync_service.GitHubService')
    @patch('core.services.github_doc_sync_service.GraphService')
    @patch('core.services.github_doc_sync_service.WeaviateItemSyncService')
    def test_updates_existing_object(self, mock_weaviate, mock_graph, mock_github):
        """Test that service updates object when it already exists"""
        
        # Setup mock GitHub service
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        
        test_content = '# Updated Document\n\nThis is updated content.'
        
        mock_github_instance.get_repository_contents.return_value = {
            'success': True,
            'contents': [{
                'type': 'file',
                'name': 'TEST.md',
                'path': 'TEST.md',
                'download_url': 'https://raw.githubusercontent.com/test/test/TEST.md',
                'size': len(test_content),
                'sha': 'abc123'
            }]
        }
        
        mock_github_instance.get_file_raw.return_value = {
            'success': True,
            'content': test_content,
            'size': len(test_content)
        }
        
        # Setup mock GraphService
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.upload_file_to_sharepoint.return_value = {
            'success': True,
            'file_id': 'test_file_id',
            'web_url': 'https://sharepoint.test/file',
            'size': len(test_content)
        }
        
        # Setup mock Weaviate service
        mock_weaviate_instance = MagicMock()
        mock_weaviate.return_value = mock_weaviate_instance
        
        # Mock the collection object - object exists
        mock_collection = MagicMock()
        mock_weaviate_instance._client.collections.get.return_value = mock_collection
        
        # Mock an existing object
        existing_object = MagicMock()
        existing_object.uuid = 'test-uuid-123'
        mock_collection.query.fetch_object_by_id.return_value = existing_object
        
        # Initialize service and sync
        service = GitHubDocSyncService(self.settings)
        result = service.sync_item(item_id=str(self.item.id), uploaded_by=self.user)
        
        # Verify sync was successful
        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('files_synced'), 1)
        
        # Verify update was called (not insert)
        mock_collection.data.update.assert_called_once()
        mock_collection.data.insert.assert_not_called()
        
        # Verify the properties contain updated content
        call_args = mock_collection.data.update.call_args
        properties = call_args.kwargs.get('properties') or call_args[1].get('properties')
        self.assertIn('Updated Document', properties['title'])
    
    @patch('core.services.github_doc_sync_service.GitHubService')
    @patch('core.services.github_doc_sync_service.GraphService')
    @patch('core.services.github_doc_sync_service.WeaviateItemSyncService')
    def test_handles_fetch_exception_gracefully(self, mock_weaviate, mock_graph, mock_github):
        """Test that service creates object when fetch raises exception"""
        
        # Setup mock GitHub service
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        
        test_content = '# Test Document\n\nThis is test content.'
        
        mock_github_instance.get_repository_contents.return_value = {
            'success': True,
            'contents': [{
                'type': 'file',
                'name': 'TEST.md',
                'path': 'TEST.md',
                'download_url': 'https://raw.githubusercontent.com/test/test/TEST.md',
                'size': len(test_content),
                'sha': 'abc123'
            }]
        }
        
        mock_github_instance.get_file_raw.return_value = {
            'success': True,
            'content': test_content,
            'size': len(test_content)
        }
        
        # Setup mock GraphService
        mock_graph_instance = MagicMock()
        mock_graph.return_value = mock_graph_instance
        mock_graph_instance.upload_file_to_sharepoint.return_value = {
            'success': True,
            'file_id': 'test_file_id',
            'web_url': 'https://sharepoint.test/file',
            'size': len(test_content)
        }
        
        # Setup mock Weaviate service
        mock_weaviate_instance = MagicMock()
        mock_weaviate.return_value = mock_weaviate_instance
        
        # Mock the collection object - fetch raises exception (object not found)
        mock_collection = MagicMock()
        mock_weaviate_instance._client.collections.get.return_value = mock_collection
        mock_collection.query.fetch_object_by_id.side_effect = Exception("Object not found")
        
        # Initialize service and sync
        service = GitHubDocSyncService(self.settings)
        result = service.sync_item(item_id=str(self.item.id), uploaded_by=self.user)
        
        # Verify sync was successful
        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('files_synced'), 1)
        
        # Verify insert was called (in the exception handler)
        mock_collection.data.insert.assert_called_once()
        mock_collection.data.update.assert_not_called()
