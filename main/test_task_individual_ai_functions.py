"""
Test Individual Task AI Functions (Title Generation, Tag Extraction, Description Optimization)
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from main.models import User, Item, Task, Tag, Settings, Section
from main.api_views import (
    api_task_generate_title, 
    api_task_extract_tags, 
    api_task_optimize_description
)


class TaskIndividualAIFunctionsTest(TestCase):
    """Test the individual AI function endpoints for tasks"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test settings
        self.settings = Settings.objects.create(
            max_tags_per_idea=5,
            kigate_api_enabled=True,
            kigate_api_token='test-token',
            kigate_api_base_url='http://localhost:8000',
            openai_api_enabled=True,
            openai_api_key='test-openai-key',
            openai_api_base_url='https://api.openai.com/v1'
        )
        
        # Create test section
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
            description='Test task description for generating a better title',
            status='new',
            item=self.item,
            created_by=self.user
        )
    
    @patch('main.api_views.KiGateService')
    def test_api_task_generate_title_success(self, mock_kigate_service):
        """Test successful title generation from description"""
        # Mock KiGate service
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': 'Generated Task Title Based on Description'
        }
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/generate-title',
            data=json.dumps({
                'description': 'This is a detailed task description about implementing a new feature for the application'
            }),
            content_type='application/json'
        )
        
        # Add user to session
        request.session = {'user_id': str(self.user.id)}
        
        # Call endpoint
        response = api_task_generate_title(request, str(self.task.id))
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['title'], 'Generated Task Title Based on Description')
        
        # Verify KiGate was called with correct parameters
        mock_kigate_instance.execute_agent.assert_called_once()
        call_args = mock_kigate_instance.execute_agent.call_args
        self.assertEqual(call_args[1]['agent_name'], 'text-to-title-generator')
        self.assertEqual(call_args[1]['provider'], 'openai')
        self.assertEqual(call_args[1]['model'], 'gpt-4')
    
    @patch('main.api_views.KiGateService')
    def test_api_task_extract_tags_success(self, mock_kigate_service):
        """Test successful tag extraction from description"""
        # Mock KiGate service
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': 'Python, Django, Testing, API, Feature'
        }
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/extract-tags',
            data=json.dumps({
                'description': 'This task involves Python and Django development, including API testing and feature implementation'
            }),
            content_type='application/json'
        )
        
        # Add user to session
        request.session = {'user_id': str(self.user.id)}
        
        # Call endpoint
        response = api_task_extract_tags(request, str(self.task.id))
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['tags']), 5)
        self.assertIn('Python', data['tags'])
        self.assertIn('Django', data['tags'])
        
        # Verify KiGate was called with correct parameters
        mock_kigate_instance.execute_agent.assert_called_once()
        call_args = mock_kigate_instance.execute_agent.call_args
        self.assertEqual(call_args[1]['agent_name'], 'text-keyword-extractor-de')
        self.assertEqual(call_args[1]['provider'], 'openai')
        self.assertEqual(call_args[1]['model'], 'gpt-4')
    
    @patch('main.api_views.KiGateService')
    def test_api_task_optimize_description_success(self, mock_kigate_service):
        """Test successful description optimization"""
        # Mock KiGate service
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': 'This is an optimized task description with improved grammar, clarity, and structure.'
        }
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/optimize-description',
            data=json.dumps({
                'description': 'This task descripshun has bad grammer and needs optimizashun'
            }),
            content_type='application/json'
        )
        
        # Add user to session
        request.session = {'user_id': str(self.user.id)}
        
        # Call endpoint
        response = api_task_optimize_description(request, str(self.task.id))
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('optimized', data['description'].lower())
        
        # Verify KiGate was called with correct parameters
        mock_kigate_instance.execute_agent.assert_called_once()
        call_args = mock_kigate_instance.execute_agent.call_args
        self.assertEqual(call_args[1]['agent_name'], 'text-optimization-agent')
        self.assertEqual(call_args[1]['provider'], 'openai')
        self.assertEqual(call_args[1]['model'], 'gpt-4')
    
    def test_api_task_generate_title_without_auth(self):
        """Test title generation without authentication"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/generate-title',
            data=json.dumps({'description': 'Test description'}),
            content_type='application/json'
        )
        # No session means no authentication
        request.session = {}
        
        response = api_task_generate_title(request, str(self.task.id))
        self.assertEqual(response.status_code, 401)
    
    def test_api_task_extract_tags_without_description(self):
        """Test tag extraction without description"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/extract-tags',
            data=json.dumps({'description': ''}),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        response = api_task_extract_tags(request, str(self.task.id))
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    @patch('main.api_views.KiGateService')
    def test_api_task_generate_title_with_new_task(self, mock_kigate_service):
        """Test title generation for unsaved task (task_id='new')"""
        # Mock KiGate service
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': 'New Task Title'
        }
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request with task_id='new'
        request = self.factory.post(
            '/api/tasks/new/generate-title',
            data=json.dumps({
                'description': 'Description for a completely new task that has not been saved yet'
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        # Call endpoint with 'new' as task_id
        response = api_task_generate_title(request, 'new')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['title'], 'New Task Title')
