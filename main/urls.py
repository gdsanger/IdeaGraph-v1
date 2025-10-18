from django.urls import path
from . import views, api_views

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
    path('admin/settings/', views.settings_list, name='settings_list'),
    path('admin/settings/create/', views.settings_create, name='settings_create'),
    path('admin/settings/<uuid:pk>/update/', views.settings_update, name='settings_update'),
    path('admin/settings/<uuid:pk>/delete/', views.settings_delete, name='settings_delete'),
    
    # User Management URLs
    path('admin/users/', views.user_list, name='user_list'),
    path('admin/users/create/', views.user_create, name='user_create'),
    path('admin/users/<uuid:user_id>/', views.user_detail, name='user_detail'),
    path('admin/users/<uuid:user_id>/edit/', views.user_edit, name='user_edit'),
    path('admin/users/<uuid:user_id>/delete/', views.user_delete, name='user_delete'),
    
    # API Authentication Endpoints
    path('api/auth/login', api_views.api_login, name='api_login'),
    path('api/auth/logout', api_views.api_logout, name='api_logout'),
    
    # API User Management Endpoints
    path('api/users', api_views.api_user_list, name='api_user_list'),
    path('api/users/create', api_views.api_user_create, name='api_user_create'),
    path('api/users/<uuid:user_id>', api_views.api_user_detail, name='api_user_detail'),
    path('api/users/<uuid:user_id>/update', api_views.api_user_update, name='api_user_update'),
    path('api/users/<uuid:user_id>/delete', api_views.api_user_delete, name='api_user_delete'),
    
    # Graph API Endpoints
    path('api/graph/sharepoint/files', api_views.api_graph_sharepoint_files, name='api_graph_sharepoint_files'),
    path('api/graph/sharepoint/upload', api_views.api_graph_sharepoint_upload, name='api_graph_sharepoint_upload'),
    path('api/graph/mail/send', api_views.api_graph_mail_send, name='api_graph_mail_send'),
    
    # GitHub API Endpoints
    path('api/github/repos', api_views.api_github_repos, name='api_github_repos'),
    path('api/github/create-issue', api_views.api_github_create_issue, name='api_github_create_issue'),
    path('api/github/issue/<str:owner>/<str:repo>/<int:issue_number>', api_views.api_github_get_issue, name='api_github_get_issue'),
    path('api/github/issues/<str:owner>/<str:repo>', api_views.api_github_list_issues, name='api_github_list_issues'),
    
    # KiGate API Endpoints
    path('api/kigate/agents', api_views.api_kigate_agents, name='api_kigate_agents'),
    path('api/kigate/execute', api_views.api_kigate_execute, name='api_kigate_execute'),
    path('api/kigate/agent/<str:agent_name>', api_views.api_kigate_agent_details, name='api_kigate_agent_details'),
]
