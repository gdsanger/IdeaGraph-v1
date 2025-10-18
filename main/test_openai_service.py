"""
Tests for OpenAI API Service
"""

import json
from unittest.mock import Mock, patch
from django.test import TestCase, Client
from django.urls import reverse

from main.models import Settings, User as AppUser
from core.services.openai_service import OpenAIService, OpenAIServiceError


class OpenAIServiceTestCase(TestCase):
    """Test suite for OpenAIService"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with OpenAI API enabled
        self.settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='sk-test-key-123',
            openai_org_id='org-test-123',
            openai_api_base_url='https://api.openai.com/v1',
            openai_default_model='gpt-4',
            openai_api_timeout=30,
            kigate_api_enabled=False
        )
    
    def test_init_without_settings(self):
        """Test OpenAIService initialization without settings object"""
        with patch('main.models.Settings') as mock_settings_model:
            mock_settings_model.objects.first.return_value = self.settings
            service = OpenAIService()
            self.assertIsNotNone(service.settings)
    
    def test_init_with_disabled_api(self):
        """Test OpenAIService raises error when API is disabled"""
        self.settings.openai_api_enabled = False
        self.settings.save()
        
        with self.assertRaises(OpenAIServiceError) as context:
            OpenAIService(self.settings)
        
        self.assertIn("not enabled", str(context.exception))
    
    def test_init_with_no_api_key(self):
        """Test OpenAIService raises error without API key"""
        self.settings.openai_api_key = ''
        self.settings.save()
        
        with self.assertRaises(OpenAIServiceError) as context:
            OpenAIService(self.settings)
        
        self.assertIn("incomplete", str(context.exception))
    
    def test_init_removes_trailing_slash(self):
        """Test that trailing slash is removed from base_url"""
        self.settings.openai_api_base_url = 'https://api.openai.com/v1/'
        self.settings.save()
        
        service = OpenAIService(self.settings)
        self.assertEqual(service.base_url, 'https://api.openai.com/v1')
    
    def test_get_headers_without_org_id(self):
        """Test header generation without organization ID"""
        self.settings.openai_org_id = ''
        self.settings.save()
        
        service = OpenAIService(self.settings)
        headers = service._get_headers()
        
        self.assertEqual(headers['Authorization'], 'Bearer sk-test-key-123')
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertNotIn('OpenAI-Organization', headers)
    
    def test_get_headers_with_org_id(self):
        """Test header generation with organization ID"""
        service = OpenAIService(self.settings)
        headers = service._get_headers()
        
        self.assertEqual(headers['Authorization'], 'Bearer sk-test-key-123')
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertEqual(headers['OpenAI-Organization'], 'org-test-123')
    
    @patch('core.services.openai_service.requests.request')
    def test_query_success(self, mock_request):
        """Test successful query to OpenAI API"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'choices': [
                    {
                        'message': {
                            'content': 'This is a test response from GPT-4'
                        }
                    }
                ],
                'usage': {
                    'total_tokens': 150
                },
                'model': 'gpt-4'
            }
        )
        
        service = OpenAIService(self.settings)
        result = service.query(
            prompt='What is a neural network?',
            user_id='test-user-123'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['result'], 'This is a test response from GPT-4')
        self.assertEqual(result['tokens_used'], 150)
        self.assertEqual(result['model'], 'gpt-4')
        self.assertEqual(result['source'], 'openai')
    
    @patch('core.services.openai_service.requests.request')
    def test_query_with_custom_model(self, mock_request):
        """Test query with custom model"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'choices': [{'message': {'content': 'Response'}}],
                'usage': {'total_tokens': 100},
                'model': 'gpt-3.5-turbo'
            }
        )
        
        service = OpenAIService(self.settings)
        result = service.query(
            prompt='Test prompt',
            model='gpt-3.5-turbo',
            user_id='test-user'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['model'], 'gpt-3.5-turbo')
        
        # Verify the model was sent in request
        call_args = mock_request.call_args
        request_data = call_args[1]['json']
        self.assertEqual(request_data['model'], 'gpt-3.5-turbo')
    
    @patch('core.services.openai_service.requests.request')
    def test_query_with_temperature_and_max_tokens(self, mock_request):
        """Test query with temperature and max_tokens parameters"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'choices': [{'message': {'content': 'Response'}}],
                'usage': {'total_tokens': 50},
                'model': 'gpt-4'
            }
        )
        
        service = OpenAIService(self.settings)
        result = service.query(
            prompt='Test',
            temperature=0.5,
            max_tokens=500
        )
        
        self.assertTrue(result['success'])
        
        # Verify parameters were sent in request
        call_args = mock_request.call_args
        request_data = call_args[1]['json']
        self.assertEqual(request_data['temperature'], 0.5)
        self.assertEqual(request_data['max_tokens'], 500)
    
    def test_query_missing_prompt(self):
        """Test that query raises error for missing prompt"""
        service = OpenAIService(self.settings)
        
        with self.assertRaises(OpenAIServiceError) as context:
            service.query(prompt='', user_id='test-user')
        
        self.assertEqual(context.exception.status_code, 400)
    
    @patch('core.services.openai_service.requests.request')
    def test_query_api_error_401(self, mock_request):
        """Test handling of API authentication error"""
        mock_request.return_value = Mock(
            status_code=401,
            json=lambda: {
                'error': {
                    'message': 'Invalid API key'
                }
            },
            text='Invalid API key'
        )
        
        service = OpenAIService(self.settings)
        
        with self.assertRaises(OpenAIServiceError) as context:
            service.query(prompt='test', user_id='test-user')
        
        self.assertEqual(context.exception.status_code, 401)
        self.assertIn('Invalid API key', context.exception.details)
    
    @patch('core.services.openai_service.requests.request')
    def test_query_timeout(self, mock_request):
        """Test handling of request timeout"""
        import requests
        mock_request.side_effect = requests.exceptions.Timeout()
        
        service = OpenAIService(self.settings)
        
        with self.assertRaises(OpenAIServiceError) as context:
            service.query(prompt='test', user_id='test-user')
        
        self.assertEqual(context.exception.status_code, 408)
        self.assertIn("timed out", str(context.exception))
    
    @patch('core.services.openai_service.requests.request')
    def test_query_connection_error(self, mock_request):
        """Test handling of connection error"""
        import requests
        mock_request.side_effect = requests.exceptions.ConnectionError('Connection refused')
        
        service = OpenAIService(self.settings)
        
        with self.assertRaises(OpenAIServiceError) as context:
            service.query(prompt='test', user_id='test-user')
        
        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("connect", str(context.exception))
    
    @patch('core.services.openai_service.requests.request')
    def test_query_with_agent_no_kigate(self, mock_request):
        """Test query_with_agent falls back to OpenAI when KiGate is disabled"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'choices': [{'message': {'content': 'OpenAI response'}}],
                'usage': {'total_tokens': 100},
                'model': 'gpt-4'
            }
        )
        
        service = OpenAIService(self.settings)
        result = service.query_with_agent(
            prompt='Optimize this text',
            agent_name='text-optimization-agent',
            user_id='test-user'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['result'], 'OpenAI response')
        self.assertEqual(result['source'], 'openai')
        self.assertEqual(result['agent_requested'], 'text-optimization-agent')
    
    @patch('core.services.openai_service.requests.request')
    def test_query_with_agent_kigate_success(self, mock_request):
        """Test query_with_agent uses KiGate when agent exists"""
        # Enable KiGate in settings
        self.settings.kigate_api_enabled = True
        self.settings.kigate_api_token = 'test-token'
        self.settings.save()
        
        # Mock KiGate agent details and execution
        mock_request.side_effect = [
            # Mock get_agent_details response
            Mock(
                status_code=200,
                json=lambda: {
                    'name': 'text-optimization-agent',
                    'provider': 'openai',
                    'model': 'gpt-4'
                }
            ),
            # Mock execute_agent response
            Mock(
                status_code=200,
                json=lambda: {
                    'job_id': 'job-123',
                    'result': 'Optimized text from KiGate',
                    'tokens_used': 120,
                    'model': 'gpt-4'
                }
            )
        ]
        
        service = OpenAIService(self.settings)
        result = service.query_with_agent(
            prompt='Optimize this text',
            agent_name='text-optimization-agent',
            user_id='test-user'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['result'], 'Optimized text from KiGate')
        self.assertEqual(result['source'], 'kigate')
        self.assertEqual(result['agent'], 'text-optimization-agent')
    
    @patch('core.services.openai_service.requests.request')
    def test_query_with_agent_kigate_fallback(self, mock_request):
        """Test query_with_agent falls back to OpenAI when KiGate agent not found"""
        # Enable KiGate in settings
        self.settings.kigate_api_enabled = True
        self.settings.kigate_api_token = 'test-token'
        self.settings.save()
        
        # Mock responses - first for KiGate (404), then for OpenAI (200)
        mock_request.side_effect = [
            # KiGate get_agent_details call (404 - agent not found)
            Mock(
                status_code=404,
                json=lambda: {'detail': 'Agent not found'},
                text='Agent not found'
            ),
            # OpenAI query call (200 - success)
            Mock(
                status_code=200,
                json=lambda: {
                    'choices': [{'message': {'content': 'OpenAI fallback response'}}],
                    'usage': {'total_tokens': 100},
                    'model': 'gpt-4'
                }
            )
        ]
        
        service = OpenAIService(self.settings)
        result = service.query_with_agent(
            prompt='Test prompt',
            agent_name='non-existent-agent',
            user_id='test-user'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['result'], 'OpenAI fallback response')
        self.assertEqual(result['source'], 'openai')
        self.assertEqual(result['agent_requested'], 'non-existent-agent')
    
    def test_query_with_agent_missing_fields(self):
        """Test that query_with_agent raises error for missing fields"""
        service = OpenAIService(self.settings)
        
        with self.assertRaises(OpenAIServiceError):
            service.query_with_agent(prompt='', agent_name='test-agent')
        
        with self.assertRaises(OpenAIServiceError):
            service.query_with_agent(prompt='test', agent_name='')
    
    @patch('core.services.openai_service.requests.request')
    def test_get_models_success(self, mock_request):
        """Test getting list of available models"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'data': [
                    {'id': 'gpt-4', 'object': 'model', 'owned_by': 'openai'},
                    {'id': 'gpt-3.5-turbo', 'object': 'model', 'owned_by': 'openai'},
                    {'id': 'whisper-1', 'object': 'model', 'owned_by': 'openai'},  # Not a chat model
                    {'id': 'gpt-4-turbo', 'object': 'model', 'owned_by': 'openai'}
                ]
            }
        )
        
        service = OpenAIService(self.settings)
        result = service.get_models()
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['models']), 3)  # Only gpt-* models
        model_ids = [m['id'] for m in result['models']]
        self.assertIn('gpt-4', model_ids)
        self.assertIn('gpt-3.5-turbo', model_ids)
        self.assertNotIn('whisper-1', model_ids)
    
    @patch('core.services.openai_service.requests.request')
    def test_get_models_api_error(self, mock_request):
        """Test handling of API error when getting models"""
        mock_request.return_value = Mock(
            status_code=500,
            json=lambda: {'error': {'message': 'Internal server error'}},
            text='Internal server error'
        )
        
        service = OpenAIService(self.settings)
        
        with self.assertRaises(OpenAIServiceError) as context:
            service.get_models()
        
        self.assertEqual(context.exception.status_code, 500)


