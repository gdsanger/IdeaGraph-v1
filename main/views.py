from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from .auth_utils import validate_password
from .models import Tag, Settings, Section, User, Item, Task, Client, Milestone
import logging

logger = logging.getLogger(__name__)


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


def _resolve_client_values(client_values):
    """Return Client objects for submitted form values."""
    if not client_values:
        return []
    
    resolved_clients = []
    seen_ids = set()
    
    for value in client_values:
        if not value:
            continue
        # Skip new client names (prefixed with "new:") - clients cannot be created inline
        if isinstance(value, str) and value[:4].lower() == 'new:':
            continue
        # Client values should only be existing IDs (no creation like tags)
        if str(value) not in seen_ids:
            try:
                client = Client.objects.get(id=value)
                resolved_clients.append(client)
                seen_ids.add(str(value))
            except (Client.DoesNotExist, ValueError, TypeError, ValidationError):
                # ValueError: invalid UUID format
                # TypeError: unexpected type for UUID conversion
                # ValidationError: Django validation error for invalid UUID
                continue
    
    return resolved_clients


def _build_selected_clients_payload(client_values):
    """Return dictionaries for rendering selected clients."""
    if not client_values:
        return []
    
    payload = []
    seen_ids = set()
    
    existing_clients = {
        str(client['id']): client
        for client in Client.objects.filter(id__in=client_values).values('id', 'name')
    }
    
    for client_id in client_values:
        if str(client_id) not in seen_ids:
            client = existing_clients.get(str(client_id))
            if client:
                payload.append(client)
                seen_ids.add(str(client_id))
    
    return payload


def home(request):
    """Home page view"""
    # Fetch statistics from database
    total_items = Item.objects.count()
    total_tasks = Task.objects.count()
    github_issues = Task.objects.filter(github_issue_id__isnull=False).count()
    completed_tasks = Task.objects.filter(status='done').count()
    
    context = {
        'total_items': total_items,
        'total_tasks': total_tasks,
        'github_issues': github_issues,
        'completed_tasks': completed_tasks,
    }
    
    return render(request, 'main/home.html', context)


def settings_view(request):
    """Settings page view"""
    return render(request, 'main/settings.html')


def tag_list(request):
    """List all tags with pagination and search"""
    search_query = request.GET.get('search', '').strip()
    page_number = request.GET.get('page', 1)
    
    tags = Tag.objects.all()
    
    # Apply search filter
    if search_query:
        tags = tags.filter(name__icontains=search_query)
    
    # Pagination
    paginator = Paginator(tags, 10)  # 10 tags per page
    tags_page = paginator.get_page(page_number)
    
    context = {
        'tags': tags_page,
        'search_query': search_query,
        'is_htmx': request.headers.get('HX-Request') == 'true'
    }
    
    # Return partial template for HTMX requests
    if context['is_htmx']:
        return render(request, 'main/tags/list_partial.html', context)
    
    return render(request, 'main/tags/list.html', context)


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
    """Delete a tag (only if not in use) - direct deletion without confirmation"""
    tag = get_object_or_404(Tag, id=tag_id)
    
    # Calculate current usage
    tag.calculate_usage_count()
    
    # Only allow POST requests for deletion
    if request.method == 'POST':
        # Check if tag is in use
        if tag.usage_count > 0:
            messages.error(
                request, 
                f'Cannot delete tag "{tag.name}". It is currently used by {tag.usage_count} item(s)/task(s). '
                f'Please remove the tag from all items and tasks before deleting it.'
            )
            return redirect('main:tag_list')
        
        # Tag not in use, delete it
        tag_name = tag.name
        tag.delete()
        messages.success(request, f'Tag "{tag_name}" deleted successfully!')
        return redirect('main:tag_list')
    
    # GET request not allowed - redirect to tag list
    messages.warning(request, 'Invalid delete request. Please use the delete button.')
    return redirect('main:tag_list')


def tag_calculate_usage(request, tag_id):
    """Calculate and update the usage count for a specific tag"""
    tag = get_object_or_404(Tag, id=tag_id)
    count = tag.calculate_usage_count()
    
    if request.headers.get('HX-Request'):
        # Return HTML fragment for HTMX
        return render(request, 'main/tags/usage_count.html', {'tag': tag})
    
    messages.success(request, f'Usage count for tag "{tag.name}" updated: {count}')
    return redirect('main:tag_list')


def tag_calculate_all_usage(request):
    """Calculate and update usage counts for all tags"""
    tags = Tag.objects.all()
    for tag in tags:
        tag.calculate_usage_count()
    
    messages.success(request, 'Usage counts updated for all tags!')
    return redirect('main:tag_list')


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


def client_list(request):
    """List all clients"""
    clients = Client.objects.all()
    return render(request, 'main/clients/list.html', {'clients': clients})


def client_create(request):
    """Create a new client"""
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if name:
            try:
                client = Client(name=name)
                client.save()
                messages.success(request, f'Client "{name}" created successfully!')
                return redirect('main:client_list')
            except Exception as e:
                messages.error(request, f'Error creating client: {str(e)}')
        else:
            messages.error(request, 'Client name is required.')
    
    return render(request, 'main/clients/form.html')


