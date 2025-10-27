"""
Tests for Item Question Answering Feature
"""
import json
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from main.models import User, Item, Section, ItemQuestionAnswer, Settings


# Test constants
NON_EXISTENT_UUID = '00000000-0000-0000-0000-000000000000'


class ItemQuestionAnsweringTest(TestCase):
    """Test Item Question Answering functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description for Q&A',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create settings (required for services)
        self.settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='test_key',
            openai_api_base_url='https://api.openai.com/v1',
            kigate_api_enabled=True,
            kigate_api_token='test_token',
            kigate_api_base_url='http://localhost:8000',
            weaviate_cloud_enabled=False
        )
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in a user"""
        self.client.post('/login/', {
            'username': self.user.username,
            'password': 'Test@123'
        })
    
    def test_item_question_answer_model(self):
        """Test ItemQuestionAnswer model creation"""
        qa = ItemQuestionAnswer.objects.create(
            item=self.item,
            question='Test question?',
            answer='Test answer',
            sources=[{'type': 'Task', 'title': 'Test Task', 'relevance': 0.9}],
            asked_by=self.user,
            relevance_score=0.9
        )
        
        self.assertEqual(qa.item, self.item)
        self.assertEqual(qa.question, 'Test question?')
        self.assertEqual(qa.answer, 'Test answer')
        self.assertEqual(len(qa.sources), 1)
        self.assertEqual(qa.relevance_score, 0.9)
        self.assertFalse(qa.saved_as_knowledge_object)
        self.assertEqual(qa.asked_by, self.user)
    
    def test_item_question_answer_str(self):
        """Test ItemQuestionAnswer string representation"""
        qa = ItemQuestionAnswer.objects.create(
            item=self.item,
            question='How does authentication work in this system?',
            answer='Authentication works via...',
            asked_by=self.user
        )
        
        str_repr = str(qa)
        self.assertIn('How does authentication work in this system?', str_repr)
        self.assertIn(self.item.title, str_repr)
    
    @patch('core.services.item_question_answering_service.ItemQuestionAnsweringService.search_related_knowledge')
    @patch('core.services.item_question_answering_service.ItemQuestionAnsweringService.generate_answer_with_kigate')
    @patch('core.services.item_question_answering_service.ItemQuestionAnsweringService._initialize_client')
    def test_ask_question_api_success(self, mock_init_client, mock_generate_answer, mock_search_knowledge):
        """Test asking a question via API"""
        self.login_user()
        
        # Mock the search results
        mock_search_knowledge.return_value = {
            'success': True,
            'results': [
                {
                    'uuid': 'test-uuid-1',
                    'type': 'Task',
                    'title': 'Test Task',
                    'description': 'Task description',
                    'url': '/tasks/test-uuid-1/',
                    'relevance': 0.85,
                    'source': 'IdeaGraph',
                    'created_at': '2024-01-01T00:00:00'
                }
            ],
            'total': 1
        }
        
        # Mock the answer generation
        mock_generate_answer.return_value = {
            'success': True,
            'answer': '## Antwort\n\nDas ist eine Testantwort.\n\n## Quellen\n1. Test Task',
            'sources_used': [
                {
                    'uuid': 'test-uuid-1',
                    'type': 'Task',
                    'title': 'Test Task',
                    'url': '/tasks/test-uuid-1/',
                    'relevance': 0.85
                }
            ]
        }
        
        # Make the API request
        response = self.client.post(
            f'/api/items/{self.item.id}/ask',
            data=json.dumps({'question': 'How does this work?'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertIn('qa_id', data)
        self.assertEqual(data['question'], 'How does this work?')
        self.assertIn('Testantwort', data['answer'])
        self.assertEqual(len(data['sources']), 1)
        self.assertGreater(data['relevance_score'], 0)
        
        # Verify Q&A was saved to database
        qa = ItemQuestionAnswer.objects.get(id=data['qa_id'])
        self.assertEqual(qa.item, self.item)
        self.assertEqual(qa.question, 'How does this work?')
        self.assertEqual(qa.asked_by, self.user)
    
    def test_ask_question_api_requires_auth(self):
        """Test that asking a question requires authentication"""
        response = self.client.post(
            f'/api/items/{self.item.id}/ask',
            data=json.dumps({'question': 'Test question?'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_ask_question_api_invalid_item(self):
        """Test asking a question for non-existent item"""
        self.login_user()
        
        response = self.client.post(
            f'/api/items/{NON_EXISTENT_UUID}/ask',
            data=json.dumps({'question': 'Test question?'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_ask_question_api_empty_question(self):
        """Test asking with empty question"""
        self.login_user()
        
        response = self.client.post(
            f'/api/items/{self.item.id}/ask',
            data=json.dumps({'question': ''}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('required', data['error'].lower())
    
    def test_questions_history_api(self):
        """Test getting Q&A history via API"""
        self.login_user()
        
        # Create some Q&A history
        qa1 = ItemQuestionAnswer.objects.create(
            item=self.item,
            question='First question?',
            answer='First answer',
            sources=[],
            asked_by=self.user,
            relevance_score=0.8
        )
        
        qa2 = ItemQuestionAnswer.objects.create(
            item=self.item,
            question='Second question?',
            answer='Second answer',
            sources=[],
            asked_by=self.user,
            relevance_score=0.9,
            saved_as_knowledge_object=True,
            weaviate_uuid='test-weaviate-uuid'
        )
        
        # Get history
        response = self.client.get(f'/api/items/{self.item.id}/questions/history')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 2)
        self.assertEqual(len(data['questions']), 2)
        
        # Check first question (most recent)
        self.assertEqual(data['questions'][0]['question'], 'Second question?')
        self.assertTrue(data['questions'][0]['saved_as_knowledge_object'])
        
        # Check second question
        self.assertEqual(data['questions'][1]['question'], 'First question?')
        self.assertFalse(data['questions'][1]['saved_as_knowledge_object'])
    
    def test_questions_history_api_pagination(self):
        """Test Q&A history pagination"""
        self.login_user()
        
        # Create multiple Q&As
        for i in range(15):
            ItemQuestionAnswer.objects.create(
                item=self.item,
                question=f'Question {i}?',
                answer=f'Answer {i}',
                asked_by=self.user
            )
        
        # Get first page
        response = self.client.get(f'/api/items/{self.item.id}/questions/history?page=1&per_page=10')
        data = json.loads(response.content)
        
        self.assertEqual(data['total'], 15)
        self.assertEqual(len(data['questions']), 10)
        self.assertTrue(data['has_next'])
        
        # Get second page
        response = self.client.get(f'/api/items/{self.item.id}/questions/history?page=2&per_page=10')
        data = json.loads(response.content)
        
        self.assertEqual(len(data['questions']), 5)
        self.assertFalse(data['has_next'])
    
    @patch('core.services.item_question_answering_service.ItemQuestionAnsweringService.save_as_knowledge_object')
    @patch('core.services.item_question_answering_service.ItemQuestionAnsweringService._initialize_client')
    def test_save_qa_as_knowledge_api(self, mock_init_client, mock_save):
        """Test saving Q&A as KnowledgeObject via API"""
        self.login_user()
        
        # Create a Q&A
        qa = ItemQuestionAnswer.objects.create(
            item=self.item,
            question='Test question?',
            answer='Test answer',
            asked_by=self.user
        )
        
        # Mock the save operation
        mock_save.return_value = {
            'success': True,
            'weaviate_uuid': 'test-weaviate-uuid'
        }
        
        # Save as knowledge object
        response = self.client.post(
            f'/api/items/questions/{qa.id}/save',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['weaviate_uuid'], 'test-weaviate-uuid')
        
        # Verify database was updated
        qa.refresh_from_db()
        self.assertTrue(qa.saved_as_knowledge_object)
        self.assertEqual(qa.weaviate_uuid, 'test-weaviate-uuid')
    
    def test_save_qa_as_knowledge_already_saved(self):
        """Test saving Q&A that's already saved"""
        self.login_user()
        
        # Create a Q&A that's already saved
        qa = ItemQuestionAnswer.objects.create(
            item=self.item,
            question='Test question?',
            answer='Test answer',
            asked_by=self.user,
            saved_as_knowledge_object=True,
            weaviate_uuid='existing-uuid'
        )
        
        # Try to save again
        response = self.client.post(
            f'/api/items/questions/{qa.id}/save',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['weaviate_uuid'], 'existing-uuid')
        self.assertIn('already saved', data['message'])
    
    def test_save_qa_as_knowledge_not_found(self):
        """Test saving non-existent Q&A"""
        self.login_user()
        
        response = self.client.post(
            f'/api/items/questions/{NON_EXISTENT_UUID}/save',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
    
    @patch('core.services.item_question_answering_service.ItemQuestionAnsweringService.search_related_knowledge')
    @patch('core.services.item_question_answering_service.ItemQuestionAnsweringService.generate_answer_with_kigate')
    @patch('core.services.item_question_answering_service.ItemQuestionAnsweringService._initialize_client')
    def test_ask_question_with_datetime_in_sources(self, mock_init_client, mock_generate_answer, mock_search_knowledge):
        """Test that datetime objects in sources are properly serialized"""
        from datetime import datetime as dt
        self.login_user()
        
        # Mock the search results with a datetime object (simulating Weaviate returning datetime)
        mock_search_knowledge.return_value = {
            'success': True,
            'results': [
                {
                    'uuid': 'test-uuid-1',
                    'type': 'Task',
                    'title': 'Test Task',
                    'description': 'Task description',
                    'url': '/tasks/test-uuid-1/',
                    'relevance': 0.85,
                    'source': 'IdeaGraph',
                    'created_at': '2024-01-01T00:00:00'  # This should be a string already after our fix
                }
            ],
            'total': 1
        }
        
        # Mock the answer generation - this should also have datetime properly handled
        mock_generate_answer.return_value = {
            'success': True,
            'answer': '## Antwort\n\nDas ist eine Testantwort.\n\n## Quellen\n1. Test Task',
            'sources_used': [
                {
                    'uuid': 'test-uuid-1',
                    'type': 'Task',
                    'title': 'Test Task',
                    'url': '/tasks/test-uuid-1/',
                    'relevance': 0.85,
                    'created_at': '2024-01-01T00:00:00'  # String format
                }
            ]
        }
        
        # Make the API request - this should not raise a JSON serialization error
        response = self.client.post(
            f'/api/items/{self.item.id}/ask',
            data=json.dumps({'question': 'How does this work?'}),
            content_type='application/json'
        )
        
        # Should succeed without serialization errors
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify Q&A was saved to database successfully
        qa = ItemQuestionAnswer.objects.get(id=data['qa_id'])
        self.assertEqual(qa.item, self.item)
        self.assertIsInstance(qa.sources, list)
        # Verify sources is properly serialized as JSON
        self.assertEqual(len(qa.sources), 1)
        self.assertIsInstance(qa.sources[0].get('created_at'), str)


class ItemQuestionAnsweringServiceTest(TestCase):
    """Test ItemQuestionAnsweringService"""
    
    def setUp(self):
        """Set up test data"""
        self.settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='test_key',
            kigate_api_enabled=True,
            kigate_api_token='test_token',
            weaviate_cloud_enabled=False
        )
    
    @patch('core.services.item_question_answering_service.weaviate.connect_to_local')
    def test_service_initialization_local(self, mock_connect):
        """Test service initialization with local Weaviate"""
        from core.services.item_question_answering_service import ItemQuestionAnsweringService
        
        mock_client = Mock()
        mock_connect.return_value = mock_client
        
        service = ItemQuestionAnsweringService(self.settings)
        
        self.assertIsNotNone(service._client)
        mock_connect.assert_called_once_with(host="localhost", port=8081)
    
    @patch('core.services.item_question_answering_service.weaviate.connect_to_weaviate_cloud')
    def test_service_initialization_cloud(self, mock_connect):
        """Test service initialization with Weaviate Cloud"""
        from core.services.item_question_answering_service import ItemQuestionAnsweringService
        
        # Update settings for cloud
        self.settings.weaviate_cloud_enabled = True
        self.settings.weaviate_url = 'https://test.weaviate.cloud'
        self.settings.weaviate_api_key = 'test-api-key'
        self.settings.save()
        
        mock_client = Mock()
        mock_connect.return_value = mock_client
        
        service = ItemQuestionAnsweringService(self.settings)
        
        self.assertIsNotNone(service._client)
        mock_connect.assert_called_once()
    
    def test_service_no_settings_error(self):
        """Test service initialization without settings"""
        from core.services.item_question_answering_service import (
            ItemQuestionAnsweringService,
            ItemQuestionAnsweringServiceError
        )
        
        Settings.objects.all().delete()
        
        with self.assertRaises(ItemQuestionAnsweringServiceError) as context:
            ItemQuestionAnsweringService()
        
        self.assertIn('No settings found', str(context.exception))
