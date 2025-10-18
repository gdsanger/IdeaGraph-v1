from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .models import Section


def home(request):
    """Home page view"""
    return render(request, 'main/home.html')


def section_list(request):
    """List all sections with CRUD operations"""
    sections = Section.objects.all()
    return render(request, 'main/section_list.html', {'sections': sections})


def section_create(request):
    """Create a new section"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            try:
                Section.objects.create(name=name)
                messages.success(request, f'Section "{name}" created successfully.')
                return redirect('main:section_list')
            except Exception as e:
                messages.error(request, f'Error creating section: {str(e)}')
        else:
            messages.error(request, 'Section name cannot be empty.')
    return render(request, 'main/section_form.html', {'action': 'Create'})


def section_update(request, pk):
    """Update an existing section"""
    section = get_object_or_404(Section, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            try:
                section.name = name
                section.save()
                messages.success(request, f'Section "{name}" updated successfully.')
                return redirect('main:section_list')
            except Exception as e:
                messages.error(request, f'Error updating section: {str(e)}')
        else:
            messages.error(request, 'Section name cannot be empty.')
    return render(request, 'main/section_form.html', {'section': section, 'action': 'Update'})


def section_delete(request, pk):
    """Delete a section"""
    section = get_object_or_404(Section, pk=pk)
    if request.method == 'POST':
        name = section.name
        section.delete()
        messages.success(request, f'Section "{name}" deleted successfully.')
        return redirect('main:section_list')
    return render(request, 'main/section_confirm_delete.html', {'section': section})

