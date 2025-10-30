"""
Tests for GitHub Doc Sync Service - itemId and full content

This test verifies that:
1. Item ID is correctly stored in the 'itemId' field (not 'related_item')
2. Full content is stored in the 'description' field (not truncated)
"""

import uuid
from unittest.mock import Mock, patch, MagicMock, call
from django.test import TestCase

from main.models import User, Item, Settings
from core.services.github_doc_sync_service import GitHubDocSyncService, GitHubDocSyncServiceError


class GitHubDocSyncItemIdTest(TestCase):
    """Test cases for GitHubDocSyncService itemId and content storage"""
    
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
    def test_itemid_field_is_used_not_related_item(self, mock_weaviate, mock_graph, mock_github):
        """Test that item ID is stored in 'itemId' field, not 'related_item'"""
        
        # Setup mock GitHub service to return a markdown file
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        
        test_content = '# Test Document\n\nThis is test content for the documentation.'
        
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
        
        # Verify that insert was called with properties containing 'itemId'
        mock_collection.data.insert.assert_called_once()
        call_args = mock_collection.data.insert.call_args
        
        # Extract properties from the call
        properties = call_args.kwargs.get('properties') or call_args[1].get('properties')
        
        # Verify 'itemId' field is present and has correct value
        self.assertIn('itemId', properties, 
                     f"'itemId' field should be present in properties. Found: {properties.keys()}")
        self.assertEqual(properties['itemId'], str(self.item.id),
                        f"'itemId' should contain the item ID")
        
        # Verify 'related_item' field is NOT present
        self.assertNotIn('related_item', properties,
                        f"'related_item' field should NOT be present. Found: {properties.keys()}")
    
    @patch('core.services.github_doc_sync_service.GitHubService')
    @patch('core.services.github_doc_sync_service.GraphService')
    @patch('core.services.github_doc_sync_service.WeaviateItemSyncService')
    def test_full_content_stored_in_description(self, mock_weaviate, mock_graph, mock_github):
        """Test that full content is stored in description field, not truncated"""
        
        # Setup mock GitHub service to return a markdown file with content longer than 500 chars
        mock_github_instance = MagicMock()
        mock_github.return_value = mock_github_instance
        
        # Create content longer than 500 characters (approximately 1486 chars)
        test_content = '# Test Document\n\n' + ('This is a long test content. ' * 50)
        
        mock_github_instance.get_repository_contents.return_value = {
            'success': True,
            'contents': [{
                'type': 'file',
                'name': 'LONG_TEST.md',
                'path': 'LONG_TEST.md',
                'download_url': 'https://raw.githubusercontent.com/test/test/LONG_TEST.md',
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
        
        # Verify that insert was called with full content in description
        mock_collection.data.insert.assert_called_once()
        call_args = mock_collection.data.insert.call_args
        
        # Extract properties from the call
        properties = call_args.kwargs.get('properties') or call_args[1].get('properties')
        
        # Verify description contains full content, not truncated
        self.assertIn('description', properties)
        description = properties['description']
        
        # Check that description is the full content (stripped)
        expected_description = test_content.strip()
        self.assertEqual(description, expected_description,
                        f"Description should contain full content. Expected length: {len(expected_description)}, got: {len(description)}")
        
        # Verify it's longer than 500 chars (proving it's not truncated)
        self.assertGreater(len(description), 500,
                          f"Description should be longer than 500 chars to prove it's not truncated. Got: {len(description)}")
