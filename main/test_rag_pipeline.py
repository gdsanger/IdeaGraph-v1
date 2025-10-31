"""
Tests for RAG Pipeline in Chat

This test suite validates the RAG pipeline functionality including:
- Question optimization
- Semantic and keyword retrieval
- Result fusion and reranking
- Context assembly with A/B/C layers
- Answer generation
"""

import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from main.models import Settings
from chat.rag_pipeline import RAGPipeline, RAGPipelineError


class RAGPipelineTest(TestCase):
    """Test suite for RAG Pipeline"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test settings
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_token='test-token',
            kigate_api_base_url='http://localhost:8000',
            kigate_api_timeout=30,
            kigate_max_tokens=10000,
            openai_default_model='gpt-4',
            weaviate_cloud_enabled=False
        )
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_pipeline_initialization(self, mock_kigate, mock_weaviate):
        """Test that pipeline initializes correctly"""
        mock_weaviate.return_value = MagicMock()
        mock_kigate.return_value = MagicMock()
        
        pipeline = RAGPipeline(settings=self.settings)
        
        self.assertIsNotNone(pipeline)
        self.assertEqual(pipeline.settings, self.settings)
        mock_weaviate.assert_called_once()
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_optimize_question_success(self, mock_kigate_class, mock_weaviate):
        """Test question optimization returns valid JSON"""
        mock_weaviate.return_value = MagicMock()
        
        # Mock KiGate response
        mock_kigate = MagicMock()
        mock_kigate.execute_agent.return_value = {
            'success': True,
            'result': json.dumps({
                'language': 'de',
                'core': 'Was ist RAG?',
                'synonyms': ['Retrieval Augmented Generation', 'RAG-System'],
                'phrases': ['semantische Suche', 'Kontextbasierte Antworten'],
                'entities': {'RAG': 'technology'},
                'tags': ['KI', 'Retrieval', 'NLP'],
                'ban': [],
                'followup_questions': ['Wie funktioniert RAG?']
            })
        }
        mock_kigate_class.return_value = mock_kigate
        
        # Update settings for default model
        self.settings.openai_default_model = 'gpt-4'
        self.settings.save()
        
        pipeline = RAGPipeline(settings=self.settings)
        result = pipeline.optimize_question("Was ist RAG?")
        
        # Verify execute_agent was called with proper parameters
        mock_kigate.execute_agent.assert_called_once()
        call_args = mock_kigate.execute_agent.call_args
        self.assertEqual(call_args[1]['agent_name'], 'question-optimization-agent')
        self.assertEqual(call_args[1]['provider'], 'openai')
        self.assertEqual(call_args[1]['model'], 'gpt-4')
        self.assertEqual(call_args[1]['user_id'], 'system')
        self.assertIn('message', call_args[1])
        
        # Validate structure
        self.assertIn('language', result)
        self.assertIn('core', result)
        self.assertIn('synonyms', result)
        self.assertIn('phrases', result)
        self.assertIn('tags', result)
        self.assertEqual(result['language'], 'de')
        self.assertEqual(result['core'], 'Was ist RAG?')
        self.assertIsInstance(result['synonyms'], list)
        self.assertIsInstance(result['tags'], list)
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_optimize_question_fallback(self, mock_kigate_class, mock_weaviate):
        """Test question optimization fallback when KiGate fails"""
        mock_weaviate.return_value = MagicMock()
        
        # Mock KiGate failure
        mock_kigate = MagicMock()
        mock_kigate.execute_agent.return_value = {
            'success': False,
            'error': 'Service unavailable'
        }
        mock_kigate_class.return_value = mock_kigate
        
        pipeline = RAGPipeline(settings=self.settings)
        result = pipeline.optimize_question("Was ist RAG?")
        
        # Should return fallback
        self.assertEqual(result['core'], "Was ist RAG?")
        self.assertEqual(result['language'], 'de')
        self.assertEqual(result['synonyms'], [])
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_retrieve_semantic_returns_results(self, mock_kigate_class, mock_weaviate):
        """Test semantic retrieval returns snippets"""
        mock_kigate_class.return_value = MagicMock()
        
        # Mock Weaviate response
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_response = MagicMock()
        
        # Create mock object
        mock_obj = MagicMock()
        mock_obj.uuid = 'test-uuid-1'
        mock_obj.properties = {
            'objectType': 'task',
            'itemId': 'item-123',
            'title': 'Test Task',
            'excerpt': 'This is a test excerpt',
            'tags': ['test', 'rag']
        }
        mock_obj.metadata.score = 0.85
        mock_obj.metadata.certainty = 0.75
        
        mock_response.objects = [mock_obj]
        mock_collection.query.hybrid.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection
        mock_weaviate.return_value = mock_client
        
        pipeline = RAGPipeline(settings=self.settings)
        
        expanded = {
            'core': 'test query',
            'synonyms': ['test'],
            'phrases': ['test phrase'],
            'tags': ['test']
        }
        
        results = pipeline.retrieve_semantic(expanded)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], 'test-uuid-1')
        self.assertEqual(results[0]['type'], 'task')
        self.assertIn('score_semantic', results[0])
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_retrieve_keywords_returns_results(self, mock_kigate_class, mock_weaviate):
        """Test keyword retrieval returns snippets"""
        mock_kigate_class.return_value = MagicMock()
        
        # Mock Weaviate response
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_response = MagicMock()
        
        mock_obj = MagicMock()
        mock_obj.uuid = 'test-uuid-2'
        mock_obj.properties = {
            'objectType': 'item',
            'itemId': 'item-456',
            'title': 'Test Item',
            'excerpt': 'Keyword search result',
            'tags': ['keyword', 'search']
        }
        mock_obj.metadata.score = 0.90
        mock_obj.metadata.certainty = 0.80
        
        mock_response.objects = [mock_obj]
        mock_collection.query.hybrid.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection
        mock_weaviate.return_value = mock_client
        
        pipeline = RAGPipeline(settings=self.settings)
        
        expanded = {
            'core': 'keyword test',
            'tags': ['keyword', 'test']
        }
        
        results = pipeline.retrieve_keywords(expanded)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], 'test-uuid-2')
        self.assertIn('score_bm25', results[0])
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_fuse_and_rerank_removes_duplicates(self, mock_kigate_class, mock_weaviate):
        """Test fusion removes duplicate entries correctly"""
        mock_weaviate.return_value = MagicMock()
        mock_kigate_class.return_value = MagicMock()
        
        pipeline = RAGPipeline(settings=self.settings)
        
        # Create results with duplicate
        results_sem = [
            {
                'id': 'uuid-1',
                'type': 'task',
                'item_id': 'item-1',
                'title': 'Task 1',
                'excerpt': 'Excerpt 1',
                'tags': ['test'],
                'score_semantic': 0.8,
                'score_bm25': 0.0,
                'certainty': 0.75
            },
            {
                'id': 'uuid-2',
                'type': 'task',
                'item_id': 'item-1',
                'title': 'Task 2',
                'excerpt': 'Excerpt 2',
                'tags': ['test'],
                'score_semantic': 0.7,
                'score_bm25': 0.0,
                'certainty': 0.65
            }
        ]
        
        results_kw = [
            {
                'id': 'uuid-1',  # Duplicate
                'type': 'task',
                'item_id': 'item-1',
                'title': 'Task 1',
                'excerpt': 'Excerpt 1',
                'tags': ['test'],
                'score_semantic': 0.0,
                'score_bm25': 0.9,
                'certainty': 0.75
            },
            {
                'id': 'uuid-3',
                'type': 'item',
                'item_id': 'item-2',
                'title': 'Item 3',
                'excerpt': 'Excerpt 3',
                'tags': ['other'],
                'score_semantic': 0.0,
                'score_bm25': 0.85,
                'certainty': 0.70
            }
        ]
        
        expanded = {
            'tags': ['test']
        }
        
        fused = pipeline.fuse_and_rerank(results_sem, results_kw, expanded)
        
        # Should have 3 unique results
        self.assertEqual(len(fused), 3)
        
        # Check that duplicate was merged (has both scores)
        uuid1_result = next(r for r in fused if r['id'] == 'uuid-1')
        self.assertGreater(uuid1_result['score_semantic'], 0)
        self.assertGreater(uuid1_result['score_bm25'], 0)
        
        # Check all have final_score
        for result in fused:
            self.assertIn('final_score', result)
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_assemble_context_has_layers(self, mock_kigate_class, mock_weaviate):
        """Test context assembly creates A/B/C layers"""
        mock_weaviate.return_value = MagicMock()
        mock_kigate_class.return_value = MagicMock()
        
        pipeline = RAGPipeline(settings=self.settings)
        
        # Create results for different layers
        results = [
            {
                'id': 'uuid-1',
                'type': 'task',
                'item_id': 'item-1',
                'title': 'High relevance task',
                'excerpt': 'This should be in A layer',
                'final_score': 0.9
            },
            {
                'id': 'uuid-2',
                'type': 'task',
                'item_id': 'item-1',
                'title': 'Medium relevance task',
                'excerpt': 'This should be in B layer',
                'final_score': 0.4
            },
            {
                'id': 'uuid-3',
                'type': 'item',
                'item_id': 'item-2',
                'title': 'Global context',
                'excerpt': 'This should be in C layer',
                'final_score': 0.7
            }
        ]
        
        context = pipeline.assemble_context(results, item_id='item-1')
        
        # Check structure
        self.assertIn('CONTEXT:', context)
        self.assertIn('#A1', context)
        self.assertIn('#B1', context)
        self.assertIn('#C1', context)
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_send_to_answering_agent_includes_markers(self, mock_kigate_class, mock_weaviate):
        """Test answer from question-answering-agent contains markers"""
        mock_weaviate.return_value = MagicMock()
        
        # Mock KiGate response with markers
        mock_kigate = MagicMock()
        mock_kigate.execute_agent.return_value = {
            'success': True,
            'result': 'Basierend auf [#A1] und [#B2], hier ist die Antwort.'
        }
        mock_kigate_class.return_value = mock_kigate
        
        # Update settings for default model
        self.settings.openai_default_model = 'gpt-4'
        self.settings.save()
        
        pipeline = RAGPipeline(settings=self.settings)
        
        context = """CONTEXT:
