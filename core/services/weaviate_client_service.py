"""
Weaviate Client Service for Actions API

This service provides a simplified interface to Weaviate for the Actions API,
wrapping the existing WeaviateSearchService and adding file content retrieval.
"""
import logging
from typing import List, Dict, Any, Optional
from core.services.weaviate_search_service import WeaviateSearchService, WeaviateSearchServiceError

logger = logging.getLogger(__name__)


class WeaviateClientServiceError(Exception):
    """Exception for WeaviateClientService errors"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class WeaviateClientService:
    """
    Weaviate Client Service for Actions API
    
    Provides:
    - semantic_search: Search across all knowledge objects
    - get_file_by_id: Retrieve file content by file ID
    """
    
    def __init__(self, settings=None):
        """Initialize the service with settings"""
        self.search_service = WeaviateSearchService(settings=settings)
    
    def semantic_search(
        self,
        query: str,
        types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across knowledge objects
        
        Args:
            query: Search query text
            types: Optional list of object types to filter by
                   (Item, Task, GitHubIssue, PullRequest, File, Email, Note, Transcript, Milestone)
            limit: Maximum number of results to return
        
        Returns:
            List of context hits with score, excerpt, and metadata
        
        Raises:
            WeaviateClientServiceError: If search fails
        """
        try:
            # Perform search using the search service
            results = self.search_service.search_knowledge(
                query=query,
                types=types,
                limit=limit
            )
            
            # Transform results to ContextHit format
            context_hits = []
            for result in results.get('results', []):
                # Extract metadata
                metadata = result.get('metadata', {})
                
                # Generate excerpt (truncate to ~350 chars)
                content = result.get('content', '')
                excerpt = content[:350] + '...' if len(content) > 350 else content
                
                context_hit = {
                    'id': result.get('id'),
                    'type': result.get('type', 'Unknown'),
                    'title': result.get('title', 'Untitled'),
                    'excerpt': excerpt,
                    'score': result.get('score', 0.0),
                    'metadata': metadata
                }
                context_hits.append(context_hit)
            
            # Sort by score (descending)
            context_hits.sort(key=lambda x: x['score'], reverse=True)
            
            return context_hits
            
        except WeaviateSearchServiceError as e:
            logger.error(f"Semantic search failed: {e.message}")
            raise WeaviateClientServiceError(
                "Semantic search failed",
                details=e.details or str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in semantic search: {str(e)}")
            raise WeaviateClientServiceError(
                "Semantic search failed",
                details=str(e)
            )
    
    def get_file_by_id(self, file_id: str) -> Dict[str, Any]:
        """
        Retrieve file content and metadata by file ID
        
        Args:
            file_id: The file ID (UUID or SharePoint ID)
        
        Returns:
            Dictionary with file content and metadata:
            {
                'file_id': str,
                'filename': str,
                'content_type': str,
                'content': str,
                'size': int,
                'excerpt': str,
                'created_at': datetime
            }
        
        Raises:
            WeaviateClientServiceError: If file not found or retrieval fails
        """
        try:
            # Search for the file by ID
            # We'll look for KnowledgeObject with type=File and matching ID
            results = self.search_service.search_knowledge(
                query=file_id,
                types=['File'],
                limit=1
            )
            
            if not results.get('results'):
                raise WeaviateClientServiceError(
                    f"File not found: {file_id}",
                    details="No file with this ID exists in Weaviate"
                )
            
            file_obj = results['results'][0]
            
            # Extract file information
            content = file_obj.get('content', '')
            metadata = file_obj.get('metadata', {})
            
            # Generate excerpt
            excerpt = content[:350] + '...' if len(content) > 350 else content
            
            return {
                'file_id': file_obj.get('id', file_id),
                'filename': file_obj.get('title', 'Unknown'),
                'content_type': metadata.get('content_type', 'text/plain'),
                'content': content,
                'size': len(content),
                'excerpt': excerpt,
                'created_at': metadata.get('created_at')
            }
            
        except WeaviateClientServiceError:
            raise
        except WeaviateSearchServiceError as e:
            logger.error(f"File retrieval failed: {e.message}")
            raise WeaviateClientServiceError(
                "File retrieval failed",
                details=e.details or str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error retrieving file: {str(e)}")
            raise WeaviateClientServiceError(
                "File retrieval failed",
                details=str(e)
            )
