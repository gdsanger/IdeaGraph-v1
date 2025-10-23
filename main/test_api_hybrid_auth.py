"""
Tests for hybrid authentication (JWT + Session) for task API endpoints.
"""
import json
import uuid
from django.test import TestCase, RequestFactory
from main.models import User, Item, Task, Section
from main.api_views import (
    api_task_ai_enhance,
    api_task_create_github_issue,
    api_item_ai_enhance,
    get_user_from_request
)
from main.auth_utils import generate_jwt_token


class HybridAuthenticationTestCase(TestCase):
    """Test case for hybrid authentication (JWT + Session)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('TestPassword123!')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(
            name='Test Section'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test description',
            status='new',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        
        # Generate JWT token
        self.jwt_token = generate_jwt_token(self.user)
    
    def test_get_user_from_request_with_jwt(self):
        """Test that get_user_from_request works with JWT token"""
        request = self.factory.get('/api/test')
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.jwt_token}'
        
        user = get_user_from_request(request)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user.id)
    
    def test_get_user_from_request_with_session(self):
        """Test that get_user_from_request works with session"""
        request = self.factory.get('/api/test')
        request.session = {
            'user_id': str(self.user.id)
        }
        
        user = get_user_from_request(request)
        self.assertIsNotNone(user)
        self.assertEqual(user.id, self.user.id)
    
    def test_get_user_from_request_without_auth(self):
        """Test that get_user_from_request returns None without authentication"""
        request = self.factory.get('/api/test')
        request.session = {}
        
        user = get_user_from_request(request)
        self.assertIsNone(user)
    
    def test_api_task_ai_enhance_with_session(self):
        """Test api_task_ai_enhance with session authentication"""
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        request.session = {
            'user_id': str(self.user.id)
        }
        
        # This should not return 401 (it will likely return 500 due to missing KiGate service,
        # but that's expected in unit tests - we just want to ensure auth works)
        response = api_task_ai_enhance(request, self.task.id)
        self.assertNotEqual(response.status_code, 401)
    
    def test_api_task_create_github_issue_with_session(self):
        """Test api_task_create_github_issue with session authentication"""
        # Update task to ready status
        self.task.status = 'ready'
        self.task.save()
        
        request = self.factory.post(f'/api/tasks/{self.task.id}/create-github-issue')
        request.session = {
            'user_id': str(self.user.id)
        }
        
        # This should not return 401 (it will likely return 400 due to missing GitHub repo,
        # but that's expected - we just want to ensure auth works)
        response = api_task_create_github_issue(request, self.task.id)
        self.assertNotEqual(response.status_code, 401)
    
    def test_api_item_ai_enhance_with_session(self):
        """Test api_item_ai_enhance with session authentication"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Item Title',
                'description': 'Test Item Description'
            }),
            content_type='application/json'
        )
        request.session = {
            'user_id': str(self.user.id)
        }
        
        # This should not return 401 (it will likely return 500 due to missing KiGate service,
        # but that's expected in unit tests - we just want to ensure auth works)
        response = api_item_ai_enhance(request, self.item.id)
        self.assertNotEqual(response.status_code, 401)
    
    def test_api_item_ai_enhance_with_jwt(self):
        """Test api_item_ai_enhance with JWT authentication"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Item Title',
                'description': 'Test Item Description'
            }),
            content_type='application/json'
        )
        request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.jwt_token}'
        
        # This should not return 401 (it will likely return 500 due to missing KiGate service,
        # but that's expected in unit tests - we just want to ensure auth works)
        response = api_item_ai_enhance(request, self.item.id)
        self.assertNotEqual(response.status_code, 401)
    
    def test_api_item_ai_enhance_without_auth(self):
        """Test api_item_ai_enhance without authentication returns 401"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Item Title',
                'description': 'Test Item Description'
            }),
            content_type='application/json'
        )
        request.session = {}
        
        response = api_item_ai_enhance(request, self.item.id)
        self.assertEqual(response.status_code, 401)
    
    def test_api_item_ai_enhance_missing_data(self):
        """Test api_item_ai_enhance returns 400 when title or description is missing"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': '',
                'description': ''
            }),
            content_type='application/json'
        )
        request.session = {
            'user_id': str(self.user.id)
        }
        
        response = api_item_ai_enhance(request, self.item.id)
        self.assertEqual(response.status_code, 400)
    
    def test_api_item_ai_enhance_access_denied(self):
        """Test api_item_ai_enhance returns 403 for unauthorized user"""
        # Create another user
        other_user = User(
            username='anotheruser',
            email='another@example.com',
            role='user',
            is_active=True
        )
        other_user.set_password('AnotherPassword123!')
        other_user.save()
        
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Item Title',
                'description': 'Test Item Description'
            }),
            content_type='application/json'
        )
        request.session = {
            'user_id': str(other_user.id)
        }
        
        response = api_item_ai_enhance(request, self.item.id)
        self.assertEqual(response.status_code, 403)
