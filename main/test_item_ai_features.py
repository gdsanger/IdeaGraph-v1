"""
Tests for Item AI Features (AI Enhance, Build Tasks, Check Similarity)
"""
import json
from django.test import TestCase, RequestFactory
from main.models import User, Item, Section, Settings
from main.api_views import api_item_ai_enhance, api_item_build_tasks, api_item_check_similarity


class ItemAIFeaturesTestCase(TestCase):
    """Test case for Item AI features"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        self.user.set_password('testpass123!')
        self.user.save()
        
        # Create a section
        self.section = Section.objects.create(
            name='Test Section'
        )
        
        # Create an item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            section=self.section,
            status='ready',
            created_by=self.user
        )
        
        # Create settings (required for KiGate and ChromaDB services)
        self.settings = Settings.objects.create(
            max_tags_per_idea=5,
            kigate_api_enabled=False,  # Disabled by default for tests
            kigate_api_token='test-token',
            kigate_api_base_url='http://localhost:8000'
        )
    
    def test_api_item_ai_enhance_authentication(self):
        """Test that AI enhance requires authentication"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        # Add empty session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # No authentication
        response = api_item_ai_enhance(request, self.item.id)
        self.assertEqual(response.status_code, 401)
    
    def test_api_item_ai_enhance_with_session(self):
        """Test AI enhance with session authentication"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        # Add session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['user_id'] = str(self.user.id)
        request.session.save()
        
        # This will fail due to KiGate not being configured, but should not return 401
        response = api_item_ai_enhance(request, self.item.id)
        self.assertNotEqual(response.status_code, 401)
    
    def test_api_item_build_tasks_authentication(self):
        """Test that build tasks requires authentication"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/build-tasks',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        # Add empty session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # No authentication
        response = api_item_build_tasks(request, self.item.id)
        self.assertEqual(response.status_code, 401)
    
    def test_api_item_build_tasks_with_session(self):
        """Test build tasks with session authentication"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/build-tasks',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        # Add session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['user_id'] = str(self.user.id)
        request.session.save()
        
        # This will fail due to KiGate not being configured, but should not return 401
        response = api_item_build_tasks(request, self.item.id)
        self.assertNotEqual(response.status_code, 401)
    
    def test_api_item_check_similarity_authentication(self):
        """Test that check similarity requires authentication"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/check-similarity',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        # Add empty session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # No authentication
        response = api_item_check_similarity(request, self.item.id)
        self.assertEqual(response.status_code, 401)
    
    def test_api_item_check_similarity_with_session(self):
        """Test check similarity with session authentication"""
        request = self.factory.post(
            f'/api/items/{self.item.id}/check-similarity',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        # Add session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['user_id'] = str(self.user.id)
        request.session.save()
        
        # This will fail due to ChromaDB not being configured, but should not return 401
        response = api_item_check_similarity(request, self.item.id)
        self.assertNotEqual(response.status_code, 401)
    
    def test_api_item_build_tasks_ownership(self):
        """Test that users can only build tasks for their own items"""
        # Create another user
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='developer'
        )
        other_user.set_password('testpass123!')
        other_user.save()
        
        request = self.factory.post(
            f'/api/items/{self.item.id}/build-tasks',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        # Add session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['user_id'] = str(other_user.id)
        request.session.save()
        
        response = api_item_build_tasks(request, self.item.id)
        self.assertEqual(response.status_code, 403)
    
    def test_api_item_check_similarity_ownership(self):
        """Test that users can only check similarity for their own items"""
        # Create another user
        other_user = User.objects.create(
            username='otheruser2',
            email='other2@example.com',
            role='developer'
        )
        other_user.set_password('testpass123!')
        other_user.save()
        
        request = self.factory.post(
            f'/api/items/{self.item.id}/check-similarity',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        # Add session
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['user_id'] = str(other_user.id)
        request.session.save()
        
        response = api_item_check_similarity(request, self.item.id)
        self.assertEqual(response.status_code, 403)
