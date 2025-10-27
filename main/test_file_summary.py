"""
Tests for file summary API endpoint
"""

import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Section, ItemFile, TaskFile, Task, Settings


class FileSummaryAPITest(TestCase):
    """Test file summary API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        self.user.set_password('testpass')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(
            name='Test Section'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            item=self.item,
            created_by=self.user
        )
        
        # Create settings
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,  # Enable KIGate for tests
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test-token'
        )
        
        # Create test item file
        self.item_file = ItemFile.objects.create(
            id=uuid.uuid4(),
            item=self.item,
            filename='test_document.txt',
            file_size=1024,
            sharepoint_url='https://sharepoint.example.com/test.txt',
            content_type='text/plain',
            weaviate_synced=True,
            uploaded_by=self.user
        )
        
        # Create test task file
        self.task_file = TaskFile.objects.create(
            id=uuid.uuid4(),
            task=self.task,
            filename='test_task_doc.txt',
            file_size=2048,
            sharepoint_url='https://sharepoint.example.com/task_test.txt',
            content_type='text/plain',
            weaviate_synced=True,
            uploaded_by=self.user
        )
    
    def test_file_summary_requires_authentication(self):
        """Test that API requires authentication"""
        url = f'/api/files/{self.item_file.id}/summary'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Authentication required', data['error'])
    
    @patch('main.api_views.get_user_from_request')
    def test_file_summary_not_found(self, mock_get_user):
        """Test API with non-existent file"""
        mock_get_user.return_value = self.user
        
        fake_id = uuid.uuid4()
        url = f'/api/files/{fake_id}/summary'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'])
    
    @patch('main.api_views.get_user_from_request')
    def test_file_summary_not_synced(self, mock_get_user):
        """Test API with file not synced to Weaviate"""
        mock_get_user.return_value = self.user
        
        # Create unsynced file
        unsynced_file = ItemFile.objects.create(
            id=uuid.uuid4(),
            item=self.item,
            filename='unsynced.txt',
            file_size=1024,
            sharepoint_url='https://sharepoint.example.com/unsynced.txt',
            content_type='text/plain',
            weaviate_synced=False,
            uploaded_by=self.user
        )
        
        url = f'/api/files/{unsynced_file.id}/summary'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('not available in Weaviate', data['error'])
    
    @patch('main.api_views.get_user_from_request')
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService')
    @patch('main.api_views.KiGateService')
    def test_file_summary_success(self, mock_kigate, mock_weaviate, mock_get_user):
        """Test successful file summary generation"""
        mock_get_user.return_value = self.user
        
        # Mock Weaviate service
        mock_weaviate_instance = MagicMock()
        mock_collection = MagicMock()
        
        # Mock fetch_object_by_id to return file content
        mock_result = MagicMock()
        mock_result.properties = {
            'description': 'This is the content of the test document.'
        }
        mock_collection.query.fetch_object_by_id.return_value = mock_result
        
        mock_weaviate_instance._client.collections.get.return_value = mock_collection
        mock_weaviate.return_value = mock_weaviate_instance
        
        # Mock KIGate service
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': '# Summary\n\nThis is a test document summary.'
        }
        mock_kigate.return_value = mock_kigate_instance
        
        url = f'/api/files/{self.item_file.id}/summary'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('summary', data)
        self.assertIn('Summary', data['summary'])
        self.assertEqual(data['filename'], 'test_document.txt')
        self.assertEqual(data['file_url'], 'https://sharepoint.example.com/test.txt')
    
    @patch('main.api_views.get_user_from_request')
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService')
    @patch('main.api_views.KiGateService')
    def test_file_summary_fallback_on_kigate_error(self, mock_kigate, mock_weaviate, mock_get_user):
        """Test fallback summary when KIGate fails"""
        mock_get_user.return_value = self.user
        
        # Mock Weaviate service
        mock_weaviate_instance = MagicMock()
        mock_collection = MagicMock()
        
        mock_result = MagicMock()
        mock_result.properties = {
            'description': 'This is the content of the test document.'
        }
        mock_collection.query.fetch_object_by_id.return_value = mock_result
        
        mock_weaviate_instance._client.collections.get.return_value = mock_collection
        mock_weaviate.return_value = mock_weaviate_instance
        
        # Mock KIGate to raise an error
        from core.services.kigate_service import KiGateServiceError
        mock_kigate.side_effect = KiGateServiceError('KIGate not available')
        
        url = f'/api/files/{self.item_file.id}/summary'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('summary', data)
        # Should contain fallback summary
        self.assertIn('AI summary service not available', data['summary'])
        self.assertIn('test_document.txt', data['summary'])
    
    @patch('main.api_views.get_user_from_request')
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService')
    @patch('main.api_views.KiGateService')
    def test_task_file_summary_success(self, mock_kigate, mock_weaviate, mock_get_user):
        """Test successful task file summary generation"""
        mock_get_user.return_value = self.user
        
        # Mock Weaviate service
        mock_weaviate_instance = MagicMock()
        mock_collection = MagicMock()
        
        mock_result = MagicMock()
        mock_result.properties = {
            'description': 'This is the content of the task document.'
        }
        mock_collection.query.fetch_object_by_id.return_value = mock_result
        
        mock_weaviate_instance._client.collections.get.return_value = mock_collection
        mock_weaviate.return_value = mock_weaviate_instance
        
        # Mock KIGate service
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': '# Task Document Summary\n\nThis is a task document summary.'
        }
        mock_kigate.return_value = mock_kigate_instance
        
        url = f'/api/files/{self.task_file.id}/summary'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('summary', data)
        self.assertIn('Task Document Summary', data['summary'])
        self.assertEqual(data['filename'], 'test_task_doc.txt')
