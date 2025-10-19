"""
API views for user management and authentication.
"""
import json
import base64
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from .models import User
from .auth_utils import generate_jwt_token, decode_jwt_token, validate_password
from core.services.graph_service import GraphService, GraphServiceError
from core.services.github_service import GitHubService, GitHubServiceError
from core.services.kigate_service import KiGateService, KiGateServiceError
from core.services.openai_service import OpenAIService, OpenAIServiceError
from core.services.chroma_task_sync_service import ChromaTaskSyncService, ChromaTaskSyncServiceError

logger = logging.getLogger(__name__)


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


def get_user_from_request(request):
    """
    Extract and validate user from either JWT token or session.
    This supports both API authentication (JWT) and web view authentication (session).
    """
    # First, try JWT authentication
    user = get_user_from_token(request)
    if user:
        return user
    
    # Fall back to session authentication
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    
    try:
        user = User.objects.get(id=user_id, is_active=True)
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


# ==================== Task API Endpoints ====================

@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_tasks(request, item_id=None):
    """
    API endpoint for task CRUD operations.
    GET /api/tasks/{item_id} - List tasks for an item
    POST /api/tasks/{item_id} - Create a new task
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    from .models import Item, Task, Tag
    
    if request.method == 'GET':
        # List tasks for an item
        if not item_id:
            return JsonResponse({'error': 'item_id is required'}, status=400)
        
        try:
            item = Item.objects.get(id=item_id)
            # Check ownership
            if user.role != 'admin' and item.created_by != user:
                return JsonResponse({'error': 'Access denied'}, status=403)
            
            # Get tasks for this item - only show owned tasks
            tasks = item.tasks.filter(created_by=user).select_related('assigned_to', 'created_by').prefetch_related('tags')
            
            # Sort tasks by status priority
            status_order = {'new': 1, 'working': 2, 'review': 3, 'ready': 4, 'done': 5}
            tasks = sorted(tasks, key=lambda t: status_order.get(t.status, 99))
            
            tasks_data = [{
                'id': str(task.id),
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'status_display': task.get_status_display(),
                'github_issue_id': task.github_issue_id,
                'github_issue_url': task.github_issue_url,
                'assigned_to': task.assigned_to.username if task.assigned_to else None,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'tags': [{'id': str(tag.id), 'name': tag.name, 'color': tag.color} for tag in task.tags.all()],
            } for task in tasks]
            
            return JsonResponse({
                'success': True,
                'tasks': tasks_data
            })
            
        except Item.DoesNotExist:
            return JsonResponse({'error': 'Item not found'}, status=404)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Task list error: {str(e)}')
            return JsonResponse({'error': 'An error occurred while listing tasks'}, status=500)
    
    elif request.method == 'POST':
        # Create a new task
        if not item_id:
            return JsonResponse({'error': 'item_id is required'}, status=400)
        
        try:
            data = json.loads(request.body)
            item = Item.objects.get(id=item_id)
            
            # Check ownership
            if user.role != 'admin' and item.created_by != user:
                return JsonResponse({'error': 'Access denied'}, status=403)
            
            title = data.get('title', '').strip()
            description = data.get('description', '').strip()
            status = data.get('status', 'new')
            tag_ids = data.get('tags', [])
            
            if not title:
                return JsonResponse({'error': 'Title is required'}, status=400)
            
            # Create task
            task = Task(
                title=title,
                description=description,
                status=status,
                item=item,
                created_by=user,
                assigned_to=user
            )
            task.save()
            
            # Add tags
            if tag_ids:
                task.tags.set(tag_ids)
            
            # Sync with ChromaDB
            try:
                from main.models import Settings
                settings = Settings.objects.first()
                if settings:
                    sync_service = ChromaTaskSyncService(settings)
                    sync_service.sync_create(task)
            except ChromaTaskSyncServiceError as e:
                import logging
                sync_logger = logging.getLogger(__name__)
                sync_logger.warning(f'ChromaDB sync failed for task {task.id}: {e.message}')
            except Exception as e:
                import logging
                sync_logger = logging.getLogger(__name__)
                sync_logger.warning(f'ChromaDB sync error for task {task.id}: {str(e)}')
            
            return JsonResponse({
                'success': True,
                'task': {
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'status_display': task.get_status_display(),
                }
            }, status=201)
            
        except Item.DoesNotExist:
            return JsonResponse({'error': 'Item not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Task create error: {str(e)}')
            return JsonResponse({'error': 'An error occurred while creating task'}, status=500)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def api_task_detail(request, task_id):
    """
    API endpoint for task detail operations.
    GET /api/tasks/{task_id} - Get task details
    PUT /api/tasks/{task_id} - Update a task
    DELETE /api/tasks/{task_id} - Delete a task
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    from .models import Task
    
    try:
        task = Task.objects.get(id=task_id)
        
        # Check ownership
        if task.created_by != user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        if request.method == 'GET':
            return JsonResponse({
                'success': True,
                'task': {
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'status_display': task.get_status_display(),
                    'github_issue_id': task.github_issue_id,
                    'github_issue_url': task.github_issue_url,
                    'assigned_to': task.assigned_to.username if task.assigned_to else None,
                    'created_at': task.created_at.isoformat(),
                    'updated_at': task.updated_at.isoformat(),
                    'tags': [{'id': str(tag.id), 'name': tag.name, 'color': tag.color} for tag in task.tags.all()],
                }
            })
        
        elif request.method == 'PUT':
            data = json.loads(request.body)
            
            title = data.get('title', '').strip()
            description = data.get('description', '').strip()
            status = data.get('status', task.status)
            tag_ids = data.get('tags', [])
            
            if not title:
                return JsonResponse({'error': 'Title is required'}, status=400)
            
            previous_status = task.status
            task.title = title
            task.description = description
            task.status = status

            # Mark as done if status changed to done
            if status == 'done' and previous_status != 'done':
                task.save()
                task.mark_as_done()
            else:
                task.save()
            
            # Update tags
            if tag_ids:
                task.tags.set(tag_ids)
            else:
                task.tags.clear()
            
            # Sync with ChromaDB
            try:
                from main.models import Settings
                settings = Settings.objects.first()
                if settings:
                    sync_service = ChromaTaskSyncService(settings)
                    sync_service.sync_update(task)
            except ChromaTaskSyncServiceError as e:
                import logging
                sync_logger = logging.getLogger(__name__)
                sync_logger.warning(f'ChromaDB sync failed for task {task.id}: {e.message}')
            except Exception as e:
                import logging
                sync_logger = logging.getLogger(__name__)
                sync_logger.warning(f'ChromaDB sync error for task {task.id}: {str(e)}')
            
            return JsonResponse({
                'success': True,
                'task': {
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'status_display': task.get_status_display(),
                }
            })
        
        elif request.method == 'DELETE':
            task_id = str(task.id)
            task.delete()
            
            # Sync with ChromaDB
            try:
                from main.models import Settings
                settings = Settings.objects.first()
                if settings:
                    sync_service = ChromaTaskSyncService(settings)
                    sync_service.sync_delete(task_id)
            except ChromaTaskSyncServiceError as e:
                import logging
                sync_logger = logging.getLogger(__name__)
                sync_logger.warning(f'ChromaDB sync failed for task {task_id}: {e.message}')
            except Exception as e:
                import logging
                sync_logger = logging.getLogger(__name__)
                sync_logger.warning(f'ChromaDB sync error for task {task_id}: {str(e)}')
            
            return JsonResponse({'success': True, 'message': 'Task deleted successfully'})
    
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Task operation error: {str(e)}')
        return JsonResponse({'error': 'An error occurred'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_task_ai_enhance(request, task_id):
    """
    API endpoint to enhance task with AI.
    POST /api/tasks/{task_id}/ai-enhance
    Body: {"title": "...", "description": "..."}
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    from .models import Task, Tag, Settings
    
    try:
        task = Task.objects.get(id=task_id)
        
        # Check ownership
        if task.created_by != user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        if not title or not description:
            return JsonResponse({'error': 'Title and description are required'}, status=400)
        
        # Get settings for max tags
        settings = Settings.objects.first()
        max_tags = settings.max_tags_per_idea if settings else 5
        
        # Use KiGate service to enhance content
        kigate = KiGateService()
        
        # First, optimize the text
        text_result = kigate.execute_agent(
            agent_name='text-optimization-agent',
            provider='openai',
            model='gpt-4',
            message=f"Title: {title}\n\nDescription:\n{description}",
            user_id=str(user.id),
            parameters={'language': 'de'}
        )
        
        if not text_result.get('success'):
            return JsonResponse({'error': text_result.get('error', 'Failed to enhance text')}, status=500)
        
        enhanced_text = text_result.get('response', description)
        
        # Extract keywords/tags
        keyword_result = kigate.execute_agent(
            agent_name='text-keyword-extractor-de',
            provider='openai',
            model='gpt-4',
            message=enhanced_text,
            user_id=str(user.id),
            parameters={'max_keywords': max_tags}
        )
        
        # Parse keywords
        tags_list = []
        if keyword_result.get('success'):
            keywords_text = keyword_result.get('response', '')
            # Extract keywords from response
            keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
            
            # Get or create tags
            for keyword in keywords[:max_tags]:
                tag, _ = Tag.objects.get_or_create(name=keyword)
                tags_list.append(tag.name)
        
        # Generate improved title if possible
        title_lines = enhanced_text.split('\n')
        enhanced_title = title_lines[0].replace('Title:', '').strip() if title_lines else title
        
        return JsonResponse({
            'success': True,
            'title': enhanced_title[:255],  # Limit to field max length
            'description': enhanced_text,
            'tags': tags_list
        })
        
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
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
        logger.error(f'Task AI enhance error: {str(e)}')
        return JsonResponse({'error': 'An error occurred during AI enhancement'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_item_ai_enhance(request, item_id):
    """
    API endpoint to enhance item with AI.
    POST /api/items/{item_id}/ai-enhance
    Body: {"title": "...", "description": "..."}
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    from .models import Item, Tag, Settings
    
    try:
        item = Item.objects.get(id=item_id)
        
        # Check ownership
        if item.created_by != user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        
        if not title or not description:
            return JsonResponse({'error': 'Title and description are required'}, status=400)
        
        # Get settings for max tags
        settings = Settings.objects.first()
        max_tags = settings.max_tags_per_idea if settings else 5
        
        # Use KiGate service to enhance content
        kigate = KiGateService()
        
        # First, optimize the text
        text_result = kigate.execute_agent(
            agent_name='text-optimization-agent',
            provider='openai',
            model='gpt-4',
            message=f"Title: {title}\n\nDescription:\n{description}",
            user_id=str(user.id),
            parameters={'language': 'de'}
        )
        
        if not text_result.get('success'):
            return JsonResponse({'error': text_result.get('error', 'Failed to enhance text')}, status=500)
        
        enhanced_text = text_result.get('response', description)
        
        # Extract keywords/tags
        keyword_result = kigate.execute_agent(
            agent_name='text-keyword-extractor-de',
            provider='openai',
            model='gpt-4',
            message=enhanced_text,
            user_id=str(user.id),
            parameters={'max_keywords': max_tags}
        )
        
        # Parse keywords
        tags_list = []
        if keyword_result.get('success'):
            keywords_text = keyword_result.get('response', '')
            # Extract keywords from response
            keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
            
            # Get or create tags
            for keyword in keywords[:max_tags]:
                tag, _ = Tag.objects.get_or_create(name=keyword)
                tags_list.append(tag.name)
        
        # Generate improved title if possible
        title_lines = enhanced_text.split('\n')
        enhanced_title = title_lines[0].replace('Title:', '').strip() if title_lines else title
        
        return JsonResponse({
            'success': True,
            'title': enhanced_title[:255],  # Limit to field max length
            'description': enhanced_text,
            'tags': tags_list
        })
        
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
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
        logger.error(f'Item AI enhance error: {str(e)}')
        return JsonResponse({'error': 'An error occurred during AI enhancement'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_item_build_tasks(request, item_id):
    """
    API endpoint to build/decompose tasks from an item using AI.
    POST /api/items/{item_id}/build-tasks
    Body: {"title": "...", "description": "..."}
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    from .models import Item, Task, Tag, Settings
    
    try:
        item = Item.objects.get(id=item_id)
        
        # Check ownership
        if item.created_by != user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        data = json.loads(request.body)
        title = data.get('title', item.title).strip()
        description = data.get('description', item.description).strip()
        
        if not title or not description:
            return JsonResponse({'error': 'Title and description are required'}, status=400)
        
        # Use KiGate service to decompose item into tasks
        kigate = KiGateService()
        
        # Use task decomposition agent to generate tasks
        decompose_result = kigate.execute_agent(
            agent_name='task-decomposition-agent',
            provider='openai',
            model='gpt-4',
            message=f"Title: {title}\n\nDescription:\n{description}\n\nPlease decompose this into actionable tasks.",
            user_id=str(user.id),
            parameters={'max_tasks': 10}
        )
        
        if not decompose_result.get('success'):
            return JsonResponse({'error': decompose_result.get('error', 'Failed to decompose tasks')}, status=500)
        
        # Parse the response to extract tasks
        # Expected format: The agent should return tasks in a structured format
        response_text = decompose_result.get('response', '')
        
        # Parse tasks from response (assuming line-by-line format or JSON)
        tasks_created = []
        try:
            # Try to parse as JSON first
            import json as json_lib
            tasks_data = json_lib.loads(response_text)
            if isinstance(tasks_data, list):
                for task_data in tasks_data[:10]:  # Limit to 10 tasks
                    if isinstance(task_data, dict):
                        task_title = task_data.get('title', '')
                        task_desc = task_data.get('description', '')
                    else:
                        task_title = str(task_data)
                        task_desc = ''
                    
                    if task_title:
                        task = Task.objects.create(
                            title=task_title[:255],
                            description=task_desc,
                            status='new',
                            item=item,
                            created_by=user,
                            assigned_to=user,
                            ai_generated=True
                        )
                        tasks_created.append({
                            'id': str(task.id),
                            'title': task.title,
                            'description': task.description
                        })
        except (json_lib.JSONDecodeError, ValueError):
            # Fallback: Parse as line-separated tasks
            lines = response_text.split('\n')
            for line in lines[:10]:  # Limit to 10 tasks
                line = line.strip()
                # Remove common prefixes like "1.", "-", "*", etc.
                line = line.lstrip('0123456789.-* ')
                if line and len(line) > 3:
                    task = Task.objects.create(
                        title=line[:255],
                        description='',
                        status='new',
                        item=item,
                        created_by=user,
                        assigned_to=user,
                        ai_generated=True
                    )
                    tasks_created.append({
                        'id': str(task.id),
                        'title': task.title,
                        'description': task.description
                    })
        
        return JsonResponse({
            'success': True,
            'tasks': tasks_created,
            'count': len(tasks_created)
        })
        
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
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
        logger.error(f'Build tasks error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while building tasks'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_item_check_similarity(request, item_id):
    """
    API endpoint to check similarity for an item using ChromaDB.
    POST /api/items/{item_id}/check-similarity
    Body: {"title": "...", "description": "..."}
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    from .models import Item, Settings
    from core.services.chroma_sync_service import ChromaItemSyncService, ChromaItemSyncServiceError
    
    try:
        item = Item.objects.get(id=item_id)
        
        # Check ownership
        if item.created_by != user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        data = json.loads(request.body)
        title = data.get('title', item.title).strip()
        description = data.get('description', item.description).strip()
        
        if not description:
            return JsonResponse({'error': 'Description is required'}, status=400)
        
        # Use ChromaDB to find similar items
        settings = Settings.objects.first()
        if not settings:
            return JsonResponse({'error': 'Settings not configured'}, status=500)
        
        chroma_service = ChromaItemSyncService(settings)
        
        # Search for similar items
        search_text = f"{title}\n\n{description}"
        result = chroma_service.search_similar(search_text, n_results=5)
        
        if not result.get('success'):
            return JsonResponse({'error': 'Failed to search for similar items'}, status=500)
        
        # Filter out the current item from results
        similar_items = []
        for similar_item in result.get('results', []):
            if similar_item.get('id') != str(item_id):
                similar_items.append(similar_item)
        
        return JsonResponse({
            'success': True,
            'similar_items': similar_items[:5]  # Limit to 5 results
        })
        
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except ChromaItemSyncServiceError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'ChromaDB error: {e.message}')
        return JsonResponse(e.to_dict(), status=500)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Check similarity error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while checking similarity'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_task_create_github_issue(request, task_id):
    """
    API endpoint to create GitHub issue from task.
    POST /api/tasks/{task_id}/create-github-issue
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    from .models import Task
    
    try:
        task = Task.objects.get(id=task_id)
        
        # Check ownership
        if task.created_by != user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Check status
        if task.status != 'ready':
            return JsonResponse({'error': 'Task must be in Ready status to create GitHub issue'}, status=400)
        
        # Check if issue already exists
        if task.github_issue_id:
            return JsonResponse({'error': 'GitHub issue already exists for this task'}, status=400)
        
        # Get GitHub repository from item
        if not task.item or not task.item.github_repo:
            return JsonResponse({'error': 'No GitHub repository configured for this item'}, status=400)
        
        # Parse owner/repo from github_repo field
        repo_parts = task.item.github_repo.split('/')
        if len(repo_parts) != 2:
            return JsonResponse({'error': 'Invalid GitHub repository format. Expected: owner/repo'}, status=400)
        
        owner, repo = repo_parts
        
        # Prepare labels from tags
        labels = [tag.name for tag in task.tags.all()]
        
        # Create GitHub issue
        github = GitHubService()
        result = github.create_issue(
            title=task.title,
            body=task.description,
            owner=owner,
            repo=repo,
            labels=labels,
            assignees=[]
        )
        
        if result.get('success'):
            # Update task with GitHub issue info
            task.github_issue_id = result.get('issue_number')
            task.github_issue_url = result.get('url')
            task.github_synced_at = timezone.now()
            task.save()
            
            return JsonResponse({
                'success': True,
                'issue_number': task.github_issue_id,
                'issue_url': task.github_issue_url,
                'message': 'GitHub issue created successfully'
            })
        else:
            return JsonResponse({'error': result.get('error', 'Failed to create GitHub issue')}, status=500)
        
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
    except GitHubServiceError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'GitHub API error: {e.message}')
        return JsonResponse(e.to_dict(), status=e.status_code or 500)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Create GitHub issue error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while creating GitHub issue'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_task_similar(request, task_id):
    """
    API endpoint to get similar tasks.
    GET /api/tasks/{task_id}/similar
    """
    user = get_user_from_request(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    from .models import Task
    
    try:
        task = Task.objects.get(id=task_id)
        
        # Check ownership
        if task.created_by != user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # TODO: Implement ChromaDB similarity search
        # For now, return empty list
        # In future, use ChromaDB to find similar tasks based on description
        
        return JsonResponse({
            'success': True,
            'similar_tasks': []
        })
        
    except Task.DoesNotExist:
        return JsonResponse({'error': 'Task not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Task similarity error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while finding similar tasks'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_task_overview(request):
    """
    API endpoint for global task overview with filtering and pagination.
    GET /api/tasks/overview?status=new&item=uuid&has_github=true&query=search&page=1&limit=20
    """
    user = get_user_from_token(request)
    if not user:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    from .models import Task, Item
    from django.db.models import Q, Count
    
    try:
        # Base query - show only user's tasks unless admin
        if user.role == 'admin':
            tasks = Task.objects.all()
        else:
            tasks = tasks = Task.objects.filter(created_by=user)
        
        # Apply filters
        status_filter = request.GET.get('status', '').strip()
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        
        item_filter = request.GET.get('item', '').strip()
        if item_filter:
            tasks = tasks.filter(item_id=item_filter)
        
        has_github = request.GET.get('has_github', '').strip().lower()
        if has_github == 'true':
            tasks = tasks.filter(github_issue_id__isnull=False)
        elif has_github == 'false':
            tasks = tasks.filter(github_issue_id__isnull=True)
        
        query = request.GET.get('query', '').strip()
        if query:
            tasks = tasks.filter(
                Q(title__icontains=query) | 
                Q(description__icontains=query)
            )
        
        # Get status counts for badges (before pagination)
        status_counts = {}
        for status_key, status_label in Task.STATUS_CHOICES:
            if user.role == 'admin':
                count = Task.objects.filter(status=status_key).count()
            else:
                count = Task.objects.filter(status=status_key, created_by=user).count()
            status_counts[status_key] = {
                'label': status_label,
                'count': count
            }
        
        # Pagination
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 20)), 100)  # Max 100 per page
        
        total_count = tasks.count()
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        
        start_index = (page - 1) * limit
        end_index = start_index + limit
        
        # Get tasks with related data
        tasks = tasks.select_related('item', 'assigned_to', 'created_by').prefetch_related('tags')
        tasks = tasks.order_by('-updated_at')[start_index:end_index]
        
        # Prepare response data
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                'id': str(task.id),
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'status_display': task.get_status_display(),
                'item': {
                    'id': str(task.item.id),
                    'title': task.item.title
                } if task.item else None,
                'github_issue_id': task.github_issue_id,
                'github_issue_url': task.github_issue_url,
                'github_synced_at': task.github_synced_at.isoformat() if task.github_synced_at else None,
                'assigned_to': {
                    'id': str(task.assigned_to.id),
                    'username': task.assigned_to.username
                } if task.assigned_to else None,
                'created_by': {
                    'id': str(task.created_by.id),
                    'username': task.created_by.username
                } if task.created_by else None,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'tags': [{'id': str(tag.id), 'name': tag.name, 'color': tag.color} for tag in task.tags.all()],
                'ai_enhanced': task.ai_enhanced,
                'ai_generated': task.ai_generated,
            })
        
        return JsonResponse({
            'success': True,
            'tasks': tasks_data,
            'status_counts': status_counts,
            'pagination': {
                'page': page,
                'limit': limit,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Task overview error: {str(e)}')
        return JsonResponse({'error': 'An error occurred while fetching task overview'}, status=500)

