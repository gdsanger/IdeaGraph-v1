"""
Authentication classes for Actions API
"""
import logging
from django.conf import settings
from rest_framework import authentication, exceptions
from main.models import ApiKey

logger = logging.getLogger(__name__)


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """
    API Key authentication for Actions API
    
    Checks for API key in X-IG-API-Key header and validates it.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using API key
        
        Returns:
            Tuple of (user, api_key) if authentication successful
            None if no API key provided (allows other auth methods)
            
        Raises:
            AuthenticationFailed if API key is invalid
        """
        # Check if Actions API is enabled
        if not settings.ACTIONS_API_ENABLED:
            raise exceptions.AuthenticationFailed('Actions API is not enabled')
        
        # Get API key from header
        api_key_header = settings.ACTIONS_API_KEY_HEADER
        api_key_value = request.META.get(f'HTTP_{api_key_header.upper().replace("-", "_")}')
        
        if not api_key_value:
            # No API key provided, allow other authentication methods
            return None
        
        # Validate API key
        try:
            api_key = ApiKey.objects.select_related('user').get(key=api_key_value)
        except ApiKey.DoesNotExist:
            # Don't log the actual key value to prevent sensitive data exposure
            logger.warning("Invalid API key attempted")
            raise exceptions.AuthenticationFailed('Invalid API key')
        
        # Check if API key is valid
        if not api_key.is_valid():
            logger.warning(f"Expired or inactive API key: {api_key.name}")
            raise exceptions.AuthenticationFailed('API key is expired or inactive')
        
        # Update last used timestamp
        api_key.update_last_used()
        
        # Log successful authentication
        actor = request.META.get(f'HTTP_{settings.ACTIONS_API_ACTOR_HEADER.upper().replace("-", "_")}', 'unknown')
        logger.info(f"API authentication successful - User: {api_key.user.username}, Actor: {actor}")
        
        return (api_key.user, api_key)
