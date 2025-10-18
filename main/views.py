from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from .auth_utils import validate_password
from .models import Tag, Settings, Section, User, Item, Task, ItemSimilarity

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
        try:
            # Validate integer fields
            max_tags = request.POST.get('max_tags_per_idea', '5')
            kigate_timeout = request.POST.get('kigate_api_timeout', '30')
            
            try:
                max_tags_int = int(max_tags)
                if max_tags_int < 1 or max_tags_int > 20:
                    messages.error(request, 'Max tags per idea must be between 1 and 20.')
                    return render(request, 'main/settings_form.html', {'action': 'Create'})
            except ValueError:
                messages.error(request, 'Max tags per idea must be a valid number.')
                return render(request, 'main/settings_form.html', {'action': 'Create'})
            
            try:
                kigate_timeout_int = int(kigate_timeout)
                if kigate_timeout_int < 1 or kigate_timeout_int > 600:
                    messages.error(request, 'KiGate API timeout must be between 1 and 600 seconds.')
                    return render(request, 'main/settings_form.html', {'action': 'Create'})
            except ValueError:
                messages.error(request, 'KiGate API timeout must be a valid number.')
                return render(request, 'main/settings_form.html', {'action': 'Create'})
            
            # Create settings
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
                kigate_api_timeout=kigate_timeout_int,
                max_tags_per_idea=max_tags_int,
            )
            messages.success(request, 'Settings created successfully!')
            return redirect('main:settings_list')
        except Exception as e:
            messages.error(request, f'Error creating settings: {str(e)}')
            return render(request, 'main/settings_form.html', {'action': 'Create'})
    
    return render(request, 'main/settings_form.html', {'action': 'Create'})


def settings_update(request, pk):
    """Update an existing settings entry"""
    settings = get_object_or_404(Settings, pk=pk)
    
    if request.method == 'POST':
        try:
            # Validate integer fields
            max_tags = request.POST.get('max_tags_per_idea', '5')
            kigate_timeout = request.POST.get('kigate_api_timeout', '30')
            
            try:
                max_tags_int = int(max_tags)
                if max_tags_int < 1 or max_tags_int > 20:
                    messages.error(request, 'Max tags per idea must be between 1 and 20.')
                    return render(request, 'main/settings_form.html', {
                        'settings': settings,
                        'action': 'Update'
                    })
            except ValueError:
                messages.error(request, 'Max tags per idea must be a valid number.')
                return render(request, 'main/settings_form.html', {
                    'settings': settings,
                    'action': 'Update'
                })
            
            try:
                kigate_timeout_int = int(kigate_timeout)
                if kigate_timeout_int < 1 or kigate_timeout_int > 600:
                    messages.error(request, 'KiGate API timeout must be between 1 and 600 seconds.')
                    return render(request, 'main/settings_form.html', {
                        'settings': settings,
                        'action': 'Update'
                    })
            except ValueError:
                messages.error(request, 'KiGate API timeout must be a valid number.')
                return render(request, 'main/settings_form.html', {
                    'settings': settings,
                    'action': 'Update'
                })
            
            # Update settings
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
            settings.kigate_api_timeout = kigate_timeout_int
            settings.max_tags_per_idea = max_tags_int
            settings.save()
            
            messages.success(request, 'Settings updated successfully!')
            return redirect('main:settings_list')
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
            return render(request, 'main/settings_form.html', {
                'settings': settings,
                'action': 'Update'
            })
    
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


# ==================== Item Views ====================

