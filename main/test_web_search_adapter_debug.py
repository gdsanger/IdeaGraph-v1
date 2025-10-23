"""
Test for Web Search Adapter Debug/Error Handling
"""
import json
import logging
from unittest.mock import patch, MagicMock, Mock
from django.test import TestCase
from main.models import Settings
from core.services.web_search_adapter import WebSearchAdapter, WebSearchAdapterError


class WebSearchAdapterDebugTest(TestCase):
    """Test WebSearchAdapter debug logging and error handling"""
    
    def setUp(self):
        """Set up test data"""
        self.settings = Settings.objects.create(
            google_search_api_key='test_api_key',
            google_search_cx='test_cx'
        )
    
    @patch('core.services.web_search_adapter.logger')
    def test_init_logs_configuration(self, mock_logger):
        """Test that initialization logs configuration status"""
        adapter = WebSearchAdapter(settings=self.settings)
        
        # Verify debug logs were called for configuration
        self.assertTrue(mock_logger.debug.called)
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        
        # Check that configuration status was logged
        self.assertTrue(any('Google API Key configured' in str(call) for call in debug_calls))
        self.assertTrue(any('Google CX configured' in str(call) for call in debug_calls))
    
    @patch('core.services.web_search_adapter.requests.get')
    @patch('core.services.web_search_adapter.logger')
    def test_search_google_logs_request_details(self, mock_logger, mock_requests_get):
        """Test that search_google logs request details"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {
                    'title': 'Test Result',
                    'link': 'https://example.com',
                    'snippet': 'Test snippet'
                }
            ]
        }
        mock_requests_get.return_value = mock_response
        
        adapter = WebSearchAdapter(settings=self.settings)
        result = adapter.search_google('test query')
        
        # Verify info logs
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        self.assertTrue(any('Searching Google for' in str(call) for call in info_calls))
        self.assertTrue(any('returned' in str(call) and 'results' in str(call) for call in info_calls))
        
        # Verify debug logs
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        self.assertTrue(any('request URL' in str(call) for call in debug_calls))
        self.assertTrue(any('response status' in str(call) for call in debug_calls))
    
    @patch('core.services.web_search_adapter.requests.get')
    @patch('core.services.web_search_adapter.logger')
    def test_search_google_logs_http_error_details(self, mock_logger, mock_requests_get):
        """Test that search_google logs detailed error information on HTTP errors"""
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = 'Access forbidden'
        mock_response.json.return_value = {
            'error': {
                'message': 'API key not valid',
                'errors': [{'reason': 'forbidden'}]
            }
        }
        mock_requests_get.return_value = mock_response
        
        adapter = WebSearchAdapter(settings=self.settings)
        
        with self.assertRaises(WebSearchAdapterError):
            adapter.search_google('test query')
        
        # Verify error logs
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        self.assertTrue(any('status 403' in str(call) for call in error_calls))
        self.assertTrue(any('API key not valid' in str(call) for call in error_calls))
        self.assertTrue(any('forbidden' in str(call) for call in error_calls))
    
    @patch('core.services.web_search_adapter.requests.get')
    @patch('core.services.web_search_adapter.logger')
    def test_search_google_logs_timeout_error(self, mock_logger, mock_requests_get):
        """Test that search_google logs timeout errors"""
        import requests
        
        # Mock timeout
        mock_requests_get.side_effect = requests.exceptions.Timeout('Connection timeout')
        
        adapter = WebSearchAdapter(settings=self.settings)
        
        with self.assertRaises(WebSearchAdapterError) as context:
            adapter.search_google('test query')
        
        # Verify the error message includes timeout information
        self.assertIn('timeout', str(context.exception).lower())
        
        # Verify error was logged
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        self.assertTrue(any('timeout' in str(call).lower() for call in error_calls))
    
    @patch('core.services.web_search_adapter.requests.get')
    @patch('core.services.web_search_adapter.logger')
    def test_search_google_logs_json_decode_error(self, mock_logger, mock_requests_get):
        """Test that search_google logs JSON decode errors"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
        mock_requests_get.return_value = mock_response
        
        adapter = WebSearchAdapter(settings=self.settings)
        
        with self.assertRaises(WebSearchAdapterError) as context:
            adapter.search_google('test query')
        
        # Verify the error message mentions JSON
        self.assertIn('JSON', str(context.exception))
        
        # Verify error was logged
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        self.assertTrue(any('JSON' in str(call) for call in error_calls))
    
    @patch('core.services.web_search_adapter.requests.get')
    @patch('core.services.web_search_adapter.logger')
    def test_search_google_logs_unexpected_exception(self, mock_logger, mock_requests_get):
        """Test that search_google logs unexpected exceptions with full details"""
        # Mock unexpected exception
        mock_requests_get.side_effect = ValueError('Unexpected error')
        
        adapter = WebSearchAdapter(settings=self.settings)
        
        with self.assertRaises(WebSearchAdapterError) as context:
            adapter.search_google('test query')
        
        # Verify the error includes exception type
        self.assertIn('ValueError', str(context.exception))
        
        # Verify error was logged with exception details
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        self.assertTrue(any('Unexpected error' in str(call) for call in error_calls))
        self.assertTrue(any('ValueError' in str(call) for call in error_calls))
        
        # Verify exception() was called for traceback
        self.assertTrue(mock_logger.exception.called)
    
    @patch('core.services.web_search_adapter.requests.get')
    @patch('core.services.web_search_adapter.logger')
    def test_search_google_logs_no_items_warning(self, mock_logger, mock_requests_get):
        """Test that search_google logs warning when no items returned"""
        # Mock response with no items
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'searchInformation': {'totalResults': '0'}}
        mock_requests_get.return_value = mock_response
        
        adapter = WebSearchAdapter(settings=self.settings)
        result = adapter.search_google('test query')
        
        # Verify warning was logged
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        self.assertTrue(any('no items' in str(call).lower() for call in warning_calls))
        
        # Verify result is still valid but empty
        self.assertTrue(result['success'])
        self.assertEqual(len(result['results']), 0)
    
    @patch('core.services.web_search_adapter.logger')
    def test_search_logs_fallback_behavior(self, mock_logger):
        """Test that search method logs when falling back to Brave"""
        import os
        # Set Brave API key to enable fallback
        os.environ['BRAVE_SEARCH_API_KEY'] = 'test_brave_key'
        
        try:
            adapter = WebSearchAdapter(settings=self.settings)
            
            # Mock Google to fail and Brave to succeed
            with patch.object(adapter, 'search_google') as mock_google:
                with patch.object(adapter, 'search_brave') as mock_brave:
                    mock_google.side_effect = WebSearchAdapterError('Google failed', 'Test error')
                    mock_brave.return_value = {'success': True, 'results': [], 'provider': 'brave'}
                    
                    result = adapter.search('test query')
                    
                    # Verify Google error was logged with details
                    warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                    self.assertTrue(any('Google search failed' in str(call) for call in warning_calls))
                    self.assertTrue(any('Test error' in str(call) for call in warning_calls))
        finally:
            # Clean up
            if 'BRAVE_SEARCH_API_KEY' in os.environ:
                del os.environ['BRAVE_SEARCH_API_KEY']
    
    @patch('core.services.web_search_adapter.logger')
    def test_search_logs_all_providers_failed(self, mock_logger):
        """Test that search method logs when all providers fail"""
        adapter = WebSearchAdapter(settings=self.settings)
        
        # Mock both to fail
        with patch.object(adapter, 'search_google') as mock_google:
            with patch.object(adapter, 'search_brave') as mock_brave:
                mock_google.side_effect = WebSearchAdapterError('Google failed', 'Google error')
                mock_brave.side_effect = WebSearchAdapterError('Brave failed', 'Brave error')
                
                with self.assertRaises(WebSearchAdapterError):
                    adapter.search('test query')
                
                # Verify final error was logged
                error_calls = [str(call) for call in mock_logger.error.call_args_list]
                self.assertTrue(any('All search providers failed' in str(call) for call in error_calls))
    
    def test_web_search_adapter_error_to_dict(self):
        """Test WebSearchAdapterError.to_dict() includes details"""
        error = WebSearchAdapterError('Test error', 'Detailed information')
        error_dict = error.to_dict()
        
        self.assertFalse(error_dict['success'])
        self.assertEqual(error_dict['error'], 'Test error')
        self.assertEqual(error_dict['details'], 'Detailed information')
    
    @patch('core.services.web_search_adapter.logger')
    def test_search_google_missing_credentials_logs_error(self, mock_logger):
        """Test that missing credentials are logged as errors"""
        settings = Settings.objects.create(
            google_search_api_key='',
            google_search_cx=''
        )
        
        adapter = WebSearchAdapter(settings=settings)
        
        with self.assertRaises(WebSearchAdapterError):
            adapter.search_google('test query')
        
        # Verify error was logged
        error_calls = [str(call) for call in mock_logger.error.call_args_list]
        self.assertTrue(any('credentials not configured' in str(call).lower() for call in error_calls))


