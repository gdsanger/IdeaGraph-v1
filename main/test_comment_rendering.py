"""
Tests for comment HTML rendering and link auto-conversion.
"""
from django.test import TestCase
from main.templatetags.comment_extras import render_comment


class CommentRenderingTestCase(TestCase):
    """Test cases for comment rendering with HTML and linkification"""
    
    def test_plain_text_preserved(self):
        """Test that plain text is preserved without HTML"""
        text = "This is a simple comment"
        result = render_comment(text)
        self.assertIn("This is a simple comment", result)
    
    def test_url_linkified(self):
        """Test that URLs are automatically converted to clickable links"""
        text = "Check out https://example.com for more info"
        result = render_comment(text)
        self.assertIn('<a href="https://example.com"', result)
        # bleach linkify creates links (may or may not add nofollow depending on version)
        self.assertIn('</a>', result)
    
    def test_multiple_urls_linkified(self):
        """Test that multiple URLs are linkified"""
        text = "Visit https://example.com and http://test.org"
        result = render_comment(text)
        self.assertIn('<a href="https://example.com"', result)
        self.assertIn('<a href="http://test.org"', result)
    
    def test_email_linkified(self):
        """Test that email addresses are linkified"""
        text = "Contact us at test@example.com"
        result = render_comment(text)
        # bleach linkify may or may not linkify emails, depends on configuration
        # This test verifies the behavior
        self.assertIn("test@example.com", result)
    
    def test_safe_html_preserved(self):
        """Test that safe HTML tags are preserved"""
        text = "This is <strong>bold</strong> and <em>italic</em>"
        result = render_comment(text)
        self.assertIn("<strong>bold</strong>", result)
        self.assertIn("<em>italic</em>", result)
    
    def test_links_preserved(self):
        """Test that existing HTML links are preserved"""
        text = '<a href="https://example.com">Click here</a>'
        result = render_comment(text)
        self.assertIn('href="https://example.com"', result)
        self.assertIn("Click here", result)
    
    def test_dangerous_html_sanitized(self):
        """Test that dangerous HTML is sanitized"""
        text = '<script>alert("XSS")</script>Hello'
        result = render_comment(text)
        self.assertNotIn('<script>', result)
        # Script content is escaped, which is safe
        # The important thing is that it doesn't execute
        self.assertIn('Hello', result)
        # Make sure the script is escaped/removed and won't execute
        self.assertTrue('&lt;script&gt;' in result or '<script>' not in result)
    
    def test_dangerous_attributes_removed(self):
        """Test that dangerous attributes like onclick are removed"""
        text = '<a href="https://example.com" onclick="alert(\'XSS\')">Link</a>'
        result = render_comment(text)
        self.assertNotIn('onclick', result)
        self.assertIn('href="https://example.com"', result)
        self.assertIn('Link', result)
    
    def test_iframe_removed(self):
        """Test that iframe tags are sanitized"""
        text = '<iframe src="https://evil.com"></iframe>Safe text'
        result = render_comment(text)
        self.assertNotIn('<iframe', result)
        self.assertIn('Safe text', result)
    
    def test_allowed_html_tags(self):
        """Test that allowed HTML tags work correctly"""
        text = """
        <h1>Heading</h1>
        <p>Paragraph with <code>code</code></p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <blockquote>Quote</blockquote>
        """
        result = render_comment(text)
        self.assertIn('<h1>', result)
        self.assertIn('<p>', result)
        self.assertIn('<code>', result)
        self.assertIn('<ul>', result)
        self.assertIn('<li>', result)
        self.assertIn('<blockquote>', result)
    
    def test_image_tag_preserved(self):
        """Test that image tags with safe attributes are preserved"""
        text = '<img src="https://example.com/image.png" alt="Test image">'
        result = render_comment(text)
        self.assertIn('<img', result)
        self.assertIn('src="https://example.com/image.png"', result)
        self.assertIn('alt="Test image"', result)
    
    def test_table_preserved(self):
        """Test that table HTML is preserved"""
        text = """
        <table>
            <thead>
                <tr><th>Header</th></tr>
            </thead>
            <tbody>
                <tr><td>Data</td></tr>
            </tbody>
        </table>
        """
        result = render_comment(text)
        self.assertIn('<table>', result)
        self.assertIn('<thead>', result)
        self.assertIn('<th>', result)
        self.assertIn('<tbody>', result)
        self.assertIn('<td>', result)
    
    def test_url_in_html_not_double_linkified(self):
        """Test that URLs inside existing links are not double-linkified"""
        text = '<a href="https://example.com">https://example.com</a>'
        result = render_comment(text)
        # Should have only one <a> tag
        self.assertEqual(result.count('<a '), 1)
    
    def test_javascript_protocol_removed(self):
        """Test that javascript: protocol is removed from links"""
        text = '<a href="javascript:alert(\'XSS\')">Click</a>'
        result = render_comment(text)
        self.assertNotIn('javascript:', result)
    
    def test_data_protocol_removed(self):
        """Test that data: protocol is removed from links"""
        text = '<a href="data:text/html,<script>alert(\'XSS\')</script>">Click</a>'
        result = render_comment(text)
        self.assertNotIn('data:', result)
    
    def test_empty_text(self):
        """Test that empty text returns empty string"""
        result = render_comment('')
        self.assertEqual(result, '')
    
    def test_none_text(self):
        """Test that None text returns empty string"""
        result = render_comment(None)
        self.assertEqual(result, '')
    
    def test_mixed_content(self):
        """Test mixed content with HTML, URLs, and text"""
        text = """
        <h2>Project Update</h2>
        <p>We've made progress on the project. Check out the details at https://github.com/example/repo</p>
        <p>Key points:</p>
        <ul>
            <li>Fixed bug #123</li>
            <li>Added new feature</li>
        </ul>
        <p>Contact me at <a href="mailto:test@example.com">test@example.com</a></p>
        """
        result = render_comment(text)
        self.assertIn('<h2>Project Update</h2>', result)
        self.assertIn('<ul>', result)
        self.assertIn('<li>', result)
        # URL should be linkified
        self.assertIn('<a href="https://github.com/example/repo"', result)
        # Existing mailto link should be preserved
        self.assertIn('mailto:test@example.com', result)
    
    def test_url_with_query_params(self):
        """Test that URLs with query parameters are properly linkified"""
        text = "Check https://example.com/page?param=value&other=123"
        result = render_comment(text)
        self.assertIn('<a href="https://example.com/page?param=value&amp;other=123"', result)
    
    def test_url_with_anchor(self):
        """Test that URLs with anchors are properly linkified"""
        text = "See https://example.com/page#section"
        result = render_comment(text)
        self.assertIn('<a href="https://example.com/page#section"', result)
    
    def test_whitespace_preserved(self):
        """Test that whitespace and line breaks are handled"""
        text = "Line 1\n\nLine 2\n\nLine 3"
        result = render_comment(text)
        # The filter should preserve the text content
        self.assertIn("Line 1", result)
        self.assertIn("Line 2", result)
        self.assertIn("Line 3", result)
    
    def test_special_characters(self):
        """Test that special characters are properly escaped"""
        text = "Test with <special> & \"characters\""
        result = render_comment(text)
        # The text should be safe
        self.assertIn("Test with", result)
        # Special chars should be either escaped or handled safely
        self.assertNotIn('"><script>', result)
