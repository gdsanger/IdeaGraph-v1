"""
Weaviate Tag Synchronization Service for IdeaGraph

This module provides synchronization of Tags with Weaviate vector database.
Tags are stored with their name and description as embeddings.
"""

import logging
from typing import Optional, Dict, Any, List
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery


logger = logging.getLogger('weaviate_tag_sync_service')


class WeaviateTagSyncServiceError(Exception):
    """Base exception for WeaviateTagSyncService errors"""
    
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


class WeaviateTagSyncService:
    """
    Weaviate Tag Synchronization Service
    
    Synchronizes Tags with Weaviate vector database:
    - Stores tag name and description as embeddings
    - Supports create, update, and delete operations
    """
    
    COLLECTION_NAME = 'Tag'
    
    def __init__(self, settings=None):
        """
        Initialize WeaviateTagSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise WeaviateTagSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise WeaviateTagSyncServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            WeaviateTagSyncServiceError: If initialization fails
        """
        try:
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise WeaviateTagSyncServiceError(
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
            raise WeaviateTagSyncServiceError(
                "Failed to initialize Weaviate client",
                details=str(e)
            )
    
    def _tag_to_properties(self, tag) -> Dict[str, Any]:
        """
        Convert Tag object to Weaviate properties dictionary
        
        Args:
            tag: Tag model instance
        
        Returns:
            Dictionary of properties
        """
        properties = {
            'name': tag.name,
            'description': tag.description or '',
        }
        
        return properties
    
    def sync_create(self, tag) -> Dict[str, Any]:
        """
        Synchronize a newly created tag to Weaviate
        
        Args:
            tag: Tag model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateTagSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Syncing new tag to Weaviate: {tag.id} - {tag.name}")
            
            # Prepare properties
            properties = self._tag_to_properties(tag)
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Add to collection with our UUID
            collection.data.insert(
                properties=properties,
                uuid=str(tag.id)
            )
            
            logger.info(f"Successfully synced tag {tag.id} to Weaviate")
            
            return {
                'success': True,
                'message': f'Tag {tag.id} synced to Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync tag {tag.id} to Weaviate: {str(e)}")
            raise WeaviateTagSyncServiceError(
                f"Failed to sync tag to Weaviate",
                details=str(e)
            )
    
    def sync_update(self, tag) -> Dict[str, Any]:
        """
        Synchronize an updated tag to Weaviate
        
        Args:
            tag: Tag model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateTagSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Updating tag in Weaviate: {tag.id} - {tag.name}")
            
            # Prepare properties
            properties = self._tag_to_properties(tag)
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Update in collection
            collection.data.update(
                uuid=str(tag.id),
                properties=properties
            )
            
            logger.info(f"Successfully updated tag {tag.id} in Weaviate")
            
            return {
                'success': True,
                'message': f'Tag {tag.id} updated in Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to update tag {tag.id} in Weaviate: {str(e)}")
            raise WeaviateTagSyncServiceError(
                f"Failed to update tag in Weaviate",
                details=str(e)
            )
    
    def sync_delete(self, tag_id: str) -> Dict[str, Any]:
        """
        Delete a tag from Weaviate
        
        Args:
            tag_id: UUID string of the tag to delete
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateTagSyncServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting tag from Weaviate: {tag_id}")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Delete from collection
            collection.data.delete_by_id(str(tag_id))
            
            logger.info(f"Successfully deleted tag {tag_id} from Weaviate")
            
            return {
                'success': True,
                'message': f'Tag {tag_id} deleted from Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete tag {tag_id} from Weaviate: {str(e)}")
            raise WeaviateTagSyncServiceError(
                f"Failed to delete tag from Weaviate",
                details=str(e)
            )
    
    def sync_all_tags(self) -> Dict[str, Any]:
        """
        Synchronize all tags from database to Weaviate
        
        Returns:
            Dictionary containing:
                - success: bool
                - synced_count: int
                - failed_count: int
                - message: str
        
        Raises:
            WeaviateTagSyncServiceError: If sync fails
        """
        try:
            from main.models import Tag
            
            logger.info("Starting bulk tag synchronization to Weaviate")
            
            tags = Tag.objects.all()
            total_count = tags.count()
            synced_count = 0
            failed_count = 0
            
            for tag in tags:
                try:
                    # Try to update first, if not exists, create
                    self.sync_update(tag)
                    synced_count += 1
                except Exception as e:
                    # If update fails, try create
                    try:
                        self.sync_create(tag)
                        synced_count += 1
                    except Exception as e2:
                        logger.error(f"Failed to sync tag {tag.id}: {str(e2)}")
                        failed_count += 1
            
            logger.info(f"Bulk tag synchronization complete: {synced_count}/{total_count} synced, {failed_count} failed")
            
            return {
                'success': True,
                'synced_count': synced_count,
                'failed_count': failed_count,
                'total_count': total_count,
                'message': f'Synced {synced_count}/{total_count} tags to Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync all tags: {str(e)}")
            raise WeaviateTagSyncServiceError(
                "Failed to sync all tags",
                details=str(e)
            )
    
    def search_similar(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Search for similar tags using semantic similarity
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
        
        Returns:
            Dictionary containing:
                - success: bool
                - results: list of similar tags with metadata
        
        Raises:
            WeaviateTagSyncServiceError: If search fails
        """
        try:
            logger.info(f"Searching for similar tags: '{query_text[:50]}...'")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Search using near_text
            response = collection.query.near_text(
                query=query_text,
                limit=n_results,
                return_metadata=MetadataQuery(distance=True)
            )
            
            # Format results
            similar_tags = []
            for obj in response.objects:
                similar_tags.append({
                    'id': str(obj.uuid),
                    'metadata': {
                        'name': obj.properties.get('name', ''),
                        'description': obj.properties.get('description', ''),
                    },
                    'distance': obj.metadata.distance if obj.metadata else 0.0
                })
            
            logger.info(f"Found {len(similar_tags)} similar tags")
            
            return {
                'success': True,
                'results': similar_tags
            }
            
        except Exception as e:
            logger.error(f"Failed to search similar tags: {str(e)}")
            raise WeaviateTagSyncServiceError(
                "Failed to search similar tags",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate client connection closed")
