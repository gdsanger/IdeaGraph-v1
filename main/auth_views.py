"""
Authentication views for login, logout, registration, and password reset.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from .models import User, PasswordResetToken
from .auth_utils import validate_password
from core.services.graph_service import GraphService, GraphServiceError


logger = logging.getLogger('auth_service')


def login_view(request):
    """Login page view"""
    # Redirect if already logged in
    if request.session.get('user_id'):
        return redirect('main:home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return render(request, 'main/auth/login.html')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'Invalid credentials.')
            logger.warning(f'Login attempt with invalid username: {username}')
            return render(request, 'main/auth/login.html')
        
        if not user.is_active:
            messages.error(request, 'Account is inactive. Please contact administrator.')
            logger.warning(f'Login attempt for inactive user: {username}')
            return render(request, 'main/auth/login.html')
        
        if not user.check_password(password):
            messages.error(request, 'Invalid credentials.')
            logger.warning(f'Failed login attempt for user: {username}')
            return render(request, 'main/auth/login.html')
        
        # Successful login
        user.update_last_login()
        request.session['user_id'] = str(user.id)
        request.session['username'] = user.username
        request.session['user_role'] = user.role
        
        logger.info(f'User logged in: {username}')
        messages.success(request, f'Welcome back, {user.username}!')
        
        # Check if this is first login with default password
        if username == 'admin' and user.check_password('admin1234'):
            messages.warning(request, 'You are using the default password. Please change it immediately!')
            return redirect('main:change_password')
        
        # Redirect to next page or home (validate URL to prevent open redirect)
        next_url = request.GET.get('next', '')
        # Use Django's built-in URL validation
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect('main:home')
    
    return render(request, 'main/auth/login.html')


def logout_view(request):
    """Logout view"""
    username = request.session.get('username', 'Unknown')
    request.session.flush()
    logger.info(f'User logged out: {username}')
    messages.success(request, 'You have been logged out successfully.')
    return redirect('main:login')


def register_view(request):
    """Registration page view (optional)"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        # Validation
        if not username:
            messages.error(request, 'Username is required.')
        elif not email:
            messages.error(request, 'Email is required.')
        elif not password:
            messages.error(request, 'Password is required.')
        elif password != password_confirm:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            # Validate password
            is_valid, error_msg = validate_password(password)
            if not is_valid:
                messages.error(request, error_msg)
            else:
                try:
                    user = User(
                        username=username,
                        email=email,
                        role='user',
                        is_active=True
                    )
                    user.set_password(password)
                    user.save()
                    
                    logger.info(f'New user registered: {username}')
                    messages.success(request, 'Registration successful! Please log in.')
                    return redirect('main:login')
                except Exception as e:
                    logger.error(f'Registration error: {str(e)}')
                    messages.error(request, f'Error during registration: {str(e)}')
    
    return render(request, 'main/auth/register.html')


def forgot_password_view(request):
    """Forgot password - request reset email"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Email is required.')
            return render(request, 'main/auth/forgot_password.html')
        
        try:
            user = User.objects.get(email=email, is_active=True)
            
            # Generate reset token
            reset_token = PasswordResetToken.generate_token(user)
            
            # Build reset URL
            reset_url = request.build_absolute_uri(
                reverse('main:reset_password', kwargs={'token': reset_token.token})
            )
            
            # Send email
            try:
                send_password_reset_email(user, reset_url)
                messages.success(
                    request,
                    'Password reset instructions have been sent to your email.'
                )
                logger.info(f'Password reset email sent to: {email}')
            except Exception as e:
                logger.error(f'Failed to send password reset email: {str(e)}')
                messages.error(
                    request,
                    'Failed to send email. Please contact administrator.'
                )
        
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            messages.success(
                request,
                'If an account with that email exists, password reset instructions have been sent.'
            )
            logger.warning(f'Password reset requested for non-existent email: {email}')
        
        return redirect('main:login')
    
    return render(request, 'main/auth/forgot_password.html')


def reset_password_view(request, token):
    """Reset password with token"""
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
        
        if not reset_token.is_valid():
            messages.error(request, 'Password reset link is invalid or has expired.')
            logger.warning(f'Invalid password reset token used: {token}')
            return redirect('main:forgot_password')
        
        if request.method == 'POST':
            password = request.POST.get('password', '')
            password_confirm = request.POST.get('password_confirm', '')
            
            if password != password_confirm:
                messages.error(request, 'Passwords do not match.')
            else:
                # Validate password
                is_valid, error_msg = validate_password(password)
                if not is_valid:
                    messages.error(request, error_msg)
                else:
                    try:
                        user = reset_token.user
                        user.set_password(password)
                        user.save()
                        
                        reset_token.mark_as_used()
                        
                        logger.info(f'Password reset successful for user: {user.username}')
                        messages.success(request, 'Password has been reset successfully. Please log in.')
                        return redirect('main:login')
                    except Exception as e:
                        logger.error(f'Password reset error: {str(e)}')
                        messages.error(request, f'Error resetting password: {str(e)}')
        
        return render(request, 'main/auth/reset_password.html', {'token': token})
    
    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Invalid password reset link.')
        logger.warning(f'Non-existent password reset token: {token}')
        return redirect('main:forgot_password')


def change_password_view(request):
    """Change password for logged-in user"""
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please log in first.')
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        else:
            # Validate new password
            is_valid, error_msg = validate_password(new_password)
            if not is_valid:
                messages.error(request, error_msg)
            else:
                try:
                    user.set_password(new_password)
                    user.save()
                    
                    logger.info(f'Password changed for user: {user.username}')
                    messages.success(request, 'Password changed successfully!')
                    return redirect('main:home')
                except Exception as e:
                    logger.error(f'Password change error: {str(e)}')
                    messages.error(request, f'Error changing password: {str(e)}')
    
    return render(request, 'main/auth/change_password.html')


def send_password_reset_email(user, reset_url):
    """Send password reset email using Graph API"""
    try:
        graph_service = GraphService()
        
        # Load email template
        from django.template.loader import render_to_string
        html_content = render_to_string('main/mailtemplates/password_reset.html', {
            'user': user,
            'reset_url': reset_url,
        })
        
        # Send email
        result = graph_service.send_mail(
            to=[user.email],
            subject='Password Reset Request - IdeaGraph',
            body=html_content
        )
        
        if not result.get('success'):
            raise Exception(result.get('error', 'Unknown error'))
        
        return True
    
    except GraphServiceError as e:
        logger.error(f'Graph API error sending password reset email: {str(e)}')
        raise
    except Exception as e:
        logger.error(f'Error sending password reset email: {str(e)}')
        raise
