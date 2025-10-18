from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from .auth_utils import validate_password
from .models import Tag, Settings, Section, User

def home(request):
    """Home page view"""
    return render(request, 'main/home.html')


def settings_view(request):
    """Settings page view"""
    return render(request, 'main/settings.html')


def tag_list(request):
    """List all tags"""
    tags = Tag.objects.all()
    return render(request, 'main/tags/list.html', {'tags': tags})


def tag_create(request):
    """Create a new tag"""
    if request.method == 'POST':
        name = request.POST.get('name')
        color = request.POST.get('color')
        
        if name:
            try:
                tag = Tag(name=name)
                if color:
                    tag.color = color
                tag.save()
                messages.success(request, f'Tag "{name}" created successfully!')
                return redirect('main:tag_list')
            except Exception as e:
                messages.error(request, f'Error creating tag: {str(e)}')
        else:
            messages.error(request, 'Tag name is required.')
    
    return render(request, 'main/tags/form.html', {'color_palette': Tag.COLOR_PALETTE})


def tag_edit(request, tag_id):
    """Edit an existing tag"""
    tag = get_object_or_404(Tag, id=tag_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        color = request.POST.get('color')
        
        if name:
            try:
                tag.name = name
                tag.color = color
                tag.save()
                messages.success(request, f'Tag "{name}" updated successfully!')
                return redirect('main:tag_list')
            except Exception as e:
                messages.error(request, f'Error updating tag: {str(e)}')
        else:
            messages.error(request, 'Tag name is required.')
    
    return render(request, 'main/tags/form.html', {
        'tag': tag,
        'color_palette': Tag.COLOR_PALETTE
    })


def tag_delete(request, tag_id):
    """Delete a tag"""
    tag = get_object_or_404(Tag, id=tag_id)
    
    if request.method == 'POST':
        tag_name = tag.name
        tag.delete()
        messages.success(request, f'Tag "{tag_name}" deleted successfully!')
        return redirect('main:tag_list')
    
    return render(request, 'main/tags/delete.html', {'tag': tag})


def section_list(request):
    """List all sections"""
    sections = Section.objects.all()
    return render(request, 'main/sections/list.html', {'sections': sections})


def section_create(request):
    """Create a new section"""
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if name:
            try:
                section = Section(name=name)
                section.save()
                messages.success(request, f'Section "{name}" created successfully!')
                return redirect('main:section_list')
            except Exception as e:
                messages.error(request, f'Error creating section: {str(e)}')
        else:
            messages.error(request, 'Section name is required.')
    
    return render(request, 'main/sections/form.html')


def section_edit(request, section_id):
    """Edit an existing section"""
    section = get_object_or_404(Section, id=section_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if name:
            try:
                section.name = name
                section.save()
                messages.success(request, f'Section "{name}" updated successfully!')
                return redirect('main:section_list')
            except Exception as e:
                messages.error(request, f'Error updating section: {str(e)}')
        else:
            messages.error(request, 'Section name is required.')
    
    return render(request, 'main/sections/form.html', {'section': section})


def section_delete(request, section_id):
    """Delete a section"""
    section = get_object_or_404(Section, id=section_id)
    
    if request.method == 'POST':
        section_name = section.name
        section.delete()
        messages.success(request, f'Section "{section_name}" deleted successfully!')
        return redirect('main:section_list')
    
    return render(request, 'main/sections/delete.html', {'section': section})


def settings_list(request):
    """List all settings"""
    settings = Settings.objects.all()
    return render(request, 'main/settings_list.html', {'settings': settings})


def settings_create(request):
    """Create a new settings entry"""
    if request.method == 'POST':
        settings = Settings.objects.create(
            openai_api_key=request.POST.get('openai_api_key', ''),
            openai_org_id=request.POST.get('openai_org_id', ''),
            client_id=request.POST.get('client_id', ''),
            client_secret=request.POST.get('client_secret', ''),
            tenant_id=request.POST.get('tenant_id', ''),
            github_token=request.POST.get('github_token', ''),
            chroma_api_key=request.POST.get('chroma_api_key', ''),
            chroma_database=request.POST.get('chroma_database', ''),
            chroma_tenant=request.POST.get('chroma_tenant', ''),
            kigate_api_enabled=request.POST.get('kigate_api_enabled', 'false') == 'true',
            kigate_api_base_url=request.POST.get('kigate_api_base_url', 'http://localhost:8000'),
            kigate_api_token=request.POST.get('kigate_api_token', ''),
            kigate_api_timeout=int(request.POST.get('kigate_api_timeout', 30)),
            max_tags_per_idea=int(request.POST.get('max_tags_per_idea', 5)),
        )
        messages.success(request, 'Settings created successfully!')
        return redirect('main:settings_list')
    
    return render(request, 'main/settings_form.html', {'action': 'Create'})


def settings_update(request, pk):
    """Update an existing settings entry"""
    settings = get_object_or_404(Settings, pk=pk)
    
    if request.method == 'POST':
        settings.openai_api_key = request.POST.get('openai_api_key', '')
        settings.openai_org_id = request.POST.get('openai_org_id', '')
        settings.client_id = request.POST.get('client_id', '')
        settings.client_secret = request.POST.get('client_secret', '')
        settings.tenant_id = request.POST.get('tenant_id', '')
        settings.github_token = request.POST.get('github_token', '')
        settings.chroma_api_key = request.POST.get('chroma_api_key', '')
        settings.chroma_database = request.POST.get('chroma_database', '')
        settings.chroma_tenant = request.POST.get('chroma_tenant', '')
        settings.kigate_api_enabled = request.POST.get('kigate_api_enabled', 'false') == 'true'
        settings.kigate_api_base_url = request.POST.get('kigate_api_base_url', 'http://localhost:8000')
        settings.kigate_api_token = request.POST.get('kigate_api_token', '')
        settings.kigate_api_timeout = int(request.POST.get('kigate_api_timeout', 30))
        settings.max_tags_per_idea = int(request.POST.get('max_tags_per_idea', 5))
        settings.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('main:settings_list')
    
    return render(request, 'main/settings_form.html', {
        'settings': settings,
        'action': 'Update'
    })


def settings_delete(request, pk):
    """Delete a settings entry"""
    settings = get_object_or_404(Settings, pk=pk)
    
    if request.method == 'POST':
        settings.delete()
        messages.success(request, 'Settings deleted successfully!')
        return redirect('main:settings_list')
    
    return render(request, 'main/settings_confirm_delete.html', {'settings': settings})


# User Management Views
def user_list(request):
    """List all users with pagination and search"""
    search_query = request.GET.get('search', '').strip()
    role_filter = request.GET.get('role', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    users = User.objects.all()
    
    # Apply filters
    if search_query:
        from django.db.models import Q
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query)
        )
    
    if role_filter:
        users = users.filter(role=role_filter)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'role_choices': User.ROLE_CHOICES,
    }
    
    return render(request, 'main/users/user_list.html', context)


