"""
Support Duplicate Finder Service

This service finds similar tasks within an item using embedding-based
semantic similarity search via Weaviate.
"""

import os
import logging
from typing import List, Dict, Any, Optional
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery
from weaviate.config import AdditionalConfig, Timeout

logger = logging.getLogger('support_duplicate_finder_service')


class SupportDuplicateFinderService:
    """
    Service to find duplicate/similar tasks within an item
    
    Uses Weaviate's semantic search to find tasks with similar titles/descriptions.
    """
    
    COLLECTION_NAME = 'Task'
    HIGH_SIMILARITY_THRESHOLD = 0.90  # Definitely a duplicate
    MEDIUM_SIMILARITY_THRESHOLD = 0.80  # Possible duplicate
    
    def __init__(self, settings=None):
        """
        Initialize SupportDuplicateFinderService
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise Exception(f"Failed to load settings: {str(e)}")
        
        self.settings = settings
        if not self.settings:
            raise Exception("No settings found in database")
        
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Weaviate client"""
        try:
            if self.settings.weaviate_cloud_enabled:
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise Exception("Weaviate Cloud enabled but URL or API key not configured")
                
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key),
                )
            else:
                # Use local Weaviate instance with configurable host and port
                # Priority: Settings model > Environment variables > Defaults
                host = self.settings.weaviate_url or os.getenv('WEAVIATE_URL', 'localhost')
                # Strip protocol if present (for backward compatibility)
                host = host.replace('http://', '').replace('https://', '')
                port = self.settings.weaviate_port or int(os.getenv('WEAVIATE_PORT', '8081'))
                grpc_port = self.settings.weaviate_grpc_port or int(os.getenv('WEAVIATE_GRPC', '50051'))
                timeout = self.settings.weaviate_timeout or int(os.getenv('WEAVIATE_TIMEOUT', '30'))
                
                self._client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    grpc_port=grpc_port,
                    additional_config=AdditionalConfig(
                        timeout=Timeout(query=timeout, insert=timeout)
                    )
                )
            
            logger.info("Weaviate client initialized successfully for duplicate finder")
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {str(e)}")
            raise Exception(f"Failed to initialize Weaviate client: {str(e)}")
    
    def find_similar_tasks(
        self,
        item_id: str,
        title: str,
        description: str = '',
        limit: int = 5,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar tasks within the same item
        
        Args:
            item_id: UUID of the item to search within
            title: Title of the task to compare
            description: Description of the task to compare
            limit: Maximum number of results to return
            source_filter: Optional filter by source (e.g., 'support')
        
        Returns:
            List of similar tasks with similarity scores, sorted by similarity descending
            Format: [
                {
                    'task_id': 'uuid',
                    'title': 'string',
                    'similarity': 0.0-1.0,
                    'status': 'new|done|...',
                    'type': 'support|bug|...'
                }
            ]
        """
        if not self._client:
            logger.error("Weaviate client not initialized")
            return []
        
        try:
            # Combine title and description for search query
            search_text = f"{title} {description}".strip()
            
            if not search_text:
                logger.warning("Empty search text provided")
                return []
            
            # Get the Task collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Build filters
            from weaviate.classes.query import Filter
            
            # Filter by item_id
            filters = Filter.by_property("item_id").equal(str(item_id))
            
            # Optionally filter by source
            if source_filter:
                filters = filters & Filter.by_property("source").equal(source_filter)
            
            # Perform hybrid search (semantic + keyword)
            response = collection.query.hybrid(
                query=search_text,
                limit=limit,
                filters=filters,
                return_metadata=MetadataQuery(score=True, distance=True)
            )
            
            # Process results
            results = []
            for obj in response.objects:
                try:
                    # Calculate similarity from score (0-1 range)
                    # Weaviate hybrid search returns score, we normalize it
                    similarity = float(obj.metadata.score) if obj.metadata.score else 0.0
                    
                    results.append({
                        'task_id': str(obj.properties.get('task_id', '')),
                        'title': obj.properties.get('title', ''),
                        'similarity': similarity,
                        'status': obj.properties.get('status', ''),
                        'type': obj.properties.get('type', ''),
                    })
                except Exception as e:
                    logger.warning(f"Failed to process search result: {str(e)}")
                    continue
            
            # Sort by similarity descending
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            logger.info(f"Found {len(results)} similar tasks for item {item_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error finding similar tasks: {str(e)}", exc_info=True)
            return []
    
    def categorize_similarity(self, similarity: float) -> str:
        """
        Categorize similarity score into HIGH/MEDIUM/LOW
        
        Args:
            similarity: Similarity score (0.0-1.0)
        
        Returns:
            'HIGH' if >= 0.90, 'MEDIUM' if >= 0.80, 'LOW' otherwise
        """
        if similarity >= self.HIGH_SIMILARITY_THRESHOLD:
            return 'HIGH'
        elif similarity >= self.MEDIUM_SIMILARITY_THRESHOLD:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def __del__(self):
        """Cleanup Weaviate client on deletion"""
        if self._client:
            try:
                self._client.close()
            except:
                pass