def client_edit(request, client_id):
    """Edit an existing client"""
    client = get_object_or_404(Client, id=client_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if name:
            try:
                client.name = name
                client.save()
                messages.success(request, f'Client "{name}" updated successfully!')
                return redirect('main:client_list')
            except Exception as e:
                messages.error(request, f'Error updating client: {str(e)}')
        else:
            messages.error(request, 'Client name is required.')
    
    return render(request, 'main/clients/form.html', {'client': client})


def client_delete(request, client_id):
    """Delete a client"""
    client = get_object_or_404(Client, id=client_id)
    
    if request.method == 'POST':
        client_name = client.name
        client.delete()
        messages.success(request, f'Client "{client_name}" deleted successfully!')
        return redirect('main:client_list')
    
    return render(request, 'main/clients/delete.html', {'client': client})


def settings_list(request):
    """List all settings"""
    settings = Settings.objects.all()
    return render(request, 'main/settings_list.html', {'settings': settings})


def settings_create(request):
    """Create a new settings entry"""
    if request.method == 'POST':
        settings = Settings.objects.create(
            openai_api_enabled=request.POST.get('openai_api_enabled') == 'on',
            openai_api_key=request.POST.get('openai_api_key', ''),
            openai_org_id=request.POST.get('openai_org_id', ''),
            openai_default_model=request.POST.get('openai_default_model', 'gpt-4'),
            openai_api_base_url=request.POST.get('openai_api_base_url', 'https://api.openai.com/v1'),
            openai_api_timeout=int(request.POST.get('openai_api_timeout') or 30),
            openai_max_tokens=int(request.POST.get('openai_max_tokens') or 10000),
            client_id=request.POST.get('client_id', ''),
            client_secret=request.POST.get('client_secret', ''),
            tenant_id=request.POST.get('tenant_id', ''),
            github_api_enabled=request.POST.get('github_api_enabled') == 'on',
            github_token=request.POST.get('github_token', ''),
            github_api_base_url=request.POST.get('github_api_base_url', 'https://api.github.com'),
            github_default_owner=request.POST.get('github_default_owner', ''),
            github_default_repo=request.POST.get('github_default_repo', ''),
            github_copilot_username=request.POST.get('github_copilot_username', ''),
            chroma_api_key=request.POST.get('chroma_api_key', ''),
            chroma_database=request.POST.get('chroma_database', ''),
            chroma_tenant=request.POST.get('chroma_tenant', ''),
            kigate_api_enabled=request.POST.get('kigate_api_enabled') == 'on',
            kigate_api_base_url=request.POST.get('kigate_api_base_url', 'http://localhost:8000'),
            kigate_api_token=request.POST.get('kigate_api_token', ''),
            kigate_api_timeout=int(request.POST.get('kigate_api_timeout') or 30),
            kigate_max_tokens=int(request.POST.get('kigate_max_tokens') or 10000),
            weaviate_cloud_enabled=request.POST.get('weaviate_cloud_enabled') == 'on',
            weaviate_url=request.POST.get('weaviate_url', ''),
            weaviate_api_key=request.POST.get('weaviate_api_key', ''),
            max_tags_per_idea=int(request.POST.get('max_tags_per_idea') or 5),
            graph_api_enabled=request.POST.get('graph_api_enabled') == 'on',
            sharepoint_site_id=request.POST.get('sharepoint_site_id', ''),
            default_mail_sender=request.POST.get('default_mail_sender', ''),
            ms_sso_enabled=request.POST.get('ms_sso_enabled') == 'on',
            ms_sso_client_id=request.POST.get('ms_sso_client_id', ''),
            ms_sso_tenant_id=request.POST.get('ms_sso_tenant_id', ''),
            ms_sso_client_secret=request.POST.get('ms_sso_client_secret', ''),
            zammad_enabled=request.POST.get('zammad_enabled') == 'on',
            zammad_api_url=request.POST.get('zammad_api_url', ''),
            zammad_api_token=request.POST.get('zammad_api_token', ''),
            zammad_groups=request.POST.get('zammad_groups', ''),
            zammad_sync_interval=int(request.POST.get('zammad_sync_interval') or 15),
            google_pse_enabled=request.POST.get('google_pse_enabled') == 'on',
            google_search_api_key=request.POST.get('google_search_api_key', ''),
            google_search_cx=request.POST.get('google_search_cx', ''),
            teams_enabled=request.POST.get('teams_enabled') == 'on',
            teams_team_id=request.POST.get('teams_team_id', ''),
            team_welcome_post=request.POST.get('team_welcome_post', ''),
        )
        messages.success(request, 'Settings created successfully!')
        return redirect('main:settings_list')
    
    return render(request, 'main/settings_form.html', {'action': 'Create'})


def settings_update(request, pk):
    """Update an existing settings entry"""
    settings = get_object_or_404(Settings, pk=pk)
    
    if request.method == 'POST':
        settings.openai_api_enabled = request.POST.get('openai_api_enabled') == 'on'
        settings.openai_api_key = request.POST.get('openai_api_key', '')
        settings.openai_org_id = request.POST.get('openai_org_id', '')
        settings.openai_default_model = request.POST.get('openai_default_model', 'gpt-4')
        settings.openai_api_base_url = request.POST.get('openai_api_base_url', 'https://api.openai.com/v1')
        settings.openai_api_timeout = int(request.POST.get('openai_api_timeout') or 30)
        settings.openai_max_tokens = int(request.POST.get('openai_max_tokens') or 10000)
        settings.client_id = request.POST.get('client_id', '')
        settings.client_secret = request.POST.get('client_secret', '')
        settings.tenant_id = request.POST.get('tenant_id', '')
        settings.github_api_enabled = request.POST.get('github_api_enabled') == 'on'
        settings.github_token = request.POST.get('github_token', '')
        settings.github_api_base_url = request.POST.get('github_api_base_url', 'https://api.github.com')
        settings.github_default_owner = request.POST.get('github_default_owner', '')
        settings.github_default_repo = request.POST.get('github_default_repo', '')
        settings.github_copilot_username = request.POST.get('github_copilot_username', '')
        settings.chroma_api_key = request.POST.get('chroma_api_key', '')
        settings.chroma_database = request.POST.get('chroma_database', '')
        settings.chroma_tenant = request.POST.get('chroma_tenant', '')
        settings.kigate_api_enabled = request.POST.get('kigate_api_enabled') == 'on'
        settings.kigate_api_base_url = request.POST.get('kigate_api_base_url', 'http://localhost:8000')
        settings.kigate_api_token = request.POST.get('kigate_api_token', '')
        settings.kigate_api_timeout = int(request.POST.get('kigate_api_timeout') or 30)
        settings.kigate_max_tokens = int(request.POST.get('kigate_max_tokens') or 10000)
        settings.weaviate_cloud_enabled = request.POST.get('weaviate_cloud_enabled') == 'on'
        settings.weaviate_url = request.POST.get('weaviate_url', '')
        settings.weaviate_api_key = request.POST.get('weaviate_api_key', '')
        settings.max_tags_per_idea = int(request.POST.get('max_tags_per_idea') or 5)
        settings.graph_api_enabled = request.POST.get('graph_api_enabled') == 'on'
        settings.sharepoint_site_id = request.POST.get('sharepoint_site_id', '')
        settings.default_mail_sender = request.POST.get('default_mail_sender', '')
        settings.ms_sso_enabled = request.POST.get('ms_sso_enabled') == 'on'
        settings.ms_sso_client_id = request.POST.get('ms_sso_client_id', '')
        settings.ms_sso_tenant_id = request.POST.get('ms_sso_tenant_id', '')
        settings.ms_sso_client_secret = request.POST.get('ms_sso_client_secret', '')
        settings.zammad_enabled = request.POST.get('zammad_enabled') == 'on'
        settings.zammad_api_url = request.POST.get('zammad_api_url', '')
        settings.zammad_api_token = request.POST.get('zammad_api_token', '')
        settings.zammad_groups = request.POST.get('zammad_groups', '')
        settings.zammad_sync_interval = int(request.POST.get('zammad_sync_interval') or 15)
        settings.google_pse_enabled = request.POST.get('google_pse_enabled') == 'on'
        settings.google_search_api_key = request.POST.get('google_search_api_key', '')
        settings.google_search_cx = request.POST.get('google_search_cx', '')
        settings.teams_enabled = request.POST.get('teams_enabled') == 'on'
        settings.teams_team_id = request.POST.get('teams_team_id', '')
        settings.team_welcome_post = request.POST.get('team_welcome_post', '')
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
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
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
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        role = request.POST.get('role', 'user')
        is_active = request.POST.get('is_active') == 'on'
        ai_classification = request.POST.get('ai_classification', '').strip()
        client_id = request.POST.get('client', '').strip()
        
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
                        first_name=first_name,
                        last_name=last_name,
                        role=role,
                        is_active=is_active,
                        ai_classification=ai_classification
                    )
                    
                    if client_id:
                        user.client_id = client_id
                    
                    user.set_password(password)
                    user.save()
                    messages.success(request, f'User "{username}" created successfully!')
                    return redirect('main:user_list')
                except Exception as e:
                    messages.error(request, f'Error creating user: {str(e)}')
    
    context = {
        'role_choices': User.ROLE_CHOICES,
        'clients': Client.objects.all(),
    }
    return render(request, 'main/users/user_create.html', context)


