"""
ChromaDB Item Synchronization Service for IdeaGraph

This module provides synchronization of Items with ChromaDB vector database.
Items are stored with their description as embeddings and metadata.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

import chromadb
from urllib.parse import urlparse, parse_qs


logger = logging.getLogger('chroma_sync_service')


class ChromaItemSyncServiceError(Exception):
    """Base exception for ChromaItemSyncService errors"""
    
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


class ChromaItemSyncService:
    """
    ChromaDB Item Synchronization Service
    
    Synchronizes Items with ChromaDB vector database:
    - Stores item description as embedding
    - Stores item metadata (id, title, section, tags, status, owner, timestamps)
    - Supports create, update, and delete operations
    """
    
    COLLECTION_NAME = 'items'
    
    def __init__(self, settings=None):
        """
        Initialize ChromaItemSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise ChromaItemSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise ChromaItemSyncServiceError("No settings found in database")
        
        # Initialize ChromaDB client
        self._client = None
        self._collection = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize ChromaDB client and collection
        
        Raises:
            ChromaItemSyncServiceError: If initialization fails
        """
        try:
            # Use local ChromaDB instance
            logger.info("Initializing ChromaDB local client at localhost:8003")
            
            self._client = chromadb.HttpClient(
                host="localhost",
                port=8003
            )

            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "IdeaGraph items with embeddings"}
            )

            logger.info(f"ChromaDB collection '{self.COLLECTION_NAME}' initialized")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise ChromaItemSyncServiceError(
                "Failed to initialize ChromaDB client",
                details=str(e)
            )

    def _resolve_cloud_credentials(self) -> Dict[str, str]:
        """Resolve ChromaDB credentials from database or Django settings."""

        api_key = (self.settings.chroma_api_key or '').strip()
        database = (self.settings.chroma_database or '').strip()
        tenant = (self.settings.chroma_tenant or '').strip()

        missing = [
            name
            for name, value in (
                ('CHROMA_API_KEY', api_key),
                ('CHROMA_DATABASE', database),
                ('CHROMA_TENANT', tenant),
            )
            if not value
        ]

        if missing:
            message = (
                "Missing ChromaDB cloud configuration in Settings. "
                "Please configure " + ', '.join(missing) + " in the Settings entity."
            )
            raise ChromaItemSyncServiceError(message)

        return {
            'api_key': api_key,
            'database': database,
            'tenant': tenant,
        }

    def _build_cloud_client_kwargs(self, *, database_value: str, api_key: str, tenant: str) -> Dict[str, Any]:
        """Build keyword arguments for ChromaDB HttpClient configuration."""
        raw_value = (database_value or '').strip()

        # Default cloud configuration for TryChroma
        host = 'api.trychroma.com'
        port = 443
        use_ssl = True
        database_name: Optional[str] = None

        if raw_value:
            # Detect if the provided value looks like a bare database name
            is_plain_database = not any(ch in raw_value for ch in ('/', ':')) and 'http' not in raw_value.lower()

            if is_plain_database:
                database_name = raw_value
            else:
                # Normalise URL to ensure parsing works even without scheme
                value_to_parse = raw_value
                if '://' not in value_to_parse:
                    value_to_parse = f'https://{value_to_parse}'

                parsed = urlparse(value_to_parse)
                if parsed.hostname:
                    host = parsed.hostname
                if parsed.scheme == 'http':
                    use_ssl = False
                    port = parsed.port or 80
                else:
                    use_ssl = True
                    port = parsed.port or 443

                if parsed.path:
                    path_parts = [segment for segment in parsed.path.split('/') if segment]
                    if 'databases' in path_parts:
                        idx = path_parts.index('databases')
                        if idx + 1 < len(path_parts):
                            database_name = path_parts[idx + 1]
                    elif path_parts:
                        database_name = path_parts[-1]

                if not database_name:
                    query_params = parse_qs(parsed.query)
                    if 'database' in query_params and query_params['database']:
                        database_name = query_params['database'][0]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Chroma-Token": api_key
        }

        client_kwargs: Dict[str, Any] = {
            'host': host,
            'port': port,
            'ssl': use_ssl,
            'headers': headers,
            'tenant': tenant
        }

        if database_name:
            client_kwargs['database'] = database_name

        return client_kwargs
    
    def _get_embedding_service(self):
        """
        Get embedding service (OpenAI) for generating embeddings
        
        Returns:
            OpenAIService instance
        
        Raises:
            ChromaItemSyncServiceError: If service initialization fails
        """
        try:
            from core.services.openai_service import OpenAIService
            return OpenAIService(self.settings)
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {str(e)}")
            raise ChromaItemSyncServiceError(
                "Embedding service not available",
                details=str(e)
            )
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI
        
        Args:
            text: Text to generate embedding for
        
        Returns:
            List of floats representing the embedding vector
        
        Raises:
            ChromaItemSyncServiceError: If embedding generation fails
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * 3072  # OpenAI text-embedding-3-large embedding size
        
        # Check if OpenAI API is enabled
        if not self.settings.openai_api_enabled or not self.settings.openai_api_key:
            error_msg = "OpenAI API is not enabled or API key is missing. Please enable OpenAI API in Settings and configure your API key."
            logger.error(error_msg)
            raise ChromaItemSyncServiceError(
                error_msg,
                details="Configure OpenAI settings: openai_api_enabled=True, openai_api_key, openai_api_base_url"
            )
        
        try:
            # Use OpenAI embedding API
            
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
                # Try to get detailed error message from response
                try:
                    error_body = response.json()
                    error_message = error_body.get('error', {}).get('message', response.text)
                except:
                    error_message = response.text
                
                logger.error(f"Embedding API failed: {response.status_code} - {error_message}")
                raise ChromaItemSyncServiceError(
                    "Failed to generate embedding",
                    details=f"API returned status {response.status_code}: {error_message}"
                )
                
        except ChromaItemSyncServiceError:
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise ChromaItemSyncServiceError(
                "Failed to generate embedding",
                details=str(e)
            )
    
    def _item_to_metadata(self, item) -> Dict[str, Any]:
        """
        Convert Item object to ChromaDB metadata dictionary
        
        Args:
            item: Item model instance
        
        Returns:
            Dictionary of metadata
        """
        # Get tag names as list
        tag_names = list(item.tags.values_list('name', flat=True))
        
        metadata = {
            'id': str(item.id),
            'title': item.title,
            'section': str(item.section.id) if item.section else '',
            'section_name': item.section.name if item.section else '',
            'tags': ','.join(tag_names),  # ChromaDB doesn't support list metadata
            'status': item.status,
            'owner': str(item.created_by.id) if item.created_by else '',
            'owner_username': item.created_by.username if item.created_by else '',
            'created_at': item.created_at.isoformat(),
            'updated_at': item.updated_at.isoformat(),
        }
        
        return metadata
    
    def sync_create(self, item) -> Dict[str, Any]:
        """
        Synchronize a newly created item to ChromaDB
        
        Args:
            item: Item model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            ChromaItemSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Syncing new item to ChromaDB: {item.id} - {item.title}")
            
            # Generate embedding from description
            embedding = self._generate_embedding(item.description)
            
            # Prepare metadata
            metadata = self._item_to_metadata(item)
            
            # Add to collection
            self._collection.add(
                ids=[str(item.id)],
                embeddings=[embedding],
                documents=[item.description or ''],
                metadatas=[metadata]
            )
            
            logger.info(f"Successfully synced item {item.id} to ChromaDB")
            
            return {
                'success': True,
                'message': f'Item {item.id} synced to ChromaDB'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync item {item.id} to ChromaDB: {str(e)}")
            raise ChromaItemSyncServiceError(
                f"Failed to sync item to ChromaDB",
                details=str(e)
            )
    
    def sync_update(self, item) -> Dict[str, Any]:
        """
        Synchronize an updated item to ChromaDB
        
        Args:
            item: Item model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            ChromaItemSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Updating item in ChromaDB: {item.id} - {item.title}")
            
            # Generate new embedding from updated description
            embedding = self._generate_embedding(item.description)
            
            # Prepare metadata
            metadata = self._item_to_metadata(item)
            
            # Update in collection (upsert operation)
            self._collection.upsert(
                ids=[str(item.id)],
                embeddings=[embedding],
                documents=[item.description or ''],
                metadatas=[metadata]
            )
            
            logger.info(f"Successfully updated item {item.id} in ChromaDB")
            
            return {
                'success': True,
                'message': f'Item {item.id} updated in ChromaDB'
            }
            
        except Exception as e:
            logger.error(f"Failed to update item {item.id} in ChromaDB: {str(e)}")
            raise ChromaItemSyncServiceError(
                f"Failed to update item in ChromaDB",
                details=str(e)
            )
    
    def sync_delete(self, item_id: str) -> Dict[str, Any]:
        """
        Delete an item from ChromaDB
        
        Args:
            item_id: UUID string of the item to delete
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            ChromaItemSyncServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting item from ChromaDB: {item_id}")
            
            # Delete from collection
            self._collection.delete(ids=[str(item_id)])
            
            logger.info(f"Successfully deleted item {item_id} from ChromaDB")
            
            return {
                'success': True,
                'message': f'Item {item_id} deleted from ChromaDB'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete item {item_id} from ChromaDB: {str(e)}")
            raise ChromaItemSyncServiceError(
                f"Failed to delete item from ChromaDB",
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
            ChromaItemSyncServiceError: If search fails
        """
        try:
            logger.info(f"Searching for similar items: '{query_text[:50]}...'")
            
            # Generate embedding for query
            query_embedding = self._generate_embedding(query_text)
            
            # Search collection
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Format results
            similar_items = []
            if results and results['ids'] and len(results['ids']) > 0:
                for i, item_id in enumerate(results['ids'][0]):
                    similar_items.append({
                        'id': item_id,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'document': results['documents'][0][i] if results['documents'] else '',
                        'distance': results['distances'][0][i] if results['distances'] else 0.0
                    })
            
            logger.info(f"Found {len(similar_items)} similar items")
            
            return {
                'success': True,
                'results': similar_items
            }
            
        except Exception as e:
            logger.error(f"Failed to search similar items: {str(e)}")
            raise ChromaItemSyncServiceError(
                "Failed to search similar items",
                details=str(e)
            )
