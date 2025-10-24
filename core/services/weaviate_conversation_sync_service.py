"""
Weaviate Conversation Synchronization Service for IdeaGraph

This module provides synchronization of Teams conversations with Weaviate vector database.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import weaviate
from weaviate.classes.init import Auth

logger = logging.getLogger('weaviate_conversation_sync_service')


class WeaviateConversationSyncServiceError(Exception):
    """Base exception for WeaviateConversationSyncService errors"""
    
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


class WeaviateConversationSyncService:
    """
    Weaviate Conversation Synchronization Service
    
    Synchronizes Teams conversations with Weaviate vector database using KnowledgeObject schema.
    """
    
    COLLECTION_NAME = 'KnowledgeObject'
    
    def __init__(self, settings=None):
        """
        Initialize WeaviateConversationSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise WeaviateConversationSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise WeaviateConversationSyncServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            WeaviateConversationSyncServiceError: If initialization fails
        """
        try:
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise WeaviateConversationSyncServiceError(
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
            
            logger.info("Weaviate client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {str(e)}")
            raise WeaviateConversationSyncServiceError(
                "Failed to initialize Weaviate client",
                details=str(e)
            )
    
    def sync_conversation(
        self,
        message_content: str,
        ai_response: str,
        item_id: str,
        item_title: str,
        created_by: str
    ) -> Dict[str, Any]:
        """
        Sync a conversation to Weaviate
        
        Args:
            message_content: Original message from user
            ai_response: AI-generated response
            item_id: UUID of the related item
            item_title: Title of the related item
            created_by: UPN of the user who created the message
            
        Returns:
            Dict with success status and sync details
        """
        if not self._client:
            raise WeaviateConversationSyncServiceError("Weaviate client not initialized")
        
        try:
            # Get the collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Prepare conversation data
            # Use first sentence of message as title
            title_parts = message_content.split('.')
            title = title_parts[0][:100] if title_parts else message_content[:100]
            
            # Combine message and AI response for description
            description = f"""**User Message:**
{message_content}

**AI Response:**
{ai_response}"""
            
            # Prepare properties for Weaviate
            properties = {
                'title': title,
                'description': description,
                'type': 'conversation',
                'source': 'Teams',
                'related_item': item_id,
                'created_by': created_by,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Add the object to Weaviate
            uuid = collection.data.insert(
                properties=properties
            )
            
            logger.info(f"Synced conversation to Weaviate with UUID: {uuid}")
            
            return {
                'success': True,
                'uuid': str(uuid),
                'message': 'Conversation synced to Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync conversation to Weaviate: {str(e)}")
            raise WeaviateConversationSyncServiceError(
                "Failed to sync conversation",
                details=str(e)
            )
    
    def close(self):
        """Close Weaviate client connection"""
        if self._client:
            try:
                self._client.close()
                logger.info("Weaviate client connection closed")
            except Exception as e:
                logger.warning(f"Error closing Weaviate client: {str(e)}")
    
    def __del__(self):
        """Destructor to ensure client is closed"""
        self.close()
