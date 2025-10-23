"""
Test Support Analysis Functions (Internal and External)
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from main.models import User, Item, Task, Settings, Section
from main.api_views import (
    api_task_support_analysis_internal,
    api_task_support_analysis_external
)


class SupportAnalysisTest(TestCase):
    """Test the support analysis endpoints for tasks"""
    
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
            description='Test task description with technical problem that needs analysis',
            status='new',
            item=self.item,
            created_by=self.user
        )
    
    @patch('main.api_views.SupportAdvisorService')
    def test_api_task_support_analysis_internal_success(self, mock_advisor_service):
        """Test successful internal support analysis"""
        # Mock SupportAdvisorService
        mock_advisor_instance = MagicMock()
        mock_advisor_instance.analyze_internal.return_value = {
            'success': True,
            'analysis': '### 🧩 Interne Analyse\n- Mögliche Ursache: Test cause\n- Empfehlung: Test recommendation',
            'similar_objects': [
                {
                    'type': 'task',
                    'id': 'test-id',
                    'title': 'Similar Task',
                    'description': 'Similar task description',
                    'similarity': 0.95
                }
            ],
            'mode': 'internal'
        }
        mock_advisor_service.return_value = mock_advisor_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-internal',
            data=json.dumps({
                'description': 'Test task description with technical problem'
            }),
            content_type='application/json'
        )
        
        # Add session data (simulating logged-in user)
        request.session = {'user_id': str(self.user.id)}
        
        # Call the API
        response = api_task_support_analysis_internal(request, self.task.id)
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('analysis', data)
        self.assertIn('🧩 Interne Analyse', data['analysis'])
        self.assertEqual(data['mode'], 'internal')
        self.assertEqual(len(data['similar_objects']), 1)
        
        # Verify service was called correctly
        mock_advisor_instance.analyze_internal.assert_called_once()
        call_args = mock_advisor_instance.analyze_internal.call_args
        self.assertEqual(call_args[1]['task_description'], 'Test task description with technical problem')
        self.assertEqual(call_args[1]['task_title'], 'Test Task')
    
    @patch('main.api_views.SupportAdvisorService')
    def test_api_task_support_analysis_external_success(self, mock_advisor_service):
        """Test successful external support analysis"""
        # Mock SupportAdvisorService
        mock_advisor_instance = MagicMock()
        mock_advisor_instance.analyze_external.return_value = {
            'success': True,
            'analysis': '### 🌍 Externe Analyse\n- Lösung: Test solution\n- Quelle: https://example.com',
            'sources': [
                {
                    'title': 'Example Solution',
                    'url': 'https://example.com',
                    'snippet': 'This is an example solution'
                }
            ],
            'mode': 'external'
        }
        mock_advisor_service.return_value = mock_advisor_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-external',
            data=json.dumps({
                'description': 'Test task description with technical problem'
            }),
            content_type='application/json'
        )
        
        # Add session data (simulating logged-in user)
        request.session = {'user_id': str(self.user.id)}
        
        # Call the API
        response = api_task_support_analysis_external(request, self.task.id)
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('analysis', data)
        self.assertIn('🌍 Externe Analyse', data['analysis'])
        self.assertEqual(data['mode'], 'external')
        self.assertEqual(len(data['sources']), 1)
        
        # Verify service was called correctly
        mock_advisor_instance.analyze_external.assert_called_once()
        call_args = mock_advisor_instance.analyze_external.call_args
        self.assertEqual(call_args[1]['task_description'], 'Test task description with technical problem')
        self.assertEqual(call_args[1]['task_title'], 'Test Task')
    
    def test_api_task_support_analysis_internal_no_auth(self):
        """Test internal support analysis without authentication"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-internal',
            data=json.dumps({
                'description': 'Test description'
            }),
            content_type='application/json'
        )
        
        # No session data (not logged in)
        request.session = {}
        
        response = api_task_support_analysis_internal(request, self.task.id)
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Authentication required')
    
    def test_api_task_support_analysis_external_no_auth(self):
        """Test external support analysis without authentication"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-external',
            data=json.dumps({
                'description': 'Test description'
            }),
            content_type='application/json'
        )
        
        # No session data (not logged in)
        request.session = {}
        
        response = api_task_support_analysis_external(request, self.task.id)
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Authentication required')
    
    def test_api_task_support_analysis_internal_missing_description(self):
        """Test internal support analysis with missing description"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-internal',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        request.session = {'user_id': str(self.user.id)}
        
        response = api_task_support_analysis_internal(request, self.task.id)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Description is required')
    
    def test_api_task_support_analysis_external_missing_description(self):
        """Test external support analysis with missing description"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-external',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        request.session = {'user_id': str(self.user.id)}
        
        response = api_task_support_analysis_external(request, self.task.id)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Description is required')
    
    @patch('main.api_views.SupportAdvisorService')
    def test_api_task_support_analysis_internal_service_error(self, mock_advisor_service):
        """Test internal support analysis with service error"""
        from core.services.support_advisor_service import SupportAdvisorServiceError
        
        # Mock service to raise error
        mock_advisor_instance = MagicMock()
        mock_advisor_instance.analyze_internal.side_effect = SupportAdvisorServiceError(
            "Service error",
            details="Test error details"
        )
        mock_advisor_service.return_value = mock_advisor_instance
        
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-internal',
            data=json.dumps({
                'description': 'Test description'
            }),
            content_type='application/json'
        )
        
        request.session = {'user_id': str(self.user.id)}
        
        response = api_task_support_analysis_internal(request, self.task.id)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Service error')
    
    @patch('main.api_views.SupportAdvisorService')
    def test_api_task_support_analysis_external_service_error(self, mock_advisor_service):
        """Test external support analysis with service error"""
        from core.services.support_advisor_service import SupportAdvisorServiceError
        
        # Mock service to raise error
        mock_advisor_instance = MagicMock()
        mock_advisor_instance.analyze_external.side_effect = SupportAdvisorServiceError(
            "Service error",
            details="Test error details"
        )
        mock_advisor_service.return_value = mock_advisor_instance
        
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-external',
            data=json.dumps({
                'description': 'Test description'
            }),
            content_type='application/json'
        )
        
        request.session = {'user_id': str(self.user.id)}
        
        response = api_task_support_analysis_external(request, self.task.id)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Service error')
    
    @patch('main.api_views.TaskFileService')
    @patch('main.api_views.WeaviateItemSyncService')
    def test_api_task_support_analysis_save_success(self, mock_weaviate_service, mock_file_service):
        """Test successful saving of support analysis"""
        # Mock TaskFileService
        mock_file_instance = MagicMock()
        mock_file_instance.upload_file.return_value = {
            'success': True,
            'file_id': 'test-file-id',
            'filename': 'Support_Analyse_intern_20240101_120000.md',
            'sharepoint_url': 'https://sharepoint.com/file'
        }
        mock_file_service.return_value = mock_file_instance
        
        # Mock WeaviateItemSyncService
        mock_weaviate_instance = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate_instance._client.collections.get.return_value = mock_collection
        mock_weaviate_service.return_value = mock_weaviate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-save',
            data=json.dumps({
                'analysis': '### 🧩 Interne Analyse\n- Test analysis content',
                'mode': 'internal'
            }),
            content_type='application/json'
        )
        
        request.session = {'user_id': str(self.user.id)}
        
        # Call the API
        from main.api_views import api_task_support_analysis_save
        response = api_task_support_analysis_save(request, self.task.id)
        
        # Assert response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('filename', data)
        self.assertIn('Support_Analyse', data['filename'])
        self.assertEqual(data['sharepoint_url'], 'https://sharepoint.com/file')
        
        # Verify file service was called
        mock_file_instance.upload_file.assert_called_once()
    
    def test_api_task_support_analysis_save_no_auth(self):
        """Test saving support analysis without authentication"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-save',
            data=json.dumps({
                'analysis': 'Test analysis',
                'mode': 'internal'
            }),
            content_type='application/json'
        )
        
        # No session data (not logged in)
        request.session = {}
        
        from main.api_views import api_task_support_analysis_save
        response = api_task_support_analysis_save(request, self.task.id)
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Authentication required')
    
    def test_api_task_support_analysis_save_missing_analysis(self):
        """Test saving support analysis with missing analysis content"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-save',
            data=json.dumps({
                'mode': 'internal'
            }),
            content_type='application/json'
        )
        
        request.session = {'user_id': str(self.user.id)}
        
        from main.api_views import api_task_support_analysis_save
        response = api_task_support_analysis_save(request, self.task.id)
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Analysis content is required')
    
    @patch('main.api_views.TaskFileService')
    def test_api_task_support_analysis_save_file_error(self, mock_file_service):
        """Test saving support analysis with file upload error"""
        from core.services.task_file_service import TaskFileServiceError
        
        # Mock service to raise error
        mock_file_instance = MagicMock()
        mock_file_instance.upload_file.side_effect = TaskFileServiceError(
            "Upload failed",
            details="Test error details"
        )
        mock_file_service.return_value = mock_file_instance
        
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/support-analysis-save',
            data=json.dumps({
                'analysis': 'Test analysis',
                'mode': 'internal'
            }),
            content_type='application/json'
        )
        
        request.session = {'user_id': str(self.user.id)}
        
        from main.api_views import api_task_support_analysis_save
        response = api_task_support_analysis_save(request, self.task.id)
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Failed to save analysis file')
