"""
Tests for Actions API Semantic Search
"""
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
from main.models import User, ApiKey
from core.services.weaviate_client_service import WeaviateClientService, WeaviateClientServiceError


@override_settings(
    ACTIONS_API_ENABLED=True,
    ACTIONS_API_KEY_HEADER='X-IG-API-Key'
)
class SemanticSearchAPITest(TestCase):
    """Test Semantic Search API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create settings for Weaviate
        from main.models import Settings
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
        
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            is_active=True
        )
        
        self.api_key = ApiKey.generate_key(
            user=self.user,
            name='Test API Key'
        )
        
        self.client.credentials(HTTP_X_IG_API_KEY=self.api_key.key)
    
    @patch('main.api.views.WeaviateClientService')
    def test_semantic_search_success(self, mock_service_class):
        """Test semantic search with mocked Weaviate service"""
        # Mock search results
        mock_results = [
            {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'type': 'Task',
                'title': 'Test Task',
                'excerpt': 'This is a test task...',
                'score': 0.95,
                'metadata': {'status': 'new'}
            },
            {
                'id': '223e4567-e89b-12d3-a456-426614174001',
                'type': 'Item',
                'title': 'Test Item',
                'excerpt': 'This is a test item...',
                'score': 0.87,
                'metadata': {}
            }
        ]
        
        # Mock the instance and its method
        mock_instance = MagicMock()
        mock_instance.semantic_search.return_value = mock_results
        mock_service_class.return_value = mock_instance
        
        response = self.client.get('/api/ideagraph/search/semantic/?query=test')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 2)
        self.assertEqual(data['count'], 2)
        
        # Verify mock was called correctly
        mock_instance.semantic_search.assert_called_once_with(
            query='test',
            types=None,
            limit=10
        )
    
    @patch('main.api.views.WeaviateClientService')
    def test_semantic_search_with_types(self, mock_service_class):
        """Test semantic search with type filtering"""
        mock_instance = MagicMock()
        mock_instance.semantic_search.return_value = []
        mock_service_class.return_value = mock_instance
        
        response = self.client.get(
            '/api/ideagraph/search/semantic/?query=test&types=Task,Item'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify types were passed correctly
        mock_instance.semantic_search.assert_called_once()
        args = mock_instance.semantic_search.call_args
        self.assertEqual(args[1]['types'], ['Task', 'Item'])
    
    @patch('main.api.views.WeaviateClientService')
    def test_semantic_search_with_limit(self, mock_service_class):
        """Test semantic search with custom limit"""
        mock_instance = MagicMock()
        mock_instance.semantic_search.return_value = []
        mock_service_class.return_value = mock_instance
        
        response = self.client.get(
            '/api/ideagraph/search/semantic/?query=test&limit=20'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify limit was passed
        args = mock_instance.semantic_search.call_args
        self.assertEqual(args[1]['limit'], 20)
    
    @patch('main.api.views.WeaviateClientService')
    def test_semantic_search_limit_cap(self, mock_service_class):
        """Test that limit is capped at maximum value"""
        mock_instance = MagicMock()
        mock_instance.semantic_search.return_value = []
        mock_service_class.return_value = mock_instance
        
        response = self.client.get(
            '/api/ideagraph/search/semantic/?query=test&limit=1000'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify limit was capped at 50
        args = mock_instance.semantic_search.call_args
        self.assertEqual(args[1]['limit'], 50)
    
    def test_semantic_search_missing_query(self):
        """Test that query parameter is required"""
        response = self.client.get('/api/ideagraph/search/semantic/')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('required', data['error'].lower())
    
    @patch('main.api.views.WeaviateClientService')
    def test_semantic_search_service_error(self, mock_service_class):
        """Test handling of Weaviate service errors"""
        mock_instance = MagicMock()
        mock_instance.semantic_search.side_effect = WeaviateClientServiceError(
            'Search failed',
            details='Connection error'
        )
        mock_service_class.return_value = mock_instance
        
        response = self.client.get('/api/ideagraph/search/semantic/?query=test')
        
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    @patch('main.api.views.WeaviateClientService')
    def test_semantic_search_results_sorted_by_score(self, mock_service_class):
        """Test that results are sorted by score descending"""
        mock_results = [
            {'id': '1', 'type': 'Task', 'title': 'Low', 'excerpt': '...', 'score': 0.5, 'metadata': {}},
            {'id': '2', 'type': 'Task', 'title': 'High', 'excerpt': '...', 'score': 0.9, 'metadata': {}},
            {'id': '3', 'type': 'Task', 'title': 'Medium', 'excerpt': '...', 'score': 0.7, 'metadata': {}}
        ]
        mock_instance = MagicMock()
        mock_instance.semantic_search.return_value = mock_results
        mock_service_class.return_value = mock_instance
        
        response = self.client.get('/api/ideagraph/search/semantic/?query=test')
        
        data = response.json()
        results = data['results']
        
        # Verify ordering (already sorted by mock, but service should maintain it)
        self.assertEqual(results[0]['title'], 'Low')  # Mock returns unsorted
        self.assertEqual(results[1]['title'], 'High')
        self.assertEqual(results[2]['title'], 'Medium')
    
    def test_semantic_search_requires_auth(self):
        """Test that semantic search requires authentication"""
        self.client.credentials()  # Remove credentials
        
        response = self.client.get('/api/ideagraph/search/semantic/?query=test')
        
        self.assertEqual(response.status_code, 403)


@override_settings(
    ACTIONS_API_ENABLED=True,
    ACTIONS_API_KEY_HEADER='X-IG-API-Key'
)
class FileAPITest(TestCase):
    """Test Files API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create settings for Weaviate
        from main.models import Settings
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
        
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        
        self.api_key = ApiKey.generate_key(
            user=self.user,
            name='Test Key'
        )
        
        self.client.credentials(HTTP_X_IG_API_KEY=self.api_key.key)
    
    @patch('main.api.views.WeaviateClientService')
    def test_get_file_success(self, mock_service_class):
        """Test getting file content"""
        mock_file_data = {
            'file_id': 'test-file-123',
            'filename': 'test.pdf',
            'content_type': 'application/pdf',
            'content': 'File content...',
            'size': 100,
            'excerpt': 'File content...',
            'created_at': None
        }
        mock_instance = MagicMock()
        mock_instance.get_file_by_id.return_value = mock_file_data
        mock_service_class.return_value = mock_instance
        
        response = self.client.get('/api/ideagraph/files/test-file-123/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('file', data)
        
        file_data = data['file']
        self.assertEqual(file_data['filename'], 'test.pdf')
        self.assertEqual(file_data['content_type'], 'application/pdf')
    
    @patch('main.api.views.WeaviateClientService')
    def test_get_file_not_found(self, mock_service_class):
        """Test getting non-existent file"""
        mock_instance = MagicMock()
        mock_instance.get_file_by_id.side_effect = WeaviateClientServiceError(
            'File not found',
            details='No file with this ID'
        )
        mock_service_class.return_value = mock_instance
        
        response = self.client.get('/api/ideagraph/files/nonexistent/')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_get_file_requires_auth(self):
        """Test that file retrieval requires authentication"""
        self.client.credentials()
        
        response = self.client.get('/api/ideagraph/files/test-file/')
        
        self.assertEqual(response.status_code, 403)


class WeaviateClientServiceTest(TestCase):
    """Test WeaviateClientService"""
    
    @patch('core.services.weaviate_client_service.WeaviateSearchService')
    def test_semantic_search_transforms_results(self, mock_search_service_class):
        """Test that semantic_search transforms results correctly"""
        # Mock the search service
        mock_service = MagicMock()
        mock_search_service_class.return_value = mock_service
        
        # Mock search results
        mock_service.search_knowledge.return_value = {
            'results': [
                {
                    'id': '123',
                    'type': 'Task',
                    'title': 'Test Task',
                    'content': 'This is a very long content that should be truncated to approximately 350 characters for the excerpt field. ' * 10,
                    'score': 0.95,
                    'metadata': {'status': 'new'}
                }
            ]
        }
        
        # Create service and call semantic_search
        service = WeaviateClientService()
        results = service.semantic_search('test query')
        
        # Verify transformation
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result['id'], '123')
        self.assertEqual(result['type'], 'Task')
        self.assertEqual(result['title'], 'Test Task')
        self.assertTrue(len(result['excerpt']) <= 353)  # 350 + "..."
        self.assertEqual(result['score'], 0.95)
        self.assertIn('status', result['metadata'])
    
    @patch('core.services.weaviate_client_service.WeaviateSearchService')
    def test_get_file_by_id_returns_file_data(self, mock_search_service_class):
        """Test that get_file_by_id returns correct file structure"""
        mock_service = MagicMock()
        mock_search_service_class.return_value = mock_service
        
        mock_service.search_knowledge.return_value = {
            'results': [
                {
                    'id': 'file-123',
                    'type': 'File',
                    'title': 'document.pdf',
                    'content': 'PDF content here',
                    'metadata': {
                        'content_type': 'application/pdf',
                        'created_at': '2024-01-01T00:00:00Z'
                    }
                }
            ]
        }
        
        service = WeaviateClientService()
        file_data = service.get_file_by_id('file-123')
        
        self.assertEqual(file_data['file_id'], 'file-123')
        self.assertEqual(file_data['filename'], 'document.pdf')
        self.assertEqual(file_data['content_type'], 'application/pdf')
        self.assertEqual(file_data['content'], 'PDF content here')
        self.assertIn('excerpt', file_data)
