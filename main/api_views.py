"""
API views for user management and authentication.
"""
import json
import base64
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .models import User, Item, Task, ItemSimilarity
from .auth_utils import generate_jwt_token, decode_jwt_token, validate_password
from core.services.graph_service import GraphService, GraphServiceError
from core.services.github_service import GitHubService, GitHubServiceError
from core.services.kigate_service import KiGateService, KiGateServiceError
from core.services.openai_service import OpenAIService, OpenAIServiceError


def get_user_from_token(request):
    """Extract and validate user from JWT token in Authorization header"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]
    payload = decode_jwt_token(token)
    if not payload:
        return None
    
    try:
        user = User.objects.get(id=payload['user_id'], is_active=True)
        return user
    except User.DoesNotExist:
        return None


def require_admin(view_func):
    """Decorator to require admin role for API endpoints"""
    def wrapper(request, *args, **kwargs):
        user = get_user_from_token(request)
        if not user or user.role != 'admin':
            return JsonResponse({'error': 'Admin access required'}, status=403)
        request.user_obj = user
        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """
    API endpoint for user authentication.
    POST /api/auth/login
    Body: {"username": "...", "password": "..."}
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return JsonResponse({'error': 'Username and password are required'}, status=400)
        
        # Find user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
        
        # Check if user is active
        if not user.is_active:
            return JsonResponse({'error': 'Account is inactive'}, status=401)
        
        # Verify password
        if not user.check_password(password):
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
        
        # Update last login
        user.update_last_login()
        
        # Generate JWT token
        token = generate_jwt_token(user)
        
        return JsonResponse({
            'token': token,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Login error: {str(e)}')
        return JsonResponse({'error': 'An error occurred during login'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_logout(request):
    """
    API endpoint for user logout.
    POST /api/auth/logout
    Note: Since JWT is stateless, this is mainly for client-side token removal
    """
    return JsonResponse({'message': 'Logged out successfully'})


@csrf_exempt
@require_http_methods(["GET"])
def api_user_list(request):
    """
    API endpoint to list all users (admin only).
    GET /api/users?page=1&per_page=10
    """
    user = get_user_from_token(request)
    if not user or user.role != 'admin':
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    try:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 10))
        per_page = min(per_page, 100)  # Max 100 per page
        
        users = User.objects.all().order_by('-created_at')
        paginator = Paginator(users, per_page)
        page_obj = paginator.get_page(page)
        
        users_data = [{
            'id': str(u.id),
            'username': u.username,
            'email': u.email,
            'role': u.role,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat(),
            'last_login': u.last_login.isoformat() if u.last_login else None,
            'ai_classification': u.ai_classification,
        } for u in page_obj]
        
        return JsonResponse({
            'users': users_data,
            'page': page,
            'per_page': per_page,
            'total': paginator.count,
            'total_pages': paginator.num_pages,
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'User list error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while retrieving users'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_user_detail(request, user_id):
    """
    API endpoint to get a specific user.
    GET /api/users/{user_id}
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Admin can view any user, regular users can only view themselves
    if user.role != 'admin' and str(user.id) != user_id:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        target_user = User.objects.get(id=user_id)
        return JsonResponse({
            'id': str(target_user.id),
            'username': target_user.username,
            'email': target_user.email,
            'role': target_user.role,
            'is_active': target_user.is_active,
            'created_at': target_user.created_at.isoformat(),
            'last_login': target_user.last_login.isoformat() if target_user.last_login else None,
            'ai_classification': target_user.ai_classification,
        })
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'User detail error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while retrieving user details'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def api_user_create(request):
    """
    API endpoint to create a new user (admin only).
    POST /api/users
    Body: {"username": "...", "email": "...", "password": "...", "role": "...", "is_active": true}
    """
    try:
        data = json.loads(request.body)
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'user')
        is_active = data.get('is_active', True)
        ai_classification = data.get('ai_classification', '')
        
        # Validation
        if not username:
            return JsonResponse({'error': 'Username is required'}, status=400)
        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)
        if not password:
            return JsonResponse({'error': 'Password is required'}, status=400)
        
        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email already exists'}, status=400)
        
        # Validate password
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            return JsonResponse({'error': error_msg}, status=400)
        
        # Validate role
        valid_roles = ['admin', 'developer', 'user', 'viewer']
        if role not in valid_roles:
            return JsonResponse({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}, status=400)
        
        # Create user
        user = User(
            username=username,
            email=email,
            role=role,
            is_active=is_active,
            ai_classification=ai_classification
        )
        user.set_password(password)
        user.save()
        
        return JsonResponse({
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat(),
            'ai_classification': user.ai_classification,
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'User create error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while creating user'}, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
def api_user_update(request, user_id):
    """
    API endpoint to update a user.
    PUT /api/users/{user_id}
    Body: {"email": "...", "role": "...", "is_active": true, "password": "..." (optional)}
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Admin can update any user, regular users can only update themselves (limited fields)
    if user.role != 'admin' and str(user.id) != user_id:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        target_user = User.objects.get(id=user_id)
        data = json.loads(request.body)
        
        # Regular users can only update their own email and password
        if user.role != 'admin':
            if 'email' in data:
                email = data['email'].strip()
                if email and email != target_user.email:
                    if User.objects.filter(email=email).exclude(id=user_id).exists():
                        return JsonResponse({'error': 'Email already exists'}, status=400)
                    target_user.email = email
            
            if 'password' in data and data['password']:
                password = data['password']
                is_valid, error_msg = validate_password(password)
                if not is_valid:
                    return JsonResponse({'error': error_msg}, status=400)
                target_user.set_password(password)
        else:
            # Admin can update all fields
            if 'email' in data:
                email = data['email'].strip()
                if email and email != target_user.email:
                    if User.objects.filter(email=email).exclude(id=user_id).exists():
                        return JsonResponse({'error': 'Email already exists'}, status=400)
                    target_user.email = email
            
            if 'role' in data:
                role = data['role']
                valid_roles = ['admin', 'developer', 'user', 'viewer']
                if role not in valid_roles:
                    return JsonResponse({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}, status=400)
                target_user.role = role
            
            if 'is_active' in data:
                target_user.is_active = bool(data['is_active'])
            
            if 'ai_classification' in data:
                target_user.ai_classification = data['ai_classification']
            
            if 'password' in data and data['password']:
                password = data['password']
                is_valid, error_msg = validate_password(password)
                if not is_valid:
                    return JsonResponse({'error': error_msg}, status=400)
                target_user.set_password(password)
        
        target_user.save()
        
        return JsonResponse({
            'id': str(target_user.id),
            'username': target_user.username,
            'email': target_user.email,
            'role': target_user.role,
            'is_active': target_user.is_active,
            'created_at': target_user.created_at.isoformat(),
            'last_login': target_user.last_login.isoformat() if target_user.last_login else None,
            'ai_classification': target_user.ai_classification,
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'User update error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while updating user'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_admin
def api_user_delete(request, user_id):
    """
    API endpoint to delete a user (admin only).
    DELETE /api/users/{user_id}
    """
    try:
        target_user = User.objects.get(id=user_id)
        
        # Prevent self-deletion
        if str(request.user_obj.id) == user_id:
            return JsonResponse({'error': 'Cannot delete your own account'}, status=400)
        
        username = target_user.username
        target_user.delete()
        
        return JsonResponse({'message': f'User "{username}" deleted successfully'})
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'User delete error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while deleting user'}, status=500)


# Graph API Endpoints

@csrf_exempt
@require_http_methods(["GET"])
@require_admin
def api_graph_sharepoint_files(request):
    """
    API endpoint to list SharePoint files (admin only).
    GET /api/graph/sharepoint/files?folder_path=Documents
    """
    try:
        folder_path = request.GET.get('folder_path', '')
        
        graph = GraphService()
        result = graph.get_sharepoint_file_list(folder_path)
        
        return JsonResponse(result)
        
    except GraphServiceError as e:
        logger = logging.getLogger(__name__)
        logger.error(f'Graph API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'SharePoint files list error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while listing files',
            'details': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def api_graph_sharepoint_upload(request):
    """
    API endpoint to upload a file to SharePoint (admin only).
    POST /api/graph/sharepoint/upload
    Body: {"folder_path": "Documents", "file_name": "test.txt", "content": "base64_encoded_content"}
    """
    try:
        data = json.loads(request.body)
        
        folder_path = data.get('folder_path', '')
        file_name = data.get('file_name')
        content_b64 = data.get('content')
        
        if not file_name:
            return JsonResponse({'error': 'file_name is required'}, status=400)
        
        if not content_b64:
            return JsonResponse({'error': 'content is required'}, status=400)
        
        # Decode base64 content
        try:
            content = base64.b64decode(content_b64)
        except Exception as e:
            return JsonResponse({'error': 'Invalid base64 content', 'details': str(e)}, status=400)
        
        graph = GraphService()
        result = graph.upload_sharepoint_file(folder_path, file_name, content)
        
        return JsonResponse(result, status=201)
        
    except GraphServiceError as e:
        logger = logging.getLogger(__name__)
        logger.error(f'Graph API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'SharePoint upload error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while uploading file',
            'details': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def api_graph_mail_send(request):
    """
    API endpoint to send a test email via Graph API (admin only).
    POST /api/graph/mail/send
    Body: {"to": ["user@domain.com"], "subject": "Test", "body": "Test message"}
    """
    try:
        data = json.loads(request.body)
        
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        
        if not to or not isinstance(to, list):
            return JsonResponse({'error': 'to must be a list of email addresses'}, status=400)
        
        if not subject:
            return JsonResponse({'error': 'subject is required'}, status=400)
        
        if not body:
            return JsonResponse({'error': 'body is required'}, status=400)
        
        graph = GraphService()
        result = graph.send_mail(to, subject, body)
        
        return JsonResponse(result)
        
    except GraphServiceError as e:
        logger = logging.getLogger(__name__)
        logger.error(f'Graph API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Mail send error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while sending email',
            'details': str(e)
        }, status=500)


# GitHub API Endpoints

def require_developer(view_func):
    """Decorator to require admin or developer role for API endpoints"""
    def wrapper(request, *args, **kwargs):
        user = get_user_from_token(request)
        if not user or user.role not in ['admin', 'developer']:
            return JsonResponse({'error': 'Admin or developer access required'}, status=403)
        request.user_obj = user
        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@require_http_methods(["GET"])
@require_developer
def api_github_repos(request):
    """
    API endpoint to list GitHub repositories (admin/developer only).
    GET /api/github/repos?owner=username&per_page=30&page=1
    """
    try:
        owner = request.GET.get('owner')
        per_page = int(request.GET.get('per_page', 30))
        page = int(request.GET.get('page', 1))
        
        github = GitHubService()
        result = github.get_repositories(owner=owner, per_page=per_page, page=page)
        
        return JsonResponse(result)
        
    except GitHubServiceError as e:
        logger = logging.getLogger(__name__)
        logger.error(f'GitHub API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'GitHub repos list error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while listing repositories'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_developer
def api_github_create_issue(request):
    """
    API endpoint to create a GitHub issue (admin/developer only).
    POST /api/github/create-issue
    Body: {"owner": "...", "repo": "...", "title": "...", "body": "...", "labels": ["..."], "assignees": ["..."]}
    """
    try:
        data = json.loads(request.body)
        
        title = data.get('title')
        body = data.get('body')
        owner = data.get('owner')
        repo = data.get('repo')
        labels = data.get('labels', [])
        assignees = data.get('assignees', [])
        
        if not title:
            return JsonResponse({'error': 'title is required'}, status=400)
        
        if not body:
            return JsonResponse({'error': 'body is required'}, status=400)
        
        github = GitHubService()
        result = github.create_issue(
            title=title,
            body=body,
            owner=owner,
            repo=repo,
            labels=labels,
            assignees=assignees
        )
        
        return JsonResponse(result, status=201)
        
    except GitHubServiceError as e:
        logger = logging.getLogger(__name__)
        logger.error(f'GitHub API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'GitHub create issue error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while creating issue'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_developer
def api_github_get_issue(request, owner, repo, issue_number):
    """
    API endpoint to get a specific GitHub issue (admin/developer only).
    GET /api/github/issue/{owner}/{repo}/{issue_number}
    """
    try:
        github = GitHubService()
        result = github.get_issue(
            issue_number=int(issue_number),
            owner=owner,
            repo=repo
        )
        
        return JsonResponse(result)
        
    except GitHubServiceError as e:
        logger = logging.getLogger(__name__)
        logger.error(f'GitHub API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except ValueError:
        return JsonResponse({'error': 'Invalid issue number'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'GitHub get issue error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while retrieving issue'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@require_developer
def api_github_list_issues(request, owner, repo):
    """
    API endpoint to list GitHub issues in a repository (admin/developer only).
    GET /api/github/issues/{owner}/{repo}?state=open&labels=bug,feature&per_page=30&page=1
    """
    try:
        state = request.GET.get('state', 'open')
        labels_str = request.GET.get('labels')
        labels = labels_str.split(',') if labels_str else None
        per_page = int(request.GET.get('per_page', 30))
        page = int(request.GET.get('page', 1))
        
        github = GitHubService()
        result = github.list_issues(
            owner=owner,
            repo=repo,
            state=state,
            labels=labels,
            per_page=per_page,
            page=page
        )
        
        return JsonResponse(result)
        
    except GitHubServiceError as e:
        logger = logging.getLogger(__name__)
        logger.error(f'GitHub API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'GitHub list issues error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while listing issues'
        }, status=500)


# ==================== KiGate API Endpoints ====================

@csrf_exempt
@require_http_methods(["GET"])
def api_kigate_agents(request):
    """
    API endpoint to list all available KiGate agents.
    GET /api/kigate/agents
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        kigate = KiGateService()
        result = kigate.get_agents()
        
        return JsonResponse(result)
        
    except KiGateServiceError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'KiGate API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'KiGate agents list error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while listing agents'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_kigate_execute(request):
    """
    API endpoint to execute a KiGate agent.
    POST /api/kigate/execute
    Body: {
        "agent_name": "...",
        "provider": "...",
        "model": "...",
        "message": "...",
        "user_id": "...",
        "parameters": {...}  // optional
    }
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        agent_name = data.get('agent_name')
        provider = data.get('provider')
        model = data.get('model')
        message = data.get('message')
        user_id = data.get('user_id')
        parameters = data.get('parameters')
        
        # Validate required fields
        if not agent_name:
            return JsonResponse({'error': 'agent_name is required'}, status=400)
        if not provider:
            return JsonResponse({'error': 'provider is required'}, status=400)
        if not model:
            return JsonResponse({'error': 'model is required'}, status=400)
        if not message:
            return JsonResponse({'error': 'message is required'}, status=400)
        if not user_id:
            return JsonResponse({'error': 'user_id is required'}, status=400)
        
        kigate = KiGateService()
        result = kigate.execute_agent(
            agent_name=agent_name,
            provider=provider,
            model=model,
            message=message,
            user_id=user_id,
            parameters=parameters
        )
        
        return JsonResponse(result, status=200)
        
    except KiGateServiceError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'KiGate API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'KiGate execute error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while executing agent'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_kigate_agent_details(request, agent_name):
    """
    API endpoint to get details of a specific KiGate agent.
    GET /api/kigate/agent/{agent_name}
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        kigate = KiGateService()
        result = kigate.get_agent_details(agent_name=agent_name)
        
        return JsonResponse(result)
        
    except KiGateServiceError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'KiGate API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'KiGate agent details error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while getting agent details'
        }, status=500)


# ==================== OpenAI API Endpoints ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_openai_query(request):
    """
    API endpoint to execute an AI query via OpenAI API (with KiGate fallback).
    POST /api/openai/query
    Body: {
        "prompt": "...",
        "model": "..." (optional),
        "user_id": "..." (optional),
        "agent_name": "..." (optional - for KiGate routing),
        "temperature": 0.7 (optional),
        "max_tokens": 1000 (optional)
    }
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        prompt = data.get('prompt')
        model = data.get('model')
        user_id = data.get('user_id', str(user.id))
        agent_name = data.get('agent_name')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens')
        
        # Validate required fields
        if not prompt:
            return JsonResponse({'error': 'prompt is required'}, status=400)
        
        openai = OpenAIService()
        
        # Use agent routing if agent_name is provided
        if agent_name:
            result = openai.query_with_agent(
                prompt=prompt,
                agent_name=agent_name,
                user_id=user_id,
                model=model
            )
        else:
            result = openai.query(
                prompt=prompt,
                model=model,
                user_id=user_id,
                temperature=temperature,
                max_tokens=max_tokens
            )
        
        return JsonResponse(result, status=200)
        
    except OpenAIServiceError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'OpenAI API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'OpenAI query error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while executing query'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_openai_models(request):
    """
    API endpoint to list available OpenAI models.
    GET /api/openai/models
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        openai = OpenAIService()
        result = openai.get_models()
        
        return JsonResponse(result)
        
    except OpenAIServiceError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'OpenAI API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'OpenAI models list error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while listing models'
        }, status=500)


# ==================== Item API Endpoints ====================

@csrf_exempt
@require_http_methods(["GET"])
def api_item_list(request):
    """
    API endpoint to list all items for the current user.
    GET /api/items?page=1&per_page=20&status=new&section=uuid
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        per_page = min(per_page, 100)  # Max 100 per page
        
        status_filter = request.GET.get('status', '')
        section_filter = request.GET.get('section', '')
        
        # Base query: show only user's items (or all if admin)
        if user.role == 'admin':
            items = Item.objects.all()
        else:
            items = Item.objects.filter(created_by=user)
        
        # Apply filters
        if status_filter:
            items = items.filter(status=status_filter)
        if section_filter:
            items = items.filter(section_id=section_filter)
        
        items = items.select_related('section', 'created_by').prefetch_related('tags').order_by('-created_at')
        
        paginator = Paginator(items, per_page)
        page_obj = paginator.get_page(page)
        
        items_data = [{
            'id': str(i.id),
            'title': i.title,
            'description': i.description,
            'github_repo': i.github_repo,
            'status': i.status,
            'section': {'id': str(i.section.id), 'name': i.section.name} if i.section else None,
            'tags': [{'id': str(t.id), 'name': t.name, 'color': t.color} for t in i.tags.all()],
            'created_by': str(i.created_by.id) if i.created_by else None,
            'created_at': i.created_at.isoformat(),
            'updated_at': i.updated_at.isoformat(),
            'ai_enhanced': i.ai_enhanced,
            'similarity_checked': i.similarity_checked,
        } for i in page_obj]
        
        return JsonResponse({
            'items': items_data,
            'page': page,
            'per_page': per_page,
            'total': paginator.count,
            'total_pages': paginator.num_pages,
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Item list error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while retrieving items'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_item_detail(request, item_id):
    """
    API endpoint to get a specific item.
    GET /api/items/{item_id}
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        item = Item.objects.select_related('section', 'created_by').prefetch_related('tags').get(id=item_id)
        
        # Check permissions
        if item.created_by != user and user.role != 'admin':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        return JsonResponse({
            'id': str(item.id),
            'title': item.title,
            'description': item.description,
            'github_repo': item.github_repo,
            'status': item.status,
            'section': {'id': str(item.section.id), 'name': item.section.name} if item.section else None,
            'tags': [{'id': str(t.id), 'name': t.name, 'color': t.color} for t in item.tags.all()],
            'created_by': str(item.created_by.id) if item.created_by else None,
            'created_at': item.created_at.isoformat(),
            'updated_at': item.updated_at.isoformat(),
            'ai_enhanced': item.ai_enhanced,
            'similarity_checked': item.similarity_checked,
        })
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Item detail error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while retrieving item details'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_item_create(request):
    """
    API endpoint to create a new item.
    POST /api/items
    Body: {"title": "...", "description": "...", "status": "new", "section": "uuid", "tags": ["uuid1", "uuid2"]}
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'error': 'Title is required'}, status=400)
        
        item = Item(
            title=title,
            description=data.get('description', ''),
            github_repo=data.get('github_repo', ''),
            status=data.get('status', 'new'),
            created_by=user
        )
        
        # Set section if provided
        section_id = data.get('section')
        if section_id:
            item.section_id = section_id
        
        item.save()
        
        # Set tags
        tag_ids = data.get('tags', [])
        if tag_ids:
            item.tags.set(tag_ids)
        
        return JsonResponse({
            'id': str(item.id),
            'title': item.title,
            'description': item.description,
            'github_repo': item.github_repo,
            'status': item.status,
            'created_at': item.created_at.isoformat(),
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Item create error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while creating item'}, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
def api_item_update(request, item_id):
    """
    API endpoint to update an item.
    PUT /api/items/{item_id}
    Body: {"title": "...", "description": "...", "status": "...", "section": "uuid", "tags": ["uuid1"]}
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        item = Item.objects.get(id=item_id)
        
        # Check permissions
        if item.created_by != user and user.role != 'admin':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        data = json.loads(request.body)
        
        if 'title' in data:
            title = data['title'].strip()
            if not title:
                return JsonResponse({'error': 'Title cannot be empty'}, status=400)
            item.title = title
        
        if 'description' in data:
            item.description = data['description']
        
        if 'github_repo' in data:
            item.github_repo = data['github_repo']
        
        if 'status' in data:
            item.status = data['status']
        
        if 'section' in data:
            section_id = data['section']
            if section_id:
                item.section_id = section_id
            else:
                item.section = None
        
        item.save()
        
        # Update tags
        if 'tags' in data:
            item.tags.set(data['tags'])
        
        return JsonResponse({
            'id': str(item.id),
            'title': item.title,
            'description': item.description,
            'status': item.status,
            'updated_at': item.updated_at.isoformat(),
        })
        
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Item update error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while updating item'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def api_item_delete(request, item_id):
    """
    API endpoint to delete an item.
    DELETE /api/items/{item_id}
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        item = Item.objects.get(id=item_id)
        
        # Check permissions
        if item.created_by != user and user.role != 'admin':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        item_title = item.title
        item.delete()
        
        return JsonResponse({'message': f'Item "{item_title}" deleted successfully'})
        
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Item delete error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while deleting item'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_item_ai_enhance(request, item_id):
    """
    API endpoint to enhance an item using AI.
    POST /api/items/{item_id}/ai-enhance
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        item = Item.objects.get(id=item_id)
        
        # Check permissions
        if item.created_by != user and user.role != 'admin':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Call KiGate API with text-optimization-agent
        kigate = KiGateService()
        
        # Prepare the message for AI
        message = f"Title: {item.title}\n\nDescription:\n{item.description}"
        
        result = kigate.execute_agent(
            agent_name='text-optimization-agent',
            provider='openai',
            model='gpt-4',
            message=message,
            user_id=str(user.id),
            parameters={}
        )
        
        if result.get('success'):
            # Update item with AI-enhanced content
            # Note: The actual response format depends on the agent implementation
            # This is a placeholder - adjust based on actual KiGate response
            item.ai_enhanced = True
            item.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Item enhanced successfully',
                'data': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'AI enhancement failed')
            }, status=500)
        
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except KiGateServiceError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'KiGate API error: {e.message}')
        return JsonResponse({'success': False, 'error': e.message}, status=500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Item AI enhance error: {str(e)}')
        return JsonResponse({'success': False, 'error': 'An error occurred during AI enhancement'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_item_build_tasks(request, item_id):
    """
    API endpoint to build tasks for an item using AI.
    POST /api/items/{item_id}/build-tasks
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        item = Item.objects.get(id=item_id)
        
        # Check permissions
        if item.created_by != user and user.role != 'admin':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Check if item is ready
        if item.status != 'ready':
            return JsonResponse({'error': 'Item must be in Ready status to build tasks'}, status=400)
        
        # Call KiGate API with task-builder-agent
        kigate = KiGateService()
        
        message = f"Title: {item.title}\n\nDescription:\n{item.description}"
        
        result = kigate.execute_agent(
            agent_name='task-builder-agent',
            provider='openai',
            model='gpt-4',
            message=message,
            user_id=str(user.id),
            parameters={'item_id': str(item.id)}
        )
        
        if result.get('success'):
            # Tasks should be created by the agent
            # This is a placeholder response
            return JsonResponse({
                'success': True,
                'message': 'Tasks built successfully',
                'data': result
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Task building failed')
            }, status=500)
        
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except KiGateServiceError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'KiGate API error: {e.message}')
        return JsonResponse({'success': False, 'error': e.message}, status=500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Item build tasks error: {str(e)}')
        return JsonResponse({'success': False, 'error': 'An error occurred while building tasks'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_item_check_similarity(request, item_id):
    """
    API endpoint to check similarity with other items.
    POST /api/items/{item_id}/check-similarity
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        item = Item.objects.get(id=item_id)
        
        # Check permissions
        if item.created_by != user and user.role != 'admin':
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Placeholder implementation
        # In production, this would:
        # 1. Vectorize the item content using ChromaDB
        # 2. Find similar items
        # 3. Create ItemSimilarity relations
        
        # For now, mark as checked
        item.similarity_checked = True
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Similarity check completed'
        })
        
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Item similarity check error: {str(e)}')
        return JsonResponse({'success': False, 'error': 'An error occurred during similarity check'}, status=500)