def user_create(request):
    """Create a new user"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        role = request.POST.get('role', 'user')
        is_active = request.POST.get('is_active') == 'on'
        ai_classification = request.POST.get('ai_classification', '').strip()
        
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
                        role=role,
                        is_active=is_active,
                        ai_classification=ai_classification
                    )
                    user.set_password(password)
                    user.save()
                    messages.success(request, f'User "{username}" created successfully!')
                    return redirect('main:user_list')
                except Exception as e:
                    messages.error(request, f'Error creating user: {str(e)}')
    
    context = {
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'main/users/user_create.html', context)


def user_edit(request, user_id):
    """Edit an existing user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', user.role)
        is_active = request.POST.get('is_active') == 'on'
        ai_classification = request.POST.get('ai_classification', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        # Validation
        if not email:
            messages.error(request, 'Email is required.')
        elif User.objects.filter(email=email).exclude(id=user_id).exists():
            messages.error(request, 'Email already exists.')
        elif password and password != password_confirm:
            messages.error(request, 'Passwords do not match.')
        else:
            # Validate password if provided
            if password:
                is_valid, error_msg = validate_password(password)
                if not is_valid:
                    messages.error(request, error_msg)
                    context = {
                        'user': user,
                        'role_choices': User.ROLE_CHOICES,
                    }
                    return render(request, 'main/users/user_edit.html', context)
            
            try:
                user.email = email
                user.role = role
                user.is_active = is_active
                user.ai_classification = ai_classification
                
                if password:
                    user.set_password(password)
                
                user.save()
                messages.success(request, f'User "{user.username}" updated successfully!')
                return redirect('main:user_list')
            except Exception as e:
                messages.error(request, f'Error updating user: {str(e)}')
    
    context = {
        'user': user,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'main/users/user_edit.html', context)


def user_detail(request, user_id):
    """View user details"""
    user = get_object_or_404(User, id=user_id)
    context = {'user': user}
    return render(request, 'main/users/user_detail.html', context)


def user_delete(request, user_id):
    """Delete a user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Prevent deleting yourself
        current_user_id = request.session.get('user_id')
        if current_user_id == str(user.id):
            messages.error(request, 'You cannot delete your own account!')
            return redirect('main:user_list')
        
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted successfully!')
        return redirect('main:user_list')
    
    context = {'user': user}
    return render(request, 'main/users/user_delete.html', context)


def user_send_password(request, user_id):
    """Generate and send a new password to user via email"""
    from main.auth_utils import generate_secure_password
    from main.mail_utils import send_password_email
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        try:
            # Generate a secure random password
            new_password = generate_secure_password(12)
            
            # Set the new password
            user.set_password(new_password)
            user.save()
            
            # Send the password via email
            success, message = send_password_email(user, new_password)
            
            if success:
                messages.success(request, f'New password generated and sent to {user.email}')
            else:
                messages.error(request, f'Password updated but failed to send email: {message}')
                
        except Exception as e:
            messages.error(request, f'Failed to generate and send password: {str(e)}')
        
        # Redirect back to where we came from
        return_url = request.POST.get('return_url', 'main:user_list')
        if return_url == 'detail':
            return redirect('main:user_detail', user_id=user_id)
        else:
            return redirect('main:user_list')
    
    # If GET request, redirect to user list
    return redirect('main:user_list')

