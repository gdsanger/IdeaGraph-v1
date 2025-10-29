"""
Activity views for IdeaGraph

This module provides views for the activity sidebar feature.
"""

import logging
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.http import HttpRequest, HttpResponse
from core.services.weaviate_activity_service import WeaviateActivityService, WeaviateActivityServiceError
from core.cache_manager import CacheManager

logger = logging.getLogger('IdeaGraph')


@require_GET
def activity_sidebar(request: HttpRequest) -> HttpResponse:
    """
    Render activity sidebar with recent 20 changes
    
    This view fetches recent activity from Weaviate KnowledgeObject collection
    and renders it as an HTML partial for HTMX.
    
    Args:
        request: HTTP request object
    
    Returns:
        Rendered activity sidebar HTML
    """
    # Get tenant from user session (if available)
    tenant = None
    user_id = request.session.get('user_id')
    if user_id:
        # Could fetch tenant from user model if needed
        # For now, we'll query all tenants
        pass
    
    # Build cache key
    cache_key = f"activity:sidebar:{tenant or 'public'}"
    
    # Initialize cache manager
    cache_manager = CacheManager()
    
    # Try to get from cache
    data = cache_manager.get(cache_key)
    
    if data is None:
        # Cache miss - fetch from Weaviate
        try:
            logger.info(f"Fetching activity for cache key: {cache_key}")
            
            # Initialize Weaviate activity service
            service = WeaviateActivityService()
            
            # Fetch recent activity
            activity_items = service.get_recent_activity(
                limit=20,
                tenant=tenant
            )
            
            # Filter by permissions (basic implementation)
            data = [
                item for item in activity_items
                if _has_permission(request, item)
            ]
            
            # Cache for 30 seconds
            cache_manager.set(cache_key, data, timeout=30)
            
            logger.info(f"Cached {len(data)} activity items")
            
            # Close service connection
            service.close()
            
        except WeaviateActivityServiceError as e:
            logger.error(f"Weaviate activity error: {e.message} - {e.details}")
            # Return empty list on error
            data = []
        except Exception as e:
            logger.error(f"Unexpected error fetching activity: {str(e)}")
            data = []
    else:
        logger.debug(f"Activity cache hit for key: {cache_key}")
    
    # Render template
    return render(
        request,
        'main/partials/activity_sidebar.html',
        {'items': data}
    )


def _has_permission(request: HttpRequest, activity_item: dict) -> bool:
    """
    Check if user has permission to view activity item
    
    This is a basic implementation. In production, you would implement
    proper tenant/object-level permissions.
    
    Args:
        request: HTTP request object
        activity_item: Activity item dictionary
    
    Returns:
        True if user has permission, False otherwise
    """
    # Basic implementation - show all items to logged-in users
    # In production, implement proper permission checks based on:
    # - Tenant membership
    # - Object visibility settings
    # - User role/permissions
    
    # For now, allow all items if user is logged in
    return bool(request.session.get('user_id'))
