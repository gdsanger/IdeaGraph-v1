"""
Test Task AI Enhancement functionality
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from main.models import User, Item, Task, Tag, Settings, Section
from main.api_views import api_task_ai_enhance


class TaskAIEnhanceTest(TestCase):
    """Test the Task AI Enhancement endpoint"""
    
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
            description='Test task description',
            status='new',
            item=self.item,
            created_by=self.user
        )
    
    @patch('main.api_views.ChromaTaskSyncService')
    @patch('main.api_views.KiGateService')
    def test_api_task_ai_enhance_success(self, mock_kigate_service, mock_chroma_service):
        """Test successful task AI enhancement"""
        # Mock ChromaDB service
        mock_chroma_instance = MagicMock()
        mock_chroma_instance.search_similar.return_value = {
            'success': True,
            'results': [
                {
                    'metadata': {'title': 'Similar Task 1'},
                    'document': 'Similar task description 1'
                },
                {
                    'metadata': {'title': 'Similar Task 2'},
                    'document': 'Similar task description 2'
                }
            ]
        }
        mock_chroma_service.return_value = mock_chroma_instance
        
        # Mock KiGate service
        mock_kigate_instance = MagicMock()
        
        # Mock github-issue-creation-agent response
        mock_kigate_instance.execute_agent.side_effect = [
            # First call: text normalization with github-issue-creation-agent
            {
                'success': True,
                'result': 'Normalized task description with improved grammar and flow.'
            },
            # Second call: title generation with text-to-title-generator
            {
                'success': True,
                'result': 'Enhanced Task Title'
            },
            # Third call: keyword extraction with text-keyword-extractor-de
            {
                'success': True,
                'result': 'Python, Django, Testing, API, Enhancement'
            }
        ]
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        # Execute
        response = api_task_ai_enhance(request, self.task.id)
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['title'], 'Enhanced Task Title')
        self.assertEqual(data['description'], 'Normalized task description with improved grammar and flow.')
        self.assertEqual(len(data['tags']), 5)
        self.assertIn('Python', data['tags'])
        self.assertIn('Django', data['tags'])
        
        # Verify ChromaDB was called for similarity search
        mock_chroma_instance.search_similar.assert_called_once()
        
        # Verify KiGate was called with correct agents
        calls = mock_kigate_instance.execute_agent.call_args_list
        self.assertEqual(len(calls), 3)
        
        # First call should be github-issue-creation-agent
        self.assertEqual(calls[0][1]['agent_name'], 'github-issue-creation-agent')
        self.assertIn('Context from similar tasks', calls[0][1]['message'])
        
        # Second call should be text-to-title-generator
        self.assertEqual(calls[1][1]['agent_name'], 'text-to-title-generator')
        
        # Third call should be text-keyword-extractor-de
        self.assertEqual(calls[2][1]['agent_name'], 'text-keyword-extractor-de')
    
    @patch('main.api_views.ChromaTaskSyncService')
    @patch('main.api_views.KiGateService')
    def test_api_task_ai_enhance_without_chroma_context(self, mock_kigate_service, mock_chroma_service):
        """Test task AI enhancement when ChromaDB context fails"""
        # Mock ChromaDB service to fail
        mock_chroma_instance = MagicMock()
        mock_chroma_instance.search_similar.side_effect = Exception("ChromaDB connection error")
        mock_chroma_service.return_value = mock_chroma_instance
        
        # Mock KiGate service
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.side_effect = [
            {'success': True, 'result': 'Normalized text'},
            {'success': True, 'result': 'New Title'},
            {'success': True, 'result': 'tag1, tag2, tag3'}
        ]
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        # Execute
        response = api_task_ai_enhance(request, self.task.id)
        
        # Should still succeed even if ChromaDB fails
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify message sent to agent does not contain context section
        first_call = mock_kigate_instance.execute_agent.call_args_list[0]
        self.assertNotIn('Context from similar tasks', first_call[1]['message'])
    
    def test_api_task_ai_enhance_requires_authentication(self):
        """Test that AI enhance requires authentication"""
        from django.contrib.sessions.middleware import SessionMiddleware
        
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        
        # Add session support to the request
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session.save()
        
        response = api_task_ai_enhance(request, self.task.id)
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_api_task_ai_enhance_requires_ownership(self):
        """Test that AI enhance requires task ownership"""
        # Create another user
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='developer',
            is_active=True
        )
        
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(other_user.id)}
        
        response = api_task_ai_enhance(request, self.task.id)
        
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_api_task_ai_enhance_requires_title_and_description(self):
        """Test that AI enhance requires both title and description"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title'
                # Missing description
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        response = api_task_ai_enhance(request, self.task.id)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    @patch('main.api_views.ChromaTaskSyncService')
    @patch('main.api_views.KiGateService')
    def test_api_task_ai_enhance_handles_kigate_error(self, mock_kigate_service, mock_chroma_service):
        """Test task AI enhancement handles KiGate errors gracefully"""
        # Mock ChromaDB service
        mock_chroma_instance = MagicMock()
        mock_chroma_instance.search_similar.return_value = {'success': True, 'results': []}
        mock_chroma_service.return_value = mock_chroma_instance
        
        # Mock KiGate service to fail
        from core.services.kigate_service import KiGateServiceError
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.side_effect = KiGateServiceError(
            "KiGate API error",
            status_code=500
        )
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        # Execute
        response = api_task_ai_enhance(request, self.task.id)
        
        # Should return error response
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
