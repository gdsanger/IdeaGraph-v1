"""
Tests for Weaviate Sync Service - itemId field verification

This test ensures that files uploaded for tasks belonging to items
correctly store the itemId field in Weaviate KnowledgeObject.
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock, call
from core.services.weaviate_sync_service import (
    WeaviateItemSyncService,
    WeaviateItemSyncServiceError
)
from main.models import Settings


class WeaviateSyncItemIdTestCase(TestCase):
    """Test suite for itemId field in Weaviate sync"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
    
    def _get_insert_properties(self, mock_data):
        """
        Helper method to extract properties from insert call
        
        Args:
            mock_data: Mocked collection.data object
            
        Returns:
            dict: Properties passed to insert()
        """
        call_args = mock_data.insert.call_args
        call_kwargs = call_args.kwargs if hasattr(call_args, 'kwargs') else call_args[1]
        return call_kwargs['properties']
    
    @patch('core.services.weaviate_sync_service.weaviate.connect_to_local')
    def test_sync_knowledge_object_with_item_id_uses_itemId_field(self, mock_connect):
        """Test that sync_knowledge_object stores item_id as itemId property"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        
        # Create service
        service = WeaviateItemSyncService(self.settings)
        
        # Sample metadata with item_id (as passed from task_file_service)
        metadata = {
            'task_id': 'task-123',
            'task_title': 'Test Task',
            'item_id': 'item-456',
            'item_title': 'Test Item',
            'filename': 'test.txt',
            'file_id': 'file-789',
            'content_type': 'text/plain',
            'object_type': 'task_file'
        }
        
        # Sync knowledge object
        result = service.sync_knowledge_object(
            title='Test File',
            content='Test content',
            metadata=metadata
        )
        
        # Verify insert was called
        self.assertTrue(result['success'])
        mock_data.insert.assert_called_once()
        
        # Get the properties passed to insert
        properties = self._get_insert_properties(mock_data)
        
        # The key assertion: itemId should be present, not item_id
        self.assertIn('itemId', properties, 
                     "itemId field must be present in Weaviate properties")
        self.assertNotIn('item_id', properties,
                        "item_id should not be used, use itemId instead")
        self.assertEqual(properties['itemId'], 'item-456',
                        "itemId should contain the item ID from metadata")
    
    @patch('core.services.weaviate_sync_service.weaviate.connect_to_local')
    def test_sync_knowledge_object_without_item_id_omits_itemId(self, mock_connect):
        """Test that sync_knowledge_object omits itemId when item_id not in metadata"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        
        # Create service
        service = WeaviateItemSyncService(self.settings)
        
        # Sample metadata without item_id (e.g., standalone task file)
        metadata = {
            'task_id': 'task-123',
            'task_title': 'Test Task',
            'filename': 'test.txt',
            'file_id': 'file-789',
            'content_type': 'text/plain',
            'object_type': 'task_file'
        }
        
        # Sync knowledge object
        result = service.sync_knowledge_object(
            title='Test File',
            content='Test content',
            metadata=metadata
        )
        
        # Verify insert was called
        self.assertTrue(result['success'])
        mock_data.insert.assert_called_once()
        
        # Get the properties passed to insert
        properties = self._get_insert_properties(mock_data)
        
        # Verify that neither itemId nor item_id is present
        self.assertNotIn('itemId', properties,
                        "itemId should not be present when item_id not in metadata")
        self.assertNotIn('item_id', properties,
                        "item_id should not be present when item_id not in metadata")
    
    @patch('core.services.weaviate_sync_service.weaviate.connect_to_local')
    def test_sync_knowledge_object_includes_all_custom_fields(self, mock_connect):
        """Test that sync_knowledge_object includes all custom metadata fields"""
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        
        # Create service
        service = WeaviateItemSyncService(self.settings)
        
        # Complete metadata with all custom fields
        metadata = {
            'task_id': 'task-123',
            'task_title': 'Test Task',
            'item_id': 'item-456',
            'item_title': 'Test Item',
            'filename': 'document.pdf',
            'file_id': 'file-789',
            'content_type': 'application/pdf',
            'object_type': 'task_file',
            'section': 'Development',
            'owner': 'testuser',
            'status': 'active',
            'tags': ['tag1', 'tag2']
        }
        
        # Sync knowledge object
        result = service.sync_knowledge_object(
            title='Document',
            content='Document content',
            metadata=metadata
        )
        
        # Verify insert was called
        self.assertTrue(result['success'])
        mock_data.insert.assert_called_once()
        
        # Get the properties passed to insert
        properties = self._get_insert_properties(mock_data)
        
        # Verify all expected fields are present
        self.assertEqual(properties['task_id'], 'task-123')
        self.assertEqual(properties['task_title'], 'Test Task')
        self.assertEqual(properties['itemId'], 'item-456')  # Key field
        self.assertEqual(properties['item_title'], 'Test Item')
        self.assertEqual(properties['filename'], 'document.pdf')
        self.assertEqual(properties['file_id'], 'file-789')
        self.assertEqual(properties['content_type'], 'application/pdf')
        self.assertEqual(properties['type'], 'task_file')
        self.assertEqual(properties['title'], 'Document')
        self.assertEqual(properties['description'], 'Document content')
