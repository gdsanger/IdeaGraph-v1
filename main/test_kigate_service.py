"""
Tests for KiGate API Service
"""

import json
from unittest.mock import Mock, patch
from django.test import TestCase, Client
from django.urls import reverse

from main.models import Settings, User as AppUser
from core.services.kigate_service import KiGateService, KiGateServiceError


class KiGateServiceTestCase(TestCase):
    """Test suite for KiGateService"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with KiGate API enabled
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_token='test_client_id:test_client_secret',
            kigate_api_base_url='http://localhost:8000',
            kigate_api_timeout=30
        )
    
    def test_init_without_settings(self):
        """Test KiGateService initialization without settings object"""
        with patch('main.models.Settings') as mock_settings_model:
            mock_settings_model.objects.first.return_value = self.settings
            service = KiGateService()
            self.assertIsNotNone(service.settings)
    
    def test_init_with_disabled_api(self):
        """Test KiGateService raises error when API is disabled"""
        self.settings.kigate_api_enabled = False
        self.settings.save()
        
        with self.assertRaises(KiGateServiceError) as context:
            KiGateService(self.settings)
        
        self.assertIn("not enabled", str(context.exception))
    
    def test_init_with_no_token(self):
        """Test KiGateService raises error without token"""
        self.settings.kigate_api_token = ''
        self.settings.save()
        
        with self.assertRaises(KiGateServiceError) as context:
            KiGateService(self.settings)
        
        self.assertIn("incomplete", str(context.exception))
    
    def test_init_removes_trailing_slash(self):
        """Test that trailing slash is removed from base_url"""
        self.settings.kigate_api_base_url = 'http://localhost:8000/'
        self.settings.save()
        
        service = KiGateService(self.settings)
        self.assertEqual(service.base_url, 'http://localhost:8000')
    
    @patch('core.services.kigate_service.requests.request')
    def test_get_agents_success(self, mock_request):
        """Test getting list of agents successfully"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'agents': [
                    {
                        'name': 'translation-agent',
                        'description': 'Translates text',
                        'provider': 'openai',
                        'model': 'gpt-4'
                    },
                    {
                        'name': 'code-review-agent',
                        'description': 'Reviews code',
                        'provider': 'openai',
                        'model': 'gpt-4'
                    }
                ]
            }
        )
        
        service = KiGateService(self.settings)
        result = service.get_agents()
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['agents']), 2)
        self.assertEqual(result['agents'][0]['name'], 'translation-agent')
    
    @patch('core.services.kigate_service.requests.request')
    def test_get_agents_api_error(self, mock_request):
        """Test handling API error when getting agents"""
        mock_request.return_value = Mock(
            status_code=500,
            json=lambda: {'detail': 'Internal server error'},
            text='Internal server error'
        )
        
        service = KiGateService(self.settings)
        
        with self.assertRaises(KiGateServiceError) as context:
            service.get_agents()
        
        self.assertEqual(context.exception.status_code, 500)
    
    @patch('core.services.kigate_service.requests.request')
    def test_execute_agent_success(self, mock_request):
        """Test executing an agent successfully"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'job_id': 'job-123-abc',
                'agent': 'translation-agent',
                'provider': 'openai',
                'model': 'gpt-4',
                'status': 'completed',
                'result': 'Translated text'
            }
        )
        
        service = KiGateService(self.settings)
        result = service.execute_agent(
            agent_name='translation-agent',
            provider='openai',
            model='gpt-4',
            message='Hello world',
            user_id='test-user-123'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['job_id'], 'job-123-abc')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['result'], 'Translated text')
    
    @patch('core.services.kigate_service.requests.request')
    def test_execute_agent_with_parameters(self, mock_request):
        """Test executing an agent with additional parameters"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'job_id': 'job-456-def',
                'agent': 'translation-agent',
                'provider': 'openai',
                'model': 'gpt-4',
                'status': 'completed',
                'result': 'Bonjour le monde'
            }
        )
        
        service = KiGateService(self.settings)
        result = service.execute_agent(
            agent_name='translation-agent',
            provider='openai',
            model='gpt-4',
            message='Hello world',
            user_id='test-user-123',
            parameters={'language': 'French'}
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['result'], 'Bonjour le monde')
        
        # Verify parameters were sent in the request
        call_args = mock_request.call_args
        request_data = call_args[1]['json']
        self.assertIn('parameters', request_data)
        self.assertEqual(request_data['parameters']['language'], 'French')
    
    def test_execute_agent_missing_required_fields(self):
        """Test that execute_agent raises error for missing required fields"""
        service = KiGateService(self.settings)
        
        with self.assertRaises(KiGateServiceError):
            service.execute_agent(
                agent_name='',
                provider='openai',
                model='gpt-4',
                message='test',
                user_id='user-123'
            )
        
        with self.assertRaises(KiGateServiceError):
            service.execute_agent(
                agent_name='test-agent',
                provider='',
                model='gpt-4',
                message='test',
                user_id='user-123'
            )
    
    @patch('core.services.kigate_service.requests.request')
    def test_execute_agent_timeout(self, mock_request):
        """Test handling timeout when executing agent"""
        import requests
        mock_request.side_effect = requests.exceptions.Timeout()
        
        service = KiGateService(self.settings)
        
        with self.assertRaises(KiGateServiceError) as context:
            service.execute_agent(
                agent_name='test-agent',
                provider='openai',
                model='gpt-4',
                message='test',
                user_id='user-123'
            )
        
        self.assertEqual(context.exception.status_code, 408)
        self.assertIn("timed out", str(context.exception))
    
    @patch('core.services.kigate_service.requests.request')
    def test_execute_agent_connection_error(self, mock_request):
        """Test handling connection error when executing agent"""
        import requests
        mock_request.side_effect = requests.exceptions.ConnectionError('Connection refused')
        
        service = KiGateService(self.settings)
        
        with self.assertRaises(KiGateServiceError) as context:
            service.execute_agent(
                agent_name='test-agent',
                provider='openai',
                model='gpt-4',
                message='test',
                user_id='user-123'
            )
        
        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("connect", str(context.exception))
    
    @patch('core.services.kigate_service.requests.request')
    def test_get_agent_details_success(self, mock_request):
        """Test getting agent details successfully"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'name': 'translation-agent',
                'description': 'Translates text',
                'role': 'You are a translation agent',
                'task': 'Translate text accurately',
                'provider': 'openai',
                'model': 'gpt-4',
                'parameters': ['language']
            }
        )
        
        service = KiGateService(self.settings)
        result = service.get_agent_details('translation-agent')
        
        self.assertTrue(result['success'])
        self.assertIn('agent', result)
        self.assertEqual(result['agent']['name'], 'translation-agent')
        self.assertEqual(result['agent']['provider'], 'openai')
    
    @patch('core.services.kigate_service.requests.request')
    def test_get_agent_details_not_found(self, mock_request):
        """Test getting details of non-existent agent"""
        mock_request.return_value = Mock(
            status_code=404,
            json=lambda: {'detail': 'Agent not found'},
            text='Agent not found'
        )
        
        service = KiGateService(self.settings)
        
        with self.assertRaises(KiGateServiceError) as context:
            service.get_agent_details('non-existent-agent')
        
        self.assertEqual(context.exception.status_code, 404)
    
    def test_get_agent_details_missing_name(self):
        """Test that get_agent_details raises error for missing agent name"""
        service = KiGateService(self.settings)
        
        with self.assertRaises(KiGateServiceError) as context:
            service.get_agent_details('')
        
        self.assertEqual(context.exception.status_code, 400)


class KiGateAPIEndpointsTestCase(TestCase):
    """Test suite for KiGate API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with KiGate API enabled
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_token='test_client_id:test_client_secret',
            kigate_api_base_url='http://localhost:8000',
            kigate_api_timeout=30
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
    
    @patch('core.services.kigate_service.requests.request')
    def test_api_kigate_agents_success(self, mock_request):
        """Test GET /api/kigate/agents endpoint"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'agents': [
                    {'name': 'agent1', 'provider': 'openai', 'model': 'gpt-4'},
                    {'name': 'agent2', 'provider': 'claude', 'model': 'claude-3'}
                ]
            }
        )
        
        response = self.client.get(
            '/api/kigate/agents',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['agents']), 2)
    
    def test_api_kigate_agents_no_auth(self):
        """Test GET /api/kigate/agents without authentication"""
        response = self.client.get('/api/kigate/agents')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)
    
    @patch('core.services.kigate_service.requests.request')
    def test_api_kigate_execute_success(self, mock_request):
        """Test POST /api/kigate/execute endpoint"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'job_id': 'job-123',
                'agent': 'test-agent',
                'provider': 'openai',
                'model': 'gpt-4',
                'status': 'completed',
                'result': 'Test result'
            }
        )
        
        response = self.client.post(
            '/api/kigate/execute',
            data=json.dumps({
                'agent_name': 'test-agent',
                'provider': 'openai',
                'model': 'gpt-4',
                'message': 'Test message',
                'user_id': 'test-user'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['job_id'], 'job-123')
    
    def test_api_kigate_execute_missing_fields(self):
        """Test POST /api/kigate/execute with missing required fields"""
        response = self.client.post(
            '/api/kigate/execute',
            data=json.dumps({
                'agent_name': 'test-agent',
                # Missing other required fields
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    @patch('core.services.kigate_service.requests.request')
    def test_api_kigate_agent_details_success(self, mock_request):
        """Test GET /api/kigate/agent/{name} endpoint"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'name': 'test-agent',
                'description': 'Test agent',
                'provider': 'openai',
                'model': 'gpt-4'
            }
        )
        
        response = self.client.get(
            '/api/kigate/agent/test-agent',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['agent']['name'], 'test-agent')
