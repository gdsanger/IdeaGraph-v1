from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Tag


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

