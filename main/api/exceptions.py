"""
Custom exception handler for Actions API
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        custom_response_data = {
            'success': False,
            'error': str(exc),
            'details': response.data if isinstance(response.data, dict) else {'message': response.data}
        }
        response.data = custom_response_data
    else:
        # Handle unexpected exceptions
        logger.error(f"Unhandled exception in API: {exc}", exc_info=True)
        custom_response_data = {
            'success': False,
            'error': 'Internal server error',
            'details': str(exc) if logger.level == logging.DEBUG else 'An unexpected error occurred'
        }
        response = Response(custom_response_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response
