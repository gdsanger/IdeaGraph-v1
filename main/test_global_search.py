"""
Tests for Global Search functionality
"""
from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
from main.models import User, Settings
from main.auth_utils import generate_jwt_token
import json


class GlobalSearchAPITest(TestCase):
    """Test Global Search API endpoint"""
    
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
        
        # Create settings with correct fields
        self.settings = Settings.objects.create(
            openai_api_enabled=False,
            weaviate_cloud_enabled=False
        )
        
        # Generate auth token
        self.token = generate_jwt_token(self.user)
        
        # Set up client
        self.client = Client()
    
    def test_search_requires_authentication(self):
        """Test that search endpoint requires authentication"""
        response = self.client.get('/api/search?query=test')
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Authentication required', data['error'])
    
    def test_search_requires_query_parameter(self):
        """Test that search endpoint requires query parameter"""
        response = self.client.get(
            '/api/search',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Query parameter is required', data['error'])
    
    @patch('core.services.weaviate_search_service.weaviate.connect_to_local')
    def test_search_returns_results(self, mock_weaviate_connect):
        """Test that search returns results successfully"""
        # Mock Weaviate client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        
        # Mock search response
        mock_obj = MagicMock()
        mock_obj.uuid = 'test-uuid-123'
        mock_obj.properties = {
            'type': 'Item',
            'title': 'Test Item',
            'description': 'Test description for the item',
            'url': '/items/test-uuid-123/',
            'owner': 'testuser',
            'section': 'Test Section',
            'status': 'new',
            'tags': ['test', 'search']
        }
        mock_obj.metadata = MagicMock()
        mock_obj.metadata.distance = 0.2
        mock_obj.metadata.certainty = 0.9
        
        mock_response = MagicMock()
        mock_response.objects = [mock_obj]
        
        mock_collection.query.near_text.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection
        mock_weaviate_connect.return_value = mock_client
        
        # Perform search
        response = self.client.get(
            '/api/search?query=test',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['query'], 'test')
        self.assertEqual(data['total'], 1)
        self.assertEqual(len(data['results']), 1)
        
        result = data['results'][0]
        self.assertEqual(result['id'], 'test-uuid-123')
        self.assertEqual(result['type'], 'Item')
        self.assertEqual(result['title'], 'Test Item')
        self.assertEqual(result['relevance'], 0.9)
        self.assertEqual(result['url'], '/items/test-uuid-123/')
    
    @patch('core.services.weaviate_search_service.weaviate.connect_to_local')
    def test_search_with_type_filter(self, mock_weaviate_connect):
        """Test search with object type filtering"""
        # Mock Weaviate client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        
        mock_response = MagicMock()
        mock_response.objects = []
        
        mock_collection.query.near_text.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection
        mock_weaviate_connect.return_value = mock_client
        
        # Perform search with type filter
        response = self.client.get(
            '/api/search?query=test&types=Item,Task',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 0)
        self.assertEqual(len(data['results']), 0)
    
    @patch('core.services.weaviate_search_service.weaviate.connect_to_local')
    def test_search_with_limit_parameter(self, mock_weaviate_connect):
        """Test search with custom limit"""
        # Mock Weaviate client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        
        mock_response = MagicMock()
        mock_response.objects = []
        
        mock_collection.query.near_text.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection
        mock_weaviate_connect.return_value = mock_client
        
        # Perform search with limit
        response = self.client.get(
            '/api/search?query=test&limit=5',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        
        # Verify limit was passed to search service
        call_args = mock_collection.query.near_text.call_args
        self.assertEqual(call_args[1]['limit'], 5)
    
    @patch('core.services.weaviate_search_service.weaviate.connect_to_local')
    def test_search_empty_results(self, mock_weaviate_connect):
        """Test search with no results"""
        # Mock Weaviate client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        
        mock_response = MagicMock()
        mock_response.objects = []
        
        mock_collection.query.near_text.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection
        mock_weaviate_connect.return_value = mock_client
        
        # Perform search
        response = self.client.get(
            '/api/search?query=nonexistent',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 0)
        self.assertEqual(len(data['results']), 0)
    
    @patch('core.services.weaviate_search_service.weaviate.connect_to_local')
    def test_search_with_session_authentication(self, mock_weaviate_connect):
        """Test that search works with session-based authentication (not just JWT)"""
        # Mock Weaviate client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        
        # Mock search response
        mock_obj = MagicMock()
        mock_obj.uuid = 'session-test-uuid'
        mock_obj.properties = {
            'type': 'Task',
            'title': 'Session Auth Test',
            'description': 'Testing session authentication',
            'url': '/tasks/session-test-uuid/',
            'owner': 'testuser',
            'status': 'new',
            'tags': []
        }
        mock_obj.metadata = MagicMock()
        mock_obj.metadata.distance = 0.3
        mock_obj.metadata.certainty = 0.85
        
        mock_response = MagicMock()
        mock_response.objects = [mock_obj]
        
        mock_collection.query.near_text.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection
        mock_weaviate_connect.return_value = mock_client
        
        # Create a new client with session authentication (no JWT token)
        session_client = Client()
        session = session_client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session['user_role'] = self.user.role
        session.save()
        
        # Perform search using session auth (no Authorization header)
        response = session_client.get('/api/search?query=test')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['query'], 'test')
        self.assertEqual(data['total'], 1)
        self.assertEqual(len(data['results']), 1)
        
        result = data['results'][0]
        self.assertEqual(result['id'], 'session-test-uuid')
        self.assertEqual(result['type'], 'Task')
        self.assertEqual(result['title'], 'Session Auth Test')


class GlobalSearchViewTest(TestCase):
    """Test Global Search View"""
    
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
        
        # Log in user
        self.client = Client()
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session['user_role'] = self.user.role
        session.save()
    
    def test_search_view_url_exists(self):
        """Test that search view URL exists"""
        from django.urls import reverse
        url = reverse('main:global_search')
        self.assertEqual(url, '/search/')
    
    def test_search_view_context(self):
        """Test that search view provides correct context"""
        from main.views import global_search_view
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/search/?q=test')
        
        # Mock session
        request.session = {}
        
        response = global_search_view(request)
        
        # Response should be successful
        self.assertEqual(response.status_code, 200)
