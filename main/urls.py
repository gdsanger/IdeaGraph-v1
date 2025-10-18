from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    
    # Settings URLs
    path('settings/', views.settings_list, name='settings_list'),
    path('settings/create/', views.settings_create, name='settings_create'),
    path('settings/<uuid:pk>/update/', views.settings_update, name='settings_update'),
    path('settings/<uuid:pk>/delete/', views.settings_delete, name='settings_delete'),
]
