from django.urls import path
from . import views, api_views, auth_views

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    
    # Global Search
    path('search/', views.global_search_view, name='global_search'),
    
    # Authentication URLs
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('register/', auth_views.register_view, name='register'),
    path('forgot-password/', auth_views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/', auth_views.reset_password_view, name='reset_password'),
    path('change-password/', auth_views.change_password_view, name='change_password'),
    
    # Microsoft SSO URLs
    path('login/microsoft/', auth_views.ms_sso_login, name='ms_sso_login'),
    path('login/microsoft/callback/', auth_views.ms_sso_callback, name='ms_sso_callback'),
    
    path('settings/', views.settings_view, name='settings'),
    path('tags/', views.tags_network_view, name='tags_network'),
    path('settings/tags/', views.tag_list, name='tag_list'),
    path('settings/tags/create/', views.tag_create, name='tag_create'),
    path('settings/tags/<uuid:tag_id>/edit/', views.tag_edit, name='tag_edit'),
    path('settings/tags/<uuid:tag_id>/delete/', views.tag_delete, name='tag_delete'),
    path('settings/tags/<uuid:tag_id>/calculate-usage/', views.tag_calculate_usage, name='tag_calculate_usage'),
    path('settings/tags/calculate-all-usage/', views.tag_calculate_all_usage, name='tag_calculate_all_usage'),
    
    # Section URLs
    path('settings/sections/', views.section_list, name='section_list'),
    path('settings/sections/create/', views.section_create, name='section_create'),
    path('settings/sections/<uuid:section_id>/edit/', views.section_edit, name='section_edit'),
    path('settings/sections/<uuid:section_id>/delete/', views.section_delete, name='section_delete'),
    
    # Client URLs
    path('settings/clients/', views.client_list, name='client_list'),
    path('settings/clients/create/', views.client_create, name='client_create'),
    path('settings/clients/<uuid:client_id>/edit/', views.client_edit, name='client_edit'),
    path('settings/clients/<uuid:client_id>/delete/', views.client_delete, name='client_delete'),
    
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
    path('admin/users/<uuid:user_id>/send-password/', views.user_send_password, name='user_send_password'),
    
    # Item Management URLs
    path('items/', views.item_list, name='item_list'),
    path('items/kanban/', views.item_kanban, name='item_kanban'),
    path('items/create/', views.item_create, name='item_create'),
    path('items/<uuid:item_id>/', views.item_detail, name='item_detail'),
    path('items/<uuid:item_id>/edit/', views.item_edit, name='item_edit'),
    path('items/<uuid:item_id>/delete/', views.item_delete, name='item_delete'),
    
    # Item API Endpoints
    path('api/items/<uuid:item_id>/ai-enhance', api_views.api_item_ai_enhance, name='api_item_ai_enhance'),
    path('api/items/<uuid:item_id>/generate-title', api_views.api_item_generate_title, name='api_item_generate_title'),
    path('api/items/<uuid:item_id>/extract-tags', api_views.api_item_extract_tags, name='api_item_extract_tags'),
    path('api/items/<uuid:item_id>/optimize-description', api_views.api_item_optimize_description, name='api_item_optimize_description'),
    path('api/items/<uuid:item_id>/build-tasks', api_views.api_item_build_tasks, name='api_item_build_tasks'),
    path('api/items/<uuid:item_id>/check-similarity', api_views.api_item_check_similarity, name='api_item_check_similarity'),
    path('api/items/<uuid:item_id>/send-email', api_views.api_send_item_email, name='api_send_item_email'),
    path('api/items/<uuid:item_id>/create-teams-channel', api_views.create_teams_channel, name='api_create_teams_channel'),
    
    # Teams Integration URLs
    path('api/teams/poll', api_views.poll_teams_messages, name='api_poll_teams_messages'),
    path('api/teams/status', api_views.teams_integration_status, name='api_teams_integration_status'),
    
    # Task Management URLs
    path('items/<uuid:item_id>/tasks/', views.task_list, name='task_list'),
    path('items/<uuid:item_id>/tasks/create/', views.task_create, name='task_create'),
    path('tasks/<uuid:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/<uuid:task_id>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<uuid:task_id>/delete/', views.task_delete, name='task_delete'),
    
    # Global Task Overview
    path('admin/tasks/overview/', views.task_overview, name='task_overview'),
    
    # Milestone Management URLs
    path('items/<uuid:item_id>/milestones/create/', views.milestone_create, name='milestone_create'),
    path('milestones/<uuid:milestone_id>/', views.milestone_detail, name='milestone_detail'),
    path('milestones/<uuid:milestone_id>/edit/', views.milestone_edit, name='milestone_edit'),
    path('milestones/<uuid:milestone_id>/delete/', views.milestone_delete, name='milestone_delete'),
    
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
    path('api/github/sync-issues-to-tasks/<uuid:item_id>', api_views.api_github_sync_issues_to_tasks, name='api_github_sync_issues_to_tasks'),
    
    # KiGate API Endpoints
    path('api/kigate/agents', api_views.api_kigate_agents, name='api_kigate_agents'),
    path('api/kigate/execute', api_views.api_kigate_execute, name='api_kigate_execute'),
    path('api/kigate/agent/<str:agent_name>', api_views.api_kigate_agent_details, name='api_kigate_agent_details'),
    
    # OpenAI API Endpoints
    path('api/openai/query', api_views.api_openai_query, name='api_openai_query'),
    path('api/openai/models', api_views.api_openai_models, name='api_openai_models'),
    
    # Task API Endpoints
    path('api/tasks/<uuid:item_id>', api_views.api_tasks, name='api_tasks'),
    path('api/tasks/<uuid:task_id>/detail', api_views.api_task_detail, name='api_task_detail'),
    path('api/tasks/<uuid:task_id>/ai-enhance', api_views.api_task_ai_enhance, name='api_task_ai_enhance'),
    path('api/tasks/<uuid:task_id>/generate-title', api_views.api_task_generate_title, name='api_task_generate_title'),
    path('api/tasks/<uuid:task_id>/extract-tags', api_views.api_task_extract_tags, name='api_task_extract_tags'),
    path('api/tasks/<uuid:task_id>/optimize-description', api_views.api_task_optimize_description, name='api_task_optimize_description'),
    path('api/tasks/<uuid:task_id>/create-github-issue', api_views.api_task_create_github_issue, name='api_task_create_github_issue'),
    path('api/tasks/<uuid:task_id>/move', api_views.api_task_move, name='api_task_move'),
    path('api/tasks/<uuid:task_id>/support-analysis-internal', api_views.api_task_support_analysis_internal, name='api_task_support_analysis_internal'),
    path('api/tasks/<uuid:task_id>/support-analysis-external', api_views.api_task_support_analysis_external, name='api_task_support_analysis_external'),
    path('api/tasks/<uuid:task_id>/support-analysis-save', api_views.api_task_support_analysis_save, name='api_task_support_analysis_save'),
    path('api/tasks/overview', api_views.api_task_overview, name='api_task_overview'),
    path('api/tasks/bulk-delete', api_views.api_task_bulk_delete, name='api_task_bulk_delete'),
    path('api/tasks/<uuid:task_id>/quick-delete', api_views.api_task_quick_delete, name='api_task_quick_delete'),
    path('api/tasks/<uuid:task_id>/quick-status-update', api_views.api_task_quick_status_update, name='api_task_quick_status_update'),
    path('api/tasks/<uuid:task_id>/quick-type-update', api_views.api_task_quick_type_update, name='api_task_quick_type_update'),
    path('api/tasks/<uuid:task_id>/mark-done', api_views.api_task_mark_done, name='api_task_mark_done'),
    path('api/items/for-move', api_views.api_get_items_for_move, name='api_get_items_for_move'),
    
    # Tags Network Graph API
    path('api/tags/network-data', api_views.api_tags_network_data, name='api_tags_network_data'),
    
    # Semantic Network API
    path('api/semantic-network/<str:object_type>/<uuid:object_id>', api_views.api_semantic_network, name='api_semantic_network'),
    path('api/milestones/<uuid:milestone_id>/semantic-network', api_views.api_milestone_semantic_network, name='api_milestone_semantic_network'),
    
    # Item File Upload API Endpoints
    path('api/items/<uuid:item_id>/files/upload', api_views.api_item_file_upload, name='api_item_file_upload'),
    path('api/items/<uuid:item_id>/files', api_views.api_item_file_list, name='api_item_file_list'),
    path('api/files/<uuid:file_id>', api_views.api_item_file_download, name='api_item_file_download'),
    path('api/files/<uuid:file_id>/delete', api_views.api_item_file_delete, name='api_item_file_delete'),
    path('api/files/<uuid:file_id>/summary', api_views.api_file_summary, name='api_file_summary'),
    
    # Task File Upload API Endpoints
    path('api/tasks/<uuid:task_id>/files/upload', api_views.api_task_file_upload, name='api_task_file_upload'),
    path('api/tasks/<uuid:task_id>/files', api_views.api_task_file_list, name='api_task_file_list'),
    path('api/tasks/<uuid:task_id>/process-link', api_views.api_task_process_link, name='api_task_process_link'),
    path('api/task-files/<uuid:file_id>', api_views.api_task_file_download, name='api_task_file_download'),
    path('api/task-files/<uuid:file_id>/delete', api_views.api_task_file_delete, name='api_task_file_delete'),
    
    # Task Comments API Endpoints
    path('api/tasks/<uuid:task_id>/comments', api_views.api_task_comments, name='api_task_comments'),
    path('api/tasks/<uuid:task_id>/comments/create', api_views.api_task_comment_create, name='api_task_comment_create'),
    path('api/comments/<uuid:comment_id>', api_views.api_task_comment_update, name='api_task_comment_update'),
    path('api/comments/<uuid:comment_id>/delete', api_views.api_task_comment_delete, name='api_task_comment_delete'),
    
    # Zammad Integration API Endpoints
    path('api/zammad/test-connection', api_views.api_zammad_test_connection, name='api_zammad_test_connection'),
    path('api/zammad/sync', api_views.api_zammad_sync, name='api_zammad_sync'),
    path('api/zammad/status', api_views.api_zammad_status, name='api_zammad_status'),
    
    # Milestone Knowledge Hub API Endpoints
    path('api/milestones/<uuid:milestone_id>/context/add', api_views.api_milestone_context_add, name='api_milestone_context_add'),
    path('api/milestones/context/<uuid:context_id>/remove', api_views.api_milestone_context_remove, name='api_milestone_context_remove'),
    path('api/milestones/<uuid:milestone_id>/context/summarize', api_views.api_milestone_context_summarize, name='api_milestone_context_summarize'),
    path('api/milestones/context/<uuid:context_id>/analyze', api_views.api_milestone_context_analyze, name='api_milestone_context_analyze'),
    path('api/milestones/<uuid:milestone_id>/context', api_views.api_milestone_context_list, name='api_milestone_context_list'),
    path('api/milestones/context/<uuid:context_id>/create-tasks', api_views.api_milestone_context_create_tasks, name='api_milestone_context_create_tasks'),
    path('api/milestones/context/<uuid:context_id>/download', api_views.api_milestone_context_download, name='api_milestone_context_download'),
    path('api/milestones/context/<uuid:context_id>/enhance-summary', api_views.api_milestone_context_enhance_summary, name='api_milestone_context_enhance_summary'),
    path('api/milestones/context/<uuid:context_id>/accept-results', api_views.api_milestone_context_accept_results, name='api_milestone_context_accept_results'),
    
    # Milestone Summary Optimization API Endpoints
    path('api/milestones/<uuid:milestone_id>/optimize-summary', api_views.api_milestone_optimize_summary, name='api_milestone_optimize_summary'),
    path('api/milestones/<uuid:milestone_id>/save-optimized-summary', api_views.api_milestone_save_optimized_summary, name='api_milestone_save_optimized_summary'),
    path('api/milestones/<uuid:milestone_id>/summary-history', api_views.api_milestone_summary_history, name='api_milestone_summary_history'),
    path('api/milestones/<uuid:milestone_id>/generate-changelog', api_views.api_milestone_generate_changelog, name='api_milestone_generate_changelog'),
    
    # Weaviate Status API Endpoints
    path('api/weaviate/<str:object_type>/<uuid:object_id>/status', api_views.check_weaviate_status, name='api_weaviate_status'),
    path('api/weaviate/<str:object_type>/<uuid:object_id>/add', api_views.add_to_weaviate, name='api_weaviate_add'),
    path('api/weaviate/<str:object_type>/<uuid:object_id>/dump', api_views.get_weaviate_dump, name='api_weaviate_dump'),
    
    # Global Search API Endpoint
    path('api/search', api_views.api_global_search, name='api_global_search'),
]
