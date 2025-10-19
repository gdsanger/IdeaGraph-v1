"""
ChromaDB Task Synchronization Service for IdeaGraph

This module provides synchronization of Tasks with ChromaDB vector database.
Tasks are stored with their description as embeddings and metadata.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

import chromadb
from chromadb.config import Settings as ChromaSettings


logger = logging.getLogger('chroma_task_sync_service')


class ChromaTaskSyncServiceError(Exception):
    """Base exception for ChromaTaskSyncService errors"""
    
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


class ChromaTaskSyncService:
    """
    ChromaDB Task Synchronization Service
    
    Synchronizes Tasks with ChromaDB vector database:
    - Stores task description as embedding
    - Stores task metadata (id, title, item_id, status, owner, github_issue_id, timestamps)
    - Supports create, update, and delete operations
    """
    
    COLLECTION_NAME = 'tasks'
    
    def __init__(self, settings=None):
        """
        Initialize ChromaTaskSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise ChromaTaskSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise ChromaTaskSyncServiceError("No settings found in database")
        
        # Initialize ChromaDB client
        self._client = None
        self._collection = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize ChromaDB client and collection
        
        Raises:
            ChromaTaskSyncServiceError: If initialization fails
        """
        try:
            # Check if cloud configuration is available
            if self.settings.chroma_api_key and self.settings.chroma_database and self.settings.chroma_tenant:
                # Cloud configuration
                logger.info("Initializing ChromaDB cloud client")
                chroma_settings = ChromaSettings(
                    chroma_api_impl="chromadb.api.fastapi.FastAPI",
                    chroma_server_host=self.settings.chroma_database,
                    chroma_server_http_port=443,
                    chroma_server_ssl_enabled=True,
                    chroma_server_headers={
                        "Authorization": f"Bearer {self.settings.chroma_api_key}",
                        "X-Chroma-Token": self.settings.chroma_api_key
                    }
                )
                self._client = chromadb.Client(chroma_settings)
            else:
                # Local/persistent storage configuration
                logger.info("Initializing ChromaDB local client")
                self._client = chromadb.PersistentClient(path="./chroma_db")
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "IdeaGraph tasks with embeddings"}
            )
            
            logger.info(f"ChromaDB collection '{self.COLLECTION_NAME}' initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise ChromaTaskSyncServiceError(
                "Failed to initialize ChromaDB client",
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
            ChromaTaskSyncServiceError: If embedding generation fails
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * 1536  # OpenAI ada-002 embedding size
        
        try:
            # Use OpenAI embedding API
            if not self.settings.openai_api_enabled or not self.settings.openai_api_key:
                logger.warning("OpenAI API not enabled, using zero vector")
                return [0.0] * 1536
            
            url = f"{self.settings.openai_api_base_url}/embeddings"
            headers = {
                'Authorization': f'Bearer {self.settings.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'text-embedding-ada-002',
                'input': text
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                embedding = result['data'][0]['embedding']
                logger.info(f"Generated embedding for text (length: {len(text)})")
                return embedding
            else:
                logger.error(f"Embedding API failed: {response.status_code}")
                raise ChromaTaskSyncServiceError(
                    "Failed to generate embedding",
                    details=f"API returned status {response.status_code}"
                )
                
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise ChromaTaskSyncServiceError(
                "Failed to generate embedding",
                details=str(e)
            )
    
    def _task_to_metadata(self, task) -> Dict[str, Any]:
        """
        Convert Task object to ChromaDB metadata dictionary
        
        Args:
            task: Task model instance
        
        Returns:
            Dictionary of metadata
        """
        metadata = {
            'id': str(task.id),
            'title': task.title,
            'item_id': str(task.item.id) if task.item else '',
            'status': task.status,
            'github_issue_id': task.github_issue_id if task.github_issue_id else 0,
            'owner': str(task.created_by.id) if task.created_by else '',
            'owner_username': task.created_by.username if task.created_by else '',
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
        }
        
        return metadata
    
    def sync_create(self, task) -> Dict[str, Any]:
        """
        Synchronize a newly created task to ChromaDB
        
        Args:
            task: Task model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            ChromaTaskSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Syncing new task to ChromaDB: {task.id} - {task.title}")
            
            # Generate embedding from description
            embedding = self._generate_embedding(task.description)
            
            # Prepare metadata
            metadata = self._task_to_metadata(task)
            
            # Add to collection
            self._collection.add(
                ids=[str(task.id)],
                embeddings=[embedding],
                documents=[task.description or ''],
                metadatas=[metadata]
            )
            
            logger.info(f"Successfully synced task {task.id} to ChromaDB")
            
            return {
                'success': True,
                'message': f'Task {task.id} synced to ChromaDB'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync task {task.id} to ChromaDB: {str(e)}")
            raise ChromaTaskSyncServiceError(
                f"Failed to sync task to ChromaDB",
                details=str(e)
            )
    
    def sync_update(self, task) -> Dict[str, Any]:
        """
        Synchronize an updated task to ChromaDB
        
        Args:
            task: Task model instance
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            ChromaTaskSyncServiceError: If sync fails
        """
        try:
            logger.info(f"Updating task in ChromaDB: {task.id} - {task.title}")
            
            # Generate new embedding from updated description
            embedding = self._generate_embedding(task.description)
            
            # Prepare metadata
            metadata = self._task_to_metadata(task)
            
            # Update in collection (upsert operation)
            self._collection.upsert(
                ids=[str(task.id)],
                embeddings=[embedding],
                documents=[task.description or ''],
                metadatas=[metadata]
            )
            
            logger.info(f"Successfully updated task {task.id} in ChromaDB")
            
            return {
                'success': True,
                'message': f'Task {task.id} updated in ChromaDB'
            }
            
        except Exception as e:
            logger.error(f"Failed to update task {task.id} in ChromaDB: {str(e)}")
            raise ChromaTaskSyncServiceError(
                f"Failed to update task in ChromaDB",
                details=str(e)
            )
    
    def sync_delete(self, task_id: str) -> Dict[str, Any]:
        """
        Delete a task from ChromaDB
        
        Args:
            task_id: UUID string of the task to delete
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            ChromaTaskSyncServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting task from ChromaDB: {task_id}")
            
            # Delete from collection
            self._collection.delete(ids=[str(task_id)])
            
            logger.info(f"Successfully deleted task {task_id} from ChromaDB")
            
            return {
                'success': True,
                'message': f'Task {task_id} deleted from ChromaDB'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id} from ChromaDB: {str(e)}")
            raise ChromaTaskSyncServiceError(
                f"Failed to delete task from ChromaDB",
                details=str(e)
            )
    
    def search_similar(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Search for similar tasks using semantic similarity
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
        
        Returns:
            Dictionary containing:
                - success: bool
                - results: list of similar tasks with metadata
        
        Raises:
            ChromaTaskSyncServiceError: If search fails
        """
        try:
            logger.info(f"Searching for similar tasks: '{query_text[:50]}...'")
            
            # Generate embedding for query
            query_embedding = self._generate_embedding(query_text)
            
            # Search collection
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Format results
            similar_tasks = []
            if results and results['ids'] and len(results['ids']) > 0:
                for i, task_id in enumerate(results['ids'][0]):
                    similar_tasks.append({
                        'id': task_id,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'document': results['documents'][0][i] if results['documents'] else '',
                        'distance': results['distances'][0][i] if results['distances'] else 0.0
                    })
            
            logger.info(f"Found {len(similar_tasks)} similar tasks")
            
            return {
                'success': True,
                'results': similar_tasks
            }
            
        except Exception as e:
            logger.error(f"Failed to search similar tasks: {str(e)}")
            raise ChromaTaskSyncServiceError(
                "Failed to search similar tasks",
                details=str(e)
            )
