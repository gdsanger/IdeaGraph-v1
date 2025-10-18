"""
Tests for ChromaItemSyncService
"""
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from main.models import User, Item, Section, Tag, Settings
from core.services.chroma_sync_service import ChromaItemSyncService, ChromaItemSyncServiceError


class ChromaItemSyncServiceTest(TestCase):
    """Test ChromaItemSyncService"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings
        self.settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='test-key-123',
            openai_api_base_url='https://api.openai.com/v1',
            chroma_api_key='',
            chroma_database='',
            chroma_tenant=''
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create tags
        self.tag1 = Tag.objects.create(name='Tag1', color='#3b82f6')
        self.tag2 = Tag.objects.create(name='Tag2', color='#ef4444')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description for embedding',
            status='new',
            section=self.section,
            created_by=self.user
        )
        self.item.tags.add(self.tag1, self.tag2)
    
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_service_initialization_local(self, mock_client):
        """Test service initializes with local storage"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaItemSyncService(self.settings)
        
        self.assertIsNotNone(service)
        mock_client.assert_called_once_with(path="./chroma_db")
        mock_client.return_value.get_or_create_collection.assert_called_once()
    
    @patch('core.services.chroma_sync_service.chromadb.Client')
    def test_service_initialization_cloud(self, mock_client):
        """Test service initializes with cloud configuration"""
        # Update settings for cloud config
        self.settings.chroma_api_key = 'test-cloud-key'
        self.settings.chroma_database = 'test-db'
        self.settings.chroma_tenant = 'test-tenant'
        self.settings.save()
        
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaItemSyncService(self.settings)
        
        self.assertIsNotNone(service)
        mock_client.assert_called_once()
    
    def test_service_requires_settings(self):
        """Test service raises error without settings"""
        Settings.objects.all().delete()
        
        with self.assertRaises(ChromaItemSyncServiceError) as context:
            ChromaItemSyncService()
        
        self.assertIn('No settings found', str(context.exception))
    
    @patch('core.services.chroma_sync_service.requests.post')
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_generate_embedding_success(self, mock_client, mock_post):
        """Test embedding generation with OpenAI API"""
        # Setup mocks
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        service = ChromaItemSyncService(self.settings)
        embedding = service._generate_embedding('test text')
        
        self.assertEqual(len(embedding), 1536)
        mock_post.assert_called_once()
    
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_generate_embedding_no_api_key(self, mock_client):
        """Test embedding generation without API key returns zero vector"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        # Disable OpenAI API
        self.settings.openai_api_enabled = False
        self.settings.save()
        
        service = ChromaItemSyncService(self.settings)
        embedding = service._generate_embedding('test text')
        
        # Should return zero vector
        self.assertEqual(len(embedding), 1536)
        self.assertEqual(embedding, [0.0] * 1536)
    
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_generate_embedding_empty_text(self, mock_client):
        """Test embedding generation with empty text"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaItemSyncService(self.settings)
        embedding = service._generate_embedding('')
        
        # Should return zero vector for empty text
        self.assertEqual(len(embedding), 1536)
        self.assertEqual(embedding, [0.0] * 1536)
    
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_item_to_metadata(self, mock_client):
        """Test conversion of Item to metadata dictionary"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaItemSyncService(self.settings)
        metadata = service._item_to_metadata(self.item)
        
        self.assertEqual(metadata['id'], str(self.item.id))
        self.assertEqual(metadata['title'], 'Test Item')
        self.assertEqual(metadata['section'], str(self.section.id))
        self.assertEqual(metadata['section_name'], 'Test Section')
        self.assertIn('Tag1', metadata['tags'])
        self.assertIn('Tag2', metadata['tags'])
        self.assertEqual(metadata['status'], 'new')
        self.assertEqual(metadata['owner'], str(self.user.id))
        self.assertEqual(metadata['owner_username'], 'testuser')
    
    @patch('core.services.chroma_sync_service.requests.post')
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_sync_create_success(self, mock_client, mock_post):
        """Test successful item creation sync"""
        # Setup mocks
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        service = ChromaItemSyncService(self.settings)
        result = service.sync_create(self.item)
        
        self.assertTrue(result['success'])
        self.assertIn('synced', result['message'])
        mock_collection.add.assert_called_once()
        
        # Check call arguments
        call_args = mock_collection.add.call_args
        self.assertEqual(call_args.kwargs['ids'], [str(self.item.id)])
        self.assertEqual(call_args.kwargs['documents'], [self.item.description])
    
    @patch('core.services.chroma_sync_service.requests.post')
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_sync_update_success(self, mock_client, mock_post):
        """Test successful item update sync"""
        # Setup mocks
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        service = ChromaItemSyncService(self.settings)
        
        # Update item
        self.item.description = 'Updated description'
        self.item.save()
        
        result = service.sync_update(self.item)
        
        self.assertTrue(result['success'])
        self.assertIn('updated', result['message'])
        mock_collection.upsert.assert_called_once()
        
        # Check call arguments
        call_args = mock_collection.upsert.call_args
        self.assertEqual(call_args.kwargs['ids'], [str(self.item.id)])
        self.assertEqual(call_args.kwargs['documents'], ['Updated description'])
    
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_sync_delete_success(self, mock_client):
        """Test successful item deletion sync"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaItemSyncService(self.settings)
        item_id = str(self.item.id)
        
        result = service.sync_delete(item_id)
        
        self.assertTrue(result['success'])
        self.assertIn('deleted', result['message'])
        mock_collection.delete.assert_called_once_with(ids=[item_id])
    
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_sync_create_collection_error(self, mock_client):
        """Test sync_create handles collection errors"""
        mock_collection = Mock()
        mock_collection.add.side_effect = Exception('Collection error')
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaItemSyncService(self.settings)
        
        with self.assertRaises(ChromaItemSyncServiceError) as context:
            service.sync_create(self.item)
        
        self.assertIn('Failed to sync item', str(context.exception))
    
    @patch('core.services.chroma_sync_service.requests.post')
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_search_similar_success(self, mock_client, mock_post):
        """Test successful similarity search"""
        # Setup mocks
        mock_collection = Mock()
        mock_collection.query.return_value = {
            'ids': [[str(self.item.id)]],
            'metadatas': [[{'title': 'Test Item', 'status': 'new'}]],
            'documents': [['Test description']],
            'distances': [[0.5]]
        }
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        service = ChromaItemSyncService(self.settings)
        result = service.search_similar('test query', n_results=5)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['results']), 1)
        self.assertEqual(result['results'][0]['id'], str(self.item.id))
        mock_collection.query.assert_called_once()
    
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_item_without_section_metadata(self, mock_client):
        """Test metadata generation for item without section"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        # Create item without section
        item_no_section = Item.objects.create(
            title='No Section Item',
            description='Test',
            status='new',
            created_by=self.user
        )
        
        service = ChromaItemSyncService(self.settings)
        metadata = service._item_to_metadata(item_no_section)
        
        self.assertEqual(metadata['section'], '')
        self.assertEqual(metadata['section_name'], '')
    
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_item_without_tags_metadata(self, mock_client):
        """Test metadata generation for item without tags"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        # Create item without tags
        item_no_tags = Item.objects.create(
            title='No Tags Item',
            description='Test',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        service = ChromaItemSyncService(self.settings)
        metadata = service._item_to_metadata(item_no_tags)
        
        self.assertEqual(metadata['tags'], '')
