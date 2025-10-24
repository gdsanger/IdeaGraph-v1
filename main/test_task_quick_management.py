"""
Tests for Quick Task Management API endpoints
"""
import json
import uuid
from django.test import TestCase, Client
from main.models import User, Item, Task, Settings


class TaskQuickManagementTest(TestCase):
    """Test Quick Task Management API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False,
            weaviate_url='http://localhost:8081',
            weaviate_api_key='',
            github_api_enabled=False
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
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
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in a user"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def get_jwt_token(self):
        """Helper to get JWT token for API calls"""
        from main.auth_utils import generate_jwt_token
        return generate_jwt_token(self.user)
    
    def test_quick_status_update(self):
        """Test task quick status update endpoint"""
        self.login_user()
        token = self.get_jwt_token()
        
        response = self.client.post(
            f'/api/tasks/{self.task.id}/quick-status-update',
            data=json.dumps({'status': 'working'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'working')
        
        # Verify task was updated in database
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'working')
    
    def test_quick_status_update_invalid_status(self):
        """Test task quick status update with invalid status"""
        self.login_user()
        token = self.get_jwt_token()
        
        response = self.client.post(
            f'/api/tasks/{self.task.id}/quick-status-update',
            data=json.dumps({'status': 'invalid_status'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    def test_quick_status_update_to_done(self):
        """Test task quick status update to done status"""
        self.login_user()
        token = self.get_jwt_token()
        
        response = self.client.post(
            f'/api/tasks/{self.task.id}/quick-status-update',
            data=json.dumps({'status': 'done'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['status'], 'done')
        
        # Verify task was marked as done with completed_at timestamp
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'done')
        self.assertIsNotNone(self.task.completed_at)
    
    def test_quick_delete(self):
        """Test task quick delete endpoint"""
        self.login_user()
        token = self.get_jwt_token()
        
        task_id = self.task.id
        
        response = self.client.post(
            f'/api/tasks/{task_id}/quick-delete',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify task was deleted from database
        self.assertFalse(Task.objects.filter(id=task_id).exists())
    
    def test_quick_delete_nonexistent_task(self):
        """Test task quick delete for non-existent task"""
        self.login_user()
        token = self.get_jwt_token()
        
        fake_task_id = uuid.uuid4()
        
        response = self.client.post(
            f'/api/tasks/{fake_task_id}/quick-delete',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)
    
    def test_unauthorized_access(self):
        """Test endpoints require authentication"""
        # Test status update without auth
        response = self.client.post(
            f'/api/tasks/{self.task.id}/quick-status-update',
            data=json.dumps({'status': 'working'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
        
        # Test delete without auth
        response = self.client.post(
            f'/api/tasks/{self.task.id}/quick-delete'
        )
        self.assertEqual(response.status_code, 401)