[#A1] Test Source 1
Content 1

[#B2] Test Source 2
Content 2
"""
        
        answer = pipeline.send_to_answering_agent("Test question?", context)
        
        # Verify execute_agent was called with proper parameters
        mock_kigate.execute_agent.assert_called_once()
        call_args = mock_kigate.execute_agent.call_args
        self.assertEqual(call_args[1]['agent_name'], 'question-answering-agent')
        self.assertEqual(call_args[1]['provider'], 'openai')
        self.assertEqual(call_args[1]['model'], 'gpt-4')
        self.assertEqual(call_args[1]['user_id'], 'system')
        self.assertIn('message', call_args[1])
        
        # Should contain markers
        self.assertIn('[#A1]', answer)
        self.assertIn('[#B2]', answer)
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_process_question_full_pipeline(self, mock_kigate_class, mock_weaviate):
        """Test full pipeline execution"""
        # Mock Weaviate
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_response = MagicMock()
        mock_response.objects = []
        mock_collection.query.hybrid.return_value = mock_response
        mock_client.collections.get.return_value = mock_collection
        mock_weaviate.return_value = mock_client
        
        # Mock KiGate
        mock_kigate = MagicMock()
        mock_kigate.execute_agent.side_effect = [
            # First call: optimization
            {
                'success': True,
                'result': json.dumps({
                    'language': 'de',
                    'core': 'Was ist RAG?',
                    'synonyms': ['RAG-System'],
                    'phrases': [],
                    'entities': {},
                    'tags': ['KI'],
                    'ban': [],
                    'followup_questions': []
                })
            },
            # Second call: answering
            {
                'success': True,
                'result': 'RAG steht für Retrieval Augmented Generation.'
            }
        ]
        mock_kigate_class.return_value = mock_kigate
        
        pipeline = RAGPipeline(settings=self.settings)
        result = pipeline.process_question("Was ist RAG?", item_id="item-123")
        
        # Validate result structure
        self.assertTrue(result['success'])
        self.assertIn('answer', result)
        self.assertIn('expanded', result)
        self.assertIn('hits_sem', result)
        self.assertIn('hits_kw', result)
        self.assertIn('context', result)
        self.assertIn('total_time', result)
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_fallback_context_when_no_results(self, mock_kigate_class, mock_weaviate):
        """Test fallback context is used when no results found"""
        mock_weaviate.return_value = MagicMock()
        mock_kigate_class.return_value = MagicMock()
        
        pipeline = RAGPipeline(settings=self.settings)
        
        # Empty results
        context = pipeline.assemble_context([], item_id="item-123")
        
        # Should contain fallback
        self.assertIn('FAQ', context)
        self.assertIn('Keine spezifischen Informationen gefunden', context)
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    def test_pipeline_without_kigate(self, mock_weaviate):
        """Test pipeline works with fallback when KiGate is unavailable"""
        mock_weaviate.return_value = MagicMock()
        
        # Disable KiGate
        self.settings.kigate_api_enabled = False
        self.settings.save()
        
        with patch('core.services.kigate_service.KiGateService') as mock_kigate_class:
            from core.services.kigate_service import KiGateServiceError
            mock_kigate_class.side_effect = KiGateServiceError("KiGate disabled")
            
            pipeline = RAGPipeline(settings=self.settings)
            
            # Should still work with fallback
            result = pipeline.optimize_question("Test question")
            self.assertEqual(result['core'], "Test question")
    
    @patch('chat.rag_pipeline.weaviate.connect_to_local')
    @patch('core.services.kigate_service.KiGateService')
    def test_build_search_query(self, mock_kigate_class, mock_weaviate):
        """Test search query building from expanded data"""
        mock_weaviate.return_value = MagicMock()
        mock_kigate_class.return_value = MagicMock()
        
        pipeline = RAGPipeline(settings=self.settings)
        
        expanded = {
            'core': 'main query',
            'synonyms': ['syn1', 'syn2', 'syn3', 'syn4'],
            'phrases': ['phrase1', 'phrase2', 'phrase3'],
            'tags': ['tag1', 'tag2', 'tag3']
        }
        
        query = pipeline._build_search_query(expanded)
        
        # Should include core
        self.assertIn('main query', query)
        
        # Should include limited synonyms (3)
        self.assertIn('syn1', query)
        self.assertIn('syn2', query)
        self.assertIn('syn3', query)
        
        # Should include limited phrases (2)
        self.assertIn('phrase1', query)
        self.assertIn('phrase2', query)
        
        # Should include limited tags (2)
        self.assertIn('tag1', query)
        self.assertIn('tag2', query)
