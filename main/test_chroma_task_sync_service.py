"""
Tests for ChromaTaskSyncService
"""
from django.test import TestCase
from unittest.mock import Mock, patch, MagicMock
from main.models import User, Item, Task, Section, Settings
from core.services.chroma_task_sync_service import ChromaTaskSyncService, ChromaTaskSyncServiceError


class ChromaTaskSyncServiceTest(TestCase):
    """Test ChromaTaskSyncService"""
    
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
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description for embedding',
            status='new',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_service_initialization_local(self, mock_client):
        """Test service initializes with local storage"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaTaskSyncService(self.settings)
        
        self.assertIsNotNone(service)
        mock_client.assert_called_once_with(path="./chroma_db")
        mock_client.return_value.get_or_create_collection.assert_called_once()
    
    @patch('core.services.chroma_task_sync_service.chromadb.HttpClient')
    def test_service_initialization_cloud(self, mock_client):
        """Test service initializes with cloud configuration"""
        # Update settings for cloud config
        self.settings.chroma_api_key = 'test-cloud-key'
        self.settings.chroma_database = 'https://api.trychroma.com/api/v1/databases/test-db'
        self.settings.chroma_tenant = 'test-tenant'
        self.settings.save()

        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        service = ChromaTaskSyncService(self.settings)

        self.assertIsNotNone(service)
        mock_client.assert_called_once()
        kwargs = mock_client.call_args.kwargs
        self.assertEqual(kwargs['host'], 'api.trychroma.com')
        self.assertTrue(kwargs['ssl'])
        self.assertEqual(kwargs['port'], 443)
        self.assertEqual(kwargs['tenant'], 'test-tenant')
        self.assertEqual(kwargs['database'], 'test-db')
        self.assertEqual(
            kwargs['headers'],
            {
                'Authorization': 'Bearer test-cloud-key',
                'X-Chroma-Token': 'test-cloud-key'
            }
        )
    
    def test_service_requires_settings(self):
        """Test service raises error without settings"""
        Settings.objects.all().delete()
        
        with self.assertRaises(ChromaTaskSyncServiceError) as context:
            ChromaTaskSyncService()
        
        self.assertIn('No settings found', str(context.exception))
    
    @patch('core.services.chroma_task_sync_service.requests.post')
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
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
        
        service = ChromaTaskSyncService(self.settings)
        embedding = service._generate_embedding("Test text")
        
        self.assertEqual(len(embedding), 1536)
        self.assertEqual(embedding[0], 0.1)
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_generate_embedding_empty_text(self, mock_client):
        """Test embedding generation with empty text returns zero vector"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaTaskSyncService(self.settings)
        embedding = service._generate_embedding("")
        
        self.assertEqual(len(embedding), 1536)
        self.assertEqual(embedding[0], 0.0)
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_generate_embedding_api_disabled(self, mock_client):
        """Test embedding generation when API is disabled"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        self.settings.openai_api_enabled = False
        self.settings.save()
        
        service = ChromaTaskSyncService(self.settings)
        embedding = service._generate_embedding("Test text")
        
        self.assertEqual(len(embedding), 1536)
        self.assertEqual(embedding[0], 0.0)
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_task_to_metadata(self, mock_client):
        """Test task metadata conversion"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaTaskSyncService(self.settings)
        metadata = service._task_to_metadata(self.task)
        
        self.assertEqual(metadata['id'], str(self.task.id))
        self.assertEqual(metadata['title'], self.task.title)
        self.assertEqual(metadata['item_id'], str(self.item.id))
        self.assertEqual(metadata['status'], self.task.status)
        self.assertEqual(metadata['owner'], str(self.user.id))
        self.assertEqual(metadata['owner_username'], self.user.username)
        self.assertIn('created_at', metadata)
        self.assertIn('updated_at', metadata)
    
    @patch('core.services.chroma_task_sync_service.requests.post')
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_sync_create(self, mock_client, mock_post):
        """Test syncing a new task to ChromaDB"""
        # Setup mocks
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        service = ChromaTaskSyncService(self.settings)
        result = service.sync_create(self.task)
        
        self.assertTrue(result['success'])
        self.assertIn('synced', result['message'])
        mock_collection.add.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_collection.add.call_args
        self.assertEqual(call_args[1]['ids'], [str(self.task.id)])
        self.assertEqual(len(call_args[1]['embeddings']), 1)
        self.assertEqual(call_args[1]['documents'], [self.task.description])
    
    @patch('core.services.chroma_task_sync_service.requests.post')
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_sync_update(self, mock_client, mock_post):
        """Test syncing an updated task to ChromaDB"""
        # Setup mocks
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        service = ChromaTaskSyncService(self.settings)
        
        # Update task
        self.task.description = 'Updated description'
        self.task.save()
        
        result = service.sync_update(self.task)
        
        self.assertTrue(result['success'])
        self.assertIn('updated', result['message'])
        mock_collection.upsert.assert_called_once()
        
        # Verify the call arguments
        call_args = mock_collection.upsert.call_args
        self.assertEqual(call_args[1]['ids'], [str(self.task.id)])
        self.assertEqual(len(call_args[1]['embeddings']), 1)
        self.assertEqual(call_args[1]['documents'], [self.task.description])
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_sync_delete(self, mock_client):
        """Test deleting a task from ChromaDB"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaTaskSyncService(self.settings)
        result = service.sync_delete(str(self.task.id))
        
        self.assertTrue(result['success'])
        self.assertIn('deleted', result['message'])
        mock_collection.delete.assert_called_once_with(ids=[str(self.task.id)])
    
    @patch('core.services.chroma_task_sync_service.requests.post')
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_search_similar(self, mock_client, mock_post):
        """Test searching for similar tasks"""
        # Setup mocks
        mock_collection = Mock()
        mock_collection.query.return_value = {
            'ids': [[str(self.task.id)]],
            'metadatas': [[{
                'id': str(self.task.id),
                'title': self.task.title,
                'status': self.task.status
            }]],
            'documents': [[self.task.description]],
            'distances': [[0.5]]
        }
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        service = ChromaTaskSyncService(self.settings)
        result = service.search_similar("Similar task query")
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['results']), 1)
        self.assertEqual(result['results'][0]['id'], str(self.task.id))
        self.assertEqual(result['results'][0]['metadata']['title'], self.task.title)
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_sync_create_collection_error(self, mock_client):
        """Test sync_create handles collection errors"""
        mock_collection = Mock()
        mock_collection.add.side_effect = Exception("Collection error")
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaTaskSyncService(self.settings)
        
        with self.assertRaises(ChromaTaskSyncServiceError) as context:
            service.sync_create(self.task)
        
        self.assertIn('Failed to sync task', str(context.exception))
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_sync_update_collection_error(self, mock_client):
        """Test sync_update handles collection errors"""
        mock_collection = Mock()
        mock_collection.upsert.side_effect = Exception("Collection error")
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaTaskSyncService(self.settings)
        
        with self.assertRaises(ChromaTaskSyncServiceError) as context:
            service.sync_update(self.task)
        
        self.assertIn('Failed to update task', str(context.exception))
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_sync_delete_collection_error(self, mock_client):
        """Test sync_delete handles collection errors"""
        mock_collection = Mock()
        mock_collection.delete.side_effect = Exception("Collection error")
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        service = ChromaTaskSyncService(self.settings)
        
        with self.assertRaises(ChromaTaskSyncServiceError) as context:
            service.sync_delete(str(self.task.id))
        
        self.assertIn('Failed to delete task', str(context.exception))
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_task_without_item(self, mock_client):
        """Test metadata conversion for task without item"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        # Create task without item
        task_no_item = Task.objects.create(
            title='Task No Item',
            description='Task without item',
            status='new',
            created_by=self.user,
            assigned_to=self.user
        )
        
        service = ChromaTaskSyncService(self.settings)
        metadata = service._task_to_metadata(task_no_item)
        
        self.assertEqual(metadata['item_id'], '')
    
    @patch('core.services.chroma_task_sync_service.chromadb.PersistentClient')
    def test_task_with_github_issue(self, mock_client):
        """Test metadata conversion for task with GitHub issue"""
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        # Update task with GitHub issue
        self.task.github_issue_id = 123
        self.task.save()
        
        service = ChromaTaskSyncService(self.settings)
        metadata = service._task_to_metadata(self.task)
        
        self.assertEqual(metadata['github_issue_id'], 123)
