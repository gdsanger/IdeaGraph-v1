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
    
    # Settings URLs
    path('settings/', views.settings_list, name='settings_list'),
    path('settings/create/', views.settings_create, name='settings_create'),
    path('settings/<uuid:pk>/update/', views.settings_update, name='settings_update'),
    path('settings/<uuid:pk>/delete/', views.settings_delete, name='settings_delete'),
]
