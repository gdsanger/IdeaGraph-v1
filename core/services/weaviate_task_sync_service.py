"""
Weaviate Task Synchronization Service for IdeaGraph

This module provides synchronization of Tasks with Weaviate vector database.
Tasks are stored with their description as embeddings and metadata.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery, Filter, HybridFusion


logger = logging.getLogger('weaviate_task_sync_service')


class WeaviateTaskSyncServiceError(Exception):
    """Base exception for WeaviateTaskSyncService errors"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to structured dictionary"""
        return {
            'success': False,
            'error': self.message,
            'details': self.details or ''
        }


class WeaviateTaskSyncService:
    """
    Weaviate Task Synchronization Service
    
    Synchronizes Tasks with Weaviate vector database using KnowledgeObject schema:
    - Stores task description as embedding
    - Stores task metadata (title, description, status, owner, item, tags, timestamps)
    - Supports create, update, and delete operations
    """
    
    COLLECTION_NAME = 'KnowledgeObject'
    
    def __init__(self, settings=None):
        """
        Initialize WeaviateTaskSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise WeaviateTaskSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise WeaviateTaskSyncServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            WeaviateTaskSyncServiceError: If initialization fails
        """
        try:
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise WeaviateTaskSyncServiceError(
                        "Weaviate Cloud enabled but URL or API key not configured"
                    )
                
                logger.info(f"Initializing Weaviate client for cloud: {self.settings.weaviate_url}")
                
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
                )
            else:
                # Use local Weaviate instance at localhost:8081 with no authentication
                logger.info("Initializing Weaviate client at localhost:8081")
                
                self._client = weaviate.connect_to_local(
                    host="localhost",
                    port=8081
                )

            logger.info(f"Weaviate client initialized, collection '{self.COLLECTION_NAME}' ready")

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {str(e)}")
            raise WeaviateTaskSyncServiceError(
                "Failed to initialize Weaviate client",
                details=str(e)
            )
    
    def _task_to_properties(self, task) -> Dict[str, Any]:
        """
        Convert Task object to Weaviate KnowledgeObject properties dictionary
        
        Args:
            task: Task model instance
        
        Returns:
            Dictionary of properties for KnowledgeObject schema
        """
        # Get tags as list of names
        tag_names = [tag.name for tag in task.tags.all()]
        
        # Build comments text for semantic search
        comments_text = self._build_comments_text(task)
        
        properties = {
            'type': 'Task',
            'title': task.title,
            'description': task.description or '',
            'status': task.status,
            'owner': task.created_by.username if task.created_by else '',
            'createdAt': task.created_at.isoformat(),
            'tags': tag_names,
            'url': f'/tasks/{task.id}/',
            'commentsText': comments_text,
        }
        
        # Add itemId if task belongs to an item
        if task.item:
            properties['itemId'] = str(task.item.id)
        
        # Add githubIssueId if task has a linked GitHub issue
        if task.github_issue_id:
            properties['githubIssueId'] = task.github_issue_id
        
        return properties
    
    def _build_comments_text(self, task) -> str:
        """
        Build a formatted text representation of all comments for semantic search
        
        Args:
            task: Task model instance
        
        Returns:
            Formatted comments text as a single string
        """
        comments = task.comments.all().order_by('created_at')
        
        if not comments:
            return ''
        
        comment_lines = []
        for comment in comments:
            author = comment.get_author_display()
            # Format: [Author | DD.MM.YYYY HH:MM] Comment text
            timestamp = comment.created_at.strftime('%d.%m.%Y %H:%M')
            comment_lines.append(f"[{author} | {timestamp}] {comment.text}")
        
        return '\n'.join(comment_lines)
    
    def sync_create(self, task) -> Dict[str, Any]:
        """
        Synchronize a newly created task to Weaviate KnowledgeObject
        
        Args:
            task: Task model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateTaskSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Syncing new task to Weaviate KnowledgeObject: {task.id} - {task.title}")
            
            # Prepare properties
            properties = self._task_to_properties(task)
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Add to collection with our UUID
            collection.data.insert(
                properties=properties,
                uuid=str(task.id)
            )
            
            logger.info(f"Successfully synced task {task.id} to Weaviate KnowledgeObject")
            
            return {
                'success': True,
                'message': f'Task {task.id} synced to Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync task {task.id} to Weaviate: {str(e)}")
            raise WeaviateTaskSyncServiceError(
                f"Failed to sync task to Weaviate",
                details=str(e)
            )
    
    def sync_update(self, task) -> Dict[str, Any]:
        """
        Synchronize an updated task to Weaviate KnowledgeObject
        
        If the task doesn't exist in Weaviate, it will be created instead.
        
        Args:
            task: Task model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateTaskSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Updating task in Weaviate KnowledgeObject: {task.id} - {task.title}")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Check if task exists in Weaviate
            try:
                existing_obj = collection.query.fetch_object_by_id(str(task.id))
                task_exists = existing_obj is not None
            except Exception as e:
                logger.debug(f"Error checking if task exists: {str(e)}")
                task_exists = False
            
            if not task_exists:
                # Task doesn't exist, create it instead
                logger.info(f"Task {task.id} not found in Weaviate, creating instead of updating")
                return self.sync_create(task)
            
            # Prepare properties
            properties = self._task_to_properties(task)
            
            # Update in collection
            collection.data.update(
                uuid=str(task.id),
                properties=properties
            )
            
            logger.info(f"Successfully updated task {task.id} in Weaviate KnowledgeObject")
            
            return {
                'success': True,
                'message': f'Task {task.id} updated in Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to update task {task.id} in Weaviate: {str(e)}")
            raise WeaviateTaskSyncServiceError(
                f"Failed to update task in Weaviate",
                details=str(e)
            )
    
    def sync_delete(self, task_id: str) -> Dict[str, Any]:
        """
        Delete a task from Weaviate KnowledgeObject
        
        Args:
            task_id: UUID string of the task to delete
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateTaskSyncServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting task from Weaviate KnowledgeObject: {task_id}")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Delete from collection
            collection.data.delete_by_id(str(task_id))
            
            logger.info(f"Successfully deleted task {task_id} from Weaviate KnowledgeObject")
            
            return {
                'success': True,
                'message': f'Task {task_id} deleted from Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id} from Weaviate: {str(e)}")
            raise WeaviateTaskSyncServiceError(
                f"Failed to delete task from Weaviate",
                details=str(e)
            )
    
    def search_similar(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Search for similar tasks using semantic similarity in KnowledgeObject
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
        
        Returns:
            Dictionary containing:
                - success: bool
                - results: list of similar tasks with metadata
        
        Raises:
            WeaviateTaskSyncServiceError: If search fails
        """
        try:
            logger.info(f"Searching for similar tasks in KnowledgeObject: '{query_text[:50]}...'")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Search using hybrid search with filter for type='Task'
            response = collection.query.hybrid(
                query=query_text,
                limit=n_results,
                return_metadata=MetadataQuery(distance=True, score=True),
                filters=Filter.by_property("type").equal("Task"),
                fusion_type=HybridFusion.RANKED
            )
            
            # Format results
            similar_tasks = []
            for obj in response.objects:
                similar_tasks.append({
                    'id': str(obj.uuid),
                    'metadata': {
                        'title': obj.properties.get('title', ''),
                        'description': obj.properties.get('description', ''),
                        'status': obj.properties.get('status', ''),
                        'owner': obj.properties.get('owner', ''),
                        'created_at': obj.properties.get('createdAt', ''),
                    },
                    'document': obj.properties.get('description', ''),
                    'distance': obj.metadata.distance if obj.metadata else 0.0
                })
            
            logger.info(f"Found {len(similar_tasks)} similar tasks")
            
            return {
                'success': True,
                'results': similar_tasks
            }
            
        except Exception as e:
            logger.error(f"Failed to search similar tasks: {str(e)}")
            raise WeaviateTaskSyncServiceError(
                "Failed to search similar tasks",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate client connection closed")
