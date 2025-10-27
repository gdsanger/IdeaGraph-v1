"""
Tests for chat widget API endpoint (api_item_chat_ask)
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Tag, Client as ClientModel, Section, Settings
from unittest.mock import patch, MagicMock


class ChatWidgetAPITestCase(TestCase):
    """Test case for chat widget Q&A API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('testpassword123')
        self.user.save()
        
        # Create test client and section
        self.client_obj = ClientModel.objects.create(name='Test Client')
        self.section = Section.objects.create(name='Test Section')
        
        # Create test tag
        self.tag = Tag.objects.create(name='test-tag')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='This is a test item for chat widget testing',
            status='new',
            section=self.section
        )
        self.item.tags.add(self.tag)
        self.item.clients.add(self.client_obj)
        
        # Create settings
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test-token',
            kigate_api_timeout=30,
            weaviate_cloud_enabled=False
        )
        
        # Set up test client for requests
        self.test_client = Client()
        
        # Login using session
        session = self.test_client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    @patch('core.services.weaviate_search_service.WeaviateSearchService._initialize_client')
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_search_service.WeaviateSearchService.search')
    def test_chat_ask_success_with_context(self, mock_search, mock_agent, mock_init):
        """Test successful chat Q&A with Weaviate context"""
        # Mock Weaviate initialization to prevent connection attempt
        mock_init.return_value = None
        
        # Mock Weaviate search results
        mock_search.return_value = {
            'success': True,
            'results': [
                {
                    'title': 'Related Document',
                    'content': 'Some relevant content about the topic',
                    'object_type': 'File',
                    'score': 0.85,
                    'object_id': 'doc-123'
                }
            ]
        }
        
        # Mock KiGate agent response
        mock_agent.return_value = {
            'success': True,
            'result': 'Based on the context, the answer to your question is...'
        }
        
        # Make request
        url = reverse('main:api_item_chat_ask', kwargs={'item_id': self.item.id})
        response = self.test_client.post(
            url,
            data=json.dumps({'question': 'What is this item about?'}),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('answer', data)
        self.assertIn('sources', data)
        self.assertEqual(len(data['sources']), 1)
        self.assertEqual(data['sources'][0]['title'], 'Related Document')
        self.assertTrue(data['has_context'])
        
        # Verify mocks were called
        mock_search.assert_called()
        mock_agent.assert_called_once()
    
    @patch('core.services.weaviate_search_service.WeaviateSearchService._initialize_client')
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_search_service.WeaviateSearchService.search')
    def test_chat_ask_success_without_context(self, mock_search, mock_agent, mock_init):
        """Test successful chat Q&A without Weaviate context"""
        # Mock Weaviate initialization to prevent connection attempt
        mock_init.return_value = None
        # Mock Weaviate search with no results
        mock_search.return_value = {
            'success': True,
            'results': []
        }
        
        # Mock KiGate agent response
        mock_agent.return_value = {
            'success': True,
            'result': 'Based on the item information, here is my answer...'
        }
        
        # Make request
        url = reverse('main:api_item_chat_ask', kwargs={'item_id': self.item.id})
        response = self.test_client.post(
            url,
            data=json.dumps({'question': 'Tell me about this item'}),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('answer', data)
        self.assertEqual(len(data['sources']), 0)
        self.assertFalse(data['has_context'])
        
        # Verify agent was called
        mock_agent.assert_called_once()
    
    def test_chat_ask_missing_question(self):
        """Test chat Q&A with missing question"""
        url = reverse('main:api_item_chat_ask', kwargs={'item_id': self.item.id})
        response = self.test_client.post(
            url,
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_chat_ask_empty_question(self):
        """Test chat Q&A with empty question"""
        url = reverse('main:api_item_chat_ask', kwargs={'item_id': self.item.id})
        response = self.test_client.post(
            url,
            data=json.dumps({'question': '   '}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_chat_ask_item_not_found(self):
        """Test chat Q&A with non-existent item"""
        url = reverse('main:api_item_chat_ask', kwargs={'item_id': '00000000-0000-0000-0000-000000000000'})
        response = self.test_client.post(
            url,
            data=json.dumps({'question': 'What is this?'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_chat_ask_authentication_required(self):
        """Test chat Q&A without authentication"""
        # Create new client without session
        unauthenticated_client = Client()
        
        url = reverse('main:api_item_chat_ask', kwargs={'item_id': self.item.id})
        response = unauthenticated_client.post(
            url,
            data=json.dumps({'question': 'What is this?'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_chat_ask_invalid_json(self):
        """Test chat Q&A with invalid JSON"""
        url = reverse('main:api_item_chat_ask', kwargs={'item_id': self.item.id})
        response = self.test_client.post(
            url,
            data='invalid json{',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    @patch('core.services.weaviate_search_service.WeaviateSearchService._initialize_client')
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_search_service.WeaviateSearchService.search')
    def test_chat_ask_kigate_error(self, mock_search, mock_agent, mock_init):
        """Test chat Q&A when KiGate service fails"""
        # Mock Weaviate initialization
        mock_init.return_value = None
        # Mock Weaviate search
        mock_search.return_value = {
            'success': True,
            'results': []
        }
        
        # Mock KiGate agent error
        mock_agent.return_value = {
            'success': False,
            'error': 'KiGate service unavailable'
        }
        
        # Make request
        url = reverse('main:api_item_chat_ask', kwargs={'item_id': self.item.id})
        response = self.test_client.post(
            url,
            data=json.dumps({'question': 'What is this?'}),
            content_type='application/json'
        )
        
        # Should return error
        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    @patch('core.services.weaviate_search_service.WeaviateSearchService._initialize_client')
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_search_service.WeaviateSearchService.search')
    def test_chat_ask_weaviate_error_continues(self, mock_search, mock_agent, mock_init):
        """Test chat Q&A continues even if Weaviate search fails"""
        # Mock Weaviate initialization
        mock_init.return_value = None
        # Mock Weaviate search error
        from core.services.weaviate_search_service import WeaviateSearchServiceError
        mock_search.side_effect = WeaviateSearchServiceError('Connection failed')
        
        # Mock KiGate agent response
        mock_agent.return_value = {
            'success': True,
            'result': 'Answer based on item information only'
        }
        
        # Make request
        url = reverse('main:api_item_chat_ask', kwargs={'item_id': self.item.id})
        response = self.test_client.post(
            url,
            data=json.dumps({'question': 'What is this?'}),
            content_type='application/json'
        )
        
        # Should still succeed without context
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertFalse(data['has_context'])
        self.assertEqual(len(data['sources']), 0)
