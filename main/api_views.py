"""
API views for user management and authentication.
"""
import json
import base64
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from .models import User
from .auth_utils import generate_jwt_token, decode_jwt_token, validate_password
from core.services.graph_service import GraphService, GraphServiceError
from core.services.github_service import GitHubService, GitHubServiceError


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
