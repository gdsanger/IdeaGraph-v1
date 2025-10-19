from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from .auth_utils import validate_password
from .models import Tag, Settings, Section, User, Item, Task


def _separate_tag_values(tag_values):
    existing_ids = []
    new_names = []
    for value in tag_values:
        if not value:
            continue
        if isinstance(value, str) and value[:4].lower() == 'new:':
            name = value[4:].strip()
            if name:
                new_names.append(name)
        else:
            existing_ids.append(value)
    return existing_ids, new_names


def _resolve_tag_values(tag_values):
    """Return Tag objects for submitted form values, creating new tags as needed."""

    existing_ids, new_names = _separate_tag_values(tag_values)

    resolved_tags = []
    seen_ids = set()
    if existing_ids:
        existing_tags_map = {
            str(tag.id): tag for tag in Tag.objects.filter(id__in=existing_ids)
        }
        for tag_id in existing_ids:
            tag_obj = existing_tags_map.get(str(tag_id))
            if tag_obj and str(tag_obj.id) not in seen_ids:
                resolved_tags.append(tag_obj)
                seen_ids.add(str(tag_obj.id))

    seen_new_names = set()
    for name in new_names:
        lower_name = name.lower()
        if lower_name in seen_new_names:
            continue
        seen_new_names.add(lower_name)

        existing_tag = Tag.objects.filter(name__iexact=name).first()
        if existing_tag:
            if str(existing_tag.id) not in seen_ids:
                resolved_tags.append(existing_tag)
                seen_ids.add(str(existing_tag.id))
            continue

        new_tag = Tag.objects.create(name=name)
        resolved_tags.append(new_tag)
        seen_ids.add(str(new_tag.id))

    return resolved_tags


def _build_selected_tags_payload(tag_values):
    """Return dictionaries for rendering selected tags without creating new records."""

    existing_ids, new_names = _separate_tag_values(tag_values)

    payload = []
    seen_names = set()

    if existing_ids:
        existing_tags = {
            str(tag['id']): tag
            for tag in Tag.objects.filter(id__in=existing_ids).values('id', 'name', 'color')
        }
        for tag_id in existing_ids:
            tag = existing_tags.get(str(tag_id))
            if tag:
                name_lower = tag['name'].lower()
                if name_lower not in seen_names:
                    payload.append(tag)
                    seen_names.add(name_lower)

    for name in new_names:
        lower_name = name.lower()
        if lower_name in seen_names:
            continue
        existing_tag = Tag.objects.filter(name__iexact=name).values('id', 'name', 'color').first()
        if existing_tag:
            if existing_tag['name'].lower() not in seen_names:
                payload.append(existing_tag)
                seen_names.add(existing_tag['name'].lower())
            continue
        payload.append({'id': None, 'name': name, 'color': None})
        seen_names.add(lower_name)

    return payload

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
            kigate_api_enabled=request.POST.get('kigate_api_enabled') == 'on',
            kigate_api_base_url=request.POST.get('kigate_api_base_url', 'http://localhost:8000'),
            kigate_api_token=request.POST.get('kigate_api_token', ''),
            kigate_api_timeout=int(request.POST.get('kigate_api_timeout') or 30),
            max_tags_per_idea=int(request.POST.get('max_tags_per_idea') or 5),
            graph_api_enabled=request.POST.get('graph_api_enabled') == 'on',
            sharepoint_site_id=request.POST.get('sharepoint_site_id', ''),
            default_mail_sender=request.POST.get('default_mail_sender', ''),
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
        settings.kigate_api_enabled = request.POST.get('kigate_api_enabled') == 'on'
        settings.kigate_api_base_url = request.POST.get('kigate_api_base_url', 'http://localhost:8000')
        settings.kigate_api_token = request.POST.get('kigate_api_token', '')
        settings.kigate_api_timeout = int(request.POST.get('kigate_api_timeout') or 30)
        settings.max_tags_per_idea = int(request.POST.get('max_tags_per_idea') or 5)
        settings.graph_api_enabled = request.POST.get('graph_api_enabled') == 'on'
        settings.sharepoint_site_id = request.POST.get('sharepoint_site_id', '')
        settings.default_mail_sender = request.POST.get('default_mail_sender', '')
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


# Item Management Views

