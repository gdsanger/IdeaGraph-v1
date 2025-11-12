"""
URL configuration for Actions API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from main.api.views import (
    ItemViewSet, TaskViewSet, SemanticSearchViewSet,
    FileViewSet, MilestoneViewSet
)

# Create router
router = DefaultRouter()
router.register(r'items', ItemViewSet, basename='item')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'search/semantic', SemanticSearchViewSet, basename='semantic-search')
router.register(r'files', FileViewSet, basename='file')
router.register(r'milestones', MilestoneViewSet, basename='milestone')

urlpatterns = [
    path('', include(router.urls)),
]
