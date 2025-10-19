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
    
    def test_api_item_ai_enhance_with_mocked_kigate(self):
        """Test AI enhance with mocked KiGate service responses"""
        from unittest.mock import patch, Mock
        
        # Enable KiGate API for this test
        self.settings.kigate_api_enabled = True
        self.settings.save()
        
        # Mock the KiGate service execute_agent method
        with patch('main.api_views.KiGateService') as mock_kigate_class:
            mock_kigate = Mock()
            mock_kigate_class.return_value = mock_kigate
            
            # Mock responses for the three agent calls
            def execute_agent_side_effect(agent_name, **kwargs):
                if agent_name == 'text-optimization-agent':
                    return {
                        'success': True,
                        'result': 'Dies ist ein verbesserter Beschreibungstext mit korrigierter Rechtschreibung und Grammatik.'
                    }
                elif agent_name == 'text-to-title-generator':
                    return {
                        'success': True,
                        'result': 'Verbesserter Titel'
                    }
                elif agent_name == 'text-keyword-extractor-de':
                    return {
                        'success': True,
                        'result': 'Python, Django, Test, KI, API'
                    }
                return {'success': False, 'error': 'Unknown agent'}
            
            mock_kigate.execute_agent.side_effect = execute_agent_side_effect
            
            # Create request
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
            
            # Call the API
            response = api_item_ai_enhance(request, self.item.id)
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertEqual(data['title'], 'Verbesserter Titel')
            self.assertIn('verbesserter Beschreibungstext', data['description'])
            self.assertEqual(len(data['tags']), 5)
            self.assertIn('Python', data['tags'])
            self.assertIn('Django', data['tags'])
            
            # Verify that all three agents were called
            self.assertEqual(mock_kigate.execute_agent.call_count, 3)
            
            # Verify agent calls
            calls = mock_kigate.execute_agent.call_args_list
            self.assertEqual(calls[0][1]['agent_name'], 'text-optimization-agent')
            self.assertEqual(calls[1][1]['agent_name'], 'text-to-title-generator')
            self.assertEqual(calls[2][1]['agent_name'], 'text-keyword-extractor-de')
            
            # Verify tags were attached to item
            self.item.refresh_from_db()
            item_tags = list(self.item.tags.values_list('name', flat=True))
            self.assertEqual(len(item_tags), 5)
            self.assertIn('Python', item_tags)
            self.assertIn('Django', item_tags)
            
            # Verify AI flags were set
            self.assertTrue(self.item.ai_enhanced)
            self.assertTrue(self.item.ai_tags_generated)
    
    def test_api_item_ai_enhance_replaces_existing_tags(self):
        """Test that AI enhance replaces existing tags instead of adding to them"""
        from unittest.mock import patch, Mock
        from main.models import Tag
        
        # Enable KiGate API for this test
        self.settings.kigate_api_enabled = True
        self.settings.save()
        
        # Add some existing tags to the item
        tag1 = Tag.objects.create(name='OldTag1')
        tag2 = Tag.objects.create(name='OldTag2')
        self.item.tags.add(tag1, tag2)
        self.assertEqual(self.item.tags.count(), 2)
        
        # Mock the KiGate service
        with patch('main.api_views.KiGateService') as mock_kigate_class:
            mock_kigate = Mock()
            mock_kigate_class.return_value = mock_kigate
            
            def execute_agent_side_effect(agent_name, **kwargs):
                if agent_name == 'text-optimization-agent':
                    return {'success': True, 'result': 'Enhanced description'}
                elif agent_name == 'text-to-title-generator':
                    return {'success': True, 'result': 'Enhanced Title'}
                elif agent_name == 'text-keyword-extractor-de':
                    return {'success': True, 'result': 'NewTag1, NewTag2, NewTag3'}
                return {'success': False, 'error': 'Unknown agent'}
            
            mock_kigate.execute_agent.side_effect = execute_agent_side_effect
            
            # Create request
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
            
            # Call the API
            response = api_item_ai_enhance(request, self.item.id)
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            
            # Verify old tags were replaced with new ones
            self.item.refresh_from_db()
            item_tags = list(self.item.tags.values_list('name', flat=True))
            self.assertEqual(len(item_tags), 3)
            self.assertIn('NewTag1', item_tags)
            self.assertIn('NewTag2', item_tags)
            self.assertIn('NewTag3', item_tags)
            self.assertNotIn('OldTag1', item_tags)
            self.assertNotIn('OldTag2', item_tags)
    
    def test_api_item_ai_enhance_handles_numbered_keywords(self):
        """Test that AI enhance correctly parses numbered or bulleted keywords"""
        from unittest.mock import patch, Mock
        
        # Enable KiGate API for this test
        self.settings.kigate_api_enabled = True
        self.settings.save()
        
        # Mock the KiGate service
        with patch('main.api_views.KiGateService') as mock_kigate_class:
            mock_kigate = Mock()
            mock_kigate_class.return_value = mock_kigate
            
            def execute_agent_side_effect(agent_name, **kwargs):
                if agent_name == 'text-optimization-agent':
                    return {'success': True, 'result': 'Enhanced description'}
                elif agent_name == 'text-to-title-generator':
                    return {'success': True, 'result': 'Enhanced Title'}
                elif agent_name == 'text-keyword-extractor-de':
                    # Return keywords in various formats (numbered, bulleted, newlines)
                    return {'success': True, 'result': '1. Tag1\n2. Tag2\n- Tag3\n* Tag4\n5. Tag5'}
                return {'success': False, 'error': 'Unknown agent'}
            
            mock_kigate.execute_agent.side_effect = execute_agent_side_effect
            
            # Create request
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
            
            # Call the API
            response = api_item_ai_enhance(request, self.item.id)
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            
            # Verify tags were correctly parsed (without numbers/bullets)
            self.assertEqual(len(data['tags']), 5)
            self.assertIn('Tag1', data['tags'])
            self.assertIn('Tag2', data['tags'])
            self.assertIn('Tag3', data['tags'])
            self.assertIn('Tag4', data['tags'])
            self.assertIn('Tag5', data['tags'])