class WebSearchAdapterBraveDebugTest(TestCase):
    """Test WebSearchAdapter Brave search debug logging"""
    
    def setUp(self):
        """Set up test data"""
        import os
        self.settings = Settings.objects.create()
        os.environ['BRAVE_SEARCH_API_KEY'] = 'test_brave_key'
    
    def tearDown(self):
        """Clean up"""
        import os
        if 'BRAVE_SEARCH_API_KEY' in os.environ:
            del os.environ['BRAVE_SEARCH_API_KEY']
    
    @patch('core.services.web_search_adapter.requests.get')
    @patch('core.services.web_search_adapter.logger')
    def test_search_brave_logs_request_details(self, mock_logger, mock_requests_get):
        """Test that search_brave logs request details"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'web': {
                'results': [
                    {
                        'title': 'Test Result',
                        'url': 'https://example.com',
                        'description': 'Test description'
                    }
                ]
            }
        }
        mock_requests_get.return_value = mock_response
        
        adapter = WebSearchAdapter(settings=self.settings)
        result = adapter.search_brave('test query')
        
        # Verify info logs
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        self.assertTrue(any('Searching Brave' in str(call) for call in info_calls))
        
        # Verify debug logs
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        self.assertTrue(any('request URL' in str(call) for call in debug_calls))
    
    @patch('core.services.web_search_adapter.requests.get')
    @patch('core.services.web_search_adapter.logger')
    def test_search_brave_logs_no_results_warning(self, mock_logger, mock_requests_get):
        """Test that search_brave logs warning when no results returned"""
        # Mock response with no web results
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests_get.return_value = mock_response
        
        adapter = WebSearchAdapter(settings=self.settings)
        result = adapter.search_brave('test query')
        
        # Verify warning was logged
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        self.assertTrue(any('no web results' in str(call).lower() for call in warning_calls))