class OpenAIAPIEndpointsTestCase(TestCase):
    """Test suite for OpenAI API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with OpenAI API enabled
        self.settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='sk-test-key-123',
            openai_org_id='org-test-123',
            openai_api_base_url='https://api.openai.com/v1',
            openai_default_model='gpt-4',
            openai_api_timeout=30,
            kigate_api_enabled=False
        )
        
        # Create test user
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Get auth token
        from main.auth_utils import generate_jwt_token
        self.token = generate_jwt_token(self.user)
        
        self.client = Client()
    
    @patch('core.services.openai_service.requests.request')
    def test_api_openai_query_success(self, mock_request):
        """Test POST /api/openai/query endpoint"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'choices': [{'message': {'content': 'AI response'}}],
                'usage': {'total_tokens': 100},
                'model': 'gpt-4'
            }
        )
        
        response = self.client.post(
            '/api/openai/query',
            data=json.dumps({
                'prompt': 'What is AI?',
                'user_id': 'test-user'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['result'], 'AI response')
    
    @patch('core.services.openai_service.requests.request')
    def test_api_openai_query_with_agent(self, mock_request):
        """Test POST /api/openai/query with agent_name"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'choices': [{'message': {'content': 'Optimized text'}}],
                'usage': {'total_tokens': 120},
                'model': 'gpt-4'
            }
        )
        
        response = self.client.post(
            '/api/openai/query',
            data=json.dumps({
                'prompt': 'Optimize this text',
                'agent_name': 'text-optimization-agent'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_api_openai_query_no_auth(self):
        """Test POST /api/openai/query without authentication"""
        response = self.client.post(
            '/api/openai/query',
            data=json.dumps({'prompt': 'Test'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)
    
    def test_api_openai_query_missing_prompt(self):
        """Test POST /api/openai/query with missing prompt"""
        response = self.client.post(
            '/api/openai/query',
            data=json.dumps({}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    @patch('core.services.openai_service.requests.request')
    def test_api_openai_models_success(self, mock_request):
        """Test GET /api/openai/models endpoint"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'data': [
                    {'id': 'gpt-4', 'object': 'model'},
                    {'id': 'gpt-3.5-turbo', 'object': 'model'}
                ]
            }
        )
        
        response = self.client.get(
            '/api/openai/models',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreater(len(data['models']), 0)
    
    def test_api_openai_models_no_auth(self):
        """Test GET /api/openai/models without authentication"""
        response = self.client.get('/api/openai/models')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)
