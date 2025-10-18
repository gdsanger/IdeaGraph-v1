"""
Authentication middleware for IdeaGraph.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class AuthenticationMiddleware:
    """Middleware to handle session-based authentication"""
    
    # URLs that don't require authentication
    PUBLIC_URLS = [
        '/login/',
        '/logout/',
        '/register/',
        '/forgot-password/',
        '/reset-password/',
        '/api/',  # API uses JWT auth
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get the path
        path = request.path
        
        # Check if URL is public
        is_public = any(path.startswith(url) for url in self.PUBLIC_URLS)
        
        # Check if user is logged in
        user_id = request.session.get('user_id')
        
        # If not public and not logged in, redirect to login
        if not is_public and not user_id:
            messages.warning(request, 'Please log in to access this page.')
            return redirect(f"{reverse('main:login')}?next={path}")
        
        response = self.get_response(request)
        return response


class AdminRequiredMiddleware:
    """Middleware to restrict admin URLs to admin users only"""
    
    ADMIN_URLS = [
        '/admin/users/',
        '/admin/settings/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get the path
        path = request.path
        
        # Check if URL is admin-only
        is_admin_url = any(path.startswith(url) for url in self.ADMIN_URLS)
        
        # If admin URL, check user role
        if is_admin_url:
            user_role = request.session.get('user_role')
            if user_role != 'admin':
                messages.error(request, 'Access denied. Admin privileges required.')
                return redirect('main:home')
        
        response = self.get_response(request)
        return response