def item_list(request):
    """List all items for the current user"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    section_filter = request.GET.get('section', '')
    search_query = request.GET.get('search', '').strip()
    
    # Base query - show only user's items unless admin
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
    
    # Get all sections and status choices for filters
    sections = Section.objects.all()
    status_choices = Item.STATUS_CHOICES
    
    context = {
        'items': page_obj,
        'sections': sections,
        'status_choices': status_choices,
        'status_filter': status_filter,
        'section_filter': section_filter,
        'search_query': search_query,
    }
    
    return render(request, 'main/items/list.html', context)


def item_kanban(request):
    """Kanban view for items"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get filter parameter for showing completed items
    show_completed = request.GET.get('show_completed', 'false') == 'true'
    
    # Base query - show only user's items unless admin
    if user.role == 'admin':
        items = Item.objects.all()
    else:
        items = Item.objects.filter(created_by=user)
    
    # Prefetch related data
    items = items.select_related('section', 'created_by').prefetch_related('tags')
    
    # Group items by status
    items_by_status = {}
    for status_key, status_label in Item.STATUS_CHOICES:
        status_items = items.filter(status=status_key)
        
        # Hide completed/rejected unless show_completed is true
        if not show_completed and status_key in ['done', 'rejected']:
            status_items = []
        
        items_by_status[status_key] = {
            'label': status_label,
            'items': list(status_items)
        }
    
    context = {
        'items_by_status': items_by_status,
        'show_completed': show_completed,
        'status_choices': Item.STATUS_CHOICES,
    }
    
    return render(request, 'main/items/kanban.html', context)


def item_detail(request, item_id):
    """Detail view for a single item"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get item - check ownership unless admin
    item = get_object_or_404(Item, id=item_id)
    if user.role != 'admin' and item.created_by != user:
        messages.error(request, 'You do not have permission to view this item.')
        return redirect('main:item_list')
    
    # Handle POST request for updating the item
    selected_tags_payload = list(item.tags.values('id', 'name', 'color'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_repo = request.POST.get('github_repo', '').strip()
        section_id = request.POST.get('section')
        status = request.POST.get('status', item.status)
        tag_values = request.POST.getlist('tags')

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
        else:
            try:
                item.title = title
                item.description = description
                item.github_repo = github_repo
                item.status = status

                if section_id:
                    item.section_id = section_id
                else:
                    item.section = None

                item.save()

                # Update tags
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    item.tags.set(resolved_tags)
                else:
                    item.tags.clear()

                # Sync update to ChromaDB
                try:
                    from core.services.chroma_sync_service import ChromaItemSyncService
                    sync_service = ChromaItemSyncService()
                    sync_service.sync_update(item)
                except Exception as sync_error:
                    # Log error but don't fail the item update
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'ChromaDB sync failed for item {item.id}: {str(sync_error)}')

                messages.success(request, f'Item "{title}" updated successfully!')
                selected_tags_payload = list(item.tags.values('id', 'name', 'color'))

            except Exception as e:
                messages.error(request, f'Error updating item: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
    
    # Get related tasks
    tasks = item.tasks.all().select_related('assigned_to', 'created_by').prefetch_related('tags')
    
    # Get all sections, tags, and status choices for the form
    sections = Section.objects.all()
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    status_choices = Item.STATUS_CHOICES

    context = {
        'item': item,
        'tasks': tasks,
        'sections': sections,
        'all_tags': all_tags,
        'selected_tags': selected_tags_payload,
        'status_choices': status_choices,
    }
    
    return render(request, 'main/items/detail.html', context)


def item_create(request):
    """Create a new item"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    selected_tags_payload = []

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_repo = request.POST.get('github_repo', '').strip()
        section_id = request.POST.get('section')
        status = request.POST.get('status', 'new')
        tag_values = request.POST.getlist('tags')

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
        else:
            try:
                # Create item
                item = Item(
                    title=title,
                    description=description,
                    github_repo=github_repo,
                    status=status,
                    created_by=user
                )

                if section_id:
                    item.section_id = section_id

                item.save()

                # Add tags
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    item.tags.set(resolved_tags)

                # Sync to ChromaDB
                try:
                    from core.services.chroma_sync_service import ChromaItemSyncService
                    sync_service = ChromaItemSyncService()
                    sync_service.sync_create(item)
                except Exception as sync_error:
                    # Log error but don't fail the item creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'ChromaDB sync failed for item {item.id}: {str(sync_error)}')

                messages.success(request, f'Item "{title}" created successfully!')
                return redirect('main:item_detail', item_id=item.id)

            except Exception as e:
                messages.error(request, f'Error creating item: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
    
    # Get all sections and tags for the form
    sections = Section.objects.all()
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    status_choices = Item.STATUS_CHOICES

    context = {
        'sections': sections,
        'all_tags': all_tags,
        'selected_tags': selected_tags_payload,
        'status_choices': status_choices,
    }
    
    return render(request, 'main/items/form.html', context)


def item_edit(request, item_id):
    """Edit an existing item"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get item - check ownership unless admin
    item = get_object_or_404(Item, id=item_id)
    if user.role != 'admin' and item.created_by != user:
        messages.error(request, 'You do not have permission to edit this item.')
        return redirect('main:item_list')
    
    selected_tags_payload = list(item.tags.values('id', 'name', 'color'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_repo = request.POST.get('github_repo', '').strip()
        section_id = request.POST.get('section')
        status = request.POST.get('status', item.status)
        tag_values = request.POST.getlist('tags')

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
        else:
            try:
                item.title = title
                item.description = description
                item.github_repo = github_repo
                item.status = status

                if section_id:
                    item.section_id = section_id
                else:
                    item.section = None

                item.save()

                # Update tags
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    item.tags.set(resolved_tags)
                else:
                    item.tags.clear()

                # Sync update to ChromaDB
                try:
                    from core.services.chroma_sync_service import ChromaItemSyncService
                    sync_service = ChromaItemSyncService()
                    sync_service.sync_update(item)
                except Exception as sync_error:
                    # Log error but don't fail the item update
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'ChromaDB sync failed for item {item.id}: {str(sync_error)}')

                messages.success(request, f'Item "{title}" updated successfully!')
                return redirect('main:item_detail', item_id=item.id)

            except Exception as e:
                messages.error(request, f'Error updating item: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
    
    # Get all sections and tags for the form
    sections = Section.objects.all()
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    status_choices = Item.STATUS_CHOICES

    context = {
        'item': item,
        'sections': sections,
        'all_tags': all_tags,
        'selected_tags': selected_tags_payload,
        'status_choices': status_choices,
    }
    
    return render(request, 'main/items/form.html', context)


def item_delete(request, item_id):
    """Delete an item"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get item - check ownership unless admin
    item = get_object_or_404(Item, id=item_id)
    if user.role != 'admin' and item.created_by != user:
        messages.error(request, 'You do not have permission to delete this item.')
        return redirect('main:item_list')
    
    if request.method == 'POST':
        item_title = item.title
        item_id_str = str(item.id)
        item.delete()
        
        # Sync delete to ChromaDB
        try:
            from core.services.chroma_sync_service import ChromaItemSyncService
            sync_service = ChromaItemSyncService()
            sync_service.sync_delete(item_id_str)
        except Exception as sync_error:
            # Log error but don't fail the item deletion
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'ChromaDB sync failed for item {item_id_str}: {str(sync_error)}')
        
        messages.success(request, f'Item "{item_title}" deleted successfully!')
        return redirect('main:item_list')
    
    context = {'item': item}
    return render(request, 'main/items/delete.html', context)


