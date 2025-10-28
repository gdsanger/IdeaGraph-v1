"""
GitHub Pull Request Synchronization Service for IdeaGraph

This module provides functionality to synchronize GitHub Pull Requests with IdeaGraph.
It stores PRs in the local database and synchronizes them to Weaviate as KnowledgeObjects.

Features:
- Initial Load: Fetch all pull requests from a repository
- Incremental Sync: Fetch only PRs updated in the last hour
- Store PRs in SQLite database (GitHubPullRequest model)
- Sync PRs to Weaviate as KnowledgeObjects (type: "pull_request")
- Optional SharePoint JSON export
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from django.utils import timezone
from pathlib import Path


logger = logging.getLogger('github_pr_sync_service')


class GitHubPRSyncServiceError(Exception):
    """Base exception for GitHub PR Sync Service errors"""
    
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


class GitHubPRSyncService:
    """
    GitHub Pull Request Synchronization Service
    
    Synchronizes GitHub Pull Requests with IdeaGraph:
    - Fetches PRs from GitHub repositories
    - Stores PRs in local database (GitHubPullRequest model)
    - Syncs PRs to Weaviate as KnowledgeObjects
    - Optionally exports PR data to SharePoint folder (JSON)
    
    Supports two sync modes:
    1. Initial Load (--initial) - Fetch all PRs
    2. Incremental Sync (default) - Fetch PRs updated in last hour
    """
    
    def __init__(self, settings=None):
        """
        Initialize GitHubPRSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise GitHubPRSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise GitHubPRSyncServiceError("No settings found in database")
        
        if not self.settings.github_api_enabled:
            raise GitHubPRSyncServiceError("GitHub API is not enabled in settings")
    
    def _parse_github_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """
        Parse GitHub datetime string to Django timezone-aware datetime
        
        Args:
            datetime_str: ISO 8601 datetime string from GitHub
        
        Returns:
            Django timezone-aware datetime or None
        """
        if not datetime_str:
            return None
        
        try:
            # GitHub returns ISO 8601 format: 2023-01-15T10:30:00Z
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return timezone.make_aware(dt, timezone.utc) if timezone.is_naive(dt) else dt
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{datetime_str}': {str(e)}")
            return None
    
    def _extract_repo_info(self, github_repo: str) -> tuple[str, str]:
        """
        Extract owner and repo name from github_repo string
        
        Args:
            github_repo: Repository string (can be "owner/repo" or URL)
        
        Returns:
            Tuple of (owner, repo_name)
        
        Raises:
            GitHubPRSyncServiceError: If repo format is invalid
        """
        if not github_repo:
            raise GitHubPRSyncServiceError("GitHub repository not specified")
        
        # Handle various formats:
        # - "owner/repo"
        # - "https://github.com/owner/repo"
        # - "https://github.com/owner/repo.git"
        
        github_repo = github_repo.strip()
        
        # Remove .git suffix if present
        if github_repo.endswith('.git'):
            github_repo = github_repo[:-4]
        
        # Extract from URL format
        if 'github.com' in github_repo:
            parts = github_repo.split('github.com/')
            if len(parts) > 1:
                github_repo = parts[1]
        
        # Split into owner/repo
        parts = github_repo.strip('/').split('/')
        if len(parts) < 2:
            raise GitHubPRSyncServiceError(
                f"Invalid repository format: {github_repo}",
                details="Expected format: 'owner/repo' or 'https://github.com/owner/repo'"
            )
        
        return parts[-2], parts[-1]
    
    def _store_pr_in_database(self, item, pr_data: Dict[str, Any], repo_owner: str, repo_name: str) -> tuple[Any, bool]:
        """
        Store or update a pull request in the database
        
        Args:
            item: Item model instance
            pr_data: Pull request data from GitHub API
            repo_owner: Repository owner
            repo_name: Repository name
        
        Returns:
            Tuple of (GitHubPullRequest model instance, was_created boolean)
        """
        from main.models import GitHubPullRequest
        
        pr_number = pr_data['number']
        
        # Determine state (GitHub returns 'open' or 'closed', but we also track 'merged')
        state = pr_data['state']
        merged = pr_data.get('merged', False)
        if merged:
            state = 'merged'
        
        # Extract author information
        author = pr_data.get('user', {})
        author_login = author.get('login', '')
        author_avatar_url = author.get('avatar_url', '')
        
        # Parse dates
        created_at = self._parse_github_datetime(pr_data.get('created_at'))
        updated_at = self._parse_github_datetime(pr_data.get('updated_at'))
        closed_at = self._parse_github_datetime(pr_data.get('closed_at'))
        merged_at = self._parse_github_datetime(pr_data.get('merged_at'))
        
        # Extract branch information
        head = pr_data.get('head', {})
        base = pr_data.get('base', {})
        head_branch = head.get('ref', '')
        base_branch = base.get('ref', '')
        
        # Create or update PR
        pr, created = GitHubPullRequest.objects.update_or_create(
            item=item,
            pr_number=pr_number,
            repo_owner=repo_owner,
            repo_name=repo_name,
            defaults={
                'title': pr_data.get('title', ''),
                'body': pr_data.get('body', ''),
                'state': state,
                'html_url': pr_data.get('html_url', ''),
                'draft': pr_data.get('draft', False),
                'merged': merged,
                'merged_at': merged_at,
                'author_login': author_login,
                'author_avatar_url': author_avatar_url,
                'head_branch': head_branch,
                'base_branch': base_branch,
                'created_at_github': created_at or timezone.now(),
                'updated_at_github': updated_at or timezone.now(),
                'closed_at_github': closed_at,
            }
        )
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} PR #{pr_number} in database: {pr.title}")
        
        return pr, created
    
    def _sync_pr_to_weaviate(self, pr, item) -> bool:
        """
        Synchronize a pull request to Weaviate as a KnowledgeObject
        
        Args:
            pr: GitHubPullRequest model instance
            item: Item model instance
        
        Returns:
            True if successful, False otherwise
        """
        try:
            from core.services.weaviate_github_issue_sync_service import WeaviateGitHubIssueSyncService
            
            # Use the existing Weaviate service
            weaviate_service = WeaviateGitHubIssueSyncService(self.settings)
            
            # Convert PR to format expected by Weaviate service
            pr_data_for_weaviate = {
                'number': pr.pr_number,
                'title': pr.title,
                'body': pr.body,
                'state': pr.state,
                'html_url': pr.html_url,
                'user': {
                    'login': pr.author_login,
                    'avatar_url': pr.author_avatar_url,
                },
                'created_at': pr.created_at_github.isoformat() if pr.created_at_github else None,
                'updated_at': pr.updated_at_github.isoformat() if pr.updated_at_github else None,
                'closed_at': pr.closed_at_github.isoformat() if pr.closed_at_github else None,
                'merged_at': pr.merged_at.isoformat() if pr.merged_at else None,
                'merged': pr.merged,
                'draft': pr.draft,
            }
            
            # Sync to Weaviate with type="pull_request"
            weaviate_service.sync_issue_to_weaviate(
                pr_data_for_weaviate,
                item=item,
                issue_type='pull_request'  # Distinguish PRs from issues
            )
            
            weaviate_service.close()
            logger.info(f"Synced PR #{pr.pr_number} to Weaviate")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to sync PR #{pr.pr_number} to Weaviate: {str(e)}")
            return False
    
    def _export_pr_to_sharepoint(self, pr, item) -> bool:
        """
        Export pull request data to SharePoint folder as JSON
        
        Args:
            pr: GitHubPullRequest model instance
            item: Item model instance
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get SharePoint folder path from settings
            sharepoint_base_path = getattr(self.settings, 'sharepoint_base_path', None)
            if not sharepoint_base_path:
                logger.debug("SharePoint export skipped: no base path configured")
                return False
            
            # Construct path: {sharepoint_base_path}/{item_id}/github_prs/
            item_folder = Path(sharepoint_base_path) / str(item.id) / 'github_prs'
            item_folder.mkdir(parents=True, exist_ok=True)
            
            # Create JSON file
            pr_file = item_folder / f"pr_{pr.pr_number}.json"
            
            pr_data = {
                'pr_number': pr.pr_number,
                'title': pr.title,
                'body': pr.body,
                'state': pr.state,
                'html_url': pr.html_url,
                'draft': pr.draft,
                'merged': pr.merged,
                'merged_at': pr.merged_at.isoformat() if pr.merged_at else None,
                'author_login': pr.author_login,
                'author_avatar_url': pr.author_avatar_url,
                'head_branch': pr.head_branch,
                'base_branch': pr.base_branch,
                'repo_owner': pr.repo_owner,
                'repo_name': pr.repo_name,
                'created_at_github': pr.created_at_github.isoformat() if pr.created_at_github else None,
                'updated_at_github': pr.updated_at_github.isoformat() if pr.updated_at_github else None,
                'closed_at_github': pr.closed_at_github.isoformat() if pr.closed_at_github else None,
                'synced_at': pr.synced_at.isoformat() if pr.synced_at else None,
            }
            
            with open(pr_file, 'w', encoding='utf-8') as f:
                json.dump(pr_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported PR #{pr.pr_number} to SharePoint: {pr_file}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to export PR #{pr.pr_number} to SharePoint: {str(e)}")
            return False
    
    def sync_pull_requests(
        self,
        item,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        initial_load: bool = False,
        export_to_sharepoint: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronize GitHub pull requests for a specific item
        
        Args:
            item: Item model instance
            owner: GitHub repository owner (extracted from item.github_repo if not provided)
            repo: GitHub repository name (extracted from item.github_repo if not provided)
            initial_load: If True, fetch all PRs. If False, fetch only PRs updated in last hour
            export_to_sharepoint: If True, export PR data to SharePoint folder as JSON
        
        Returns:
            Dictionary with sync results:
                - success: bool
                - prs_checked: int
                - prs_created: int
                - prs_updated: int
                - prs_synced_to_weaviate: int
                - prs_exported_to_sharepoint: int
                - errors: list of error messages
        """
        from core.services.github_service import GitHubService, GitHubServiceError
        
        # Extract repository information
        if not owner or not repo:
            try:
                owner, repo = self._extract_repo_info(item.github_repo)
            except GitHubPRSyncServiceError as e:
                return {
                    'success': False,
                    'error': e.message,
                    'details': e.details or ''
                }
        
        results = {
            'success': True,
            'prs_checked': 0,
            'prs_created': 0,
            'prs_updated': 0,
            'prs_synced_to_weaviate': 0,
            'prs_exported_to_sharepoint': 0,
            'errors': []
        }
        
        try:
            # Initialize GitHub service
            github_service = GitHubService(self.settings)
            
            # Determine state filter
            # For initial load, fetch all PRs (open, closed, merged)
            # For incremental, fetch all but rely on updated_at filtering
            state = 'all'
            
            # Fetch all pull requests from GitHub (paginated)
            all_prs = []
            page = 1
            per_page = 100
            
            # Calculate time threshold for incremental sync (last hour)
            if not initial_load:
                time_threshold = timezone.now() - timedelta(hours=1)
                logger.info(f"Incremental sync: fetching PRs updated since {time_threshold}")
            else:
                logger.info(f"Initial load: fetching all PRs for {owner}/{repo}")
            
            while True:
                logger.info(f"Fetching GitHub PRs page {page} for {owner}/{repo}")
                result = github_service.list_pull_requests(
                    owner=owner,
                    repo=repo,
                    state=state,
                    per_page=per_page,
                    page=page
                )
                
                if not result['success']:
                    results['errors'].append(f"Failed to fetch PRs: {result.get('error', 'Unknown error')}")
                    break
                
                prs = result.get('pull_requests', [])
                if not prs:
                    break
                
                # For incremental sync, filter by updated_at
                if not initial_load:
                    filtered_prs = []
                    for pr in prs:
                        updated_at = self._parse_github_datetime(pr.get('updated_at'))
                        if updated_at and updated_at >= time_threshold:
                            filtered_prs.append(pr)
                    
                    prs = filtered_prs
                    
                    # If no PRs match the time filter, we can stop paginating
                    if not prs:
                        logger.info("No more PRs matching time threshold, stopping pagination")
                        break
                
                all_prs.extend(prs)
                
                # Check if there are more pages
                if len(result.get('pull_requests', [])) < per_page:
                    break
                
                page += 1
            
            logger.info(f"Found {len(all_prs)} GitHub PRs for {owner}/{repo}")
            
            # Process each PR
            for pr_data in all_prs:
                results['prs_checked'] += 1
                
                try:
                    pr_number = pr_data['number']
                    pr_title = pr_data['title']
                    
                    logger.info(f"Processing PR #{pr_number}: {pr_title}")
                    
                    # Store in database
                    pr, was_created = self._store_pr_in_database(item, pr_data, owner, repo)
                    
                    # Track if created or updated
                    if was_created:
                        results['prs_created'] += 1
                    else:
                        results['prs_updated'] += 1
                    
                    # Sync to Weaviate
                    if self._sync_pr_to_weaviate(pr, item):
                        results['prs_synced_to_weaviate'] += 1
                    
                    # Export to SharePoint (optional)
                    if export_to_sharepoint:
                        if self._export_pr_to_sharepoint(pr, item):
                            results['prs_exported_to_sharepoint'] += 1
                
                except Exception as pr_error:
                    error_msg = f"Error processing PR #{pr_data.get('number', 'unknown')}"
                    logger.error(f"{error_msg}: {str(pr_error)}")
                    results['errors'].append(error_msg)
                    continue
            
            logger.info(
                f"Sync completed: {results['prs_created']} created, "
                f"{results['prs_updated']} updated from {results['prs_checked']} PRs"
            )
            
            return results
        
        except GitHubServiceError as e:
            logger.error(f"GitHub service error: {e.message}")
            return {
                'success': False,
                'error': e.message,
                'details': e.details or ''
            }
        except Exception as e:
            logger.exception(f"Unexpected error during GitHub PR sync: {str(e)}")
            return {
                'success': False,
                'error': 'Unexpected error during synchronization',
                'details': str(e)
            }
