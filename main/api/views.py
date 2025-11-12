"""
API Views for Actions API

Provides RESTful endpoints for Items, Tasks, Files, Semantic Search, and Milestones.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from main.models import Item, Task, Milestone, ItemFile, TaskFile
from main.api.serializers import (
    ItemSerializer, ItemDetailSerializer, TaskSerializer, MilestoneSerializer,
    FileRefSerializer, TaskFileRefSerializer, ContextHitSerializer, FileContentSerializer
)
from main.api.authentication import ApiKeyAuthentication
from main.api.permissions import IsAuthenticated, IsOwnerOrReadOnly
from main.api.throttling import ActionsAPIRateThrottle, ActionsAPIBurstRateThrottle
from core.services.weaviate_client_service import WeaviateClientService, WeaviateClientServiceError
from core.services.milestone_service import MilestoneService, MilestoneServiceError

logger = logging.getLogger(__name__)


class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Item operations
    
    Provides:
    - list: GET /api/ideagraph/items - List/search items
    - retrieve: GET /api/ideagraph/items/{id} - Get item detail
    - files: GET /api/ideagraph/items/{id}/files - Get item files
    """
    
    serializer_class = ItemSerializer
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ActionsAPIRateThrottle, ActionsAPIBurstRateThrottle]
    
    def get_queryset(self):
        """Get queryset with filtering and search"""
        queryset = Item.objects.select_related('section', 'created_by').prefetch_related('tags')
        
        # Apply filters
        query = self.request.query_params.get('query', '').strip()
        tag = self.request.query_params.get('tag', '').strip()
        
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        
        if tag:
            queryset = queryset.filter(tags__name__iexact=tag)
        
        return queryset.distinct()
    
    def get_serializer_class(self):
        """Use detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return ItemDetailSerializer
        return ItemSerializer
    
    def list(self, request, *args, **kwargs):
        """List items with pagination"""
        limit = int(request.query_params.get('limit', 20))
        limit = min(limit, 100)  # Cap at 100
        
        queryset = self.get_queryset()[:limit]
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'items': serializer.data,
            'count': len(serializer.data)
        })
    
    def retrieve(self, request, *args, **kwargs):
        """Get item detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'item': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def files(self, request, pk=None):
        """Get files for an item"""
        item = self.get_object()
        files = item.files.all()
        serializer = FileRefSerializer(files, many=True)
        
        return Response({
            'success': True,
            'files': serializer.data,
            'count': len(serializer.data)
        })


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Task operations
    
    Provides:
    - list: GET /api/ideagraph/tasks - List/search tasks
    - create: POST /api/ideagraph/tasks - Create task
    - retrieve: GET /api/ideagraph/tasks/{id} - Get task detail
    - partial_update: PATCH /api/ideagraph/tasks/{id} - Update task
    """
    
    serializer_class = TaskSerializer
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ActionsAPIRateThrottle, ActionsAPIBurstRateThrottle]
    
    def get_queryset(self):
        """Get queryset with filtering and search"""
        queryset = Task.objects.select_related('item', 'milestone', 'created_by', 'assigned_to').prefetch_related('tags')
        
        # Apply filters
        item_id = self.request.query_params.get('itemId', '').strip()
        status_filter = self.request.query_params.get('status', '').strip()
        query = self.request.query_params.get('query', '').strip()
        
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        
        return queryset.distinct()
    
    def list(self, request, *args, **kwargs):
        """List tasks with pagination"""
        limit = int(request.query_params.get('limit', 20))
        limit = min(limit, 100)  # Cap at 100
        
        queryset = self.get_queryset()[:limit]
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'tasks': serializer.data,
            'count': len(serializer.data)
        })
    
    def create(self, request, *args, **kwargs):
        """Create a new task"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set created_by to current user
        task = serializer.save(created_by=request.user)
        
        logger.info(f"Task created via API: {task.id} by {request.user.username}")
        
        return Response({
            'success': True,
            'task': TaskSerializer(task).data
        }, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """Get task detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'task': serializer.data
        })
    
    def partial_update(self, request, *args, **kwargs):
        """Update task (PATCH)"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        
        logger.info(f"Task updated via API: {task.id} by {request.user.username}")
        
        return Response({
            'success': True,
            'task': TaskSerializer(task).data
        })


class SemanticSearchViewSet(viewsets.ViewSet):
    """
    ViewSet for Semantic Search
    
    Provides:
    - list: GET /api/ideagraph/search/semantic - Semantic search
    """
    
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ActionsAPIRateThrottle, ActionsAPIBurstRateThrottle]
    
    def list(self, request):
        """Perform semantic search"""
        query = request.query_params.get('query', '').strip()
        types_param = request.query_params.get('types', '').strip()
        limit = int(request.query_params.get('limit', 10))
        
        if not query:
            return Response({
                'success': False,
                'error': 'Query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parse types
        types = None
        if types_param:
            types = [t.strip() for t in types_param.split(',') if t.strip()]
        
        # Limit to reasonable value
        limit = min(limit, 50)
        
        try:
            # Perform semantic search
            weaviate_service = WeaviateClientService()
            results = weaviate_service.semantic_search(
                query=query,
                types=types,
                limit=limit
            )
            
            serializer = ContextHitSerializer(results, many=True)
            
            return Response({
                'success': True,
                'results': serializer.data,
                'count': len(serializer.data)
            })
            
        except WeaviateClientServiceError as e:
            logger.error(f"Semantic search failed: {e.message}")
            return Response({
                'success': False,
                'error': 'Semantic search failed',
                'details': e.details or str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FileViewSet(viewsets.ViewSet):
    """
    ViewSet for File operations
    
    Provides:
    - retrieve: GET /api/ideagraph/files/{fileId} - Get file content from Weaviate
    """
    
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ActionsAPIRateThrottle, ActionsAPIBurstRateThrottle]
    
    def retrieve(self, request, pk=None):
        """Get file content by file ID"""
        if not pk:
            return Response({
                'success': False,
                'error': 'File ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Retrieve file from Weaviate
            weaviate_service = WeaviateClientService()
            file_data = weaviate_service.get_file_by_id(pk)
            
            serializer = FileContentSerializer(file_data)
            
            return Response({
                'success': True,
                'file': serializer.data
            })
            
        except WeaviateClientServiceError as e:
            if 'not found' in e.message.lower():
                return Response({
                    'success': False,
                    'error': 'File not found',
                    'details': e.details or str(e)
                }, status=status.HTTP_404_NOT_FOUND)
            
            logger.error(f"File retrieval failed: {e.message}")
            return Response({
                'success': False,
                'error': 'File retrieval failed',
                'details': e.details or str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MilestoneViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Milestone operations
    
    Provides:
    - list: GET /api/ideagraph/milestones - List milestones
    - retrieve: GET /api/ideagraph/milestones/{id} - Get milestone detail
    - changelog: GET /api/ideagraph/milestones/{id}/changelog - Get changelog
    - summarize: POST /api/ideagraph/milestones/{id}/summarize - Generate summary
    """
    
    serializer_class = MilestoneSerializer
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ActionsAPIRateThrottle, ActionsAPIBurstRateThrottle]
    
    def get_queryset(self):
        """Get queryset with filtering"""
        queryset = Milestone.objects.select_related('item').prefetch_related('tasks')
        
        # Apply filters
        item_id = self.request.query_params.get('itemId', '').strip()
        status_filter = self.request.query_params.get('status', '').strip()
        
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """List milestones"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'milestones': serializer.data,
            'count': len(serializer.data)
        })
    
    def retrieve(self, request, *args, **kwargs):
        """Get milestone detail"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'success': True,
            'milestone': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def changelog(self, request, pk=None):
        """Get milestone changelog"""
        milestone = self.get_object()
        
        # Return existing changelog if available
        if milestone.changelog:
            return Response({
                'success': True,
                'changelog': milestone.changelog
            })
        
        # Generate new changelog
        try:
            milestone_service = MilestoneService()
            result = milestone_service.changelog_milestone(str(milestone.id))
            
            return Response({
                'success': True,
                'changelog': result['changelog'],
                'metadata': {
                    'task_count': result['task_count'],
                    'agent_used': result.get('agent_used')
                }
            })
            
        except MilestoneServiceError as e:
            logger.error(f"Changelog generation failed: {e.message}")
            return Response({
                'success': False,
                'error': 'Changelog generation failed',
                'details': e.details or str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def summarize(self, request, pk=None):
        """Generate AI summary for milestone"""
        milestone = self.get_object()
        
        try:
            milestone_service = MilestoneService()
            result = milestone_service.summarize_milestone(str(milestone.id))
            
            return Response({
                'success': True,
                'summary': result['summary'],
                'metadata': {
                    'context_count': result['context_count'],
                    'agent_used': result.get('agent_used')
                }
            })
            
        except MilestoneServiceError as e:
            logger.error(f"Summary generation failed: {e.message}")
            return Response({
                'success': False,
                'error': 'Summary generation failed',
                'details': e.details or str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
