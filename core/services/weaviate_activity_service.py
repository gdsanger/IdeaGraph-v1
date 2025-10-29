"""
Weaviate Activity Service for IdeaGraph

This module provides functionality to query recent activity from Weaviate KnowledgeObject collection.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery, Filter, Sort

logger = logging.getLogger('weaviate_activity_service')


class WeaviateActivityServiceError(Exception):
    """Base exception for WeaviateActivityService errors"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class WeaviateActivityService:
    """
    Weaviate Activity Service
    
    Provides functionality to query recent activity from KnowledgeObject collection:
    - Emails (Email)
    - Tasks (Task)
    - Items (Item)
    - GitHub Pull Requests (GitHubPullRequest)
    - GitHub Issues (GitHubIssue)
    """
    
    COLLECTION_NAME = 'KnowledgeObject'
    ACTIVITY_TYPES = ['Email', 'Task', 'Item', 'GitHubPullRequest', 'GitHubIssue']
    
    def __init__(self, settings=None):
        """
        Initialize WeaviateActivityService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise WeaviateActivityServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise WeaviateActivityServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            WeaviateActivityServiceError: If initialization fails
        """
        try:
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise WeaviateActivityServiceError(
                        "Weaviate Cloud enabled but URL or API key not configured"
                    )
                
                logger.info(f"Initializing Weaviate activity client for cloud: {self.settings.weaviate_url}")
                
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
                )
            else:
                # Use local Weaviate instance at localhost:8081 with no authentication
                logger.info("Initializing Weaviate activity client at localhost:8081")
                
                self._client = weaviate.connect_to_local(
                    host="localhost",
                    port=8081
                )

            logger.info(f"Weaviate activity client initialized, collection '{self.COLLECTION_NAME}' ready")

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate activity client: {str(e)}")
            raise WeaviateActivityServiceError(
                "Failed to initialize Weaviate activity client",
                details=str(e)
            )
    
    def get_recent_activity(
        self,
        limit: int = 20,
        tenant: Optional[str] = None,
        types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent activity from KnowledgeObject collection
        
        Args:
            limit: Maximum number of results to return (default: 20)
            tenant: Optional tenant filter
            types: Optional list of types to filter by (defaults to ACTIVITY_TYPES)
        
        Returns:
            List of activity objects with:
                - id: UUID of the object
                - type: Object type
                - title: Title of the object
                - createdAt: Creation timestamp
                - updatedAt: Update timestamp (if available)
                - url: External URL (for GitHub objects)
                - slug: Internal slug for routing
                - itemId: Parent item ID (for tasks)
                - taskId: Task ID (for emails/comments)
                - icon: Icon identifier
        
        Raises:
            WeaviateActivityServiceError: If query fails
        """
        try:
            logger.info(f"Fetching recent activity (limit: {limit}, tenant: {tenant})")
            
            if types is None:
                types = self.ACTIVITY_TYPES
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Build type filter
            type_filters = [Filter.by_property("type").equal(t) for t in types]
            type_filter = type_filters[0]
            for f in type_filters[1:]:
                type_filter = type_filter | f
            
            # Add tenant filter if provided
            if tenant:
                tenant_filter = Filter.by_property("tenant").equal(tenant)
                type_filter = type_filter & tenant_filter
            
            # Query with sorting by updatedAt/createdAt (descending)
            # Note: Weaviate v4 sorts by properties, fallback in code if needed
            response = collection.query.fetch_objects(
                filters=type_filter,
                limit=limit,
                return_properties=[
                    'id', 'type', 'title', 'createdAt', 'updatedAt',
                    'url', 'slug', 'itemId', 'taskId', 'icon'
                ]
            )
            
            # Convert response to list of dictionaries
            results = []
            for obj in response.objects:
                props = obj.properties
                
                # Use title property for all object types
                title = props.get('title') or '(ohne Betreff)'
                
                results.append({
                    'id': props.get('id'),
                    'type': props.get('type'),
                    'title': title,
                    'createdAt': props.get('createdAt'),
                    'updatedAt': props.get('updatedAt'),
                    'url': props.get('url'),
                    'slug': props.get('slug'),
                    'itemId': props.get('itemId'),
                    'taskId': props.get('taskId'),
                    'icon': props.get('icon')
                })
            
            # Sort by updatedAt or createdAt (descending)
            results.sort(
                key=lambda x: x.get('updatedAt') or x.get('createdAt') or '',
                reverse=True
            )
            
            logger.info(f"Found {len(results)} activity items")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to fetch recent activity: {str(e)}")
            raise WeaviateActivityServiceError(
                "Failed to fetch recent activity",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            try:
                self._client.close()
                logger.info("Weaviate activity client connection closed")
            except Exception as e:
                logger.warning(f"Error closing Weaviate activity client: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure client is closed"""
        self.close()
