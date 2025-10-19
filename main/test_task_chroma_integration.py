"""
Integration tests for Task ChromaDB synchronization
"""
from django.test import TestCase, Client
from unittest.mock import Mock, patch, call
from main.models import User, Item, Task, Section, Settings
from main.auth_utils import generate_jwt_token
import json


class TaskChromaIntegrationTest(TestCase):
    """Test Task API endpoints integration with ChromaDB"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings
        self.settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='test-key-123',
            openai_api_base_url='https://api.openai.com/v1',
            chroma_api_key='',
            chroma_database='',
            chroma_tenant=''
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Generate JWT token
        self.token = generate_jwt_token(self.user)
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create client
        self.client = Client()
    
    @patch('main.api_views.ChromaTaskSyncService')
    def test_task_create_syncs_with_chromadb(self, mock_sync_service_class):
        """Test that creating a task syncs it to ChromaDB"""
        # Setup mock
        mock_service = Mock()
        mock_service.sync_create.return_value = {'success': True, 'message': 'Task synced'}
        mock_sync_service_class.return_value = mock_service
        
        # Make request
        url = f'/api/tasks/{self.item.id}'
        data = {
            'title': 'New Test Task',
            'description': 'Test task description',
            'status': 'new'
        }
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 201)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        # Verify ChromaDB sync was called
        mock_sync_service_class.assert_called_once_with(self.settings)
        mock_service.sync_create.assert_called_once()
        
        # Verify the task was passed to sync_create
        call_args = mock_service.sync_create.call_args
        task = call_args[0][0]
        self.assertEqual(task.title, 'New Test Task')
        self.assertEqual(task.description, 'Test task description')
    
    @patch('main.api_views.ChromaTaskSyncService')
    def test_task_update_syncs_with_chromadb(self, mock_sync_service_class):
        """Test that updating a task syncs it to ChromaDB"""
        # Create a task first
        task = Task.objects.create(
            title='Original Task',
            description='Original description',
            status='new',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        
        # Setup mock
        mock_service = Mock()
        mock_service.sync_update.return_value = {'success': True, 'message': 'Task updated'}
        mock_sync_service_class.return_value = mock_service
        
        # Make request
        url = f'/api/tasks/{task.id}/detail'
        data = {
            'title': 'Updated Task',
            'description': 'Updated description',
            'status': 'working'
        }
        response = self.client.put(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        # Verify ChromaDB sync was called
        mock_sync_service_class.assert_called_once_with(self.settings)
        mock_service.sync_update.assert_called_once()
        
        # Verify the task was updated
        call_args = mock_service.sync_update.call_args
        updated_task = call_args[0][0]
        self.assertEqual(updated_task.title, 'Updated Task')
        self.assertEqual(updated_task.description, 'Updated description')
        self.assertEqual(updated_task.status, 'working')
    
    @patch('main.api_views.ChromaTaskSyncService')
    def test_task_delete_syncs_with_chromadb(self, mock_sync_service_class):
        """Test that deleting a task removes it from ChromaDB"""
        # Create a task first
        task = Task.objects.create(
            title='Task to Delete',
            description='This task will be deleted',
            status='new',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        task_id = str(task.id)
        
        # Setup mock
        mock_service = Mock()
        mock_service.sync_delete.return_value = {'success': True, 'message': 'Task deleted'}
        mock_sync_service_class.return_value = mock_service
        
        # Make request
        url = f'/api/tasks/{task.id}/detail'
        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        # Verify ChromaDB sync was called
        mock_sync_service_class.assert_called_once_with(self.settings)
        mock_service.sync_delete.assert_called_once_with(task_id)
        
        # Verify the task was deleted from database
        with self.assertRaises(Task.DoesNotExist):
            Task.objects.get(id=task_id)
    
    @patch('main.api_views.ChromaTaskSyncService')
    def test_task_create_handles_sync_failure_gracefully(self, mock_sync_service_class):
        """Test that task creation succeeds even if ChromaDB sync fails"""
        # Setup mock to raise error
        mock_service = Mock()
        mock_service.sync_create.side_effect = Exception("ChromaDB connection error")
        mock_sync_service_class.return_value = mock_service
        
        # Make request
        url = f'/api/tasks/{self.item.id}'
        data = {
            'title': 'New Test Task',
            'description': 'Test task description',
            'status': 'new'
        }
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        # Verify response is still successful
        self.assertEqual(response.status_code, 201)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        # Verify task was created in database
        task = Task.objects.get(title='New Test Task')
        self.assertEqual(task.description, 'Test task description')
    
    @patch('main.api_views.ChromaTaskSyncService')
    def test_task_update_handles_sync_failure_gracefully(self, mock_sync_service_class):
        """Test that task update succeeds even if ChromaDB sync fails"""
        # Create a task first
        task = Task.objects.create(
            title='Original Task',
            description='Original description',
            status='new',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        
        # Setup mock to raise error
        mock_service = Mock()
        mock_service.sync_update.side_effect = Exception("ChromaDB connection error")
        mock_sync_service_class.return_value = mock_service
        
        # Make request
        url = f'/api/tasks/{task.id}/detail'
        data = {
            'title': 'Updated Task',
            'description': 'Updated description',
            'status': 'working'
        }
        response = self.client.put(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        # Verify response is still successful
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        # Verify task was updated in database
        task.refresh_from_db()
        self.assertEqual(task.title, 'Updated Task')
        self.assertEqual(task.description, 'Updated description')
    
    @patch('main.api_views.ChromaTaskSyncService')
    def test_task_delete_handles_sync_failure_gracefully(self, mock_sync_service_class):
        """Test that task deletion succeeds even if ChromaDB sync fails"""
        # Create a task first
        task = Task.objects.create(
            title='Task to Delete',
            description='This task will be deleted',
            status='new',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        task_id = str(task.id)
        
        # Setup mock to raise error
        mock_service = Mock()
        mock_service.sync_delete.side_effect = Exception("ChromaDB connection error")
        mock_sync_service_class.return_value = mock_service
        
        # Make request
        url = f'/api/tasks/{task.id}/detail'
        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        # Verify response is still successful
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        # Verify the task was deleted from database
        with self.assertRaises(Task.DoesNotExist):
            Task.objects.get(id=task_id)
    
    def test_task_operations_work_without_settings(self):
        """Test that task operations work even if settings are missing"""
        # Delete settings
        Settings.objects.all().delete()
        
        # Create task
        url = f'/api/tasks/{self.item.id}'
        data = {
            'title': 'New Test Task',
            'description': 'Test task description',
            'status': 'new'
        }
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        # Verify response is successful
        self.assertEqual(response.status_code, 201)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        # Verify task was created in database
        task = Task.objects.get(title='New Test Task')
        self.assertEqual(task.description, 'Test task description')
