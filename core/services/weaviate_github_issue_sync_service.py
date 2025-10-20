"""
Weaviate GitHub Issue Synchronization Service for IdeaGraph

This module provides synchronization of GitHub Issues and Pull Requests with Weaviate vector database.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery


logger = logging.getLogger('weaviate_github_issue_sync_service')


class WeaviateGitHubIssueSyncServiceError(Exception):
    """Base exception for WeaviateGitHubIssueSyncService errors"""
    
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


class WeaviateGitHubIssueSyncService:
    """
    Weaviate GitHub Issue Synchronization Service
    
    Synchronizes GitHub Issues and Pull Requests with Weaviate vector database:
    - Stores issue/PR descriptions as embeddings
    - Stores metadata (title, state, URL, issue number, references to tasks/items)
    - Supports create, update, and delete operations
    """
    
    COLLECTION_NAME = 'GitHubIssue'
    
    def __init__(self, settings=None):
        """
        Initialize WeaviateGitHubIssueSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise WeaviateGitHubIssueSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise WeaviateGitHubIssueSyncServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            WeaviateGitHubIssueSyncServiceError: If initialization fails
        """
        try:
            # Use local Weaviate instance at localhost:8081 with no authentication
            logger.info("Initializing Weaviate client for GitHub Issues at localhost:8081")
            
            self._client = weaviate.connect_to_local(
                host="localhost",
                port=8081
            )

            logger.info(f"Weaviate client initialized, collection '{self.COLLECTION_NAME}' ready")

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {str(e)}")
            raise WeaviateGitHubIssueSyncServiceError(
                "Failed to initialize Weaviate client",
                details=str(e)
            )
    
    def sync_issue_to_weaviate(self, issue: Dict[str, Any], task=None, item=None, uuid: str = None) -> Dict[str, Any]:
        """
        Synchronize a GitHub issue to Weaviate
        
        Args:
            issue: GitHub issue data from API
            task: Optional Task model instance linked to this issue
            item: Optional Item model instance linked to this issue
            uuid: Optional UUID to use for the issue (for consistency)
        
        Returns:
            Dictionary with success status and message
        
        Raises:
            WeaviateGitHubIssueSyncServiceError: If sync fails
        """
        try:
            issue_number = issue.get('number')
            issue_title = issue.get('title', '')
            issue_body = issue.get('body', '')
            issue_state = issue.get('state', 'open')
            issue_url = issue.get('html_url', '')
            created_at = issue.get('created_at', datetime.now().isoformat())
            
            logger.info(f"Syncing issue #{issue_number} to Weaviate: {issue_title}")
            
            # Prepare properties
            properties = {
                'issue_title': issue_title,
                'issue_description': issue_body or '',
                'issue_state': issue_state,
                'issue_url': issue_url,
                'issue_number': issue_number,
                'createdAt': created_at,
            }
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Generate UUID if not provided (use issue_number as part of UUID generation)
            import uuid as uuid_lib
            if not uuid:
                # Create a deterministic UUID based on issue number and URL
                uuid = str(uuid_lib.uuid5(uuid_lib.NAMESPACE_URL, issue_url))
            
            # Upsert to collection with our UUID
            collection.data.insert(
                properties=properties,
                uuid=uuid
            )
            
            # Add task reference if exists
            if task:
                try:
                    collection.data.reference_add(
                        from_uuid=uuid,
                        from_property="task",
                        to=str(task.id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to add task reference: {str(e)}")
            
            # Add item reference if exists
            if item:
                try:
                    collection.data.reference_add(
                        from_uuid=uuid,
                        from_property="item",
                        to=str(item.id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to add item reference: {str(e)}")
            
            logger.info(f"Successfully synced issue #{issue_number} to Weaviate")
            
            return {
                'success': True,
                'message': f'Issue #{issue_number} synced to Weaviate',
                'uuid': uuid
            }
            
        except Exception as e:
            logger.error(f"Failed to sync issue to Weaviate: {str(e)}")
            raise WeaviateGitHubIssueSyncServiceError(
                "Failed to sync issue to Weaviate",
                details=str(e)
            )
    
    def sync_pull_request_to_weaviate(self, pr: Dict[str, Any], task=None, item=None, uuid: str = None) -> Dict[str, Any]:
        """
        Synchronize a GitHub pull request to Weaviate
        
        Args:
            pr: GitHub pull request data from API
            task: Optional Task model instance linked to this PR
            item: Optional Item model instance linked to this PR
            uuid: Optional UUID to use for the PR (for consistency)
        
        Returns:
            Dictionary with success status and message
        
        Raises:
            WeaviateGitHubIssueSyncServiceError: If sync fails
        """
        try:
            pr_number = pr.get('number')
            pr_title = pr.get('title', '')
            pr_body = pr.get('body', '')
            pr_state = pr.get('state', 'open')
            pr_url = pr.get('html_url', '')
            created_at = pr.get('created_at', datetime.now().isoformat())
            
            logger.info(f"Syncing PR #{pr_number} to Weaviate: {pr_title}")
            
            # Prepare properties (same as issue since PRs are issues in GitHub)
            properties = {
                'issue_title': pr_title,
                'issue_description': pr_body or '',
                'issue_state': pr_state,
                'issue_url': pr_url,
                'issue_number': pr_number,
                'createdAt': created_at,
            }
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Generate UUID if not provided
            import uuid as uuid_lib
            if not uuid:
                uuid = str(uuid_lib.uuid5(uuid_lib.NAMESPACE_URL, pr_url))
            
            # Upsert to collection
            collection.data.insert(
                properties=properties,
                uuid=uuid
            )
            
            # Add task reference if exists
            if task:
                try:
                    collection.data.reference_add(
                        from_uuid=uuid,
                        from_property="task",
                        to=str(task.id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to add task reference: {str(e)}")
            
            # Add item reference if exists
            if item:
                try:
                    collection.data.reference_add(
                        from_uuid=uuid,
                        from_property="item",
                        to=str(item.id)
                    )
                except Exception as e:
                    logger.warning(f"Failed to add item reference: {str(e)}")
            
            logger.info(f"Successfully synced PR #{pr_number} to Weaviate")
            
            return {
                'success': True,
                'message': f'PR #{pr_number} synced to Weaviate',
                'uuid': uuid
            }
            
        except Exception as e:
            logger.error(f"Failed to sync PR to Weaviate: {str(e)}")
            raise WeaviateGitHubIssueSyncServiceError(
                "Failed to sync PR to Weaviate",
                details=str(e)
            )
    
    def delete_issue(self, uuid: str) -> Dict[str, Any]:
        """
        Delete a GitHub issue from Weaviate
        
        Args:
            uuid: UUID string of the issue to delete
        
        Returns:
            Dictionary with success status and message
        
        Raises:
            WeaviateGitHubIssueSyncServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting issue from Weaviate: {uuid}")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Delete from collection
            collection.data.delete_by_id(str(uuid))
            
            logger.info(f"Successfully deleted issue {uuid} from Weaviate")
            
            return {
                'success': True,
                'message': f'Issue {uuid} deleted from Weaviate'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete issue {uuid} from Weaviate: {str(e)}")
            raise WeaviateGitHubIssueSyncServiceError(
                f"Failed to delete issue from Weaviate",
                details=str(e)
            )
    
    def search_similar_issues(self, query_text: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Search for similar GitHub issues using semantic similarity
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
        
        Returns:
            Dictionary containing:
                - success: bool
                - results: list of similar issues with metadata
        
        Raises:
            WeaviateGitHubIssueSyncServiceError: If search fails
        """
        try:
            logger.info(f"Searching for similar GitHub issues: '{query_text[:50]}...'")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Search using near_text
            response = collection.query.near_text(
                query=query_text,
                limit=n_results,
                return_metadata=MetadataQuery(distance=True)
            )
            
            # Format results
            similar_issues = []
            for obj in response.objects:
                similar_issues.append({
                    'id': str(obj.uuid),
                    'metadata': {
                        'issue_title': obj.properties.get('issue_title', ''),
                        'issue_description': obj.properties.get('issue_description', ''),
                        'issue_state': obj.properties.get('issue_state', ''),
                        'issue_url': obj.properties.get('issue_url', ''),
                        'issue_number': obj.properties.get('issue_number', 0),
                        'created_at': obj.properties.get('createdAt', ''),
                    },
                    'document': obj.properties.get('issue_description', ''),
                    'distance': obj.metadata.distance if obj.metadata else 0.0
                })
            
            logger.info(f"Found {len(similar_issues)} similar GitHub issues")
            
            return {
                'success': True,
                'results': similar_issues
            }
            
        except Exception as e:
            logger.error(f"Failed to search similar issues: {str(e)}")
            raise WeaviateGitHubIssueSyncServiceError(
                "Failed to search similar issues",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate client connection closed")
