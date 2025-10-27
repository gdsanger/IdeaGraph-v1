"""
Tests for Weaviate Maintenance Service and API endpoints
"""
from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
from main.models import User, Settings
import uuid
import json


class WeaviateMaintenanceServiceTest(TestCase):
    """Test Weaviate Maintenance Service"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_local')
    def test_initialize_client_local(self, mock_connect):
        """Test initializing Weaviate client for local instance"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        service = WeaviateMaintenanceService(self.settings)
        
        self.assertIsNotNone(service._client)
        mock_connect.assert_called_once_with(host="localhost", port=8081)
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_weaviate_cloud')
    def test_initialize_client_cloud(self, mock_connect):
        """Test initializing Weaviate client for cloud instance"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        # Update settings for cloud
        self.settings.weaviate_cloud_enabled = True
        self.settings.weaviate_url = 'https://test.weaviate.network'
        self.settings.weaviate_api_key = 'test-api-key'
        self.settings.save()
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        service = WeaviateMaintenanceService(self.settings)
        
        self.assertIsNotNone(service._client)
        mock_connect.assert_called_once()
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_local')
    def test_get_meta(self, mock_connect):
        """Test getting Weaviate metadata"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.get_meta.return_value = {
            'version': '1.24.0',
            'hostname': 'test-node-1'
        }
        
        service = WeaviateMaintenanceService(self.settings)
        result = service.get_meta()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['version'], '1.24.0')
        self.assertEqual(result['hostname'], 'test-node-1')
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_local')
    def test_get_schema(self, mock_connect):
        """Test getting Weaviate schema"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.collections.list_all.return_value = {
            'KnowledgeObject': MagicMock(),
            'TestCollection': MagicMock()
        }
        
        service = WeaviateMaintenanceService(self.settings)
        result = service.get_schema()
        
        self.assertTrue(result['success'])
        self.assertIn('schema', result)
        self.assertIn('collections', result)
        self.assertEqual(len(result['collections']), 2)
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_local')
    def test_search_object_found(self, mock_connect):
        """Test searching for an object that exists"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        mock_collection = MagicMock()
        mock_client.collections.get.return_value = mock_collection
        
        test_uuid = uuid.uuid4()
        mock_obj = MagicMock()
        mock_obj.uuid = test_uuid
        mock_obj.properties = {
            'title': 'Test Object',
            'type': 'Item',
            'description': 'Test description'
        }
        mock_collection.query.fetch_object_by_id.return_value = mock_obj
        
        service = WeaviateMaintenanceService(self.settings)
        result = service.search_object(str(test_uuid))
        
        self.assertTrue(result['success'])
        self.assertTrue(result['found'])
        self.assertIsNotNone(result['object'])
        self.assertEqual(result['object']['properties']['title'], 'Test Object')
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_local')
    def test_search_object_not_found(self, mock_connect):
        """Test searching for an object that doesn't exist"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        mock_collection = MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_collection.query.fetch_object_by_id.return_value = None
        
        service = WeaviateMaintenanceService(self.settings)
        result = service.search_object(str(uuid.uuid4()))
        
        self.assertTrue(result['success'])
        self.assertFalse(result['found'])
        self.assertIsNone(result['object'])
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_local')
    def test_export_schema(self, mock_connect):
        """Test exporting schema"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        mock_client.collections.list_all.return_value = {'KnowledgeObject': MagicMock()}
        mock_client.get_meta.return_value = {'version': '1.24.0', 'hostname': 'test'}
        
        service = WeaviateMaintenanceService(self.settings)
        result = service.export_schema()
        
        self.assertTrue(result['success'])
        self.assertIn('schema', result)
        self.assertIn('export_time', result)
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_local')
    def test_restore_schema_no_confirm(self, mock_connect):
        """Test restore schema without confirmation"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        service = WeaviateMaintenanceService(self.settings)
        result = service.restore_schema({'test': 'data'}, confirm=False)
        
        self.assertFalse(result['success'])
        self.assertIn('confirmation', result['error'].lower())
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_local')
    def test_rebuild_index(self, mock_connect):
        """Test rebuilding index"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        service = WeaviateMaintenanceService(self.settings)
        result = service.rebuild_index()
        
        self.assertTrue(result['success'])
        self.assertIn('message', result)
    
    @patch('core.services.weaviate_maintenance_service.weaviate.connect_to_local')
    def test_get_collection_stats(self, mock_connect):
        """Test getting collection statistics"""
        from core.services.weaviate_maintenance_service import WeaviateMaintenanceService
        
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        mock_collection = MagicMock()
        mock_client.collections.get.return_value = mock_collection
        
        # Mock objects response
        mock_obj1 = MagicMock()
        mock_obj1.properties = {'type': 'Item'}
        mock_obj2 = MagicMock()
        mock_obj2.properties = {'type': 'Task'}
        mock_obj3 = MagicMock()
        mock_obj3.properties = {'type': 'Item'}
        
        mock_response = MagicMock()
        mock_response.objects = [mock_obj1, mock_obj2, mock_obj3]
        mock_collection.query.fetch_objects.return_value = mock_response
        
        service = WeaviateMaintenanceService(self.settings)
        result = service.get_collection_stats()
        
        self.assertTrue(result['success'])
        self.assertIn('stats', result)
        self.assertEqual(result['stats']['total_objects'], 3)
        self.assertEqual(result['stats']['objects_by_type']['Item'], 2)
        self.assertEqual(result['stats']['objects_by_type']['Task'], 1)


