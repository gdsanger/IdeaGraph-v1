from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Settings


def home(request):
    """Home page view"""
    return render(request, 'main/home.html')


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

