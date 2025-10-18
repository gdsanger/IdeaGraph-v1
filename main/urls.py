from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.home, name='home'),
    
    # Section URLs
    path('sections/', views.section_list, name='section_list'),
    path('sections/create/', views.section_create, name='section_create'),
    path('sections/<uuid:pk>/update/', views.section_update, name='section_update'),
    path('sections/<uuid:pk>/delete/', views.section_delete, name='section_delete'),
]
