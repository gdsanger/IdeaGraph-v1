"""
Support Views

Views for embeddable support chat and form.
"""

import logging
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger('support_views')


# Exempt from authentication middleware
def exempt_from_auth(view_func):
    """Mark view as exempt from authentication middleware"""
    view_func.exempt_from_auth = True
    return view_func


@xframe_options_exempt
@exempt_from_auth
def embed_support_view(request):
    """
    GET /embed/support
    
    Render the embeddable support chat/form interface
    
    Query params:
        - itemId: UUID of the item (required)
        - key: Long-lived embed API key (recommended for static embeds)
        - t: JWT access token or sig+ts for HMAC (alternative)
        - r: JWT refresh token (optional, for automatic token refresh with t)
        - locale: Language (de|en, default: de)
        - theme: Theme (auto|light|dark, default: auto)
    """
    # Get parameters from query string
    item_id = request.GET.get('itemId', '')
    embed_key = request.GET.get('key', '')
    token = request.GET.get('t', '')
    refresh_token = request.GET.get('r', '')
    locale = request.GET.get('locale', 'de')
    theme = request.GET.get('theme', 'auto')
    
    # Basic validation
    if not item_id:
        return render(request, 'main/embed/support_error.html', {
            'error': 'Missing itemId parameter'
        }, status=400)
    
    # Check authentication: embed key, access token, or HMAC
    if not embed_key and not token:
        # Check for HMAC params
        sig = request.GET.get('sig', '')
        ts = request.GET.get('ts', '')
        if not sig or not ts:
            return render(request, 'main/embed/support_error.html', {
                'error': 'Missing authentication (key, t, or sig+ts)'
            }, status=401)
    
    context = {
        'item_id': item_id,
        'embed_key': embed_key,
        'token': token,
        'refresh_token': refresh_token,
        'locale': locale,
        'theme': theme,
    }
    
    logger.info(f"Rendering embed support for item {item_id}")
    return render(request, 'main/embed/support.html', context)
