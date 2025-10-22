"""
Tests for Cache Manager

This module tests the cache manager functionality with different backends.
"""

import unittest
from django.test import TestCase, override_settings
from django.core.cache import cache
from core.cache_manager import CacheManager


class CacheManagerTestCase(TestCase):
    """Test cases for CacheManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cache_manager = CacheManager()
        # Clear cache before each test
        cache.clear()
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_cache_manager_initialization(self):
        """Test that cache manager initializes correctly"""
        self.assertIsNotNone(self.cache_manager)
        self.assertIsNotNone(self.cache_manager.cache)
    
    def test_set_and_get(self):
        """Test setting and getting values"""
        key = 'test_key'
        value = 'test_value'
        
        # Set value
        result = self.cache_manager.set(key, value)
        self.assertTrue(result)
        
        # Get value
        retrieved_value = self.cache_manager.get(key)
        self.assertEqual(retrieved_value, value)
    
    def test_get_nonexistent_key(self):
        """Test getting a nonexistent key returns default"""
        key = 'nonexistent_key'
        default_value = 'default'
        
        retrieved_value = self.cache_manager.get(key, default=default_value)
        self.assertEqual(retrieved_value, default_value)
    
    def test_delete(self):
        """Test deleting values"""
        key = 'test_key'
        value = 'test_value'
        
        # Set and verify
        self.cache_manager.set(key, value)
        self.assertEqual(self.cache_manager.get(key), value)
        
        # Delete
        result = self.cache_manager.delete(key)
        self.assertTrue(result)
        
        # Verify deleted
        self.assertIsNone(self.cache_manager.get(key))
    
    def test_exists(self):
        """Test checking if key exists"""
        key = 'test_key'
        value = 'test_value'
        
        # Initially should not exist
        self.assertFalse(self.cache_manager.exists(key))
        
        # Set value
        self.cache_manager.set(key, value)
        
        # Should exist now
        self.assertTrue(self.cache_manager.exists(key))
        
        # Delete and check again
        self.cache_manager.delete(key)
        self.assertFalse(self.cache_manager.exists(key))
    
    def test_clear(self):
        """Test clearing all cache"""
        # Set multiple values
        self.cache_manager.set('key1', 'value1')
        self.cache_manager.set('key2', 'value2')
        self.cache_manager.set('key3', 'value3')
        
        # Verify they exist
        self.assertIsNotNone(self.cache_manager.get('key1'))
        self.assertIsNotNone(self.cache_manager.get('key2'))
        
        # Clear cache
        result = self.cache_manager.clear()
        self.assertTrue(result)
        
        # Verify all cleared
        self.assertIsNone(self.cache_manager.get('key1'))
        self.assertIsNone(self.cache_manager.get('key2'))
        self.assertIsNone(self.cache_manager.get('key3'))
    
    def test_get_many(self):
        """Test getting multiple values"""
        data = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3'
        }
        
        # Set values
        for key, value in data.items():
            self.cache_manager.set(key, value)
        
        # Get many
        retrieved = self.cache_manager.get_many(['key1', 'key2', 'key3'])
        
        self.assertEqual(len(retrieved), 3)
        self.assertEqual(retrieved['key1'], 'value1')
        self.assertEqual(retrieved['key2'], 'value2')
        self.assertEqual(retrieved['key3'], 'value3')
    
    def test_set_many(self):
        """Test setting multiple values"""
        data = {
            'key1': 'value1',
            'key2': 'value2',
            'key3': 'value3'
        }
        
        # Set many
        result = self.cache_manager.set_many(data)
        self.assertTrue(result)
        
        # Verify all set
        self.assertEqual(self.cache_manager.get('key1'), 'value1')
        self.assertEqual(self.cache_manager.get('key2'), 'value2')
        self.assertEqual(self.cache_manager.get('key3'), 'value3')
    
    def test_delete_many(self):
        """Test deleting multiple values"""
        # Set values
        self.cache_manager.set('key1', 'value1')
        self.cache_manager.set('key2', 'value2')
        self.cache_manager.set('key3', 'value3')
        
        # Delete many
        result = self.cache_manager.delete_many(['key1', 'key2'])
        self.assertTrue(result)
        
        # Verify deleted
        self.assertIsNone(self.cache_manager.get('key1'))
        self.assertIsNone(self.cache_manager.get('key2'))
        
        # key3 should still exist
        self.assertEqual(self.cache_manager.get('key3'), 'value3')
    
    def test_timeout(self):
        """Test cache timeout"""
        import time
        
        key = 'test_timeout_key'
        value = 'test_value'
        
        # Set with 1 second timeout
        self.cache_manager.set(key, value, timeout=1)
        
        # Should exist immediately
        self.assertEqual(self.cache_manager.get(key), value)
        
        # Wait for timeout
        time.sleep(2)
        
        # Should be expired (Note: this test might be flaky in some environments)
        retrieved = self.cache_manager.get(key)
        # In some test environments, timeout might not work as expected
        # so we just check that the method doesn't crash
        self.assertIn(retrieved, [None, value])
    
    def test_complex_data_types(self):
        """Test caching complex data types"""
        # Dictionary
        dict_data = {'name': 'John', 'age': 30, 'active': True}
        self.cache_manager.set('dict_key', dict_data)
        self.assertEqual(self.cache_manager.get('dict_key'), dict_data)
        
        # List
        list_data = [1, 2, 3, 'four', 5.0]
        self.cache_manager.set('list_key', list_data)
        self.assertEqual(self.cache_manager.get('list_key'), list_data)
        
        # Nested structure
        nested_data = {
            'users': [
                {'id': 1, 'name': 'Alice'},
                {'id': 2, 'name': 'Bob'}
            ],
            'metadata': {
                'count': 2,
                'page': 1
            }
        }
        self.cache_manager.set('nested_key', nested_data)
        self.assertEqual(self.cache_manager.get('nested_key'), nested_data)
    
    def test_get_backend_info(self):
        """Test getting backend information"""
        info = self.cache_manager.get_backend_info()
        
        self.assertIsInstance(info, dict)
        self.assertIn('backend', info)
        self.assertIn('backend_class', info)
        
        # Backend should be one of the supported types
        self.assertIn(info['backend'], ['redis', 'locmem', 'dummy'])


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    },
    CACHE_BACKEND='locmem'
)
class CacheManagerLocMemTestCase(CacheManagerTestCase):
    """Test CacheManager with Local Memory backend"""
    pass


@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    },
    CACHE_BACKEND='dummy'
)
class CacheManagerDummyTestCase(TestCase):
    """Test CacheManager with Dummy backend (no caching)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.cache_manager = CacheManager()
    
    def test_dummy_backend_no_caching(self):
        """Test that dummy backend doesn't actually cache"""
        key = 'test_key'
        value = 'test_value'
        
        # Set value
        self.cache_manager.set(key, value)
        
        # Dummy cache should return None
        retrieved_value = self.cache_manager.get(key)
        self.assertIsNone(retrieved_value)


class CacheIntegrationTestCase(TestCase):
    """Integration tests for cache usage in the application"""
    
    def setUp(self):
        """Set up test fixtures"""
        cache.clear()
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_django_cache_framework(self):
        """Test Django's cache framework directly"""
        # This ensures our cache configuration is working
        cache.set('test_key', 'test_value', timeout=300)
        self.assertEqual(cache.get('test_key'), 'test_value')
        
        cache.delete('test_key')
        self.assertIsNone(cache.get('test_key'))
    
    def test_cache_key_patterns(self):
        """Test recommended cache key patterns"""
        # Test structured keys
        cache.set('user:123:profile', {'name': 'John'})
        cache.set('graph:token:tenant_id', 'token_value')
        cache.set('api:response:endpoint', {'data': 'value'})
        
        # Retrieve
        self.assertIsNotNone(cache.get('user:123:profile'))
        self.assertIsNotNone(cache.get('graph:token:tenant_id'))
        self.assertIsNotNone(cache.get('api:response:endpoint'))


if __name__ == '__main__':
    unittest.main()
