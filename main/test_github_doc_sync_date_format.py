"""
Tests for GitHub Doc Sync Service - RFC3339 Date Format

This test verifies that the last_synced field uses proper RFC3339 format
and is accepted by Weaviate without errors.
"""

import uuid
import re
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase

from main.models import User, Item, Settings
from core.services.github_doc_sync_service import GitHubDocSyncService, GitHubDocSyncServiceError


class GitHubDocSyncDateFormatTest(TestCase):
    """Test cases for GitHubDocSyncService RFC3339 date format"""
    
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
    def test_last_synced_uses_valid_rfc3339_format(self, mock_weaviate, mock_graph, mock_github):
        """Test that last_synced field uses valid RFC3339 format (ends with Z, not +00:00Z)"""
        
        # Setup mock GitHub service to return a markdown file
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
        
        # Setup mock Weaviate service to capture the properties
        mock_weaviate_instance = MagicMock()
        mock_weaviate.return_value = mock_weaviate_instance
        
        # Mock the collection object
        mock_collection = MagicMock()
        mock_weaviate_instance._client.collections.get.return_value = mock_collection
        # Mock fetch_object_by_id to return None (object doesn't exist)
        mock_collection.query.fetch_object_by_id.return_value = None
        
        # Initialize service and sync
        service = GitHubDocSyncService(self.settings)
        result = service.sync_item(item_id=str(self.item.id), uploaded_by=self.user)
        
        # Verify sync was successful
        self.assertTrue(result.get('success'))
        self.assertEqual(result.get('files_synced'), 1)
        
        # Verify that insert was called with valid RFC3339 date format
        mock_collection.data.insert.assert_called_once()
        call_args = mock_collection.data.insert.call_args
        
        # Extract properties from the call
        properties = call_args.kwargs.get('properties') or call_args[1].get('properties')
        
        # Verify 'last_synced' field is present
        self.assertIn('last_synced', properties, 
                     f"'last_synced' field should be present in properties. Found: {properties.keys()}")
        
        last_synced = properties['last_synced']
        
        # RFC3339 format check: Should end with 'Z' (for UTC), not '+00:00Z'
        self.assertTrue(last_synced.endswith('Z'),
                       f"last_synced should end with 'Z' for UTC. Got: {last_synced}")
        
        # Should NOT contain '+00:00Z' (double timezone indicator)
        self.assertNotIn('+00:00Z', last_synced,
                        f"last_synced should not contain '+00:00Z' (invalid format). Got: {last_synced}")
        
        # Verify it matches RFC3339 pattern: YYYY-MM-DDTHH:MM:SS.ffffffZ
        rfc3339_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
        self.assertIsNotNone(re.match(rfc3339_pattern, last_synced),
                           f"last_synced should match RFC3339 pattern. Got: {last_synced}")
    
    @patch('core.services.github_doc_sync_service.GitHubService')
    @patch('core.services.github_doc_sync_service.GraphService')
    @patch('core.services.github_doc_sync_service.WeaviateItemSyncService')
    def test_last_synced_format_on_update(self, mock_weaviate, mock_graph, mock_github):
        """Test that last_synced field uses valid RFC3339 format when updating existing objects"""
        
        # Setup mock GitHub service to return a markdown file
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
        
        # Verify update was called with valid RFC3339 date format
        mock_collection.data.update.assert_called_once()
        call_args = mock_collection.data.update.call_args
        
        # Extract properties from the call
        properties = call_args.kwargs.get('properties') or call_args[1].get('properties')
        
        # Verify 'last_synced' field is present
        self.assertIn('last_synced', properties)
        
        last_synced = properties['last_synced']
        
        # RFC3339 format check: Should end with 'Z', not '+00:00Z'
        self.assertTrue(last_synced.endswith('Z'),
                       f"last_synced should end with 'Z' for UTC. Got: {last_synced}")
        
        # Should NOT contain '+00:00Z' (double timezone indicator)
        self.assertNotIn('+00:00Z', last_synced,
                        f"last_synced should not contain '+00:00Z'. Got: {last_synced}")
        
        # Verify it matches RFC3339 pattern
        rfc3339_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$'
        self.assertIsNotNone(re.match(rfc3339_pattern, last_synced),
                           f"last_synced should match RFC3339 pattern. Got: {last_synced}")
