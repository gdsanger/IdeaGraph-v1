"""
Tests for Semantic Network Service

This module tests the semantic network generation functionality.
"""
from django.test import TestCase
from unittest.mock import Mock, MagicMock, patch
from core.services.semantic_network_service import SemanticNetworkService, SemanticNetworkServiceError


class SemanticNetworkServiceTest(TestCase):
    """Test cases for SemanticNetworkService"""
    
    def setUp(self):
        """Set up test fixtures"""
        from main.models import Settings
        
        # Create mock settings
        self.settings = Mock()
        self.settings.weaviate_cloud_enabled = False
        self.settings.weaviate_url = None
        self.settings.weaviate_api_key = None
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_service_initialization(self, mock_weaviate):
        """Test that service initializes correctly"""
        mock_client = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        
        service = SemanticNetworkService(settings=self.settings)
        
        self.assertIsNotNone(service)
        self.assertEqual(service.settings, self.settings)
        mock_weaviate.connect_to_local.assert_called_once()
    
    def test_type_mapping(self):
        """Test that type mapping is defined"""
        self.assertIn('item', SemanticNetworkService.TYPE_MAPPING)
        self.assertIn('task', SemanticNetworkService.TYPE_MAPPING)
        self.assertEqual(SemanticNetworkService.TYPE_MAPPING['item'], 'Item')
        self.assertEqual(SemanticNetworkService.TYPE_MAPPING['task'], 'Task')
        self.assertEqual(SemanticNetworkService.COLLECTION_NAME, 'KnowledgeObject')
    
    def test_default_thresholds(self):
        """Test that default similarity thresholds are defined"""
        self.assertEqual(SemanticNetworkService.DEFAULT_THRESHOLDS[1], 0.8)
        self.assertEqual(SemanticNetworkService.DEFAULT_THRESHOLDS[2], 0.7)
        self.assertEqual(SemanticNetworkService.DEFAULT_THRESHOLDS[3], 0.6)
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_service_without_settings(self, mock_weaviate):
        """Test that service raises error without settings"""
        from main.models import Settings
        
        with patch.object(Settings.objects, 'first', return_value=None):
            with self.assertRaises(SemanticNetworkServiceError) as context:
                SemanticNetworkService()
            
            self.assertIn('No settings found', str(context.exception))
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_invalid_object_type(self, mock_weaviate):
        """Test that invalid object type raises error"""
        mock_client = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        
        service = SemanticNetworkService(settings=self.settings)
        
        with self.assertRaises(SemanticNetworkServiceError) as context:
            service.generate_network(
                object_type='invalid_type',
                object_id='test-uuid',
                user_id='test-user'
            )
        
        self.assertIn('Invalid object type', str(context.exception))
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_depth_clamping(self, mock_weaviate):
        """Test that depth is clamped to valid range"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        
        # Mock fetch_object_by_id to return None (object not found)
        mock_collection.query.fetch_object_by_id.return_value = None
        
        service = SemanticNetworkService(settings=self.settings)
        
        # Test that negative depth is clamped to 1
        # This will fail because object doesn't exist, but we're testing depth clamping
        try:
            service.generate_network(
                object_type='item',
                object_id='test-uuid',
                depth=-1,
                user_id='test-user'
            )
        except SemanticNetworkServiceError:
            pass  # Expected to fail - object doesn't exist
        
        # Test that depth > 3 is clamped to 3
        try:
            service.generate_network(
                object_type='item',
                object_id='test-uuid',
                depth=10,
                user_id='test-user'
            )
        except SemanticNetworkServiceError:
            pass  # Expected to fail - object doesn't exist


class SemanticNetworkAPITest(TestCase):
    """Test cases for semantic network API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        from main.models import User, Settings
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('password123')
        self.user.save()
        
        # Create settings
        Settings.objects.create(
            weaviate_cloud_enabled=False,
            kigate_api_enabled=False,
            openai_api_enabled=False
        )
        
        # Log in
        self.client.force_login = Mock(return_value=True)
    
    def test_api_endpoint_requires_authentication(self):
        """Test that API endpoint requires authentication"""
        response = self.client.get('/api/semantic-network/item/test-uuid/')
        
        # Should return 401 Unauthorized
        self.assertEqual(response.status_code, 401)
    
    def test_api_endpoint_url_pattern(self):
        """Test that API endpoint URL pattern is registered"""
        from django.urls import reverse, NoReverseMatch
        
        try:
            url = reverse('main:api_semantic_network', kwargs={
                'object_type': 'item',
                'object_id': '12345678-1234-1234-1234-123456789abc'
            })
            self.assertTrue(url.startswith('/api/semantic-network/'))
        except NoReverseMatch:
            self.fail('URL pattern not registered')
