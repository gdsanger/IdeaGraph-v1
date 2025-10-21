"""
Test suite for static files accessibility.
"""
from django.test import TestCase, Client
from django.urls import reverse


class StaticFilesAccessTest(TestCase):
    """Test static files are accessible without authentication"""
    
    def setUp(self):
        self.client = Client()
    
    def test_static_files_accessible_without_login(self):
        """Test static files can be accessed without authentication"""
        # Try to access a static file path (even if the file doesn't exist,
        # it should not redirect to login)
        response = self.client.get('/static/main/js/tag-token.js')
        
        # Should not redirect to login (302 with Location to /login/)
        # It might return 404 if file doesn't exist in test, or 200 if it does,
        # but it should NOT return 302 redirect to login
        self.assertNotEqual(response.status_code, 302)
        
        # Verify it's not redirecting to login
        if response.status_code == 302:
            self.assertNotIn('/login/', response.get('Location', ''))
    
    def test_static_directory_accessible_without_login(self):
        """Test static directory paths are accessible without authentication"""
        # Try to access static directory path
        response = self.client.get('/static/')
        
        # Should not redirect to login
        self.assertNotEqual(response.status_code, 302)
        
        # Verify it's not redirecting to login
        if response.status_code == 302:
            self.assertNotIn('/login/', response.get('Location', ''))
    
    def test_protected_pages_still_require_login(self):
        """Test that non-static pages still require authentication"""
        # Try to access a protected page
        response = self.client.get(reverse('main:home'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.get('Location', ''))
