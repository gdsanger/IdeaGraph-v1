"""
Test Task Move functionality
"""
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, Section, Settings, TaskFile
from unittest.mock import Mock, patch, MagicMock
from core.services.task_move_service import TaskMoveService, TaskMoveServiceError
import json
import uuid


class TaskMoveServiceTest(TestCase):
    """Test TaskMoveService"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test items
        self.item1 = Item.objects.create(
            title='Test Item 1',
            description='Test item 1 description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        self.item2 = Item.objects.create(
            title='Test Item 2',
            description='Test item 2 description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item1,
            created_by=self.user
        )
        
        # Create settings
        self.settings = Settings.objects.create(
            graph_api_enabled=False  # Disable for unit tests
        )
    
    @patch('core.services.task_move_service.GraphService')
    def test_move_task_without_files(self, mock_graph_service):
        """Test moving a task without files"""
        service = TaskMoveService(self.settings)
        
        # Move task from item1 to item2
        result = service.move_task(
            task_id=str(self.task.id),
            target_item_id=str(self.item2.id),
            user=self.user
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertTrue(result['moved'])
        self.assertEqual(result['files_count'], 0)
        
        # Verify task was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.item.id, self.item2.id)
    
    @patch('core.services.task_move_service.GraphService')
    def test_move_task_with_files(self, mock_graph_service):
        """Test moving a task with files"""
        # Create mock task files
        task_file1 = TaskFile.objects.create(
            task=self.task,
            filename='test1.pdf',
            file_size=1024,
            sharepoint_file_id='file-123',
            sharepoint_url='https://sharepoint.com/file1',
            content_type='application/pdf',
            uploaded_by=self.user
        )
        
        task_file2 = TaskFile.objects.create(
            task=self.task,
            filename='test2.docx',
            file_size=2048,
            sharepoint_file_id='file-456',
            sharepoint_url='https://sharepoint.com/file2',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            uploaded_by=self.user
        )
        
        # Mock graph service methods
        mock_instance = mock_graph_service.return_value
        mock_instance.get_folder_by_path.side_effect = [
            # First call: check if item folder exists
            {'success': True, 'exists': True, 'folder_id': 'item2-folder-id'},
            # Second call: check if task folder exists
            {'success': True, 'exists': True, 'folder_id': 'task-folder-id'}
        ]
        mock_instance.move_folder.return_value = {
            'success': True,
            'folder_id': 'moved-folder-id',
            'folder_name': str(self.task.id)
        }
        
        service = TaskMoveService(self.settings)
        service.graph_service = mock_instance
        
        # Move task from item1 to item2
        result = service.move_task(
            task_id=str(self.task.id),
            target_item_id=str(self.item2.id),
            user=self.user
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertTrue(result['moved'])
        self.assertEqual(result['files_count'], 2)
        
        # Verify task was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.item.id, self.item2.id)
    
    def test_move_task_to_same_item(self):
        """Test moving a task to its current item"""
        service = TaskMoveService(self.settings)
        
        # Try to move task to its current item
        result = service.move_task(
            task_id=str(self.task.id),
            target_item_id=str(self.item1.id),
            user=self.user
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertFalse(result['moved'])
        self.assertIn('already in the target item', result['message'])
    
    def test_move_task_invalid_task_id(self):
        """Test moving a non-existent task"""
        service = TaskMoveService(self.settings)
        
        # Try to move non-existent task
        with self.assertRaises(TaskMoveServiceError) as context:
            service.move_task(
                task_id=str(uuid.uuid4()),
                target_item_id=str(self.item2.id),
                user=self.user
            )
        
        self.assertIn('Task not found', str(context.exception))
    
    def test_move_task_invalid_target_item_id(self):
        """Test moving a task to a non-existent item"""
        service = TaskMoveService(self.settings)
        
        # Try to move task to non-existent item
        with self.assertRaises(TaskMoveServiceError) as context:
            service.move_task(
                task_id=str(self.task.id),
                target_item_id=str(uuid.uuid4()),
                user=self.user
            )
        
        self.assertIn('Target item not found', str(context.exception))
    
    @patch('core.services.task_move_service.GraphService')
    def test_ensure_item_folder_creates_folder(self, mock_graph_service):
        """Test that ensure_item_folder_exists creates folder when it doesn't exist"""
        # Mock graph service
        mock_instance = mock_graph_service.return_value
        mock_instance.get_folder_by_path.return_value = {
            'success': True,
            'exists': False
        }
        mock_instance.create_folder.return_value = {
            'success': True,
            'folder_id': 'new-folder-id',
            'folder_name': 'Test_Item_2'
        }
        
        service = TaskMoveService(self.settings)
        service.graph_service = mock_instance
        
        # Ensure folder exists
        result = service._ensure_item_folder_exists(self.item2)
        
        # Verify folder was created
        self.assertTrue(result['success'])
        self.assertTrue(result['created'])
        self.assertEqual(result['folder_id'], 'new-folder-id')
        
        # Verify create_folder was called
        mock_instance.create_folder.assert_called_once()


class TaskMoveAPITest(TestCase):
    """Test Task Move API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create another user
        self.other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='developer',
            is_active=True
        )
        self.other_user.set_password('testpass123')
        self.other_user.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test items
        self.item1 = Item.objects.create(
            title='Test Item 1',
            description='Test item 1 description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        self.item2 = Item.objects.create(
            title='Test Item 2',
            description='Test item 2 description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item1,
            created_by=self.user
        )
        
        # Create settings
        self.settings = Settings.objects.create(
            graph_api_enabled=False
        )
        
        # Create client
        self.client = Client()
    
    def login(self, user=None):
        """Helper to log in a user"""
        if user is None:
            user = self.user
        session = self.client.session
        session['user_id'] = str(user.id)
        session.save()
    
    @patch('core.services.task_move_service.TaskMoveService.move_task')
    def test_api_task_move_success(self, mock_move_task):
        """Test API task move endpoint success"""
        self.login()
        
        # Mock the move_task method
        mock_move_task.return_value = {
            'success': True,
            'message': 'Task moved successfully',
            'moved': True,
            'files_moved': False,
            'files_count': 0,
            'task_id': str(self.task.id),
            'source_item_id': str(self.item1.id),
            'target_item_id': str(self.item2.id)
        }
        
        url = reverse('main:api_task_move', args=[self.task.id])
        data = {
            'target_item_id': str(self.item2.id)
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertTrue(response_data['moved'])
    
    def test_api_task_move_requires_authentication(self):
        """Test that API task move requires authentication"""
        url = reverse('main:api_task_move', args=[self.task.id])
        data = {
            'target_item_id': str(self.item2.id)
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_api_task_move_permission_denied(self):
        """Test that users can't move other users' tasks"""
        self.login(self.other_user)
        
        url = reverse('main:api_task_move', args=[self.task.id])
        data = {
            'target_item_id': str(self.item2.id)
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_api_task_move_missing_target_item_id(self):
        """Test that target_item_id is required"""
        self.login()
        
        url = reverse('main:api_task_move', args=[self.task.id])
        data = {}
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('target_item_id is required', response_data['error'])
    
    def test_api_task_move_invalid_task_id(self):
        """Test moving a non-existent task"""
        self.login()
        
        url = reverse('main:api_task_move', args=[uuid.uuid4()])
        data = {
            'target_item_id': str(self.item2.id)
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