# Task Management Views

def task_list(request, item_id):
    """List all tasks for an item"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get item - check ownership unless admin
    item = get_object_or_404(Item, id=item_id)
    if user.role != 'admin' and item.created_by != user:
        messages.error(request, 'You do not have permission to view this item.')
        return redirect('main:item_list')
    
    # Get tasks for this item - only show owned tasks
    tasks = item.tasks.filter(created_by=user).select_related('assigned_to', 'created_by').prefetch_related('tags')
    
    # Sort tasks by status priority
    status_order = {'new': 1, 'working': 2, 'review': 3, 'ready': 4, 'done': 5}
    tasks = sorted(tasks, key=lambda t: status_order.get(t.status, 99))
    
    context = {
        'item': item,
        'tasks': tasks,
    }
    
    return render(request, 'main/tasks/list.html', context)


def task_detail(request, task_id):
    """Detail view for a single task"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get task - check ownership
    task = get_object_or_404(Task, id=task_id)
    if task.created_by != user:
        messages.error(request, 'You do not have permission to view this task.')
        return redirect('main:item_list')

    selected_tags_payload = list(task.tags.values('id', 'name', 'color'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', task.status)
        tag_values = request.POST.getlist('tags')

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
        else:
            try:
                previous_status = task.status
                task.title = title
                task.description = description
                task.status = status

                if status == 'done' and previous_status != 'done':
                    task.mark_as_done()
                else:
                    task.save()

                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    task.tags.set(resolved_tags)
                else:
                    task.tags.clear()

                messages.success(request, f'Task "{title}" updated successfully!')
                selected_tags_payload = list(task.tags.values('id', 'name', 'color'))

            except Exception as e:
                messages.error(request, f'Error updating task: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)

    # Get all tags and status choices
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    status_choices = Task.STATUS_CHOICES

    context = {
        'task': task,
        'all_tags': all_tags,
        'selected_tags': selected_tags_payload,
        'status_choices': status_choices,
    }

    return render(request, 'main/tasks/detail.html', context)


def task_create(request, item_id):
    """Create a new task"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get item - check ownership unless admin
    item = get_object_or_404(Item, id=item_id)
    if user.role != 'admin' and item.created_by != user:
        messages.error(request, 'You do not have permission to create tasks for this item.')
        return redirect('main:item_list')
    
    selected_tags_payload = list(item.tags.values('id', 'name', 'color'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', 'new')
        tag_values = request.POST.getlist('tags')

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
        else:
            try:
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
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    task.tags.set(resolved_tags)

                messages.success(request, f'Task "{title}" created successfully!')
                return redirect('main:task_detail', task_id=task.id)

            except Exception as e:
                messages.error(request, f'Error creating task: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
    
    # Get all tags for the form
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    status_choices = Task.STATUS_CHOICES

    context = {
        'item': item,
        'all_tags': all_tags,
        'selected_tags': selected_tags_payload,
        'status_choices': status_choices,
    }
    
    return render(request, 'main/tasks/form.html', context)


def task_edit(request, task_id):
    """Edit an existing task"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get task - check ownership
    task = get_object_or_404(Task, id=task_id)
    if task.created_by != user:
        messages.error(request, 'You do not have permission to edit this task.')
        return redirect('main:item_list')
    
    selected_tags_payload = list(task.tags.values('id', 'name', 'color'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', task.status)
        tag_values = request.POST.getlist('tags')

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
        else:
            try:
                previous_status = task.status
                task.title = title
                task.description = description
                task.status = status

                # Mark as done if status changed to done
                if status == 'done' and previous_status != 'done':
                    task.mark_as_done()
                else:
                    task.save()

                # Update tags
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    task.tags.set(resolved_tags)
                else:
                    task.tags.clear()

                messages.success(request, f'Task "{title}" updated successfully!')
                return redirect('main:task_detail', task_id=task.id)

            except Exception as e:
                messages.error(request, f'Error updating task: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
    
    # Get all tags for the form
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    status_choices = Task.STATUS_CHOICES

    context = {
        'task': task,
        'all_tags': all_tags,
        'selected_tags': selected_tags_payload,
        'status_choices': status_choices,
    }
    
    return render(request, 'main/tasks/form.html', context)


def task_delete(request, task_id):
    """Delete a task"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get task - check ownership
    task = get_object_or_404(Task, id=task_id)
    if task.created_by != user:
        messages.error(request, 'You do not have permission to delete this task.')
        return redirect('main:item_list')
    
    item = task.item
    
    if request.method == 'POST':
        task_title = task.title
        task.delete()
        messages.success(request, f'Task "{task_title}" deleted successfully!')
        return redirect('main:item_detail', item_id=item.id)
    
    context = {'task': task}
    return render(request, 'main/tasks/delete.html', context)


def task_overview(request):
    """Global task overview - shows all tasks for the user"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    item_filter = request.GET.get('item', '')
    has_github = request.GET.get('has_github', '')
    search_query = request.GET.get('search', '').strip()
    
    # Base query - show only user's tasks unless admin
    if user.role == 'admin':
        tasks = Task.objects.all()
    else:
        tasks = Task.objects.filter(created_by=user)
    
    # Apply filters
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if item_filter:
        tasks = tasks.filter(item_id=item_filter)
    
    if has_github == 'true':
        tasks = tasks.filter(github_issue_id__isnull=False)
    elif has_github == 'false':
        tasks = tasks.filter(github_issue_id__isnull=True)
    
    if search_query:
        from django.db.models import Q
        tasks = tasks.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Prefetch related data
    tasks = tasks.select_related('item', 'assigned_to', 'created_by').prefetch_related('tags')
    tasks = tasks.order_by('-updated_at')
    
    # Calculate status counts
    status_counts = {}
    for status_key, status_label in Task.STATUS_CHOICES:
        if user.role == 'admin':
            count = Task.objects.filter(status=status_key).count()
        else:
            count = Task.objects.filter(status=status_key, created_by=user).count()
        status_counts[status_key] = count
    
    # Pagination
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get all items for filter dropdown
    if user.role == 'admin':
        items = Item.objects.all()
    else:
        items = Item.objects.filter(created_by=user)
    
    context = {
        'tasks': page_obj,
        'items': items,
        'status_choices': Task.STATUS_CHOICES,
        'status_counts': status_counts,
        'status_filter': status_filter,
        'item_filter': item_filter,
        'has_github': has_github,
        'search_query': search_query,
    }
    
    return render(request, 'main/tasks/overview.html', context)

