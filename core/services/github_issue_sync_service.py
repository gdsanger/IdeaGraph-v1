"""
GitHub Issue Synchronization Service for IdeaGraph (DEPRECATED - ChromaDB)

⚠️ DEPRECATED: This service uses ChromaDB with a separate "GitHubIssues" collection,
which does not comply with the IdeaGraph KnowledgeObject architecture.

USE INSTEAD: WeaviateGitHubIssueSyncService (weaviate_github_issue_sync_service.py)
which correctly stores all GitHub Issues in the unified KnowledgeObject collection.

This module is kept for reference and backward compatibility only.
It is not used in production code and is not exported from core.services.

Legacy description:
This module provides synchronization between GitHub Issues/PRs and IdeaGraph tasks,
storing issue and PR data in ChromaDB for semantic search and retrieval.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

import chromadb
from urllib.parse import urlparse, parse_qs


logger = logging.getLogger('github_issue_sync_service')


class GitHubIssueSyncServiceError(Exception):
    """Base exception for GitHubIssueSyncService errors"""
    
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


class GitHubIssueSyncService:
    """
    GitHub Issue Synchronization Service (DEPRECATED)
    
    ⚠️ DEPRECATED: This service stores GitHub Issues in a separate "GitHubIssues" collection
    in ChromaDB, which violates the KnowledgeObject architecture requirement.
    
    USE INSTEAD: WeaviateGitHubIssueSyncService
    
    Legacy description:
    Synchronizes GitHub Issues and Pull Requests with:
    - IdeaGraph Tasks (status updates)
    - ChromaDB GitHubIssues collection (for semantic search)
    
    Features:
    - Monitors GitHub issues and updates task status when closed
    - Stores issue and PR descriptions in ChromaDB with metadata
    - Supports filtering by repository, labels, and state
    """
    
    COLLECTION_NAME = 'GitHubIssues'  # DEPRECATED: Should use KnowledgeObject instead
    
    def __init__(self, settings=None):
        """
        Initialize GitHubIssueSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise GitHubIssueSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise GitHubIssueSyncServiceError("No settings found in database")
        
        # Initialize ChromaDB client
        self._client = None
        self._collection = None
        self._initialize_chroma_client()
    
    def _initialize_chroma_client(self):
        """
        Initialize ChromaDB client and GitHubIssues collection
        
        Raises:
            GitHubIssueSyncServiceError: If initialization fails
        """
        try:
            # Use local ChromaDB instance
            logger.info("Initializing ChromaDB local client for GitHub Issues at localhost:8003")
            
            self._client = chromadb.HttpClient(
                host="localhost",
                port=8003
            )

            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "GitHub Issues and Pull Requests with embeddings"}
            )

            logger.info(f"ChromaDB collection '{self.COLLECTION_NAME}' initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise GitHubIssueSyncServiceError(
                "Failed to initialize ChromaDB client",
                details=str(e)
            )

    def _resolve_cloud_credentials(self) -> Dict[str, str]:
        """Resolve ChromaDB credentials from database settings."""
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
            raise GitHubIssueSyncServiceError(message)

        return {
            'api_key': api_key,
            'database': database,
            'tenant': tenant,
        }

    def _build_cloud_client_kwargs(self, *, database_value: str, api_key: str, tenant: str) -> Dict[str, Any]:
        """Build keyword arguments for ChromaDB HttpClient configuration."""
        raw_value = (database_value or '').strip()

        host = 'api.trychroma.com'
        port = 443
        use_ssl = True
        database_name: Optional[str] = None

        if raw_value:
            is_plain_database = not any(ch in raw_value for ch in ('/', ':')) and 'http' not in raw_value.lower()

            if is_plain_database:
                database_name = raw_value
            else:
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
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI
        
        Args:
            text: Text to generate embedding for
        
        Returns:
            List of floats representing the embedding vector
        
        Raises:
            GitHubIssueSyncServiceError: If embedding generation fails
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * 3072  # OpenAI text-embedding-3-large embedding size
        
        # Check if OpenAI API is enabled
        if not self.settings.openai_api_enabled or not self.settings.openai_api_key:
            error_msg = "OpenAI API is not enabled or API key is missing. Please enable OpenAI API in Settings and configure your API key."
            logger.error(error_msg)
            raise GitHubIssueSyncServiceError(
                error_msg,
                details="Configure OpenAI settings: openai_api_enabled=True, openai_api_key, openai_api_base_url"
            )
        
        try:
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
                logger.error(f"Embedding API failed: {response.status_code}")
                raise GitHubIssueSyncServiceError(
                    "Failed to generate embedding",
                    details=f"API returned status {response.status_code}"
                )
                
        except GitHubIssueSyncServiceError:
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise GitHubIssueSyncServiceError(
                "Failed to generate embedding",
                details=str(e)
            )
    
    def sync_issue_to_chroma(self, issue: Dict[str, Any], task=None) -> Dict[str, Any]:
        """
        Synchronize a GitHub issue to ChromaDB
        
        Args:
            issue: GitHub issue data from API
            task: Optional Task model instance linked to this issue
        
        Returns:
            Dictionary with success status and message
        
        Raises:
            GitHubIssueSyncServiceError: If sync fails
        """
        try:
            issue_number = issue.get('number')
            issue_title = issue.get('title', '')
            issue_body = issue.get('body', '')
            issue_state = issue.get('state', 'open')
            
            logger.info(f"Syncing issue #{issue_number} to ChromaDB: {issue_title}")
            
            # Generate unique ID for ChromaDB
            chroma_id = f"issue_{issue_number}"
            
            # Generate embedding from issue body
            embedding = self._generate_embedding(issue_body or issue_title)
            
            # Prepare metadata
            metadata = {
                'type': 'issue',
                'github_issue_id': issue_number,
                'github_issue_title': issue_title,
                'github_issue_state': issue_state,
                'github_issue_url': issue.get('html_url', ''),
            }
            
            # Add task metadata if available
            if task:
                tag_names = list(task.tags.values_list('name', flat=True))
                metadata.update({
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'task_status': task.status,
                    'task_tags': ','.join(tag_names),
                    'item_id': str(task.item.id) if task.item else '',
                    'item_title': task.item.title if task.item else '',
                })
            else:
                metadata.update({
                    'task_id': '',
                    'task_title': '',
                    'task_status': '',
                    'task_tags': '',
                    'item_id': '',
                    'item_title': '',
                })
            
            # Add to collection (upsert to handle updates)
            self._collection.upsert(
                ids=[chroma_id],
                embeddings=[embedding],
                documents=[issue_body or issue_title],
                metadatas=[metadata]
            )
            
            logger.info(f"Successfully synced issue #{issue_number} to ChromaDB")
            
            return {
                'success': True,
                'message': f'Issue #{issue_number} synced to ChromaDB'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync issue to ChromaDB: {str(e)}")
            raise GitHubIssueSyncServiceError(
                "Failed to sync issue to ChromaDB",
                details=str(e)
            )
    
    def sync_pull_request_to_chroma(self, pr: Dict[str, Any], task=None) -> Dict[str, Any]:
        """
        Synchronize a GitHub pull request to ChromaDB
        
        Args:
            pr: GitHub pull request data from API
            task: Optional Task model instance linked to this PR
        
        Returns:
            Dictionary with success status and message
        
        Raises:
            GitHubIssueSyncServiceError: If sync fails
        """
        try:
            pr_number = pr.get('number')
            pr_title = pr.get('title', '')
            pr_body = pr.get('body', '')
            pr_state = pr.get('state', 'open')
            
            logger.info(f"Syncing PR #{pr_number} to ChromaDB: {pr_title}")
            
            # Generate unique ID for ChromaDB
            chroma_id = f"pr_{pr_number}"
            
            # Generate embedding from PR body
            embedding = self._generate_embedding(pr_body or pr_title)
            
            # Prepare metadata
            metadata = {
                'type': 'pull_request',
                'github_issue_id': pr_number,  # PRs are also issues in GitHub
                'github_issue_title': pr_title,
                'github_issue_state': pr_state,
                'github_issue_url': pr.get('html_url', ''),
                'pr_merged': pr.get('merged', False),
                'pr_mergeable': pr.get('mergeable', False),
            }
            
            # Add task metadata if available
            if task:
                tag_names = list(task.tags.values_list('name', flat=True))
                metadata.update({
                    'task_id': str(task.id),
                    'task_title': task.title,
                    'task_status': task.status,
                    'task_tags': ','.join(tag_names),
                    'item_id': str(task.item.id) if task.item else '',
                    'item_title': task.item.title if task.item else '',
                })
            else:
                metadata.update({
                    'task_id': '',
                    'task_title': '',
                    'task_status': '',
                    'task_tags': '',
                    'item_id': '',
                    'item_title': '',
                })
            
            # Add to collection (upsert to handle updates)
            self._collection.upsert(
                ids=[chroma_id],
                embeddings=[embedding],
                documents=[pr_body or pr_title],
                metadatas=[metadata]
            )
            
            logger.info(f"Successfully synced PR #{pr_number} to ChromaDB")
            
            return {
                'success': True,
                'message': f'PR #{pr_number} synced to ChromaDB'
            }
            
        except Exception as e:
            logger.error(f"Failed to sync PR to ChromaDB: {str(e)}")
            raise GitHubIssueSyncServiceError(
                "Failed to sync PR to ChromaDB",
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
        Stores issue and PR data in ChromaDB
        
        Args:
            repo: Repository name (uses default if not provided)
            owner: Repository owner (uses default if not provided)
        
        Returns:
            Dictionary with sync results
        
        Raises:
            GitHubIssueSyncServiceError: If sync fails
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
                                # Sync PR to ChromaDB
                                self.sync_pull_request_to_chroma(pr, task)
                                results['prs_synced'] += 1
                        else:
                            # Sync issue to ChromaDB
                            self.sync_issue_to_chroma(issue, task)
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
            raise GitHubIssueSyncServiceError(
                "Failed to sync tasks with GitHub issues",
                details=str(e)
            )
    
    def search_similar(self, query_text: str, n_results: int = 5, 
                      issue_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for similar issues or PRs using semantic similarity
        
        Args:
            query_text: Text to search for
            n_results: Number of results to return
            issue_type: Optional filter ('issue' or 'pull_request')
        
        Returns:
            Dictionary containing:
                - success: bool
                - results: list of similar issues/PRs with metadata
        
        Raises:
            GitHubIssueSyncServiceError: If search fails
        """
        try:
            logger.info(f"Searching for similar GitHub issues/PRs: '{query_text[:50]}...'")
            
            # Generate embedding for query
            query_embedding = self._generate_embedding(query_text)
            
            # Prepare where filter if type is specified
            where_filter = None
            if issue_type in ['issue', 'pull_request']:
                where_filter = {'type': issue_type}
            
            # Search collection
            search_kwargs = {
                'query_embeddings': [query_embedding],
                'n_results': n_results,
                'include': ['metadatas', 'documents', 'distances']
            }
            
            if where_filter:
                search_kwargs['where'] = where_filter
            
            results = self._collection.query(**search_kwargs)
            
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
            raise GitHubIssueSyncServiceError(
                "Failed to search similar items",
                details=str(e)
            )
