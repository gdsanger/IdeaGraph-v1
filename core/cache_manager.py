"""
Cache Manager for IdeaGraph

This module provides a flexible cache abstraction layer that allows
switching between different cache backends (Redis, Local Memory, Dummy).

Usage:
    from core.cache_manager import CacheManager
    
    cache_manager = CacheManager()
    
    # Set a value
    cache_manager.set('my_key', 'my_value', timeout=300)
    
    # Get a value
    value = cache_manager.get('my_key')
    
    # Delete a value
    cache_manager.delete('my_key')
    
    # Check if key exists
    if cache_manager.exists('my_key'):
        # ...
"""

import logging
from typing import Any, Optional, List
from django.core.cache import cache
from django.conf import settings


logger = logging.getLogger('IdeaGraph')


class CacheManager:
    """
    Cache Manager providing abstraction over Django's cache framework
    
    This class provides a clean interface for cache operations and includes
    logging and error handling. It supports all Django cache backends:
    - Redis (production)
    - Local Memory (development)
    - Dummy (testing/disabled)
    """
    
    def __init__(self):
        """Initialize the cache manager"""
        self.cache = cache
        self.backend = getattr(settings, 'CACHE_BACKEND', 'locmem')
        logger.debug(f"CacheManager initialized with backend: {self.backend}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from cache
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        try:
            value = self.cache.get(key, default)
            if value is not None:
                logger.debug(f"Cache hit for key: {key}")
            else:
                logger.debug(f"Cache miss for key: {key}")
            return value
        except Exception as e:
            logger.error(f"Error getting cache key '{key}': {str(e)}")
            return default
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """
        Set a value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Optional timeout in seconds (uses default if not specified)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache.set(key, value, timeout=timeout)
            logger.debug(f"Cache set for key: {key}, timeout: {timeout or 'default'}")
            return True
        except Exception as e:
            logger.error(f"Error setting cache key '{key}': {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache.delete(key)
            logger.debug(f"Cache deleted for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting cache key '{key}': {str(e)}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return self.cache.get(key) is not None
        except Exception as e:
            logger.error(f"Error checking cache key '{key}': {str(e)}")
            return False
    
    def clear(self) -> bool:
        """
        Clear all cache entries
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache.clear()
            logger.info("Cache cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False
    
    def get_many(self, keys: List[str]) -> dict:
        """
        Get multiple values from cache
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary of key-value pairs
        """
        try:
            values = self.cache.get_many(keys)
            logger.debug(f"Cache get_many for {len(keys)} keys, found {len(values)} values")
            return values
        except Exception as e:
            logger.error(f"Error getting multiple cache keys: {str(e)}")
            return {}
    
    def set_many(self, data: dict, timeout: Optional[int] = None) -> bool:
        """
        Set multiple values in cache
        
        Args:
            data: Dictionary of key-value pairs
            timeout: Optional timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache.set_many(data, timeout=timeout)
            logger.debug(f"Cache set_many for {len(data)} keys, timeout: {timeout or 'default'}")
            return True
        except Exception as e:
            logger.error(f"Error setting multiple cache keys: {str(e)}")
            return False
    
    def delete_many(self, keys: List[str]) -> bool:
        """
        Delete multiple values from cache
        
        Args:
            keys: List of cache keys
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache.delete_many(keys)
            logger.debug(f"Cache delete_many for {len(keys)} keys")
            return True
        except Exception as e:
            logger.error(f"Error deleting multiple cache keys: {str(e)}")
            return False
    
    def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """
        Increment a cache value
        
        Args:
            key: Cache key
            delta: Amount to increment by
            
        Returns:
            New value or None if error
        """
        try:
            value = self.cache.incr(key, delta)
            logger.debug(f"Cache incremented key: {key}, delta: {delta}")
            return value
        except Exception as e:
            logger.error(f"Error incrementing cache key '{key}': {str(e)}")
            return None
    
    def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """
        Decrement a cache value
        
        Args:
            key: Cache key
            delta: Amount to decrement by
            
        Returns:
            New value or None if error
        """
        try:
            value = self.cache.decr(key, delta)
            logger.debug(f"Cache decremented key: {key}, delta: {delta}")
            return value
        except Exception as e:
            logger.error(f"Error decrementing cache key '{key}': {str(e)}")
            return None
    
    def get_backend_info(self) -> dict:
        """
        Get information about the current cache backend
        
        Returns:
            Dictionary with backend information
        """
        info = {
            'backend': self.backend,
            'backend_class': str(type(self.cache)),
        }
        
        if self.backend == 'redis':
            try:
                info['redis_host'] = getattr(settings, 'REDIS_HOST', 'localhost')
                info['redis_port'] = getattr(settings, 'REDIS_PORT', 6379)
                info['redis_db'] = getattr(settings, 'REDIS_DB', 0)
            except Exception:
                pass
        
        return info
