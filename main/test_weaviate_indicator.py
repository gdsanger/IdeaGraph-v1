"""
Tests for Weaviate Indicator API endpoints
"""
from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
from main.models import User, Item, Task, ItemFile, TaskFile, Settings, Section
import uuid


class WeaviateIndicatorAPITest(TestCase):
    """Test Weaviate Indicator API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create settings
        self.settings = Settings.objects.create(
            smtp_server='smtp.test.com',
            smtp_port=587,
            smtp_username='test@test.com',
            smtp_password='testpass',
            smtp_from_email='test@test.com',
            weaviate_cloud_enabled=False
        )
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            created_by=self.user
        )
        
        # Create test file
        self.item_file = ItemFile.objects.create(
            item=self.item,
            filename='test.pdf',
            file_size=1024,
            uploaded_by=self.user
        )
        
        self.client = Client()
        
    def login_user(self):
        """Helper to log in a user"""
        self.client.post('/login/', {
            'username': 'testuser',
            'password': 'Test@123'
        })
    
    @patch('main.api_views.WeaviateItemSyncService')
    def test_check_weaviate_status_exists(self, mock_service_class):
        """Test checking Weaviate status when object exists"""
        self.login_user()
        
        # Mock Weaviate service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        mock_collection = MagicMock()
        mock_service._client.collections.get.return_value = mock_collection
        
        mock_obj = MagicMock()
        mock_obj.uuid = self.item.id
        mock_obj.properties = {
            'title': 'Test Item',
            'description': 'Test description',
            'type': 'Item'
        }
        mock_collection.query.fetch_object_by_id.return_value = mock_obj
        
        response = self.client.get(f'/api/weaviate/item/{self.item.id}/status')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['exists'])
        self.assertIn('data', data)
    
    @patch('main.api_views.WeaviateItemSyncService')
    def test_check_weaviate_status_not_exists(self, mock_service_class):
        """Test checking Weaviate status when object doesn't exist"""
        self.login_user()
        
        # Mock Weaviate service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        mock_collection = MagicMock()
        mock_service._client.collections.get.return_value = mock_collection
        mock_collection.query.fetch_object_by_id.return_value = None
        
        response = self.client.get(f'/api/weaviate/item/{self.item.id}/status')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['exists'])
    
    def test_check_weaviate_status_unauthorized(self):
        """Test checking Weaviate status without authentication"""
        response = self.client.get(f'/api/weaviate/item/{self.item.id}/status')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Unauthorized')
    
    @patch('main.api_views.WeaviateItemSyncService')
    def test_add_item_to_weaviate(self, mock_service_class):
        """Test adding an item to Weaviate"""
        self.login_user()
        
        # Mock Weaviate service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.sync_create.return_value = {
            'success': True,
            'message': 'Item synced'
        }
        
        response = self.client.post(f'/api/weaviate/item/{self.item.id}/add')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('message', data)
        mock_service.sync_create.assert_called_once()
    
    @patch('main.api_views.WeaviateTaskSyncService')
    def test_add_task_to_weaviate(self, mock_service_class):
        """Test adding a task to Weaviate"""
        self.login_user()
        
        # Mock Weaviate service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.sync_create.return_value = {
            'success': True,
            'message': 'Task synced'
        }
        
        response = self.client.post(f'/api/weaviate/task/{self.task.id}/add')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('message', data)
        mock_service.sync_create.assert_called_once()
    
    def test_add_item_file_to_weaviate(self):
        """Test marking an item file for Weaviate sync"""
        self.login_user()
        
        response = self.client.post(f'/api/weaviate/item_file/{self.item_file.id}/add')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Check that file is marked as synced
        self.item_file.refresh_from_db()
        self.assertTrue(self.item_file.weaviate_synced)
    
    def test_add_to_weaviate_unauthorized(self):
        """Test adding to Weaviate without authentication"""
        response = self.client.post(f'/api/weaviate/item/{self.item.id}/add')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Unauthorized')
    
    def test_add_to_weaviate_not_found(self):
        """Test adding non-existent object to Weaviate"""
        self.login_user()
        
        fake_id = uuid.uuid4()
        response = self.client.post(f'/api/weaviate/item/{fake_id}/add')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Item not found')
    
    @patch('main.api_views.WeaviateItemSyncService')
    def test_get_weaviate_dump(self, mock_service_class):
        """Test getting Weaviate dump for an object"""
        self.login_user()
        
        # Mock Weaviate service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        mock_collection = MagicMock()
        mock_service._client.collections.get.return_value = mock_collection
        
        mock_obj = MagicMock()
        mock_obj.uuid = self.item.id
        mock_obj.properties = {
            'title': 'Test Item',
            'description': 'Test description',
            'type': 'Item',
            'createdAt': '2024-01-01T00:00:00Z'
        }
        mock_collection.query.fetch_object_by_id.return_value = mock_obj
        
        response = self.client.get(f'/api/weaviate/item/{self.item.id}/dump')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('dump', data)
        self.assertEqual(data['dump']['properties']['title'], 'Test Item')
    
    @patch('main.api_views.WeaviateItemSyncService')
    def test_get_weaviate_dump_not_found(self, mock_service_class):
        """Test getting Weaviate dump when object doesn't exist"""
        self.login_user()
        
        # Mock Weaviate service
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        mock_collection = MagicMock()
        mock_service._client.collections.get.return_value = mock_collection
        mock_collection.query.fetch_object_by_id.return_value = None
        
        response = self.client.get(f'/api/weaviate/item/{self.item.id}/dump')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Object not found in Weaviate')
    
    def test_get_weaviate_dump_unauthorized(self):
        """Test getting Weaviate dump without authentication"""
        response = self.client.get(f'/api/weaviate/item/{self.item.id}/dump')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Unauthorized')
