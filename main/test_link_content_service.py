"""
Tests for Link Content Service

This module tests the link content extraction and processing functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from core.services.link_content_service import (
    LinkContentService,
    LinkContentServiceError,
    HTMLCleaner
)


class HTMLCleanerTest(TestCase):
    """Test HTML cleaning functionality"""
    
    def test_extract_text_from_simple_html(self):
        """Test extracting text from simple HTML"""
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Hello World</h1>
                <p>This is a test paragraph.</p>
            </body>
        </html>
        """
        cleaner = HTMLCleaner()
        cleaner.feed(html)
        text = cleaner.get_text()
        
        self.assertIn('Hello World', text)
        self.assertIn('This is a test paragraph.', text)
        self.assertNotIn('<h1>', text)
        self.assertNotIn('<p>', text)
    
    def test_remove_script_tags(self):
        """Test that script tags are removed"""
        html = """
        <html>
            <body>
                <p>Content</p>
                <script>alert('test');</script>
                <p>More content</p>
            </body>
        </html>
        """
        cleaner = HTMLCleaner()
        cleaner.feed(html)
        text = cleaner.get_text()
        
        self.assertIn('Content', text)
        self.assertIn('More content', text)
        self.assertNotIn('alert', text)
        self.assertNotIn('test', text)
    
    def test_remove_style_tags(self):
        """Test that style tags are removed"""
        html = """
        <html>
            <head>
                <style>body { color: red; }</style>
            </head>
            <body>
                <p>Content</p>
            </body>
        </html>
        """
        cleaner = HTMLCleaner()
        cleaner.feed(html)
        text = cleaner.get_text()
        
        self.assertIn('Content', text)
        self.assertNotIn('color', text)
        self.assertNotIn('red', text)


class LinkContentServiceTest(TestCase):
    """Test Link Content Service functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock settings
        self.mock_settings = Mock()
        self.mock_settings.kigate_max_tokens = 10000
        self.mock_settings.kigate_api_enabled = True
        self.mock_settings.kigate_api_token = 'test-token'
        self.mock_settings.kigate_api_base_url = 'http://test.com'
        self.mock_settings.kigate_api_timeout = 30
    
    def test_normalize_filename(self):
        """Test filename normalization"""
        service = LinkContentService(settings=self.mock_settings)
        
        # Test with special characters
        result = service.normalize_filename('Test: Article <2024>')
        self.assertEqual(result, 'Test_Article_2024')
        
        # Test with long title
        long_title = 'A' * 150
        result = service.normalize_filename(long_title)
        self.assertEqual(len(result), 100)
        
        # Test with empty title
        result = service.normalize_filename('')
        self.assertEqual(result, 'web_content')
    
    def test_extract_title_from_title_tag(self):
        """Test title extraction from HTML title tag"""
        service = LinkContentService(settings=self.mock_settings)
        html = '<html><head><title>Test Page Title</title></head><body></body></html>'
        
        title = service._extract_title(html)
        self.assertEqual(title, 'Test Page Title')
    
    def test_extract_title_from_h1_fallback(self):
        """Test title extraction falls back to h1 when no title tag"""
        service = LinkContentService(settings=self.mock_settings)
        html = '<html><body><h1>Main Heading</h1><p>Content</p></body></html>'
        
        title = service._extract_title(html)
        self.assertEqual(title, 'Main Heading')
    
    def test_extract_title_returns_none_when_not_found(self):
        """Test title extraction returns None when no title or h1"""
        service = LinkContentService(settings=self.mock_settings)
        html = '<html><body><p>Just content</p></body></html>'
        
        title = service._extract_title(html)
        self.assertIsNone(title)
    
    def test_clean_html_content(self):
        """Test HTML content cleaning"""
        service = LinkContentService(settings=self.mock_settings)
        html = """
        <html>
            <head>
                <script>alert('test');</script>
                <style>body { color: red; }</style>
            </head>
            <body>
                <h1>Article Title</h1>
                <p>Paragraph 1</p>
                <p>Paragraph 2</p>
                <!-- Comment -->
            </body>
        </html>
        """
        
        result = service.clean_html_content(html)
        
        self.assertTrue(result['success'])
        self.assertIn('Article Title', result['text'])
        self.assertIn('Paragraph 1', result['text'])
        self.assertNotIn('alert', result['text'])
        self.assertNotIn('color', result['text'])
        self.assertNotIn('Comment', result['text'])
    
    @patch('core.services.link_content_service.requests.get')
    def test_download_url_content_success(self, mock_get):
        """Test successful URL download"""
        service = LinkContentService(settings=self.mock_settings)
        
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.text = '<html><head><title>Test</title></head><body>Content</body></html>'
        mock_response.url = 'http://example.com'
        mock_get.return_value = mock_response
        
        result = service.download_url_content('http://example.com')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['title'], 'Test')
        self.assertIn('Content', result['content'])
    
    @patch('core.services.link_content_service.requests.get')
    def test_download_url_content_invalid_url(self, mock_get):
        """Test download with invalid URL"""
        service = LinkContentService(settings=self.mock_settings)
        
        with self.assertRaises(LinkContentServiceError) as context:
            service.download_url_content('not-a-url')
        
        self.assertIn('Invalid URL format', str(context.exception))
    
    @patch('core.services.link_content_service.requests.get')
    def test_download_url_content_http_error(self, mock_get):
        """Test download with HTTP error"""
        service = LinkContentService(settings=self.mock_settings)
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Not Found'
        mock_get.return_value = mock_response
        
        with self.assertRaises(LinkContentServiceError) as context:
            service.download_url_content('http://example.com')
        
        self.assertIn('HTTP 404', str(context.exception))
    
    @patch('core.services.link_content_service.requests.get')
    def test_download_url_content_non_html(self, mock_get):
        """Test download rejects non-HTML content"""
        service = LinkContentService(settings=self.mock_settings)
        
        # Mock response with PDF content type
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/pdf'}
        mock_response.text = 'PDF content'
        mock_get.return_value = mock_response
        
        with self.assertRaises(LinkContentServiceError) as context:
            service.download_url_content('http://example.com/file.pdf')
        
        self.assertIn('does not return HTML', str(context.exception))
    
    def test_process_with_ai_truncates_large_content(self):
        """Test that large content is truncated before sending to AI"""
        service = LinkContentService(settings=self.mock_settings)
        
        # Create content larger than max tokens
        large_content = 'A' * 50000  # 50k chars
        
        # Mock KiGate service
        with patch.object(service, '_get_kigate_service') as mock_kigate_getter:
            mock_kigate = Mock()
            mock_kigate.execute_agent.return_value = {
                'success': True,
                'result': '# Processed Content'
            }
            mock_kigate_getter.return_value = mock_kigate
            
            result = service.process_with_ai(
                content=large_content,
                title='Test',
                url='http://example.com',
                user_id='test-user'
            )
            
            # Verify the content was truncated
            call_args = mock_kigate.execute_agent.call_args
            message = call_args[1]['message']
            self.assertIn('[Content truncated due to size limit]', message)


if __name__ == '__main__':
    unittest.main()
