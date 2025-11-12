"""
Tests for Actions API authentication
"""
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIRequestFactory
from rest_framework import exceptions
from main.models import User, ApiKey
from main.api.authentication import ApiKeyAuthentication


@override_settings(
    ACTIONS_API_ENABLED=True,
    ACTIONS_API_KEY_HEADER='X-IG-API-Key'
)
class ApiKeyAuthenticationTest(TestCase):
    """Test API key authentication"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = APIRequestFactory()
        self.auth = ApiKeyAuthentication()
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            is_active=True
        )
        
        # Create valid API key
        self.api_key = ApiKey.generate_key(
            user=self.user,
            name='Test API Key'
        )
        
        # Create expired API key
        self.expired_key = ApiKey.generate_key(
            user=self.user,
            name='Expired Key',
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        # Create inactive API key
        self.inactive_key = ApiKey.generate_key(
            user=self.user,
            name='Inactive Key'
        )
        self.inactive_key.is_active = False
        self.inactive_key.save()
    
    def test_valid_api_key(self):
        """Test authentication with valid API key"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_IG_API_KEY'] = self.api_key.key
        
        result = self.auth.authenticate(request)
        
        self.assertIsNotNone(result)
        user, api_key = result
        self.assertEqual(user, self.user)
        self.assertEqual(api_key, self.api_key)
    
    def test_no_api_key(self):
        """Test authentication without API key returns None"""
        request = self.factory.get('/api/test/')
        
        result = self.auth.authenticate(request)
        
        self.assertIsNone(result)
    
    def test_invalid_api_key(self):
        """Test authentication with invalid API key raises exception"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_IG_API_KEY'] = 'invalid-key-12345'
        
        with self.assertRaises(exceptions.AuthenticationFailed) as cm:
            self.auth.authenticate(request)
        
        self.assertIn('Invalid API key', str(cm.exception))
    
    def test_expired_api_key(self):
        """Test authentication with expired API key raises exception"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_IG_API_KEY'] = self.expired_key.key
        
        with self.assertRaises(exceptions.AuthenticationFailed) as cm:
            self.auth.authenticate(request)
        
        self.assertIn('expired or inactive', str(cm.exception).lower())
    
    def test_inactive_api_key(self):
        """Test authentication with inactive API key raises exception"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_IG_API_KEY'] = self.inactive_key.key
        
        with self.assertRaises(exceptions.AuthenticationFailed) as cm:
            self.auth.authenticate(request)
        
        self.assertIn('expired or inactive', str(cm.exception).lower())
    
    def test_api_key_last_used_updated(self):
        """Test that last_used_at is updated on successful auth"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_IG_API_KEY'] = self.api_key.key
        
        # Get initial last_used_at
        initial_last_used = self.api_key.last_used_at
        
        # Authenticate
        self.auth.authenticate(request)
        
        # Refresh from database
        self.api_key.refresh_from_db()
        
        # Check that last_used_at was updated
        self.assertIsNotNone(self.api_key.last_used_at)
        if initial_last_used:
            self.assertGreater(self.api_key.last_used_at, initial_last_used)
    
    @override_settings(ACTIONS_API_ENABLED=False)
    def test_api_disabled(self):
        """Test authentication fails when API is disabled"""
        request = self.factory.get('/api/test/')
        request.META['HTTP_X_IG_API_KEY'] = self.api_key.key
        
        with self.assertRaises(exceptions.AuthenticationFailed) as cm:
            self.auth.authenticate(request)
        
        self.assertIn('not enabled', str(cm.exception).lower())


class ApiKeyModelTest(TestCase):
    """Test ApiKey model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
    
    def test_generate_key(self):
        """Test API key generation"""
        api_key = ApiKey.generate_key(
            user=self.user,
            name='Test Key'
        )
        
        self.assertIsNotNone(api_key.key)
        self.assertEqual(api_key.user, self.user)
        self.assertEqual(api_key.name, 'Test Key')
        self.assertTrue(api_key.is_active)
        self.assertIsNone(api_key.expires_at)
    
    def test_generate_key_with_expiration(self):
        """Test API key generation with expiration"""
        expires_at = timezone.now() + timedelta(days=30)
        api_key = ApiKey.generate_key(
            user=self.user,
            name='Expiring Key',
            expires_at=expires_at
        )
        
        self.assertEqual(api_key.expires_at, expires_at)
    
    def test_is_valid_active(self):
        """Test is_valid returns True for active key"""
        api_key = ApiKey.generate_key(user=self.user, name='Test')
        
        self.assertTrue(api_key.is_valid())
    
    def test_is_valid_inactive(self):
        """Test is_valid returns False for inactive key"""
        api_key = ApiKey.generate_key(user=self.user, name='Test')
        api_key.is_active = False
        api_key.save()
        
        self.assertFalse(api_key.is_valid())
    
    def test_is_valid_expired(self):
        """Test is_valid returns False for expired key"""
        api_key = ApiKey.generate_key(
            user=self.user,
            name='Test',
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        self.assertFalse(api_key.is_valid())
    
    def test_is_valid_not_expired(self):
        """Test is_valid returns True for not yet expired key"""
        api_key = ApiKey.generate_key(
            user=self.user,
            name='Test',
            expires_at=timezone.now() + timedelta(days=1)
        )
        
        self.assertTrue(api_key.is_valid())
    
    def test_update_last_used(self):
        """Test update_last_used updates timestamp"""
        api_key = ApiKey.generate_key(user=self.user, name='Test')
        
        self.assertIsNone(api_key.last_used_at)
        
        api_key.update_last_used()
        
        self.assertIsNotNone(api_key.last_used_at)