def user_edit(request, user_id):
    """Edit an existing user"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', user.role)
        is_active = request.POST.get('is_active') == 'on'
        ai_classification = request.POST.get('ai_classification', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        client_id = request.POST.get('client', '').strip()
        
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
                        'clients': Client.objects.all(),
                    }
                    return render(request, 'main/users/user_edit.html', context)
            
            try:
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.role = role
                user.is_active = is_active
                user.ai_classification = ai_classification
                
                if client_id:
                    user.client_id = client_id
                else:
                    user.client = None
                
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
        'clients': Client.objects.all(),
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
    """List all items"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    section_filter = request.GET.get('section', '')
    search_query = request.GET.get('search', '').strip()
    
    # Base query - show all items
    items = Item.objects.all()
    
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
    """Tile view for items with search and filter functionality"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    section_filter = request.GET.get('section', '')
    search_query = request.GET.get('search', '').strip()
    
    # Base query - show all items
    items = Item.objects.all()
    
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
    
    # Order by creation date (most recent first)
    items = items.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(items, 24)  # 24 items per page (4 columns x 6 rows)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get all sections and status choices for filters
    sections = Section.objects.all()
    status_choices = Item.STATUS_CHOICES
    
    # Get settings for Teams integration
    settings = Settings.objects.first()
    
    context = {
        'items': page_obj,
        'sections': sections,
        'status_choices': status_choices,
        'status_filter': status_filter,
        'section_filter': section_filter,
        'search_query': search_query,
        'settings': settings,
    }
    
    return render(request, 'main/items/kanban.html', context)



def item_detail(request, item_id):
    """Detail view for a single item"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get item
    item = get_object_or_404(Item, id=item_id)
    
    # Handle POST request for updating the item
    selected_tags_payload = list(item.tags.values('id', 'name', 'color'))
    selected_clients_payload = list(item.clients.values('id', 'name'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_repo = request.POST.get('github_repo', '').strip()
        section_id = request.POST.get('section')
        status = request.POST.get('status', item.status)
        tag_values = request.POST.getlist('tags')
        client_values = request.POST.getlist('clients')
        parent_id = request.POST.get('parent')
        is_template = request.POST.get('is_template') == 'on'
        inherit_context = request.POST.get('inherit_context') == 'on'

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
            selected_clients_payload = _build_selected_clients_payload(client_values)
        else:
            try:
                item.title = title
                item.description = description
                item.github_repo = github_repo
                item.status = status
                item.is_template = is_template
                item.inherit_context = inherit_context

                if section_id:
                    item.section_id = section_id
                else:
                    item.section = None
                
                if parent_id:
                    item.parent_id = parent_id
                else:
                    item.parent = None

                item.save()

                # Update tags
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    item.tags.set(resolved_tags)
                else:
                    item.tags.clear()

                # Update clients
                resolved_clients = _resolve_client_values(client_values)
                if resolved_clients:
                    item.clients.set(resolved_clients)
                else:
                    item.clients.clear()

                # Sync update to Weaviate
                sync_service = None
                try:
                    from core.services.weaviate_sync_service import WeaviateItemSyncService
                    sync_service = WeaviateItemSyncService()
                    sync_service.sync_update(item)
                except Exception as sync_error:
                    # Log error but don't fail the item update
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Weaviate sync failed for item {item.id}: {str(sync_error)}')
                finally:
                    if sync_service:
                        sync_service.close()

                messages.success(request, f'Item "{title}" updated successfully!')
                selected_tags_payload = list(item.tags.values('id', 'name', 'color'))
                selected_clients_payload = list(item.clients.values('id', 'name'))

            except Exception as e:
                messages.error(request, f'Error updating item: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
                selected_clients_payload = _build_selected_clients_payload(client_values)
    
    # Get show_completed filter parameter (default: false - don't show completed)
    show_completed = request.GET.get('show_completed', 'false').lower() == 'true'
    
    # Get search query parameter
    search_query = request.GET.get('search', '').strip()
    
    # Get page parameter
    page_number = request.GET.get('page', 1)
    
    # Get related tasks
    tasks = item.tasks.all().select_related('assigned_to', 'created_by').prefetch_related('tags')
    
    # Filter by completion status
    if not show_completed:
        # Show only non-completed tasks (default)
        tasks = tasks.exclude(status='done')
    # else: show all tasks (both completed and non-completed)
    
    # Filter by search query (search in title and description)
    if search_query:
        from django.db.models import Q
        tasks = tasks.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )
    
    # Paginate tasks (10 per page)
    paginator = Paginator(tasks, 10)
    tasks_page = paginator.get_page(page_number)
    
    # Get all sections, tags, clients, items, and status choices for the form
    sections = Section.objects.all()
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    all_clients = list(Client.objects.values('id', 'name'))
    all_items = Item.objects.exclude(id=item.id).order_by('title')  # Exclude current item
    status_choices = Item.STATUS_CHOICES

    from django.utils import timezone
    from datetime import timedelta
    from main.models import Settings
    
    today = timezone.now().date()
    week_from_today = today + timedelta(days=7)
    
    # Get settings for GitHub button state
    settings = Settings.objects.first()
    
    context = {
        'item': item,
        'tasks': tasks_page,
        'sections': sections,
        'all_tags': all_tags,
        'all_clients': all_clients,
        'all_items': all_items,
        'selected_tags': selected_tags_payload,
        'selected_clients': selected_clients_payload,
        'status_choices': status_choices,
        'show_completed': show_completed,
        'search_query': search_query,
        'today': today,
        'week_from_today': week_from_today,
        'settings': settings,
    }
    
    # If HTMX request, return only the partial template
    if request.headers.get('HX-Request'):
        return render(request, 'main/items/_item_tasks_table.html', context)
    
    return render(request, 'main/items/detail.html', context)


def item_create(request):
    """Create a new item"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    selected_tags_payload = []
    selected_clients_payload = []

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_repo = request.POST.get('github_repo', '').strip()
        section_id = request.POST.get('section')
        status = request.POST.get('status', 'new')
        tag_values = request.POST.getlist('tags')
        client_values = request.POST.getlist('clients')
        parent_id = request.POST.get('parent')
        is_template = request.POST.get('is_template') == 'on'
        inherit_context = request.POST.get('inherit_context') == 'on'

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
            selected_clients_payload = _build_selected_clients_payload(client_values)
        else:
            try:
                # Create item
                item = Item(
                    title=title,
                    description=description,
                    github_repo=github_repo,
                    status=status,
                    created_by=user,
                    is_template=is_template,
                    inherit_context=inherit_context
                )

                if section_id:
                    item.section_id = section_id
                
                if parent_id:
                    item.parent_id = parent_id

                item.save()

                # Add tags
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    item.tags.set(resolved_tags)

                # Add clients
                resolved_clients = _resolve_client_values(client_values)
                if resolved_clients:
                    item.clients.set(resolved_clients)

                # Sync to Weaviate
                sync_service = None
                try:
                    from core.services.weaviate_sync_service import WeaviateItemSyncService
                    sync_service = WeaviateItemSyncService()
                    sync_service.sync_create(item)
                except Exception as sync_error:
                    # Log error but don't fail the item creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Weaviate sync failed for item {item.id}: {str(sync_error)}')
                finally:
                    if sync_service:
                        sync_service.close()

                messages.success(request, f'Item "{title}" created successfully!')
                return redirect('main:item_detail', item_id=item.id)

            except Exception as e:
                messages.error(request, f'Error creating item: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
                selected_clients_payload = _build_selected_clients_payload(client_values)
    
    # Get all sections, tags, clients, items and status choices for the form
    sections = Section.objects.all()
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    all_clients = list(Client.objects.values('id', 'name'))
    all_items = Item.objects.all().order_by('title')
    status_choices = Item.STATUS_CHOICES

    context = {
        'sections': sections,
        'all_tags': all_tags,
        'all_clients': all_clients,
        'all_items': all_items,
        'selected_tags': selected_tags_payload,
        'selected_clients': selected_clients_payload,
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
    
    # Get item
    item = get_object_or_404(Item, id=item_id)
    
    selected_tags_payload = list(item.tags.values('id', 'name', 'color'))
    selected_clients_payload = list(item.clients.values('id', 'name'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        github_repo = request.POST.get('github_repo', '').strip()
        section_id = request.POST.get('section')
        status = request.POST.get('status', item.status)
        tag_values = request.POST.getlist('tags')
        client_values = request.POST.getlist('clients')
        parent_id = request.POST.get('parent')
        is_template = request.POST.get('is_template') == 'on'
        inherit_context = request.POST.get('inherit_context') == 'on'

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
            selected_clients_payload = _build_selected_clients_payload(client_values)
        else:
            try:
                item.title = title
                item.description = description
                item.github_repo = github_repo
                item.status = status
                item.is_template = is_template
                item.inherit_context = inherit_context

                if section_id:
                    item.section_id = section_id
                else:
                    item.section = None
                
                if parent_id:
                    item.parent_id = parent_id
                else:
                    item.parent = None

                item.save()

                # Update tags
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    item.tags.set(resolved_tags)
                else:
                    item.tags.clear()

                # Update clients
                resolved_clients = _resolve_client_values(client_values)
                if resolved_clients:
                    item.clients.set(resolved_clients)
                else:
                    item.clients.clear()

                # Sync update to Weaviate
                sync_service = None
                try:
                    from core.services.weaviate_sync_service import WeaviateItemSyncService
                    sync_service = WeaviateItemSyncService()
                    sync_service.sync_update(item)
                except Exception as sync_error:
                    # Log error but don't fail the item update
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Weaviate sync failed for item {item.id}: {str(sync_error)}')
                finally:
                    if sync_service:
                        sync_service.close()

                messages.success(request, f'Item "{title}" updated successfully!')
                return redirect('main:item_detail', item_id=item.id)

            except Exception as e:
                messages.error(request, f'Error updating item: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
                selected_clients_payload = _build_selected_clients_payload(client_values)
    
    # Get all sections, tags, clients, items and status choices for the form
    sections = Section.objects.all()
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    all_clients = list(Client.objects.values('id', 'name'))
    all_items = Item.objects.exclude(id=item.id).order_by('title')  # Exclude current item to prevent self-reference
    status_choices = Item.STATUS_CHOICES

    context = {
        'item': item,
        'sections': sections,
        'all_tags': all_tags,
        'all_clients': all_clients,
        'all_items': all_items,
        'selected_tags': selected_tags_payload,
        'selected_clients': selected_clients_payload,
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
    
    # Get item
    item = get_object_or_404(Item, id=item_id)
    
    if request.method == 'POST':
        item_title = item.title
        item_id_str = str(item.id)
        item.delete()
        
        # Sync delete to Weaviate
        sync_service = None
        try:
            from core.services.weaviate_sync_service import WeaviateItemSyncService
            sync_service = WeaviateItemSyncService()
            sync_service.sync_delete(item_id_str)
        except Exception as sync_error:
            # Log error but don't fail the item deletion
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'Weaviate sync failed for item {item_id_str}: {str(sync_error)}')
        finally:
            if sync_service:
                sync_service.close()
        
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
    
    # Get item
    item = get_object_or_404(Item, id=item_id)
    
    # Get show_completed filter parameter (default: false - don't show completed)
    show_completed = request.GET.get('show_completed', 'false').lower() == 'true'
    
    # Get tasks for this item
    tasks = item.tasks.select_related('assigned_to', 'created_by').prefetch_related('tags')
    
    # Filter by completion status
    if not show_completed:
        # Show only non-completed tasks (default)
        tasks = tasks.exclude(status='done')
    # else: show all tasks (both completed and non-completed)
    
    # Sort tasks by status priority
    status_order = {'new': 1, 'working': 2, 'review': 3, 'ready': 4, 'done': 5}
    tasks = sorted(tasks, key=lambda t: status_order.get(t.status, 99))
    
    context = {
        'item': item,
        'tasks': tasks,
        'show_completed': show_completed,
    }
    
    return render(request, 'main/tasks/list.html', context)


def task_detail(request, task_id):
    """Detail view for a single task"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get task
    task = get_object_or_404(Task, id=task_id)

    selected_tags_payload = list(task.tags.values('id', 'name', 'color'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', task.status)
        milestone_id = request.POST.get('milestone', '').strip()
        tag_values = request.POST.getlist('tags')
        requester_id = request.POST.get('requester', None)

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
        else:
            try:
                # Get requester if provided
                requester = None
                if requester_id:
                    try:
                        requester = User.objects.get(id=requester_id)
                    except User.DoesNotExist:
                        pass
                
                previous_status = task.status
                task.title = title
                task.description = description
                task.status = status
                task.requester = requester
                
                # Set milestone
                if milestone_id:
                    try:
                        milestone = Milestone.objects.get(id=milestone_id, item=task.item)
                        task.milestone = milestone
                    except Milestone.DoesNotExist:
                        task.milestone = None
                else:
                    task.milestone = None

                if status == 'done' and previous_status != 'done':
                    task.mark_as_done()
                else:
                    task.save()

                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    task.tags.set(resolved_tags)
                else:
                    task.tags.clear()

                # Sync update to Weaviate
                sync_service = None
                try:
                    from core.services.weaviate_task_sync_service import WeaviateTaskSyncService
                    sync_service = WeaviateTaskSyncService()
                    sync_service.sync_update(task)
                except Exception as sync_error:
                    # Log error but don't fail the task update
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Weaviate sync failed for task {task.id}: {str(sync_error)}')
                finally:
                    if sync_service:
                        sync_service.close()

                messages.success(request, f'Task "{title}" updated successfully!')
                selected_tags_payload = list(task.tags.values('id', 'name', 'color'))

            except Exception as e:
                messages.error(request, f'Error updating task: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)

    # Get all tags and status choices
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    status_choices = Task.STATUS_CHOICES
    
    # Get all milestones for the task's item
    milestones = task.item.milestones.all() if task.item else []
    
    # Get all active users for requester selection
    all_users = User.objects.filter(is_active=True).order_by('username')
    
    # Get settings for Google PSE configuration
    settings = Settings.objects.first()

    context = {
        'task': task,
        'all_tags': all_tags,
        'selected_tags': selected_tags_payload,
        'status_choices': status_choices,
        'milestones': milestones,
        'all_users': all_users,
        'settings': settings,
    }

    return render(request, 'main/tasks/detail.html', context)


def task_create(request, item_id):
    """Create a new task"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get item
    item = get_object_or_404(Item, id=item_id)
    
    selected_tags_payload = list(item.tags.values('id', 'name', 'color'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', 'new')
        milestone_id = request.POST.get('milestone', '').strip()
        tag_values = request.POST.getlist('tags')
        requester_id = request.POST.get('requester', None)

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
        else:
            try:
                # Get requester if provided
                requester = None
                if requester_id:
                    try:
                        requester = User.objects.get(id=requester_id)
                    except User.DoesNotExist:
                        pass
                
                # Create task
                task = Task(
                    title=title,
                    description=description,
                    status=status,
                    item=item,
                    created_by=user,
                    assigned_to=user,
                    requester=requester
                )
                
                # Set milestone if provided
                if milestone_id:
                    try:
                        milestone = Milestone.objects.get(id=milestone_id, item=item)
                        task.milestone = milestone
                    except Milestone.DoesNotExist:
                        pass
                
                task.save()

                # Add tags
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    task.tags.set(resolved_tags)

                # Sync to Weaviate
                sync_service = None
                try:
                    from core.services.weaviate_task_sync_service import WeaviateTaskSyncService
                    sync_service = WeaviateTaskSyncService()
                    sync_service.sync_create(task)
                except Exception as sync_error:
                    # Log error but don't fail the task creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Weaviate sync failed for task {task.id}: {str(sync_error)}')
                finally:
                    if sync_service:
                        sync_service.close()

                messages.success(request, f'Task "{title}" created successfully!')
                return redirect('main:task_detail', task_id=task.id)

            except Exception as e:
                messages.error(request, f'Error creating task: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
    
    # Get all tags and milestones for the form
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    milestones = item.milestones.all()
    status_choices = Task.STATUS_CHOICES
    
    # Get all active users for requester selection
    all_users = User.objects.filter(is_active=True).order_by('username')

    context = {
        'item': item,
        'all_tags': all_tags,
        'selected_tags': selected_tags_payload,
        'status_choices': status_choices,
        'milestones': milestones,
        'all_users': all_users,
    }
    
    return render(request, 'main/tasks/form.html', context)


def task_edit(request, task_id):
    """Edit an existing task"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get task
    task = get_object_or_404(Task, id=task_id)
    
    selected_tags_payload = list(task.tags.values('id', 'name', 'color'))

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', task.status)
        milestone_id = request.POST.get('milestone', '').strip()
        tag_values = request.POST.getlist('tags')
        requester_id = request.POST.get('requester', None)

        if not title:
            messages.error(request, 'Title is required.')
            selected_tags_payload = _build_selected_tags_payload(tag_values)
        else:
            try:
                # Get requester if provided
                requester = None
                if requester_id:
                    try:
                        requester = User.objects.get(id=requester_id)
                    except User.DoesNotExist:
                        pass
                
                previous_status = task.status
                task.title = title
                task.description = description
                task.status = status
                
                # Set milestone
                if milestone_id:
                    try:
                        milestone = Milestone.objects.get(id=milestone_id, item=task.item)
                        task.milestone = milestone
                    except Milestone.DoesNotExist:
                        task.milestone = None
                else:
                    task.milestone = None
                task.requester = requester

                # Mark as done if status changed to done
                if status == 'done' and previous_status != 'done':
                    task.save()
                    task.mark_as_done()
                else:
                    task.save()

                # Update tags
                resolved_tags = _resolve_tag_values(tag_values)
                if resolved_tags:
                    task.tags.set(resolved_tags)
                else:
                    task.tags.clear()

                # Sync update to Weaviate
                sync_service = None
                try:
                    from core.services.weaviate_task_sync_service import WeaviateTaskSyncService
                    sync_service = WeaviateTaskSyncService()
                    sync_service.sync_update(task)
                except Exception as sync_error:
                    # Log error but don't fail the task update
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f'Weaviate sync failed for task {task.id}: {str(sync_error)}')
                finally:
                    if sync_service:
                        sync_service.close()

                messages.success(request, f'Task "{title}" updated successfully!')
                return redirect('main:task_detail', task_id=task.id)

            except Exception as e:
                messages.error(request, f'Error updating task: {str(e)}')
                selected_tags_payload = _build_selected_tags_payload(tag_values)
    
    # Get all tags and milestones for the form
    all_tags = list(Tag.objects.values('id', 'name', 'color'))
    milestones = task.item.milestones.all() if task.item else []
    status_choices = Task.STATUS_CHOICES
    
    # Get all active users for requester selection
    all_users = User.objects.filter(is_active=True).order_by('username')

    context = {
        'task': task,
        'all_tags': all_tags,
        'selected_tags': selected_tags_payload,
        'status_choices': status_choices,
        'milestones': milestones,
        'all_users': all_users,
    }
    
    return render(request, 'main/tasks/form.html', context)


def task_delete(request, task_id):
    """Delete a task"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get task
    task = get_object_or_404(Task, id=task_id)
    
    item = task.item
    
    if request.method == 'POST':
        task_title = task.title
        task_id_str = str(task.id)
        task.delete()
        
        # Sync delete to Weaviate
        sync_service = None
        try:
            from core.services.weaviate_task_sync_service import WeaviateTaskSyncService
            sync_service = WeaviateTaskSyncService()
            sync_service.sync_delete(task_id_str)
        except Exception as sync_error:
            # Log error but don't fail the task deletion
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'Weaviate sync failed for task {task_id_str}: {str(sync_error)}')
        finally:
            if sync_service:
                sync_service.close()
        
        messages.success(request, f'Task "{task_title}" deleted successfully!')
        return redirect('main:item_detail', item_id=item.id)
    
    context = {'task': task}
    return render(request, 'main/tasks/delete.html', context)


def task_overview(request):
    """Global task overview - shows all tasks"""
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
    
    # Base query - show all tasks
    tasks = Task.objects.all()
    
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
        count = Task.objects.filter(status=status_key).count()
        status_counts[status_key] = count
    
    # Pagination
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get all items for filter dropdown
    items = Item.objects.all()
    
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
    
    # If HTMX request, return only the partial template
    if request.headers.get('HX-Request'):
        return render(request, 'main/tasks/_task_table.html', context)
    
    return render(request, 'main/tasks/overview.html', context)


def tags_network_view(request):
    """Tags network graph visualization view"""
    return render(request, 'main/tags/network.html')


def milestone_create(request, item_id):
    """Create a new milestone for an item"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    
    # Get item
    item = get_object_or_404(Item, id=item_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        due_date = request.POST.get('due_date', '').strip()
        status = request.POST.get('status', 'planned').strip()
        summary = request.POST.get('summary', '').strip()
        
        if not name:
            messages.error(request, 'Name is required.')
        elif not due_date:
            messages.error(request, 'Due date is required.')
        else:
            try:
                # Create milestone
                milestone = Milestone(
                    name=name,
                    description=description,
                    due_date=due_date,
                    status=status,
                    item=item,
                    summary=summary
                )
                milestone.save()
                
                # Sync to Weaviate
                try:
                    from core.services.milestone_knowledge_service import MilestoneKnowledgeService
                    service = MilestoneKnowledgeService()
                    service.sync_to_weaviate(milestone)
                except Exception as weaviate_error:
                    logger.warning(f'Failed to sync milestone to Weaviate: {str(weaviate_error)}')
                    # Don't fail the whole operation if Weaviate sync fails
                
                messages.success(request, f'Milestone "{name}" created successfully!')
                return redirect('main:item_detail', item_id=item_id)
            except Exception as e:
                messages.error(request, f'Error creating milestone: {str(e)}')
    
    context = {
        'item': item,
        'status_choices': Milestone.STATUS_CHOICES,
    }
    
    return render(request, 'main/milestones/form.html', context)


def milestone_edit(request, milestone_id):
    """Edit an existing milestone"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    milestone = get_object_or_404(Milestone, id=milestone_id)
    item = milestone.item
    
    # Check ownership unless admin
    if user.role != 'admin' and item.created_by != user:
        messages.error(request, 'You do not have permission to edit this milestone.')
        return redirect('main:item_detail', item_id=item.id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        due_date = request.POST.get('due_date', '').strip()
        status = request.POST.get('status', 'planned').strip()
        summary = request.POST.get('summary', '').strip()
        
        if not name:
            messages.error(request, 'Name is required.')
        elif not due_date:
            messages.error(request, 'Due date is required.')
        else:
            try:
                milestone.name = name
                milestone.description = description
                milestone.due_date = due_date
                milestone.status = status
                
                # Build summary with task list
                summary_parts = []
                if summary:
                    summary_parts.append(summary)
                
                # Add task list if there are tasks
                tasks = milestone.tasks.all()
                if tasks.exists():
                    task_titles = [f"- {task.title}" for task in tasks]
                    task_list = "\n\nAufgaben:\n" + "\n".join(task_titles)
                    summary_parts.append(task_list)
                
                milestone.summary = "\n\n".join(summary_parts) if summary_parts else summary
                milestone.save()
                
                # Sync to Weaviate
                try:
                    from core.services.milestone_knowledge_service import MilestoneKnowledgeService
                    service = MilestoneKnowledgeService()
                    service.sync_to_weaviate(milestone)
                except Exception as weaviate_error:
                    logger.warning(f'Failed to sync milestone to Weaviate: {str(weaviate_error)}')
                    # Don't fail the whole operation if Weaviate sync fails
                
                messages.success(request, f'Milestone "{name}" updated successfully!')
                return redirect('main:item_detail', item_id=item.id)
            except Exception as e:
                messages.error(request, f'Error updating milestone: {str(e)}')
    
    context = {
        'milestone': milestone,
        'item': item,
        'status_choices': Milestone.STATUS_CHOICES,
    }
    
    return render(request, 'main/milestones/form.html', context)


def milestone_delete(request, milestone_id):
    """Delete a milestone"""
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    milestone = get_object_or_404(Milestone, id=milestone_id)
    item = milestone.item
    
    # Check ownership unless admin
    if user.role != 'admin' and item.created_by != user:
        messages.error(request, 'You do not have permission to delete this milestone.')
        return redirect('main:item_detail', item_id=item.id)
    
    if request.method == 'POST':
        milestone_name = milestone.name
        milestone.delete()
        messages.success(request, f'Milestone "{milestone_name}" deleted successfully!')
        return redirect('main:item_detail', item_id=item.id)
    
    context = {
        'milestone': milestone,
        'item': item,
    }
    
    return render(request, 'main/milestones/delete.html', context)


def milestone_detail(request, milestone_id):
    """Show detailed view of a milestone with tabs for Summary, Tasks, and Context"""
    from datetime import date, timedelta
    
    # Get current user from session
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('main:login')
    
    user = get_object_or_404(User, id=user_id)
    milestone = get_object_or_404(Milestone, id=milestone_id)
    item = milestone.item
    
    # Check ownership unless admin
    if user.role != 'admin' and item.created_by != user:
        messages.error(request, 'You do not have permission to view this milestone.')
        return redirect('main:item_detail', item_id=item.id)
    
    # Calculate some helper dates for the template
    today = date.today()
    week_from_today = today + timedelta(days=7)
    
    # Count analyzed context objects
    analyzed_count = milestone.context_objects.filter(analyzed=True).count()
    
    context = {
        'milestone': milestone,
        'today': today,
        'week_from_today': week_from_today,
        'analyzed_count': analyzed_count,
    }
    
    return render(request, 'main/milestones/detail.html', context)

