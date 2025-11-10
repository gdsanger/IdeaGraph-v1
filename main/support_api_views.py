"""
Support API Views

API endpoints for embeddable support chat and form.
"""

import json
import logging
import hashlib
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger('support_api_views')


# Telemetry counters (in-memory for MVP, could be exported to Prometheus/StatsD)
_telemetry = {
    'support_chat_send_total': 0,
    'support_chat_send_success': 0,
    'support_chat_send_error': 0,
    'support_precheck_total': 0,
    'support_precheck_resolved_total': 0,
    'support_submit_total': 0,
    'support_submit_success': 0,
    'support_submit_despite_duplicate_total': 0,
    'support_auth_failure_total': 0,
    'support_rate_limit_exceeded_total': 0,
    'support_token_refresh_total': 0,
    'support_token_refresh_success': 0,
}


def _increment_telemetry(counter: str):
    """Increment a telemetry counter"""
    global _telemetry
    if counter in _telemetry:
        _telemetry[counter] += 1
        if _telemetry[counter] % 10 == 0:  # Log every 10th event
            logger.info(f"Telemetry: {counter}={_telemetry[counter]}")


def _authenticate_request(request, item_id):
    """
    Authenticate support embed request
    
    Checks JWT token (Authorization header) or HMAC signature (query params).
    Also validates referrer against allowlist.
    
    Returns:
        tuple: (authenticated: bool, error_response: JsonResponse or None)
    """
    from core.services.support_auth_service import SupportAuthService
    from main.models import Settings
    
    auth_service = SupportAuthService()
    
    # Try JWT authentication first
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        result = auth_service.verify_jwt(token)
        
        if not result['valid']:
            return False, JsonResponse({
                'success': False,
                'error': result['error']
            }, status=401)
        
        # Verify item_id matches
        if result['item_id'] != str(item_id):
            return False, JsonResponse({
                'success': False,
                'error': 'Token item_id mismatch'
            }, status=403)
        
        return True, None
    
    # Try HMAC authentication
    signature = request.GET.get('sig') or request.POST.get('sig')
    timestamp = request.GET.get('ts') or request.POST.get('ts')
    
    if signature and timestamp:
        # Get HMAC secret from settings
        try:
            settings = Settings.objects.first()
            if not settings or not hasattr(settings, 'support_embed_secret'):
                logger.error("Support embed secret not configured")
                return False, JsonResponse({
                    'success': False,
                    'error': 'Authentication not configured'
                }, status=500)
            
            secret = getattr(settings, 'support_embed_secret', '')
            if not secret:
                # Fallback to JWT secret
                from django.conf import settings as django_settings
                secret = django_settings.JWT_SECRET
            
            result = auth_service.verify_hmac(
                item_id=str(item_id),
                signature=signature,
                timestamp=timestamp,
                secret=secret
            )
            
            if not result['valid']:
                return False, JsonResponse({
                    'success': False,
                    'error': result['error']
                }, status=401)
            
            return True, None
        
        except Exception as e:
            logger.error(f"HMAC authentication error: {str(e)}")
            return False, JsonResponse({
                'success': False,
                'error': 'Authentication failed'
            }, status=500)
    
    # No valid authentication method found
    return False, JsonResponse({
        'success': False,
        'error': 'Missing authentication'
    }, status=401)


def _check_referrer(request):
    """
    Check if referrer is in allowlist
    
    Returns:
        tuple: (allowed: bool, error_response: JsonResponse or None)
    """
    from main.models import Settings
    
    referrer = request.headers.get('Referer', '')
    
    # Get allowlist from settings
    try:
        settings = Settings.objects.first()
        # For MVP, we'll be permissive - only block if explicitly configured
        # In production, this should be a proper allowlist
        if settings and hasattr(settings, 'support_embed_allowlist'):
            allowlist = getattr(settings, 'support_embed_allowlist', '')
            if allowlist and referrer:
                # Simple domain check
                allowed_domains = [d.strip() for d in allowlist.split(',')]
                referrer_domain = referrer.split('/')[2] if '/' in referrer else referrer
                
                if not any(domain in referrer_domain for domain in allowed_domains if domain):
                    logger.warning(f"Referrer not in allowlist: {referrer}")
                    return False, JsonResponse({
                        'success': False,
                        'error': 'Referrer not allowed'
                    }, status=403)
    except Exception as e:
        logger.error(f"Error checking referrer: {str(e)}")
    
    return True, None


