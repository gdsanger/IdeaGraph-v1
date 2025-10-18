"""
Integration tests for ChromaDB synchronization with Item views
"""
from django.test import TestCase, Client
from unittest.mock import patch, Mock
from main.models import User, Item, Section, Tag, Settings


class ItemChromaIntegrationTest(TestCase):
    """Test ChromaDB integration with Item CRUD operations"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings
        self.settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='test-key-123',
            openai_api_base_url='https://api.openai.com/v1'
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
        
        # Create tag
        self.tag = Tag.objects.create(name='Test Tag', color='#3b82f6')
        
        self.client = Client()
        
        # Login user
        self.client.post('/login/', {
            'username': 'testuser',
            'password': 'Test@123'
        })
    
    @patch('core.services.chroma_sync_service.requests.post')
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_item_create_triggers_chroma_sync(self, mock_client, mock_post):
        """Test that creating an item triggers ChromaDB sync"""
        # Setup mocks
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        # Create item via view
        response = self.client.post('/items/create/', {
            'title': 'New Test Item',
            'description': 'Test description for sync',
            'status': 'new',
            'section': self.section.id,
            'tags': [self.tag.id]
        })
        
        # Check item was created
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Item.objects.filter(title='New Test Item').exists())
        
        # Verify ChromaDB sync was called
        mock_collection.add.assert_called_once()
    
    @patch('core.services.chroma_sync_service.requests.post')
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_item_update_triggers_chroma_sync(self, mock_client, mock_post):
        """Test that updating an item triggers ChromaDB sync"""
        # Setup mocks
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        # Create item first
        item = Item.objects.create(
            title='Test Item',
            description='Original description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        item.tags.add(self.tag)
        
        # Update item via view
        response = self.client.post(f'/items/{item.id}/edit/', {
            'title': 'Updated Title',
            'description': 'Updated description',
            'status': 'working',
            'section': self.section.id,
            'tags': [self.tag.id]
        })
        
        # Check item was updated
        self.assertEqual(response.status_code, 302)  # Redirect after success
        item.refresh_from_db()
        self.assertEqual(item.title, 'Updated Title')
        
        # Verify ChromaDB sync was called
        mock_collection.upsert.assert_called_once()
    
    @patch('core.services.chroma_sync_service.chromadb.PersistentClient')
    def test_item_delete_triggers_chroma_sync(self, mock_client):
        """Test that deleting an item triggers ChromaDB sync"""
        # Setup mocks
        mock_collection = Mock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        # Create item first
        item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        item_id = str(item.id)
        
        # Delete item via view
        response = self.client.post(f'/items/{item.id}/delete/')
        
        # Check item was deleted
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertFalse(Item.objects.filter(id=item_id).exists())
        
        # Verify ChromaDB sync was called
        mock_collection.delete.assert_called_once_with(ids=[item_id])
    
    def test_item_create_handles_chroma_sync_failure_gracefully(self):
        """Test that item creation succeeds even if ChromaDB sync fails"""
        # No mocks - let ChromaDB initialization fail
        
        # Create item via view
        response = self.client.post('/items/create/', {
            'title': 'New Test Item',
            'description': 'Test description',
            'status': 'new',
            'section': self.section.id,
            'tags': [self.tag.id]
        })
        
        # Check item was still created despite sync failure
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Item.objects.filter(title='New Test Item').exists())
