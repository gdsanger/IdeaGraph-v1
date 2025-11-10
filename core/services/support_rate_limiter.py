"""
Support Rate Limiter

This service implements rate limiting for support embed endpoints
using Django's cache backend (Redis in production, locmem in dev).
"""

import logging
import hashlib
from typing import Optional
from django.core.cache import cache

logger = logging.getLogger('support_rate_limiter')


class SupportRateLimiter:
    """
    Rate limiter for support endpoints
    
    Implements sliding window rate limiting per referrer+itemId.
    Uses Django's cache backend for storage.
    """
    
    DEFAULT_LIMIT = 60  # requests
    DEFAULT_WINDOW = 600  # seconds (10 minutes)
    CACHE_PREFIX = 'support_ratelimit'
    
    def __init__(
        self,
        limit: int = DEFAULT_LIMIT,
        window: int = DEFAULT_WINDOW
    ):
        """
        Initialize SupportRateLimiter
        
        Args:
            limit: Maximum requests allowed in window
            window: Time window in seconds
        """
        self.limit = limit
        self.window = window
    
    def check_rate_limit(
        self,
        referrer: str,
        item_id: str,
        fingerprint: Optional[str] = None
    ) -> dict:
        """
        Check if request is within rate limits
        
        Args:
            referrer: Referrer URL
            item_id: UUID of the item
            fingerprint: Optional client fingerprint (hash of UA+IP)
        
        Returns:
            {
                'allowed': bool,
                'limit': int,
                'remaining': int,
                'reset_in': int (seconds until reset)
            }
        """
        # Generate cache key
        key_parts = [referrer, item_id]
        if fingerprint:
            key_parts.append(fingerprint)
        
        cache_key = self._generate_cache_key(key_parts)
        
        # Get current count
        current = cache.get(cache_key, 0)
        
        if current >= self.limit:
            # Rate limit exceeded
            # Try to get TTL (only works with Redis)
            try:
                ttl = cache.ttl(cache_key) or self.window
            except (AttributeError, NotImplementedError):
                # LocMemCache doesn't support ttl()
                ttl = self.window
            
            logger.warning(f"Rate limit exceeded for {cache_key}: {current}/{self.limit}")
            return {
                'allowed': False,
                'limit': self.limit,
                'remaining': 0,
                'reset_in': ttl
            }
        
        # Increment counter
        if current == 0:
            # First request, set with expiry
            cache.set(cache_key, 1, self.window)
            remaining = self.limit - 1
            reset_in = self.window
        else:
            # Increment existing counter
            try:
                cache.incr(cache_key)
                remaining = self.limit - (current + 1)
                # Try to get TTL (only works with Redis)
                try:
                    reset_in = cache.ttl(cache_key) or self.window
                except (AttributeError, NotImplementedError):
                    # LocMemCache doesn't support ttl()
                    reset_in = self.window
            except ValueError:
                # Key expired between get and incr, start fresh
                cache.set(cache_key, 1, self.window)
                remaining = self.limit - 1
                reset_in = self.window
        
        logger.info(f"Rate limit check for {cache_key}: {current + 1}/{self.limit}")
        
        return {
            'allowed': True,
            'limit': self.limit,
            'remaining': max(0, remaining),
            'reset_in': reset_in
        }
    
    def _generate_cache_key(self, parts: list) -> str:
        """
        Generate cache key from parts
        
        Args:
            parts: List of strings to combine
        
        Returns:
            Cache key string
        """
        combined = '|'.join(str(p) for p in parts)
        # Hash to keep key length reasonable
        hashed = hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]
        return f"{self.CACHE_PREFIX}:{hashed}"
    
    def reset(self, referrer: str, item_id: str, fingerprint: Optional[str] = None):
        """
        Reset rate limit for a specific key (for testing)
        
        Args:
            referrer: Referrer URL
            item_id: UUID of the item
            fingerprint: Optional client fingerprint
        """
        key_parts = [referrer, item_id]
        if fingerprint:
            key_parts.append(fingerprint)
        
        cache_key = self._generate_cache_key(key_parts)
        cache.delete(cache_key)
        logger.info(f"Rate limit reset for {cache_key}")
