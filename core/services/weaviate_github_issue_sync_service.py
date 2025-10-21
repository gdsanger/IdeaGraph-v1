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
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise WeaviateGitHubIssueSyncServiceError(
                        "Weaviate Cloud enabled but URL or API key not configured"
                    )
                
                logger.info(f"Initializing Weaviate client for GitHub Issues (cloud): {self.settings.weaviate_url}")
                
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
                )
            else:
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
            
            # Check if object already exists
            exists = collection.data.exists(uuid)
            
            if exists:
                # Update existing object (PATCH operation)
                logger.info(f"Issue #{issue_number} already exists in Weaviate, updating...")
                collection.data.update(
                    uuid=uuid,
                    properties=properties
                )
            else:
                # Insert new object (POST operation)
                logger.info(f"Issue #{issue_number} is new, inserting into Weaviate...")
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
            
            # Check if object already exists
            exists = collection.data.exists(uuid)
            
            if exists:
                # Update existing object (PATCH operation)
                logger.info(f"PR #{pr_number} already exists in Weaviate, updating...")
                collection.data.update(
                    uuid=uuid,
                    properties=properties
                )
            else:
                # Insert new object (POST operation)
                logger.info(f"PR #{pr_number} is new, inserting into Weaviate...")
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
    
    def sync_tasks_with_github_issues(
        self,
        repo: Optional[str] = None,
        owner: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronize tasks with their linked GitHub issues
        Updates task status when GitHub issue is closed
        Stores issue and PR data in Weaviate
        
        Args:
            repo: Repository name (uses default if not provided)
            owner: Repository owner (uses default if not provided)
        
        Returns:
            Dictionary with sync results
        
        Raises:
            WeaviateGitHubIssueSyncServiceError: If sync fails
        """
        try:
            from main.models import Task
            from core.services.github_service import GitHubService
            
            logger.info("Starting GitHub issues and tasks synchronization")
            
            # Initialize GitHub service
            github_service = GitHubService(self.settings)
            
            # Find all tasks with linked GitHub issues that are not done
            # This optimization skips tasks that are already completed to save resources
            tasks_with_issues = Task.objects.filter(
                github_issue_id__isnull=False
            ).exclude(
                status='done'
            ).select_related('item', 'created_by').prefetch_related('tags')
            
            results = {
                'tasks_checked': 0,
                'tasks_updated': 0,
                'issues_synced': 0,
                'prs_synced': 0,
                'errors': []
            }
            
            for task in tasks_with_issues:
                results['tasks_checked'] += 1
                
                try:
                    # Get issue from GitHub
                    issue_result = github_service.get_issue(
                        issue_number=task.github_issue_id,
                        repo=repo,
                        owner=owner
                    )
                    
                    if issue_result['success']:
                        issue = issue_result['issue']
                        
                        # Check if it's a pull request (GitHub API returns PRs as issues too)
                        is_pr = 'pull_request' in issue
                        
                        if is_pr:
                            # Fetch full PR data
                            pr_result = github_service.get_pull_request(
                                pr_number=task.github_issue_id,
                                repo=repo,
                                owner=owner
                            )
                            if pr_result['success']:
                                pr = pr_result['pull_request']
                                # Sync PR to Weaviate
                                self.sync_pull_request_to_weaviate(pr, task, task.item if task.item else None)
                                results['prs_synced'] += 1
                        else:
                            # Sync issue to Weaviate
                            self.sync_issue_to_weaviate(issue, task, task.item if task.item else None)
                            results['issues_synced'] += 1
                        
                        # Update task status if issue/PR is closed and task is not done
                        issue_state = issue.get('state', 'open')
                        if issue_state == 'closed' and task.status != 'done':
                            task.mark_as_done()
                            results['tasks_updated'] += 1
                            logger.info(
                                f"Task {task.id} marked as done (GitHub issue #{task.github_issue_id} closed)"
                            )
                
                except Exception as e:
                    error_msg = f"Error syncing task {task.id}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            logger.info(
                f"Synchronization complete: {results['tasks_checked']} tasks checked, "
                f"{results['tasks_updated']} tasks updated, "
                f"{results['issues_synced']} issues synced, "
                f"{results['prs_synced']} PRs synced"
            )
            
            return {
                'success': True,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Failed to sync tasks with GitHub issues: {str(e)}")
            raise WeaviateGitHubIssueSyncServiceError(
                "Failed to sync tasks with GitHub issues",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate client connection closed")
