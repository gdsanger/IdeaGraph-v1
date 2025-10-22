"""
GitHub Task Synchronization Service for IdeaGraph

This module provides functionality to synchronize GitHub Issues with IdeaGraph Tasks.
It creates new tasks from GitHub issues that don't already exist in the system,
with duplicate detection based on GitHub Issue ID and title comparison.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from difflib import SequenceMatcher


logger = logging.getLogger('github_task_sync_service')


class GitHubTaskSyncServiceError(Exception):
    """Base exception for GitHub Task Sync Service errors"""
    
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


class GitHubTaskSyncService:
    """
    GitHub Task Synchronization Service
    
    Synchronizes GitHub Issues with IdeaGraph Tasks:
    - Creates tasks from GitHub issues that don't exist
    - Detects duplicates by GitHub Issue ID
    - Detects duplicates by title similarity
    - Marks potential duplicates with "*** Duplikat? ***" prefix
    """
    
    # Threshold for title similarity (0.0 to 1.0)
    TITLE_SIMILARITY_THRESHOLD = 0.85
    
    def __init__(self, settings=None):
        """
        Initialize GitHubTaskSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise GitHubTaskSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise GitHubTaskSyncServiceError("No settings found in database")
        
        if not self.settings.github_api_enabled:
            raise GitHubTaskSyncServiceError("GitHub API is not enabled in settings")
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles
        
        Args:
            title1: First title
            title2: Second title
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize titles (lowercase, strip whitespace)
        norm_title1 = title1.lower().strip()
        norm_title2 = title2.lower().strip()
        
        # Use SequenceMatcher for similarity calculation
        return SequenceMatcher(None, norm_title1, norm_title2).ratio()
    
    def _check_duplicate_by_issue_id(self, item, github_issue_id: int) -> bool:
        """
        Check if a task with the given GitHub Issue ID already exists for the item
        
        Args:
            item: Item model instance
            github_issue_id: GitHub issue number
        
        Returns:
            True if duplicate exists, False otherwise
        """
        from main.models import Task
        
        return Task.objects.filter(
            item=item,
            github_issue_id=github_issue_id
        ).exists()
    
    def _check_duplicate_by_title(self, item, title: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a task with similar title exists for the item
        
        Args:
            item: Item model instance
            title: GitHub issue title
        
        Returns:
            Tuple of (is_duplicate, matching_task_title)
        """
        from main.models import Task
        
        # Get all tasks for this item
        tasks = Task.objects.filter(item=item)
        
        for task in tasks:
            similarity = self._calculate_title_similarity(title, task.title)
            if similarity >= self.TITLE_SIMILARITY_THRESHOLD:
                return True, task.title
        
        return False, None
    
    def sync_github_issues_to_tasks(
        self,
        item,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        state: str = 'all',
        created_by=None
    ) -> Dict[str, Any]:
        """
        Synchronize GitHub issues to tasks for a specific item
        
        Args:
            item: Item model instance
            owner: GitHub repository owner (uses default from settings if not provided)
            repo: GitHub repository name (uses item's github_repo if not provided)
            state: Issue state filter ('open', 'closed', 'all')
            created_by: User who initiated the sync (for task creation)
        
        Returns:
            Dictionary with sync results:
                - success: bool
                - issues_checked: int
                - tasks_created: int
                - duplicates_by_id: int
                - duplicates_by_title: int
                - errors: list of error messages
        """
        from core.services.github_service import GitHubService, GitHubServiceError
        from main.models import Task
        
        # Validate inputs
        if not repo and not item.github_repo:
            return {
                'success': False,
                'error': 'No GitHub repository specified',
                'details': 'Please set a GitHub repository for this item'
            }
        
        # Use item's github_repo if not provided
        if not repo:
            repo = item.github_repo
        
        # Use default owner from settings if not provided
        if not owner:
            owner = self.settings.github_default_owner
        
        if not owner:
            return {
                'success': False,
                'error': 'No GitHub owner specified',
                'details': 'Please configure a default GitHub owner in settings'
            }
        
        results = {
            'success': True,
            'issues_checked': 0,
            'tasks_created': 0,
            'duplicates_by_id': 0,
            'duplicates_by_title': 0,
            'errors': []
        }
        
        try:
            # Initialize GitHub service
            github_service = GitHubService(self.settings)
            
            # Fetch all issues from GitHub (paginated)
            all_issues = []
            page = 1
            per_page = 100
            
            while True:
                logger.info(f"Fetching GitHub issues page {page} for {owner}/{repo}")
                result = github_service.list_issues(
                    owner=owner,
                    repo=repo,
                    state=state,
                    per_page=per_page,
                    page=page
                )
                
                if not result['success']:
                    results['errors'].append(f"Failed to fetch issues: {result.get('error', 'Unknown error')}")
                    break
                
                issues = result.get('issues', [])
                if not issues:
                    break
                
                all_issues.extend(issues)
                
                # Check if there are more pages
                if len(issues) < per_page:
                    break
                
                page += 1
            
            logger.info(f"Found {len(all_issues)} GitHub issues for {owner}/{repo}")
            
            # Process each issue
            for issue in all_issues:
                results['issues_checked'] += 1
                
                try:
                    # Skip pull requests (GitHub API includes PRs in issues endpoint)
                    if 'pull_request' in issue:
                        logger.debug(f"Skipping PR #{issue['number']}")
                        continue
                    
                    issue_number = issue['number']
                    issue_title = issue['title']
                    issue_body = issue.get('body', '')
                    issue_state = issue['state']
                    issue_url = issue['html_url']
                    
                    logger.info(f"Processing issue #{issue_number}: {issue_title}")
                    
                    # Check for duplicate by GitHub Issue ID
                    duplicate_by_id = self._check_duplicate_by_issue_id(item, issue_number)
                    
                    # Check for duplicate by title
                    duplicate_by_title, matching_title = self._check_duplicate_by_title(item, issue_title)
                    
                    # Determine task title
                    task_title = issue_title
                    is_potential_duplicate = False
                    
                    if duplicate_by_id:
                        logger.info(f"Issue #{issue_number} already exists (by ID)")
                        results['duplicates_by_id'] += 1
                        # Still create task but mark as duplicate
                        task_title = f"*** Duplikat? *** {issue_title}"
                        is_potential_duplicate = True
                    elif duplicate_by_title:
                        logger.info(f"Issue #{issue_number} appears to be duplicate of: {matching_title}")
                        results['duplicates_by_title'] += 1
                        # Create task but mark as potential duplicate
                        task_title = f"*** Duplikat? *** {issue_title}"
                        is_potential_duplicate = True
                    
                    # Create task
                    task = Task.objects.create(
                        title=task_title,
                        description=issue_body or '',
                        item=item,
                        github_issue_id=issue_number,
                        github_issue_url=issue_url,
                        status='done' if issue_state == 'closed' else 'new',
                        type='task',
                        created_by=created_by,
                        github_synced_at=datetime.now()
                    )
                    
                    results['tasks_created'] += 1
                    logger.info(f"Created task for issue #{issue_number}: {task_title}")
                    
                    # Optionally sync to Weaviate
                    try:
                        from core.services.weaviate_github_issue_sync_service import WeaviateGitHubIssueSyncService
                        weaviate_service = WeaviateGitHubIssueSyncService(self.settings)
                        weaviate_service.sync_issue_to_weaviate(issue, task=task, item=item)
                        weaviate_service.close()
                    except Exception as weaviate_error:
                        # Don't fail task creation if Weaviate sync fails
                        logger.warning(f"Weaviate sync failed for issue #{issue_number}: {str(weaviate_error)}")
                
                except Exception as task_error:
                    error_msg = f"Error processing issue #{issue.get('number', 'unknown')}: {str(task_error)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    continue
            
            logger.info(f"Sync completed: {results['tasks_created']} tasks created from {results['issues_checked']} issues")
            
            return results
        
        except GitHubServiceError as e:
            logger.error(f"GitHub service error: {e.message}")
            return {
                'success': False,
                'error': e.message,
                'details': e.details or ''
            }
        except Exception as e:
            logger.exception(f"Unexpected error during GitHub issue sync: {str(e)}")
            return {
                'success': False,
                'error': 'Unexpected error during synchronization',
                'details': str(e)
            }
