"""
Tests for Mail Processing Service Token Limit Handling

This module tests the token limit enforcement when processing emails with
large content that would exceed OpenAI's token limits.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from core.services.mail_processing_service import (
    MailProcessingService,
    estimate_token_count,
    truncate_text_to_tokens
)


class TokenLimitUtilsTestCase(unittest.TestCase):
    """Test cases for token limit utility functions"""
    
    def test_estimate_token_count(self):
        """Test token count estimation"""
        # Empty string
        self.assertEqual(estimate_token_count(""), 0)
        
        # Short text (4 chars per token)
        self.assertEqual(estimate_token_count("test"), 1)
        
        # Longer text
        text = "This is a test message with multiple words."
        # 44 characters / 4 = 11 tokens (but integer division gives 10)
        self.assertEqual(estimate_token_count(text), 10)
        
        # Very long text
        long_text = "a" * 10000
        self.assertEqual(estimate_token_count(long_text), 2500)
    
    def test_truncate_text_to_tokens_no_truncation(self):
        """Test text is not truncated when within limit"""
        text = "This is a short text."
        max_tokens = 100
        result = truncate_text_to_tokens(text, max_tokens)
        self.assertEqual(result, text)
    
    def test_truncate_text_to_tokens_with_truncation(self):
        """Test text is truncated when exceeding limit"""
        # Create text that's definitely too long (10000 chars = 2500 tokens)
        text = "a" * 10000
        max_tokens = 100
        result = truncate_text_to_tokens(text, max_tokens)
        
        # Result should be shorter than original
        self.assertLess(len(result), len(text))
        
        # Result should contain the truncation suffix
        self.assertIn("[...content truncated due to length...]", result)
        
        # Result should not exceed token limit significantly
        result_tokens = estimate_token_count(result)
        self.assertLessEqual(result_tokens, max_tokens * 1.1)  # Allow 10% margin
    
    def test_truncate_text_to_tokens_sentence_boundary(self):
        """Test truncation tries to break at sentence boundary"""
        # Create text with clear sentence boundaries
        sentences = ["This is sentence one. ", "This is sentence two. ", "This is sentence three. "]
        text = "".join(sentences * 100)  # Repeat to make it long
        
        max_tokens = 50
        result = truncate_text_to_tokens(text, max_tokens)
        
        # Result should end at a sentence boundary or with the suffix
        self.assertTrue(
            result.endswith(". ") or 
            result.endswith("...") or 
            "[...content truncated due to length...]" in result
        )
    
    def test_truncate_text_custom_suffix(self):
        """Test truncation with custom suffix"""
        text = "a" * 10000
        max_tokens = 100
        custom_suffix = "\n\n[CUSTOM SUFFIX]"
        result = truncate_text_to_tokens(text, max_tokens, suffix=custom_suffix)
        
        self.assertIn("[CUSTOM SUFFIX]", result)


class MailProcessingTokenLimitTestCase(unittest.TestCase):
    """Test cases for token limit handling in mail processing"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock settings
        self.mock_settings = Mock()
        self.mock_settings.openai_api_enabled = True
        self.mock_settings.openai_api_key = 'test-key'
        self.mock_settings.openai_api_base_url = 'https://api.openai.com/v1'
        self.mock_settings.openai_default_model = 'gpt-4'
        self.mock_settings.openai_api_timeout = 30
        self.mock_settings.openai_max_tokens = 1000  # Set a low limit for testing
        self.mock_settings.kigate_api_enabled = False
        self.mock_settings.kigate_max_tokens = 1000
        
        # Mock Weaviate service
        self.mock_weaviate_service = Mock()
        self.mock_weaviate_service.search_similar.return_value = {
            'success': True,
            'results': [
                {
                    'id': 'test-item-id-1',
                    'distance': 0.1,
                    'metadata': {
                        'title': 'Test Item 1',
                        'description': 'Description 1',
                        'section': 'Test Section',
                        'status': 'active'
                    }
                },
                {
                    'id': 'test-item-id-2',
                    'distance': 0.2,
                    'metadata': {
                        'title': 'Test Item 2',
                        'description': 'Description 2',
                        'section': 'Test Section',
                        'status': 'active'
                    }
                }
            ]
        }
        
        # Mock OpenAI service
        self.mock_openai_service = Mock()
        self.mock_openai_service.chat_completion.return_value = {
            'success': True,
            'content': 'test-item-id-1',
            'tokens_used': 100
        }
        
        # Mock Graph service
        self.mock_graph_service = Mock()
    
    @patch('core.services.mail_processing_service.GraphService')
    @patch('core.services.mail_processing_service.WeaviateItemSyncService')
    @patch('core.services.mail_processing_service.OpenAIService')
    def test_find_matching_item_with_large_content(self, mock_openai_cls, mock_weaviate_cls, mock_graph_cls):
        """Test find_matching_item truncates large mail content"""
        # Setup mocks
        mock_graph_cls.return_value = self.mock_graph_service
        mock_weaviate_cls.return_value = self.mock_weaviate_service
        mock_openai_cls.return_value = self.mock_openai_service
        
        # Create service
        service = MailProcessingService(self.mock_settings)
        
        # Create large mail content (more than 1000 tokens = 4000 chars)
        large_content = "This is a very long email. " * 500  # ~14000 characters = ~3500 tokens
        
        # Call find_matching_item
        result = service.find_matching_item(large_content)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'test-item-id-1')
        
        # Verify OpenAI was called
        self.assertTrue(self.mock_openai_service.chat_completion.called)
        
        # Get the prompt that was sent to OpenAI
        call_args = self.mock_openai_service.chat_completion.call_args
        messages = call_args[1]['messages']
        prompt = messages[0]['content']
        
        # Verify the prompt is truncated
        prompt_tokens = estimate_token_count(prompt)
        self.assertLess(prompt_tokens, self.mock_settings.openai_max_tokens * 1.1)  # Allow 10% margin
        
        # Verify truncation message is present
        self.assertIn("[...E-Mail-Inhalt wurde gekürzt...]", prompt)
    
    @patch('core.services.mail_processing_service.GraphService')
    @patch('core.services.mail_processing_service.WeaviateItemSyncService')
    @patch('core.services.mail_processing_service.OpenAIService')
    def test_find_matching_item_with_normal_content(self, mock_openai_cls, mock_weaviate_cls, mock_graph_cls):
        """Test find_matching_item does not truncate normal-sized content"""
        # Setup mocks
        mock_graph_cls.return_value = self.mock_graph_service
        mock_weaviate_cls.return_value = self.mock_weaviate_service
        mock_openai_cls.return_value = self.mock_openai_service
        
        # Create service
        service = MailProcessingService(self.mock_settings)
        
        # Create normal-sized mail content
        normal_content = "This is a normal email with reasonable length. " * 10
        
        # Call find_matching_item
        result = service.find_matching_item(normal_content)
        
        # Verify result
        self.assertIsNotNone(result)
        
        # Get the prompt that was sent to OpenAI
        call_args = self.mock_openai_service.chat_completion.call_args
        messages = call_args[1]['messages']
        prompt = messages[0]['content']
        
        # Verify the prompt is NOT truncated
        self.assertNotIn("[...E-Mail-Inhalt wurde gekürzt...]", prompt)
        
        # Verify original content is in the prompt
        self.assertIn(normal_content, prompt)
    
    @patch('core.services.mail_processing_service.GraphService')
    @patch('core.services.mail_processing_service.WeaviateItemSyncService')
    @patch('core.services.mail_processing_service.KiGateService')
    def test_generate_normalized_description_with_large_content(self, mock_kigate_cls, mock_weaviate_cls, mock_graph_cls):
        """Test generate_normalized_description truncates large mail body"""
        # Setup mocks
        mock_graph_cls.return_value = self.mock_graph_service
        mock_weaviate_cls.return_value = self.mock_weaviate_service
        
        mock_kigate_service = Mock()
        mock_kigate_service.execute_agent.return_value = {
            'success': True,
            'result': 'Normalized description'
        }
        mock_kigate_cls.return_value = mock_kigate_service
        
        # Update settings to enable KiGate
        self.mock_settings.kigate_api_enabled = True
        self.mock_settings.kigate_api_token = 'test-token'
        self.mock_settings.kigate_api_base_url = 'http://localhost:8000'
        self.mock_settings.kigate_api_timeout = 30
        
        # Create service
        service = MailProcessingService(self.mock_settings)
        
        # Create large mail body (more than 1000 tokens = 4000 chars)
        large_body = "This is a very long email body. " * 500  # ~16500 characters = ~4125 tokens
        
        # Call generate_normalized_description
        result = service.generate_normalized_description(
            mail_subject="Test Subject",
            mail_body=large_body,
            item_context={
                'id': 'test-item-id',
                'metadata': {
                    'title': 'Test Item',
                    'description': 'Test Description'
                }
            }
        )
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result, 'Normalized description')
        
        # Verify KiGate was called
        self.assertTrue(mock_kigate_service.execute_agent.called)
        
        # Get the message that was sent to KiGate
        call_args = mock_kigate_service.execute_agent.call_args
        message = call_args[1]['message']
        
        # Verify the message is truncated
        message_tokens = estimate_token_count(message)
        # Allow 15% margin for template overhead variations
        self.assertLess(message_tokens, self.mock_settings.openai_max_tokens * 1.15)
        
        # Verify truncation message is present
        self.assertIn("[...E-Mail-Inhalt wurde aufgrund der Länge gekürzt...]", message)


if __name__ == '__main__':
    unittest.main()
