from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/tags/', views.tag_list, name='tag_list'),
    path('settings/tags/create/', views.tag_create, name='tag_create'),
    path('settings/tags/<uuid:tag_id>/edit/', views.tag_edit, name='tag_edit'),
    path('settings/tags/<uuid:tag_id>/delete/', views.tag_delete, name='tag_delete'),
    
    # Section URLs
    path('settings/sections/', views.section_list, name='section_list'),
    path('settings/sections/create/', views.section_create, name='section_create'),
    path('settings/sections/<uuid:section_id>/edit/', views.section_edit, name='section_edit'),
    path('settings/sections/<uuid:section_id>/delete/', views.section_delete, name='section_delete'),
    
    # Settings URLs
    path('settings/', views.settings_list, name='settings_list'),
    path('settings/create/', views.settings_create, name='settings_create'),
    path('settings/<uuid:pk>/update/', views.settings_update, name='settings_update'),
    path('settings/<uuid:pk>/delete/', views.settings_delete, name='settings_delete'),
]
