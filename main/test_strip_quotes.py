"""
Test for verifying quotation marks are stripped from AI-generated titles
"""
from django.test import TestCase
from main.api_views import strip_quotes_from_title


class TestStripQuotesFromTitle(TestCase):
    """Test the strip_quotes_from_title helper function"""
    
    def test_strips_double_quotes(self):
        """Test that double quotes are removed"""
        result = strip_quotes_from_title('"Test Title"')
        self.assertEqual(result, 'Test Title')
    
    def test_strips_single_quotes(self):
        """Test that single quotes are removed"""
        result = strip_quotes_from_title("'Test Title'")
        self.assertEqual(result, 'Test Title')
    
    def test_strips_mixed_quotes(self):
        """Test that mixed quotes are handled"""
        result = strip_quotes_from_title('"Test Title\'')
        self.assertEqual(result, 'Test Title')
    
    def test_preserves_internal_quotes(self):
        """Test that quotes inside the title are preserved"""
        result = strip_quotes_from_title('"Test "Quoted" Title"')
        self.assertEqual(result, 'Test "Quoted" Title')
    
    def test_handles_title_without_quotes(self):
        """Test that titles without quotes are returned unchanged"""
        result = strip_quotes_from_title('Test Title')
        self.assertEqual(result, 'Test Title')
    
    def test_handles_empty_string(self):
        """Test that empty strings are handled"""
        result = strip_quotes_from_title('')
        self.assertEqual(result, '')
    
    def test_handles_none(self):
        """Test that None is handled"""
        result = strip_quotes_from_title(None)
        self.assertIsNone(result)
    
    def test_strips_with_internal_whitespace(self):
        """Test that whitespace inside quotes is preserved"""
        result = strip_quotes_from_title('"  Test Title  "')
        self.assertEqual(result, 'Test Title')
