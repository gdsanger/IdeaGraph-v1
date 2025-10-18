from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from .models import Tag, Settings


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
@staff_member_required
def settings_list(request):
    """List all settings"""
    settings = Settings.objects.all()
    return render(request, 'main/settings_list.html', {'settings': settings})


@staff_member_required
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
            kigate_url=request.POST.get('kigate_url', ''),
            kigate_token=request.POST.get('kigate_token', ''),
            max_tags_per_idea=int(request.POST.get('max_tags_per_idea', 5)),
        )
        messages.success(request, 'Settings created successfully!')
        return redirect('main:settings_list')
    
    return render(request, 'main/settings_form.html', {'action': 'Create'})


@staff_member_required
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
        settings.kigate_url = request.POST.get('kigate_url', '')
        settings.kigate_token = request.POST.get('kigate_token', '')
        settings.max_tags_per_idea = int(request.POST.get('max_tags_per_idea', 5))
        settings.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('main:settings_list')
    
    return render(request, 'main/settings_form.html', {
        'settings': settings,
        'action': 'Update'
    })


@staff_member_required
def settings_delete(request, pk):
    """Delete a settings entry"""
    settings = get_object_or_404(Settings, pk=pk)
    
    if request.method == 'POST':
        settings.delete()
        messages.success(request, 'Settings deleted successfully!')
        return redirect('main:settings_list')
    
    return render(request, 'main/settings_confirm_delete.html', {'settings': settings})