def item_list(request):
    """List all items for the current user"""
    # Check if user is logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please log in to view items.')
        return redirect('main:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('main:login')
    
    # Get filters from request
    status_filter = request.GET.get('status', '')
    section_filter = request.GET.get('section', '')
    search_query = request.GET.get('search', '').strip()
    
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
    
    if search_query:
        from django.db.models import Q
        items = items.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Prefetch related data
    items = items.select_related('section', 'created_by').prefetch_related('tags')
    
    # Pagination
    paginator = Paginator(items, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get all sections for filter dropdown
    sections = Section.objects.all()
    
    context = {
        'items': page_obj,
        'status_choices': Item.STATUS_CHOICES,
        'sections': sections,
        'status_filter': status_filter,
        'section_filter': section_filter,
        'search_query': search_query,
    }
    
    return render(request, 'main/items/list.html', context)


def item_kanban(request):
    """Kanban view of items for the current user"""
    # Check if user is logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please log in to view items.')
        return redirect('main:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('main:login')
    
    # Get show_done filter
    show_done = request.GET.get('show_done', 'false') == 'true'
    
    # Base query: show only user's items (or all if admin)
    if user.role == 'admin':
        items = Item.objects.all()
    else:
        items = Item.objects.filter(created_by=user)
    
    # Prefetch related data
    items = items.select_related('section', 'created_by').prefetch_related('tags')
    
    # Group items by status
    items_by_status = {}
    for status_code, status_label in Item.STATUS_CHOICES:
        if not show_done and status_code in ['done', 'rejected']:
            continue
        items_by_status[status_code] = {
            'label': status_label,
            'items': items.filter(status=status_code)
        }
    
    context = {
        'items_by_status': items_by_status,
        'status_choices': Item.STATUS_CHOICES,
        'show_done': show_done,
    }
    
    return render(request, 'main/items/kanban.html', context)


def item_detail(request, item_id):
    """Detail view and edit form for a single item"""
    # Check if user is logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please log in to view items.')
        return redirect('main:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('main:login')
    
    # Get the item
    item = get_object_or_404(Item, id=item_id)
    
    # Check permissions: only owner or admin can view
    if item.created_by != user and user.role != 'admin':
        messages.error(request, 'You do not have permission to view this item.')
        return redirect('main:item_list')
    
    if request.method == 'POST':
        # Handle form submission
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_repo = request.POST.get('github_repo', '').strip()
        status = request.POST.get('status', 'new')
        section_id = request.POST.get('section', '')
        tag_ids = request.POST.getlist('tags')
        
        if not title:
            messages.error(request, 'Title is required.')
        else:
            try:
                item.title = title
                item.description = description
                item.github_repo = github_repo
                item.status = status
                
                # Update section
                if section_id:
                    item.section_id = section_id
                else:
                    item.section = None
                
                item.save()
                
                # Update tags
                item.tags.set(tag_ids)
                
                messages.success(request, 'Item updated successfully!')
                return redirect('main:item_detail', item_id=item.id)
            except Exception as e:
                messages.error(request, f'Error updating item: {str(e)}')
    
    # Get related data
    sections = Section.objects.all()
    tags = Tag.objects.all()
    
    # Get similar items
    similar_items = ItemSimilarity.objects.filter(source_item=item).select_related('target_item')[:10]
    
    # Get tasks for this item
    tasks = Task.objects.filter(item=item).select_related('assigned_to')
    
    # Get settings for AI features
    settings = Settings.objects.first()
    
    context = {
        'item': item,
        'sections': sections,
        'tags': tags,
        'status_choices': Item.STATUS_CHOICES,
        'similar_items': similar_items,
        'tasks': tasks,
        'settings': settings,
    }
    
    return render(request, 'main/items/detail.html', context)


def item_create(request):
    """Create a new item"""
    # Check if user is logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please log in to create items.')
        return redirect('main:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('main:login')
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_repo = request.POST.get('github_repo', '').strip()
        status = request.POST.get('status', 'new')
        section_id = request.POST.get('section', '')
        tag_ids = request.POST.getlist('tags')
        
        if not title:
            messages.error(request, 'Title is required.')
        else:
            try:
                item = Item(
                    title=title,
                    description=description,
                    github_repo=github_repo,
                    status=status,
                    created_by=user
                )
                
                # Set section if provided
                if section_id:
                    item.section_id = section_id
                
                item.save()
                
                # Set tags
                item.tags.set(tag_ids)
                
                messages.success(request, f'Item "{title}" created successfully!')
                return redirect('main:item_detail', item_id=item.id)
            except Exception as e:
                messages.error(request, f'Error creating item: {str(e)}')
    
    # Get related data
    sections = Section.objects.all()
    tags = Tag.objects.all()
    
    context = {
        'sections': sections,
        'tags': tags,
        'status_choices': Item.STATUS_CHOICES,
    }
    
    return render(request, 'main/items/form.html', context)


def item_delete(request, item_id):
    """Delete an item"""
    # Check if user is logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please log in to delete items.')
        return redirect('main:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('main:login')
    
    # Get the item
    item = get_object_or_404(Item, id=item_id)
    
    # Check permissions: only owner or admin can delete
    if item.created_by != user and user.role != 'admin':
        messages.error(request, 'You do not have permission to delete this item.')
        return redirect('main:item_list')
    
    if request.method == 'POST':
        item_title = item.title
        item.delete()
        messages.success(request, f'Item "{item_title}" deleted successfully!')
        return redirect('main:item_list')
    
    context = {'item': item}
    return render(request, 'main/items/delete.html', context)