def _check_rate_limit(request, item_id):
    """
    Check rate limits for support requests
    
    Returns:
        tuple: (allowed: bool, error_response: JsonResponse or None)
    """
    from core.services.support_rate_limiter import SupportRateLimiter
    
    referrer = request.headers.get('Referer', 'unknown')
    user_agent = request.headers.get('User-Agent', '')
    
    # Generate fingerprint from referrer + user agent
    fingerprint = hashlib.sha256(f"{referrer}|{user_agent}".encode()).hexdigest()[:16]
    
    rate_limiter = SupportRateLimiter()
    result = rate_limiter.check_rate_limit(
        referrer=referrer,
        item_id=str(item_id),
        fingerprint=fingerprint
    )
    
    if not result['allowed']:
        return False, JsonResponse({
            'success': False,
            'error': 'Rate limit exceeded',
            'retry_after': result['reset_in']
        }, status=429)
    
    return True, fingerprint


@csrf_exempt
@require_http_methods(["POST"])
def api_support_chat_send(request, item_id):
    """
    POST /api/support/chat/send
    
    Send a message to the support chat (uses existing Q&A service)
    
    Body: {
        "message": "string",
        "sessionId": "optional string"
    }
    
    Returns: {
        "success": true,
        "answer": "string",
        "sources": [...],
        "meta": {...}
    }
    """
    # Authenticate
    authenticated, error_response = _authenticate_request(request, item_id)
    if not authenticated:
        return error_response
    
    # Check referrer
    allowed, error_response = _check_referrer(request)
    if not allowed:
        return error_response
    
    # Check rate limit
    allowed, fingerprint = _check_rate_limit(request, item_id)
    if not allowed:
        _increment_telemetry('support_rate_limit_exceeded_total')
        return fingerprint  # This is actually the error response
    
    _increment_telemetry('support_chat_send_total')
    
    # Parse request
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    
    message = data.get('message', '').strip()
    session_id = data.get('sessionId')
    conversation_history = data.get('conversation_history', [])
    
    if not message:
        return JsonResponse({
            'success': False,
            'error': 'Message is required'
        }, status=400)
    
    # Use existing Q&A service
    try:
        from core.services.item_question_answering_service import (
            ItemQuestionAnsweringService,
            ItemQuestionAnsweringServiceError
        )
        
        qa_service = ItemQuestionAnsweringService()
        result = qa_service.answer_question(
            item_id=str(item_id),
            question=message,
            conversation_history=conversation_history
        )
        
        if result.get('success'):
            logger.info(f"Support chat answer generated for item {item_id}")
            _increment_telemetry('support_chat_send_success')
            return JsonResponse({
                'success': True,
                'answer': result.get('answer', ''),
                'sources': result.get('sources', []),
                'meta': {
                    'relevance_score': result.get('relevance_score', 0.0),
                    'qa_id': result.get('qa_id', '')
                }
            })
        else:
            logger.error(f"Q&A service error: {result.get('error')}")
            _increment_telemetry('support_chat_send_error')
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to generate answer')
            }, status=500)
    
    except ItemQuestionAnsweringServiceError as e:
        logger.error(f"Q&A service error: {str(e)}")
        _increment_telemetry('support_chat_send_error')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in chat send: {str(e)}", exc_info=True)
        _increment_telemetry('support_chat_send_error')
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_support_precheck(request, item_id):
    """
    POST /api/support/precheck
    
    Precheck a support submission (auto-answer + duplicates)
    
    Body: {
        "type": "support|improvement|feature|bug",
        "title": "string",
        "description": "string"
    }
    
    Returns: {
        "success": true,
        "autoAnswer": {...},
        "duplicates": [...],
        "recommendation": "resolve|submit|ask_user"
    }
    """
    # Authenticate
    authenticated, error_response = _authenticate_request(request, item_id)
    if not authenticated:
        return error_response
    
    # Check referrer
    allowed, error_response = _check_referrer(request)
    if not allowed:
        return error_response
    
    # Check rate limit
    allowed, fingerprint = _check_rate_limit(request, item_id)
    if not allowed:
        return fingerprint
    
    # Parse request
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    
    task_type = data.get('type', 'support')
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    
    if not title:
        return JsonResponse({
            'success': False,
            'error': 'Title is required'
        }, status=400)
    
    # Run precheck
    try:
        from core.services.support_precheck_service import SupportPrecheckService
        
        precheck_service = SupportPrecheckService()
        result = precheck_service.precheck(
            item_id=str(item_id),
            title=title,
            description=description,
            task_type=task_type
        )
        
        logger.info(f"Support precheck complete for item {item_id}: {result['recommendation']}")
        
        # Track if issue was resolved by precheck
        if result['recommendation'] == 'resolve':
            _increment_telemetry('support_precheck_resolved_total')
        
        return JsonResponse({
            'success': True,
            'autoAnswer': result['auto_answer'],
            'duplicates': result['duplicates'],
            'recommendation': result['recommendation']
        })
    
    except Exception as e:
        logger.error(f"Error in precheck: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Precheck failed'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_support_submit(request, item_id):
    """
    POST /api/support/submit
    
    Submit a support request as a task
    
    Body: {
        "type": "support|improvement|feature|bug",
        "title": "string",
        "description": "string",
        "reporter": {"email": "optional", "referrer": "auto"},
        "autoAnswer": {"offered": bool, "accepted": bool, "summary": "optional"},
        "duplicateOfTaskId": "uuid|null",
        "chatHistory": [...]
    }
    
    Returns: {
        "success": true,
        "taskId": "uuid",
        "url": "/items/<id>/tasks/"
    }
    """
    # Authenticate
    authenticated, error_response = _authenticate_request(request, item_id)
    if not authenticated:
        return error_response
    
    # Check referrer
    allowed, error_response = _check_referrer(request)
    if not allowed:
        return error_response
    
    # Check rate limit
    allowed, fingerprint = _check_rate_limit(request, item_id)
    if not allowed:
        return fingerprint
    
    # Parse request
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    
    task_type = data.get('type', 'support')
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    reporter = data.get('reporter', {})
    auto_answer = data.get('autoAnswer')
    duplicate_of_task_id = data.get('duplicateOfTaskId')
    chat_history = data.get('chatHistory')
    
    if not title:
        return JsonResponse({
            'success': False,
            'error': 'Title is required'
        }, status=400)
    
    # Submit task
    try:
        from core.services.support_submit_service import SupportSubmitService
        
        submit_service = SupportSubmitService()
        result = submit_service.submit(
            item_id=str(item_id),
            title=title,
            description=description,
            task_type=task_type,
            reporter_email=reporter.get('email'),
            reporter_referrer=request.headers.get('Referer', ''),
            auto_answer=auto_answer,
            duplicate_of_task_id=duplicate_of_task_id,
            client_fingerprint=fingerprint,
            chat_history=chat_history
        )
        
        if result['success']:
            logger.info(f"Support task submitted for item {item_id}: {result['task_id']}")
            _increment_telemetry('support_submit_success')
            
            # Track if submitted despite duplicate
            if duplicate_of_task_id:
                _increment_telemetry('support_submit_despite_duplicate_total')
            
            return JsonResponse({
                'success': True,
                'taskId': result['task_id'],
                'url': result['url']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Submission failed')
            }, status=500)
    
    except Exception as e:
        logger.error(f"Error in submit: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Submission failed'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_support_token_refresh(request):
    """
    POST /api/support/token/refresh
    
    Refresh access token using refresh token
    
    Body: {
        "refresh_token": "string"
    }
    
    Returns: {
        "success": true,
        "access_token": "string",
        "expires_in": 1800
    }
    """
    _increment_telemetry('support_token_refresh_total')
    
    # Parse request
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    
    refresh_token = data.get('refresh_token', '').strip()
    
    if not refresh_token:
        return JsonResponse({
            'success': False,
            'error': 'Refresh token is required'
        }, status=400)
    
    # Refresh the token
    try:
        from core.services.support_auth_service import SupportAuthService
        
        auth_service = SupportAuthService()
        result = auth_service.refresh_access_token(refresh_token)
        
        if result['success']:
            logger.info("Access token refreshed successfully")
            _increment_telemetry('support_token_refresh_success')
            return JsonResponse({
                'success': True,
                'access_token': result['access_token'],
                'expires_in': result['expires_in']
            })
        else:
            logger.warning(f"Token refresh failed: {result.get('error')}")
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Token refresh failed')
            }, status=401)
    
    except Exception as e:
        logger.error(f"Error in token refresh: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Token refresh failed'
        }, status=500)
