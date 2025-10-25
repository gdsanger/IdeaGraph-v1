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
from weaviate.classes.query import MetadataQuery, Filter


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
    
    Synchronizes Items with Weaviate vector database using KnowledgeObject schema:
    - Stores item description as embedding
    - Stores item metadata (title, description, section, owner, status, tags, timestamps)
    - Supports create, update, and delete operations
    """
    
    COLLECTION_NAME = 'KnowledgeObject'
    
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
        Convert Item object to Weaviate KnowledgeObject properties dictionary
        
        Args:
            item: Item model instance
        
        Returns:
            Dictionary of properties for KnowledgeObject schema
        """
        # Get inherited context if applicable
        context = item.get_inherited_context()
        
        # Get tags as list of names from inherited context
        tag_names = [tag.name for tag in context['tags']]
        
        properties = {
            'type': 'Item',
            'title': item.title,
            'description': context['description'],  # Use inherited description if applicable
            'section': item.section.name if item.section else '',
            'owner': item.created_by.username if item.created_by else '',
            'status': item.status,
            'createdAt': item.created_at.isoformat(),
            'tags': tag_names,
            'url': f'/items/{item.id}/',
            'parent_id': context.get('parent_id', ''),
            'context_inherited': context['has_parent'],
        }
        
        return properties
    
    def sync_create(self, item) -> Dict[str, Any]:
        """
        Synchronize a newly created item to Weaviate KnowledgeObject
        
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
            logger.info(f"Syncing new item to Weaviate KnowledgeObject: {item.id} - {item.title}")
            
            # Prepare properties
            properties = self._item_to_properties(item)
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Add to collection with our UUID
            collection.data.insert(
                properties=properties,
                uuid=str(item.id)
            )
            
            logger.info(f"Successfully synced item {item.id} to Weaviate KnowledgeObject")
            
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
        Synchronize an updated item to Weaviate KnowledgeObject
        
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
            logger.info(f"Updating item in Weaviate KnowledgeObject: {item.id} - {item.title}")
            
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
            
            logger.info(f"Successfully updated item {item.id} in Weaviate KnowledgeObject")
            
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
        Delete an item from Weaviate KnowledgeObject
        
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
            logger.info(f"Deleting item from Weaviate KnowledgeObject: {item_id}")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Delete from collection
            collection.data.delete_by_id(str(item_id))
            
            logger.info(f"Successfully deleted item {item_id} from Weaviate KnowledgeObject")
            
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
        Search for similar items using semantic similarity in KnowledgeObject
        
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
            logger.info(f"Searching for similar items in KnowledgeObject: '{query_text[:50]}...'")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Search using near_text with filter for type='Item'
            from weaviate.classes.query import Filter
            response = collection.query.near_text(
                query=query_text,
                limit=n_results,
                return_metadata=MetadataQuery(distance=True),
                filters=Filter.by_property("type").equal("Item")
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
    
    def sync_knowledge_object(
        self,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync a generic knowledge object to Weaviate
        
        This method allows storing arbitrary knowledge objects (files, documents, etc.)
        in the KnowledgeObject collection alongside Items.
        
        Args:
            title: Title of the knowledge object
            content: Text content to be stored and vectorized
            metadata: Dictionary of additional metadata
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
                - object_id: str (UUID of created object)
        
        Raises:
            WeaviateItemSyncServiceError: If sync fails
        """
        try:
            import uuid
            
            # Generate a unique ID for this knowledge object
            object_id = str(uuid.uuid4())
            
            logger.info(f"Syncing knowledge object to Weaviate: {title}")
            
            # Prepare properties for KnowledgeObject schema
            properties = {
                'type': metadata.get('object_type', 'KnowledgeObject'),
                'title': title,
                'description': content,
                'section': metadata.get('section', ''),
                'owner': metadata.get('owner', ''),
                'status': metadata.get('status', ''),
                'createdAt': datetime.now().isoformat(),
                'tags': metadata.get('tags', []),
                'url': metadata.get('url', ''),
                'parent_id': metadata.get('parent_id', ''),
                'context_inherited': False,
            }
            
            # Add custom metadata fields if provided
            if 'task_id' in metadata:
                properties['task_id'] = metadata['task_id']
            if 'task_title' in metadata:
                properties['task_title'] = metadata['task_title']
            if 'item_id' in metadata:
                properties['item_id'] = metadata['item_id']
            if 'item_title' in metadata:
                properties['item_title'] = metadata['item_title']
            if 'filename' in metadata:
                properties['filename'] = metadata['filename']
            if 'file_id' in metadata:
                properties['file_id'] = metadata['file_id']
            if 'content_type' in metadata:
                properties['content_type'] = metadata['content_type']
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Add to collection
            collection.data.insert(
                properties=properties,
                uuid=object_id
            )
            
            logger.info(f"Successfully synced knowledge object {object_id} to Weaviate")
            
            return {
                'success': True,
                'message': f'Knowledge object {object_id} synced to Weaviate',
                'object_id': object_id
            }
            
        except Exception as e:
            logger.error(f"Failed to sync knowledge object to Weaviate: {str(e)}")
            raise WeaviateItemSyncServiceError(
                "Failed to sync knowledge object to Weaviate",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate client connection closed")


# Alias for backward compatibility
WeaviateSyncService = WeaviateItemSyncService
