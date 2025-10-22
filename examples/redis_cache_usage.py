"""
Redis Cache Usage Examples

This module demonstrates how to use the Redis cache system in IdeaGraph.
Run this script to test cache functionality.

Usage:
    python examples/redis_cache_usage.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideagraph.settings')
django.setup()

from core.cache_manager import CacheManager
from django.core.cache import cache
import time


def example_basic_operations():
    """Example: Basic cache operations"""
    print("\n=== Example 1: Basic Cache Operations ===")
    
    cache_manager = CacheManager()
    
    # Get backend info
    info = cache_manager.get_backend_info()
    print(f"Using cache backend: {info['backend']}")
    print(f"Backend class: {info['backend_class']}")
    
    # Set a value
    print("\n1. Setting value in cache...")
    cache_manager.set('example_key', 'Hello Redis!', timeout=300)
    
    # Get the value
    print("2. Getting value from cache...")
    value = cache_manager.get('example_key')
    print(f"   Retrieved: {value}")
    
    # Check if key exists
    print("3. Checking if key exists...")
    exists = cache_manager.exists('example_key')
    print(f"   Exists: {exists}")
    
    # Delete the value
    print("4. Deleting value from cache...")
    cache_manager.delete('example_key')
    
    # Try to get deleted value
    value = cache_manager.get('example_key')
    print(f"   After deletion: {value}")


def example_complex_data():
    """Example: Caching complex data structures"""
    print("\n=== Example 2: Caching Complex Data ===")
    
    cache_manager = CacheManager()
    
    # Cache a dictionary
    user_profile = {
        'id': 123,
        'name': 'John Doe',
        'email': 'john@example.com',
        'permissions': ['read', 'write', 'admin'],
        'settings': {
            'theme': 'dark',
            'language': 'de'
        }
    }
    
    print("1. Caching user profile...")
    cache_manager.set('user:123:profile', user_profile, timeout=3600)
    
    # Retrieve and display
    print("2. Retrieving user profile...")
    cached_profile = cache_manager.get('user:123:profile')
    print(f"   User: {cached_profile['name']}")
    print(f"   Email: {cached_profile['email']}")
    print(f"   Theme: {cached_profile['settings']['theme']}")
    
    # Cache a list
    recent_activities = [
        {'action': 'login', 'timestamp': '2025-10-22 10:00:00'},
        {'action': 'edit_item', 'timestamp': '2025-10-22 10:15:00'},
        {'action': 'create_task', 'timestamp': '2025-10-22 10:30:00'}
    ]
    
    print("\n3. Caching activity log...")
    cache_manager.set('user:123:activities', recent_activities, timeout=1800)
    
    cached_activities = cache_manager.get('user:123:activities')
    print(f"   Cached {len(cached_activities)} activities")


def example_batch_operations():
    """Example: Batch cache operations"""
    print("\n=== Example 3: Batch Operations ===")
    
    cache_manager = CacheManager()
    
    # Set multiple values at once
    print("1. Setting multiple values...")
    data = {
        'config:app_name': 'IdeaGraph',
        'config:version': '1.0',
        'config:max_items': 1000,
        'config:enable_ai': True
    }
    cache_manager.set_many(data, timeout=600)
    print(f"   Set {len(data)} configuration values")
    
    # Get multiple values at once
    print("\n2. Getting multiple values...")
    keys = ['config:app_name', 'config:version', 'config:max_items']
    values = cache_manager.get_many(keys)
    for key, value in values.items():
        print(f"   {key}: {value}")
    
    # Delete multiple values
    print("\n3. Deleting multiple values...")
    cache_manager.delete_many(['config:app_name', 'config:version'])
    
    # Verify deletion
    remaining = cache_manager.get_many(keys)
    print(f"   Remaining keys: {list(remaining.keys())}")


def example_token_caching():
    """Example: Token caching (similar to GraphService)"""
    print("\n=== Example 4: Token Caching Pattern ===")
    
    cache_manager = CacheManager()
    
    def get_access_token():
        """Simulate getting an access token with caching"""
        TOKEN_CACHE_KEY = 'example:access_token'
        
        # Check cache first
        cached_token = cache_manager.get(TOKEN_CACHE_KEY)
        if cached_token:
            print("   ✓ Using cached token")
            return cached_token
        
        # Simulate expensive token acquisition
        print("   → Acquiring new token (expensive operation)...")
        time.sleep(0.5)  # Simulate API call
        new_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        
        # Cache the token
        cache_manager.set(TOKEN_CACHE_KEY, new_token, timeout=3300)  # 55 minutes
        print("   ✓ Token cached for 55 minutes")
        
        return new_token
    
    # First call - no cache
    print("1. First token request (no cache):")
    token1 = get_access_token()
    print(f"   Token: {token1[:20]}...")
    
    # Second call - from cache
    print("\n2. Second token request (from cache):")
    token2 = get_access_token()
    print(f"   Token: {token2[:20]}...")
    
    # Verify same token
    assert token1 == token2, "Tokens should match!"


def example_cache_patterns():
    """Example: Common caching patterns"""
    print("\n=== Example 5: Common Cache Patterns ===")
    
    cache_manager = CacheManager()
    
    # Pattern 1: Cache-aside (lazy loading)
    print("1. Cache-aside pattern:")
    def get_user_data(user_id):
        cache_key = f'user:{user_id}:data'
        
        # Try cache first
        data = cache_manager.get(cache_key)
        if data:
            print("   ✓ Cache hit")
            return data
        
        # Cache miss - load from "database"
        print("   → Cache miss - loading from database")
        data = {'id': user_id, 'name': f'User {user_id}', 'status': 'active'}
        
        # Store in cache
        cache_manager.set(cache_key, data, timeout=300)
        return data
    
    user = get_user_data(456)
    print(f"   User: {user['name']}")
    
    user = get_user_data(456)  # Should hit cache
    print(f"   User: {user['name']}")
    
    # Pattern 2: Cache invalidation on update
    print("\n2. Cache invalidation pattern:")
    def update_user_data(user_id, new_data):
        cache_key = f'user:{user_id}:data'
        
        # Update database (simulated)
        print(f"   → Updating user {user_id}")
        
        # Invalidate cache
        cache_manager.delete(cache_key)
        print("   ✓ Cache invalidated")
    
    update_user_data(456, {'status': 'inactive'})
    
    # Next read will fetch fresh data
    user = get_user_data(456)  # Cache miss after invalidation


def example_structured_keys():
    """Example: Using structured cache keys"""
    print("\n=== Example 6: Structured Cache Keys ===")
    
    cache_manager = CacheManager()
    
    # Use structured keys for better organization
    print("Setting values with structured keys...")
    
    # User-related keys
    cache_manager.set('user:123:profile', {'name': 'Alice'})
    cache_manager.set('user:123:settings', {'theme': 'dark'})
    cache_manager.set('user:456:profile', {'name': 'Bob'})
    
    # API response keys
    cache_manager.set('api:items:list', [1, 2, 3])
    cache_manager.set('api:items:123', {'title': 'Item 123'})
    
    # Graph API token
    cache_manager.set('graph:token:tenant_xyz', 'token_value')
    
    print("\nStructured keys created:")
    print("  User profiles: user:<id>:profile")
    print("  User settings: user:<id>:settings")
    print("  API responses: api:<resource>:<id>")
    print("  Tokens: graph:token:<tenant_id>")


def example_django_cache():
    """Example: Using Django's cache framework directly"""
    print("\n=== Example 7: Django Cache Framework ===")
    
    print("Using Django's cache directly (lower-level API)...")
    
    # Set value
    cache.set('django_key', 'Django cache value', 300)
    
    # Get value
    value = cache.get('django_key')
    print(f"Retrieved: {value}")
    
    # Set multiple
    cache.set_many({
        'key1': 'value1',
        'key2': 'value2'
    })
    
    # Get multiple
    values = cache.get_many(['key1', 'key2'])
    print(f"Multiple values: {values}")
    
    # Clean up
    cache.delete('django_key')
    cache.delete_many(['key1', 'key2'])


def run_all_examples():
    """Run all examples"""
    print("=" * 60)
    print("Redis Cache Usage Examples for IdeaGraph")
    print("=" * 60)
    
    try:
        example_basic_operations()
        example_complex_data()
        example_batch_operations()
        example_token_caching()
        example_cache_patterns()
        example_structured_keys()
        example_django_cache()
        
        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_examples()