class WeaviateMaintenanceAPITest(TestCase):
    """Test Weaviate Maintenance API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create admin user
        self.admin = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        self.admin.set_password('Admin@123')
        self.admin.save()
        
        # Create regular user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create settings
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
        
        self.client = Client()
    
    def login_admin(self):
        """Helper to log in admin user"""
        self.client.post('/login/', {
            'username': 'admin',
            'password': 'Admin@123'
        })
    
    def login_user(self):
        """Helper to log in regular user"""
        self.client.post('/login/', {
            'username': 'testuser',
            'password': 'Test@123'
        })
    
    @patch('core.services.weaviate_maintenance_service.WeaviateMaintenanceService')
    def test_api_weaviate_status_success(self, mock_service_class):
        """Test getting Weaviate status as admin"""
        self.login_admin()
        
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_meta.return_value = {
            'success': True,
            'meta': {'version': '1.24.0', 'hostname': 'test'},
            'version': '1.24.0',
            'hostname': 'test'
        }
        mock_service.get_collection_stats.return_value = {
            'success': True,
            'stats': {'total_objects': 100}
        }
        
        response = self.client.get('/api/weaviate/status')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('meta', data)
        self.assertIn('version', data)
        self.assertIn('stats', data)
    
    def test_api_weaviate_status_unauthorized(self):
        """Test getting Weaviate status without authentication"""
        response = self.client.get('/api/weaviate/status')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Unauthorized')
    
    def test_api_weaviate_status_forbidden(self):
        """Test getting Weaviate status as regular user"""
        self.login_user()
        
        response = self.client.get('/api/weaviate/status')
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Admin', data['error'])
    
    @patch('core.services.weaviate_maintenance_service.WeaviateMaintenanceService')
    def test_api_weaviate_rebuild_success(self, mock_service_class):
        """Test rebuilding index as admin"""
        self.login_admin()
        
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.rebuild_index.return_value = {
            'success': True,
            'message': 'Index rebuild completed'
        }
        
        response = self.client.post('/api/weaviate/rebuild')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('message', data)
    
    def test_api_weaviate_rebuild_unauthorized(self):
        """Test rebuilding index without authentication"""
        response = self.client.post('/api/weaviate/rebuild')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
    
    @patch('core.services.weaviate_maintenance_service.WeaviateMaintenanceService')
    def test_api_weaviate_schema_export_success(self, mock_service_class):
        """Test exporting schema as admin"""
        self.login_admin()
        
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.export_schema.return_value = {
            'success': True,
            'schema': {'collections': ['KnowledgeObject']},
            'export_time': '2024-01-01T00:00:00'
        }
        
        response = self.client.post('/api/weaviate/schema/export')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('schema', data)
        self.assertIn('export_time', data)
    
    @patch('core.services.weaviate_maintenance_service.WeaviateMaintenanceService')
    def test_api_weaviate_schema_restore_no_confirm(self, mock_service_class):
        """Test restoring schema without confirmation"""
        self.login_admin()
        
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.restore_schema.return_value = {
            'success': False,
            'error': 'Schema restore requires confirmation'
        }
        
        response = self.client.post(
            '/api/weaviate/schema/restore',
            data=json.dumps({
                'schema': {'test': 'data'},
                'confirm': False
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_api_weaviate_schema_restore_no_schema(self):
        """Test restoring schema without schema data"""
        self.login_admin()
        
        response = self.client.post(
            '/api/weaviate/schema/restore',
            data=json.dumps({'confirm': True}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Schema data required', data['error'])
    
    @patch('core.services.weaviate_maintenance_service.WeaviateMaintenanceService')
    def test_api_weaviate_search_object_found(self, mock_service_class):
        """Test searching for an object that exists"""
        self.login_admin()
        
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        test_uuid = uuid.uuid4()
        mock_service.search_object.return_value = {
            'success': True,
            'found': True,
            'object': {
                'uuid': str(test_uuid),
                'properties': {'title': 'Test'}
            }
        }
        
        response = self.client.get(f'/api/weaviate/object/{test_uuid}')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['found'])
        self.assertIsNotNone(data['object'])
    
    @patch('core.services.weaviate_maintenance_service.WeaviateMaintenanceService')
    def test_api_weaviate_search_object_not_found(self, mock_service_class):
        """Test searching for an object that doesn't exist"""
        self.login_admin()
        
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.search_object.return_value = {
            'success': True,
            'found': False,
            'object': None
        }
        
        response = self.client.get(f'/api/weaviate/object/{uuid.uuid4()}')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['found'])
    
    def test_api_weaviate_search_object_unauthorized(self):
        """Test searching for an object without authentication"""
        response = self.client.get(f'/api/weaviate/object/{uuid.uuid4()}')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
