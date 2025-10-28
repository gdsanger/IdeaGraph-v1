"""
Tests for Weaviate GitHub Issue Sync Service - Upsert functionality
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock, call
from core.services.weaviate_github_issue_sync_service import (
    WeaviateGitHubIssueSyncService,
    WeaviateGitHubIssueSyncServiceError
)
from main.models import Settings


class WeaviateGitHubIssueSyncUpsertTestCase(TestCase):
    """Test suite for GitHub Issue sync upsert functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
        
        # Sample GitHub issue data
        self.sample_issue = {
            'number': 221,
            'title': 'Test Issue',
            'body': 'Test issue body',
            'state': 'open',
            'html_url': 'https://github.com/test/repo/issues/221',
            'created_at': '2025-10-21T10:00:00Z',
            'user': {
                'login': 'testuser'
            }
        }
        
        # Sample PR data
        self.sample_pr = {
            'number': 222,
            'title': 'Test PR',
            'body': 'Test PR body',
            'state': 'open',
            'html_url': 'https://github.com/test/repo/pull/222',
            'created_at': '2025-10-21T11:00:00Z',
            'user': {
                'login': 'prauthor'
            }
        }
    
    @patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_local')
    def test_sync_issue_inserts_when_not_exists(self, mock_connect):
        """Test that sync_issue_to_weaviate inserts when object doesn't exist"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_data.exists.return_value = False  # Object doesn't exist
        
        # Create service
        service = WeaviateGitHubIssueSyncService(self.settings)
        
        # Sync issue
        result = service.sync_issue_to_weaviate(self.sample_issue)
        
        # Verify insert was called
        self.assertTrue(result['success'])
        mock_data.exists.assert_called_once()
        mock_data.insert.assert_called_once()
        mock_data.update.assert_not_called()
    
    @patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_local')
    def test_sync_issue_updates_when_exists(self, mock_connect):
        """Test that sync_issue_to_weaviate updates when object exists"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_data.exists.return_value = True  # Object exists
        
        # Create service
        service = WeaviateGitHubIssueSyncService(self.settings)
        
        # Sync issue
        result = service.sync_issue_to_weaviate(self.sample_issue)
        
        # Verify update was called, not insert
        self.assertTrue(result['success'])
        mock_data.exists.assert_called_once()
        mock_data.update.assert_called_once()
        mock_data.insert.assert_not_called()
    
    @patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_local')
    def test_sync_pr_inserts_when_not_exists(self, mock_connect):
        """Test that sync_pull_request_to_weaviate inserts when object doesn't exist"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_data.exists.return_value = False  # Object doesn't exist
        
        # Create service
        service = WeaviateGitHubIssueSyncService(self.settings)
        
        # Sync PR
        result = service.sync_pull_request_to_weaviate(self.sample_pr)
        
        # Verify insert was called
        self.assertTrue(result['success'])
        mock_data.exists.assert_called_once()
        mock_data.insert.assert_called_once()
        mock_data.update.assert_not_called()
    
    @patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_local')
    def test_sync_pr_updates_when_exists(self, mock_connect):
        """Test that sync_pull_request_to_weaviate updates when object exists"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_data.exists.return_value = True  # Object exists
        
        # Create service
        service = WeaviateGitHubIssueSyncService(self.settings)
        
        # Sync PR
        result = service.sync_pull_request_to_weaviate(self.sample_pr)
        
        # Verify update was called, not insert
        self.assertTrue(result['success'])
        mock_data.exists.assert_called_once()
        mock_data.update.assert_called_once()
        mock_data.insert.assert_not_called()
    
    @patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_local')
    def test_sync_issue_uses_deterministic_uuid(self, mock_connect):
        """Test that sync generates deterministic UUID based on issue URL"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_data.exists.return_value = False
        
        # Create service
        service = WeaviateGitHubIssueSyncService(self.settings)
        
        # Sync same issue twice
        result1 = service.sync_issue_to_weaviate(self.sample_issue)
        result2 = service.sync_issue_to_weaviate(self.sample_issue)
        
        # Both should generate same UUID
        self.assertEqual(result1['uuid'], result2['uuid'])
    
    @patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_local')
    def test_sync_issue_with_custom_uuid(self, mock_connect):
        """Test that sync respects custom UUID if provided"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_data.exists.return_value = False
        
        # Create service
        service = WeaviateGitHubIssueSyncService(self.settings)
        
        # Sync with custom UUID
        custom_uuid = '12345678-1234-5678-1234-567812345678'
        result = service.sync_issue_to_weaviate(self.sample_issue, uuid=custom_uuid)
        
        # Should use provided UUID
        self.assertEqual(result['uuid'], custom_uuid)
        
        # Verify exists was called with the custom UUID
        mock_data.exists.assert_called_once_with(custom_uuid)
    
    @patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_local')
    def test_sync_issue_handles_references(self, mock_connect):
        """Test that sync properly includes task and item IDs in properties"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_data.exists.return_value = False
        
        # Create mock task and item
        mock_task = MagicMock()
        mock_task.id = 'task-123'
        mock_item = MagicMock()
        mock_item.id = 'item-456'
        
        # Create service
        service = WeaviateGitHubIssueSyncService(self.settings)
        
        # Sync with task and item
        result = service.sync_issue_to_weaviate(
            self.sample_issue,
            task=mock_task,
            item=mock_item
        )
        
        # Verify success
        self.assertTrue(result['success'])
        
        # Verify insert was called with properties including taskId and itemId
        mock_data.insert.assert_called_once()
        call_kwargs = mock_data.insert.call_args[1]
        self.assertIn('taskId', call_kwargs['properties'])
        self.assertEqual(call_kwargs['properties']['taskId'], 'task-123')
        self.assertIn('itemId', call_kwargs['properties'])
        self.assertEqual(call_kwargs['properties']['itemId'], 'item-456')
    
    @patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_local')
    def test_sync_continues_on_insert_success(self, mock_connect):
        """Test that sync completes successfully with task reference"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_data.exists.return_value = False
        
        # Create mock task
        mock_task = MagicMock()
        mock_task.id = 'task-123'
        
        # Create service
        service = WeaviateGitHubIssueSyncService(self.settings)
        
        # Sync with task - should succeed
        result = service.sync_issue_to_weaviate(self.sample_issue, task=mock_task)
        
        # Should still succeed
        self.assertTrue(result['success'])
