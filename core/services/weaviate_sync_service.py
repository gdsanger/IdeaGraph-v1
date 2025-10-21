"""
Weaviate Item Synchronization Service for IdeaGraph

This module provides synchronization of Items with Weaviate vector database.
Items are stored with their description as embeddings and metadata.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery


logger = logging.getLogger('weaviate_sync_service')


class WeaviateItemSyncServiceError(Exception):
    """Base exception for WeaviateItemSyncService errors"""
    
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


class WeaviateItemSyncService:
    """
    Weaviate Item Synchronization Service
    
    Synchronizes Items with Weaviate vector database:
    - Stores item description as embedding
    - Stores item metadata (title, description, section, owner, status, tags, timestamps)
    - Supports create, update, and delete operations
    """
    
    COLLECTION_NAME = 'Item'
    
    def __init__(self, settings=None):
        """
        Initialize WeaviateItemSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise WeaviateItemSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise WeaviateItemSyncServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            WeaviateItemSyncServiceError: If initialization fails
        """
        try:
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise WeaviateItemSyncServiceError(
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
            raise WeaviateItemSyncServiceError(
                "Failed to initialize Weaviate client",
                details=str(e)
            )
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI
        
        Note: Weaviate with text2vec-transformers handles embeddings automatically,
        but we keep this for compatibility if needed for manual embedding generation.
        
        Args:
            text: Text to generate embedding for
        
        Returns:
            List of floats representing the embedding vector
        
        Raises:
            WeaviateItemSyncServiceError: If embedding generation fails
        """
        if not text or not text.strip():
            # Return empty list - Weaviate will handle it
            return []
        
        # Check if OpenAI API is enabled
        if not self.settings.openai_api_enabled or not self.settings.openai_api_key:
            # For Weaviate with text2vec-transformers, we don't need OpenAI
            # Just return empty - Weaviate handles vectorization
            logger.info("Using Weaviate's built-in text2vec-transformers for embeddings")
            return []
        
        try:
            # Use OpenAI embedding API (optional, Weaviate can handle this)
            url = f"{self.settings.openai_api_base_url}/embeddings"
            headers = {
                'Authorization': f'Bearer {self.settings.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'text-embedding-3-large',
                'input': text
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                embedding = result['data'][0]['embedding']
                logger.info(f"Generated embedding for text (length: {len(text)})")
                return embedding
            else:
                logger.warning(f"Embedding API failed: {response.status_code}, using Weaviate's built-in vectorization")
                return []
                
        except Exception as e:
            logger.warning(f"Error generating embedding: {str(e)}, using Weaviate's built-in vectorization")
            return []
    
    def _item_to_properties(self, item) -> Dict[str, Any]:
        """
        Convert Item object to Weaviate properties dictionary
        
        Args:
            item: Item model instance
        
        Returns:
            Dictionary of properties
        """
        # Get tag references (UUIDs)
        from main.models import Tag
        tag_refs = []
        for tag in item.tags.all():
            tag_refs.append(str(tag.id))
        
        properties = {
            'title': item.title,
            'description': item.description or '',
            'section': item.section.name if item.section else '',
            'owner': item.created_by.username if item.created_by else '',
            'status': item.status,
            'createdAt': item.created_at.isoformat(),
        }
        
        return properties
    
    def sync_create(self, item) -> Dict[str, Any]:
        """
        Synchronize a newly created item to Weaviate
        
        Args:
            item: Item model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateItemSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Syncing new item to Weaviate: {item.id} - {item.title}")
            
            # Prepare properties
            properties = self._item_to_properties(item)
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Add to collection with our UUID
            collection.data.insert(
                properties=properties,
                uuid=str(item.id)
            )
            
            # Add tag references after creation
            tag_refs = [str(tag.id) for tag in item.tags.all()]
            if tag_refs:
                try:
                    collection.data.reference_add_many(
                        from_uuid=str(item.id),
                        from_property="tagRefs",
                        to_uuids=tag_refs
                    )
                except Exception as e:
                    logger.warning(f"Failed to add tag references: {str(e)}")
            
            logger.info(f"Successfully synced item {item.id} to Weaviate")
            
            return {
                'success': True,
                'message': f'Item {item.id} synced to Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync item {item.id} to Weaviate: {str(e)}")
            raise WeaviateItemSyncServiceError(
                f"Failed to sync item to Weaviate",
                details=str(e)
            )
    
    def sync_update(self, item) -> Dict[str, Any]:
        """
        Synchronize an updated item to Weaviate
        
        If the item doesn't exist in Weaviate, it will be created instead.
        
        Args:
            item: Item model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateItemSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Updating item in Weaviate: {item.id} - {item.title}")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Check if item exists in Weaviate
            try:
                existing_obj = collection.query.fetch_object_by_id(str(item.id))
                item_exists = existing_obj is not None
            except Exception as e:
                logger.debug(f"Error checking if item exists: {str(e)}")
                item_exists = False
            
            if not item_exists:
                # Item doesn't exist, create it instead
                logger.info(f"Item {item.id} not found in Weaviate, creating instead of updating")
                return self.sync_create(item)
            
            # Prepare properties
            properties = self._item_to_properties(item)
            
            # Update in collection
            collection.data.update(
                uuid=str(item.id),
                properties=properties
            )
            
            # Update tag references
            # First, delete all existing references
            try:
                collection.data.reference_delete(
                    from_uuid=str(item.id),
                    from_property="tagRefs"
                )
            except Exception as e:
                logger.debug(f"No existing references to delete: {str(e)}")
            
            # Add new tag references
            tag_refs = [str(tag.id) for tag in item.tags.all()]
            if tag_refs:
                try:
                    collection.data.reference_add_many(
                        from_uuid=str(item.id),
                        from_property="tagRefs",
                        to_uuids=tag_refs
                    )
                except Exception as e:
                    logger.warning(f"Failed to add tag references: {str(e)}")
            
            logger.info(f"Successfully updated item {item.id} in Weaviate")
            
            return {
                'success': True,
                'message': f'Item {item.id} updated in Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to update item {item.id} in Weaviate: {str(e)}")
            raise WeaviateItemSyncServiceError(
                f"Failed to update item in Weaviate",
                details=str(e)
            )
    
    def sync_delete(self, item_id: str) -> Dict[str, Any]:
        """
        Delete an item from Weaviate
        
        Args:
            item_id: UUID string of the item to delete
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateItemSyncServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting item from Weaviate: {item_id}")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Delete from collection
            collection.data.delete_by_id(str(item_id))
            
            logger.info(f"Successfully deleted item {item_id} from Weaviate")
            
            return {
                'success': True,
                'message': f'Item {item_id} deleted from Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete item {item_id} from Weaviate: {str(e)}")
            raise WeaviateItemSyncServiceError(
                f"Failed to delete item from Weaviate",
                details=str(e)
            )
    
    def search_similar(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Search for similar items using semantic similarity
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
        
        Returns:
            Dictionary containing:
                - success: bool
                - results: list of similar items with metadata
        
        Raises:
            WeaviateItemSyncServiceError: If search fails
        """
        try:
            logger.info(f"Searching for similar items: '{query_text[:50]}...'")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Search using near_text
            response = collection.query.near_text(
                query=query_text,
                limit=n_results,
                return_metadata=MetadataQuery(distance=True)
            )
            
            # Format results
            similar_items = []
            for obj in response.objects:
                similar_items.append({
                    'id': str(obj.uuid),
                    'metadata': {
                        'title': obj.properties.get('title', ''),
                        'description': obj.properties.get('description', ''),
                        'section': obj.properties.get('section', ''),
                        'owner': obj.properties.get('owner', ''),
                        'status': obj.properties.get('status', ''),
                        'created_at': obj.properties.get('createdAt', ''),
                    },
                    'document': obj.properties.get('description', ''),
                    'distance': obj.metadata.distance if obj.metadata else 0.0
                })
            
            logger.info(f"Found {len(similar_items)} similar items")
            
            return {
                'success': True,
                'results': similar_items
            }
            
        except Exception as e:
            logger.error(f"Failed to search similar items: {str(e)}")
            raise WeaviateItemSyncServiceError(
                "Failed to search similar items",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate client connection closed")
