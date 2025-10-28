"""
Tests for Weaviate admin views
"""
from django.test import TestCase, Client
from main.models import User, Settings


class WeaviateViewsTest(TestCase):
    """Test Weaviate admin views authentication and authorization"""
    
    def setUp(self):
        """Set up test data"""
        # Create admin user
        self.admin = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        self.admin.set_password('Admin@123')
        self.admin.save()
        
        # Create regular user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create settings
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
        
        self.client = Client()
    
    def login_admin(self):
        """Helper to log in admin user"""
        response = self.client.post('/login/', {
            'username': 'admin',
            'password': 'Admin@123'
        })
        return response
    
    def login_user(self):
        """Helper to log in regular user"""
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'Test@123'
        })
        return response
    
    def test_weaviate_status_view_unauthenticated(self):
        """Test accessing Weaviate status view without authentication"""
        response = self.client.get('/admin/weaviate/status/')
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_weaviate_status_view_non_admin(self):
        """Test accessing Weaviate status view as non-admin"""
        self.login_user()
        
        response = self.client.get('/admin/weaviate/status/')
        
        # Should redirect to home (forbidden)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.url)
    
    def test_weaviate_status_view_admin(self):
        """Test accessing Weaviate status view as admin"""
        self.login_admin()
        
        response = self.client.get('/admin/weaviate/status/')
        
        # Should return 200 and render the template
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Weaviate')
    
    def test_weaviate_maintenance_view_unauthenticated(self):
        """Test accessing Weaviate maintenance view without authentication"""
        response = self.client.get('/admin/weaviate/maintenance/')
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_weaviate_maintenance_view_non_admin(self):
        """Test accessing Weaviate maintenance view as non-admin"""
        self.login_user()
        
        response = self.client.get('/admin/weaviate/maintenance/')
        
        # Should redirect to home (forbidden)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.url)
    
    def test_weaviate_maintenance_view_admin(self):
        """Test accessing Weaviate maintenance view as admin"""
        self.login_admin()
        
        response = self.client.get('/admin/weaviate/maintenance/')
        
        # Should return 200 and render the template
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Weaviate')
    
    def test_admin_middleware_protects_weaviate_urls(self):
        """Test that AdminRequiredMiddleware protects Weaviate URLs"""
        # Test with regular user
        self.login_user()
        
        # Try to access both views
        response1 = self.client.get('/admin/weaviate/status/')
        response2 = self.client.get('/admin/weaviate/maintenance/')
        
        # Both should redirect (not accessible to non-admin)
        self.assertEqual(response1.status_code, 302)
        self.assertEqual(response2.status_code, 302)
        
        # Now test with admin
        self.client.logout()
        self.login_admin()
        
        response1 = self.client.get('/admin/weaviate/status/')
        response2 = self.client.get('/admin/weaviate/maintenance/')
        
        # Both should be accessible
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
