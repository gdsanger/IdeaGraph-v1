"""
Weaviate Global Search Service for IdeaGraph

This module provides global semantic search functionality across all objects
stored in the Weaviate KnowledgeObject collection.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery, Filter, HybridFusion

logger = logging.getLogger('weaviate_search_service')


class WeaviateSearchServiceError(Exception):
    """Base exception for WeaviateSearchService errors"""
    
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


class WeaviateSearchService:
    """
    Weaviate Global Search Service
    
    Provides semantic search functionality across all KnowledgeObject types:
    - Items, Tasks, Milestones, Files, Mails, Issues, Comments, Conversations, etc.
    - Returns top N semantically relevant results with relevance scores
    - Supports filtering by type and other metadata
    """
    
    COLLECTION_NAME = 'KnowledgeObject'
    
    def __init__(self, settings=None):
        """
        Initialize WeaviateSearchService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise WeaviateSearchServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise WeaviateSearchServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            WeaviateSearchServiceError: If initialization fails
        """
        try:
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise WeaviateSearchServiceError(
                        "Weaviate Cloud enabled but URL or API key not configured"
                    )
                
                logger.info(f"Initializing Weaviate search client for cloud: {self.settings.weaviate_url}")
                
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
                )
            else:
                # Use local Weaviate instance at localhost:8081 with no authentication
                logger.info("Initializing Weaviate search client at localhost:8081")
                
                self._client = weaviate.connect_to_local(
                    host="localhost",
                    port=8081
                )

            logger.info(f"Weaviate search client initialized, collection '{self.COLLECTION_NAME}' ready")

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate search client: {str(e)}")
            raise WeaviateSearchServiceError(
                "Failed to initialize Weaviate search client",
                details=str(e)
            )
    
    def search(
        self,
        query: str,
        limit: int = 10,
        object_types: Optional[List[str]] = None,
        search_type: str = 'hybrid'
    ) -> Dict[str, Any]:
        """
        Perform global semantic search across all KnowledgeObject types
        
        Args:
            query: Search query (natural language text or question)
            limit: Maximum number of results to return (default: 10)
            object_types: Optional list of object types to filter by 
                         (e.g., ['Item', 'Task', 'File'])
            search_type: Type of search to perform ('hybrid', 'neartext', 'bm25')
                        - hybrid: Combines semantic and keyword search (default)
                        - neartext: Pure semantic/vector search
                        - bm25: Pure keyword/BM25 search
        
        Returns:
            Dictionary containing:
                - success: bool
                - results: list of search results with:
                    - id: UUID of the object
                    - type: Object type (Item, Task, File, etc.)
                    - title: Title of the object
                    - description: Description or content excerpt
                    - url: Link to the object in IdeaGraph
                    - relevance: Relevance score (0-1, higher is better)
                    - metadata: Additional metadata (owner, section, created_at, etc.)
                - total: Total number of results found
                - query: Original query text
                - search_type: Type of search performed
        
        Raises:
            WeaviateSearchServiceError: If search fails
        """
        try:
            logger.info(f"Performing {search_type} search for: '{query[:100]}...'")
            
            if not query or not query.strip():
                return {
                    'success': True,
                    'results': [],
                    'total': 0,
                    'query': query,
                    'search_type': search_type
                }
            
            # Validate search_type
            valid_search_types = ['hybrid', 'neartext', 'bm25']
            if search_type not in valid_search_types:
                logger.warning(f"Invalid search_type '{search_type}', defaulting to 'hybrid'")
                search_type = 'hybrid'
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Build type filter if specified
            type_filter = None
            if object_types and len(object_types) > 0:
                # Create filter for multiple types
                if len(object_types) == 1:
                    type_filter = Filter.by_property("type").equal(object_types[0])
                else:
                    # For multiple types, use OR logic
                    type_filters = [Filter.by_property("type").equal(t) for t in object_types]
                    type_filter = type_filters[0]
                    for f in type_filters[1:]:
                        type_filter = type_filter | f
            
            # Perform search based on search_type
            if search_type == 'neartext':
                # Pure semantic/vector search
                query_kwargs = {
                    'query': query,
                    'limit': limit,
                    'return_metadata': MetadataQuery(distance=True, certainty=True, score=True)
                }
                if type_filter:
                    query_kwargs['filters'] = type_filter
                response = collection.query.near_text(**query_kwargs)
                
            elif search_type == 'bm25':
                # Pure keyword/BM25 search
                query_kwargs = {
                    'query': query,
                    'limit': limit,
                    'return_metadata': MetadataQuery(score=True)
                }
                if type_filter:
                    query_kwargs['filters'] = type_filter
                response = collection.query.bm25(**query_kwargs)
                
            else:  # hybrid (default)
                # Hybrid search combining semantic and keyword search
                query_kwargs = {
                    'query': query,
                    'limit': limit,
                    'return_metadata': MetadataQuery(distance=True, certainty=True, score=True),
                    'fusion_type': HybridFusion.RANKED
                }
                if type_filter:
                    query_kwargs['filters'] = type_filter
                response = collection.query.hybrid(**query_kwargs)
            
            # Format results with deduplication
            search_results = []
            seen_ids = set()  # Track seen IDs to prevent duplicates
            
            for obj in response.objects:
                # Skip duplicates
                obj_id = str(obj.uuid)
                if obj_id in seen_ids:
                    continue
                seen_ids.add(obj_id)
                
                # Calculate relevance score - try multiple approaches
                # Priority: score > certainty > distance
                relevance = 0.0
                
                # Method 1: Use score if available (preferred for hybrid and BM25)
                if obj.metadata and hasattr(obj.metadata, 'score') and obj.metadata.score is not None:
                    # Score is typically between 0 and a positive number
                    # Normalize to 0-1 range by clamping and scaling
                    raw_score = float(obj.metadata.score)
                    if raw_score > 0:
                        # For hybrid/BM25, scores can vary. We'll use a sigmoid-like normalization
                        # to map scores to 0-1 range
                        relevance = min(1.0, raw_score / (raw_score + 1.0))
                
                # Method 2: Use certainty if score not available (for neartext)
                elif obj.metadata and hasattr(obj.metadata, 'certainty') and obj.metadata.certainty is not None:
                    certainty = float(obj.metadata.certainty)
                    if certainty > 0:
                        relevance = certainty
                
                # Method 3: Use distance as fallback (inverse relationship)
                elif obj.metadata and hasattr(obj.metadata, 'distance') and obj.metadata.distance is not None:
                    distance = float(obj.metadata.distance)
                    # Distance is 0-2 (0=identical, 2=completely different)
                    # Convert to relevance score 0-1 (1=most relevant, 0=least relevant)
                    relevance = max(0.0, 1.0 - (distance / 2.0))
                
                # If still 0, use a small default to indicate match was found
                if relevance == 0.0:
                    relevance = 0.1
                
                # Extract properties
                props = obj.properties
                obj_type = props.get('type', 'Unknown')
                title = props.get('title', 'Untitled')
                description = props.get('description', '')
                url = props.get('url', '')
                
                # Truncate description for preview
                description_preview = description[:200] + '...' if len(description) > 200 else description
                
                # Ensure created_at is always a string (convert datetime if necessary)
                created_at = props.get('createdAt', '')
                if isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                
                result = {
                    'id': obj_id,
                    'type': obj_type,
                    'title': title,
                    'description': description_preview,
                    'url': url,
                    'relevance': round(relevance, 3),
                    'metadata': {
                        'owner': props.get('owner', ''),
                        'section': props.get('section', ''),
                        'status': props.get('status', ''),
                        'created_at': created_at,
                        'tags': props.get('tags', []),
                    }
                }
                
                search_results.append(result)
            
            logger.info(f"Found {len(search_results)} unique results for {search_type} query: '{query[:50]}...'")
            
            return {
                'success': True,
                'results': search_results,
                'total': len(search_results),
                'query': query,
                'search_type': search_type
            }
            
        except Exception as e:
            logger.error(f"Global search failed: {str(e)}")
            raise WeaviateSearchServiceError(
                "Global search failed",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate search client connection closed")
