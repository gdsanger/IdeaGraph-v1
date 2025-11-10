"""
Sentry Task Sync Service for IdeaGraph

This service fetches errors from Sentry API and creates Bug tasks in IdeaGraph.
It includes duplicate detection to prevent creating the same task multiple times.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone

from core.services.sentry_service import SentryService
from core.logger_config import get_logger
from main.models import Item, Task, Settings

logger = get_logger('sentry_task_sync_service')


class SentryTaskSyncService:
    """Service to sync Sentry errors to IdeaGraph tasks"""
    
    def __init__(self):
        """Initialize the Sentry Task Sync Service"""
        self.settings = self._get_settings()
    
    def _get_settings(self) -> Optional[Settings]:
        """Get the application settings"""
        try:
            return Settings.objects.first()
        except Exception as e:
            logger.error(f"Error fetching settings: {e}", exc_info=True)
            return None
    
    def _parse_sentry_dsn_info(self, dsn: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse organization and project information from Sentry DSN
        
        Args:
            dsn: Sentry DSN string
            
        Returns:
            Tuple of (organization, project_id)
        """
        from urllib.parse import urlparse
        
        try:
            # Parse the DSN URL
            parsed = urlparse(dsn)
            
            # Validate it's a Sentry URL
            if not parsed.hostname or not parsed.hostname.endswith('.ingest.sentry.io'):
                logger.warning(f"Invalid Sentry DSN hostname: {parsed.hostname}")
                return None, None
            
            # Extract organization from hostname (e.g., 'o123456.ingest.sentry.io' -> 'o123456')
            hostname_parts = parsed.hostname.split('.')
            if len(hostname_parts) >= 3 and hostname_parts[-3:] == ['ingest', 'sentry', 'io']:
                org = hostname_parts[0]
            else:
                logger.warning(f"Could not extract organization from hostname: {parsed.hostname}")
                return None, None
            
            # Extract project ID from path
            path_parts = parsed.path.strip('/').split('/')
            project_id = path_parts[0] if path_parts and path_parts[0] else None
            
            return org, project_id
            
        except Exception as e:
            logger.error(f"Error parsing DSN: {e}", exc_info=True)
        return None, None
    
    def fetch_and_create_tasks(
        self,
        item: Item,
        hours_back: int = 24,
        dry_run: bool = False
    ) -> Dict:
        """
        Fetch errors from Sentry and create tasks for an item
        
        Args:
            item: The Item to create tasks for
            hours_back: Number of hours to look back for errors
            dry_run: If True, don't actually create tasks
            
        Returns:
            Dictionary with statistics about the sync operation
        """
        if not item.sentry_dsn:
            logger.warning(f"Item {item.id} has no Sentry DSN configured")
            return {
                'success': False,
                'error': 'No Sentry DSN configured',
                'issues_fetched': 0,
                'tasks_created': 0,
                'duplicates_skipped': 0
            }
        
        if not item.enable_sentry_fetch:
            logger.info(f"Sentry fetch is disabled for item {item.id}")
            return {
                'success': False,
                'error': 'Sentry fetch is disabled',
                'issues_fetched': 0,
                'tasks_created': 0,
                'duplicates_skipped': 0
            }
        
        # Get Sentry auth token from settings
        if not self.settings:
            logger.error("No settings found - cannot fetch Sentry errors")
            return {
                'success': False,
                'error': 'Settings not configured',
                'issues_fetched': 0,
                'tasks_created': 0,
                'duplicates_skipped': 0
            }
        
        # Note: We'll need to add sentry_auth_token to Settings model
        # For now, we'll use a placeholder
        sentry_auth_token = getattr(self.settings, 'sentry_auth_token', None)
        if not sentry_auth_token:
            logger.error("Sentry auth token not configured in settings")
            return {
                'success': False,
                'error': 'Sentry auth token not configured',
                'issues_fetched': 0,
                'tasks_created': 0,
                'duplicates_skipped': 0
            }
        
        # Parse DSN for organization and project
        org, project_id = self._parse_sentry_dsn_info(item.sentry_dsn)
        if not org:
            logger.error(f"Could not parse organization from DSN: {item.sentry_dsn}")
            return {
                'success': False,
                'error': 'Invalid Sentry DSN format',
                'issues_fetched': 0,
                'tasks_created': 0,
                'duplicates_skipped': 0
            }
        
        # We need the project slug, which needs to be configured separately
        # For now, we'll require it to be part of the item configuration
        # In a real implementation, this should be fetched from the API or configured
        sentry_project = getattr(item, 'sentry_project_slug', None)
        if not sentry_project:
            logger.warning(f"Item {item.id} has no Sentry project slug configured")
            # Try to use project_id from DSN as fallback
            sentry_project = project_id
        
        if not sentry_project:
            return {
                'success': False,
                'error': 'No Sentry project configured',
                'issues_fetched': 0,
                'tasks_created': 0,
                'duplicates_skipped': 0
            }
        
        # Initialize Sentry service
        sentry_service = SentryService()
        sentry_service.configure(org, sentry_project, sentry_auth_token)
        
        # Fetch issues
        logger.info(f"Fetching Sentry issues for item {item.id} (org: {org}, project: {sentry_project})")
        issues = sentry_service.get_issues(hours_back=hours_back, limit=100)
        
        if not issues:
            logger.info(f"No Sentry issues found for item {item.id}")
            return {
                'success': True,
                'issues_fetched': 0,
                'tasks_created': 0,
                'duplicates_skipped': 0
            }
        
        logger.info(f"Found {len(issues)} Sentry issues for item {item.id}")
        
        # Process each issue and create tasks
        tasks_created = 0
        duplicates_skipped = 0
        
        for issue in issues:
            try:
                # Check for duplicates
                if self._is_duplicate_task(item, issue):
                    duplicates_skipped += 1
                    logger.debug(f"Skipping duplicate Sentry issue: {issue.get('id')}")
                    continue
                
                if not dry_run:
                    task = self._create_task_from_issue(item, issue)
                    if task:
                        tasks_created += 1
                        logger.info(f"Created task {task.id} from Sentry issue {issue.get('id')}")
                else:
                    tasks_created += 1
                    logger.info(f"[DRY RUN] Would create task from Sentry issue {issue.get('id')}")
                    
            except Exception as e:
                logger.error(f"Error processing Sentry issue {issue.get('id')}: {e}", exc_info=True)
        
        result = {
            'success': True,
            'issues_fetched': len(issues),
            'tasks_created': tasks_created,
            'duplicates_skipped': duplicates_skipped
        }
        
        logger.info(f"Sentry sync completed for item {item.id}: {result}")
        return result
    
    def _is_duplicate_task(self, item: Item, issue: Dict) -> bool:
        """
        Check if a task already exists for this Sentry issue
        
        Args:
            item: The Item to check
            issue: The Sentry issue data
            
        Returns:
            True if duplicate exists
        """
        issue_id = issue.get('id')
        
        # Check by Sentry issue ID in external_id field
        if issue_id:
            existing = Task.objects.filter(
                item=item,
                external_id=f"sentry-{issue_id}"
            ).first()
            
            if existing:
                return True
        
        # Check by title similarity (exact match)
        title = self._generate_task_title(issue)
        existing = Task.objects.filter(
            item=item,
            title=title,
            type='bug'
        ).first()
        
        return existing is not None
    
    def _generate_task_title(self, issue: Dict) -> str:
        """
        Generate a task title from a Sentry issue
        
        Args:
            issue: Sentry issue data
            
        Returns:
            Task title string
        """
        # Get the issue title or metadata
        title = issue.get('title', '')
        if not title:
            metadata = issue.get('metadata', {})
            title = metadata.get('value', 'Sentry Error')
        
        # Truncate if too long
        max_length = 250
        if len(title) > max_length:
            title = title[:max_length] + '...'
        
        return title
    
    def _generate_task_description(self, issue: Dict) -> str:
        """
        Generate a task description from a Sentry issue
        
        Args:
            issue: Sentry issue data
            
        Returns:
            Task description in markdown format
        """
        lines = []
        
        # Title
        title = issue.get('title', 'Unknown Error')
        lines.append(f"# {title}\n")
        
        # Issue metadata
        issue_id = issue.get('id', '')
        issue_url = issue.get('permalink', '')
        level = issue.get('level', 'error')
        count = issue.get('count', 0)
        user_count = issue.get('userCount', 0)
        
        lines.append(f"**Sentry Issue ID:** {issue_id}")
        if issue_url:
            lines.append(f"**Sentry URL:** [{issue_url}]({issue_url})")
        lines.append(f"**Severity:** {level.upper()}")
        lines.append(f"**Occurrences:** {count}")
        if user_count:
            lines.append(f"**Affected Users:** {user_count}")
        lines.append("")
        
        # Error message
        metadata = issue.get('metadata', {})
        error_type = metadata.get('type', '')
        error_value = metadata.get('value', '')
        
        if error_type or error_value:
            lines.append("## Error Details\n")
            if error_type:
                lines.append(f"**Type:** `{error_type}`")
            if error_value:
                lines.append(f"**Message:** {error_value}")
            lines.append("")
        
        # First seen / Last seen
        first_seen = issue.get('firstSeen', '')
        last_seen = issue.get('lastSeen', '')
        
        if first_seen or last_seen:
            lines.append("## Timeline\n")
            if first_seen:
                lines.append(f"**First Seen:** {first_seen}")
            if last_seen:
                lines.append(f"**Last Seen:** {last_seen}")
            lines.append("")
        
        # Culprit (location in code)
        culprit = issue.get('culprit', '')
        if culprit:
            lines.append("## Location\n")
            lines.append(f"```\n{culprit}\n```\n")
        
        # Footer
        lines.append("---")
        lines.append("*This task was automatically created from a Sentry error.*")
        
        return '\n'.join(lines)
    
    @transaction.atomic
    def _create_task_from_issue(self, item: Item, issue: Dict) -> Optional[Task]:
        """
        Create a Task from a Sentry issue
        
        Args:
            item: The Item to associate the task with
            issue: Sentry issue data
            
        Returns:
            Created Task or None
        """
        try:
            issue_id = issue.get('id', '')
            title = self._generate_task_title(issue)
            description = self._generate_task_description(issue)
            
            # Get Sentry issue URL
            external_url = issue.get('permalink', '')
            
            # Create the task
            task = Task.objects.create(
                title=title,
                description=description,
                type='bug',
                status='new',
                item=item,
                external_id=f"sentry-{issue_id}",
                external_url=external_url,
                ai_generated=True,
                created_by=item.created_by
            )
            
            # Copy tags from item to task
            if item.tags.exists():
                task.tags.set(item.tags.all())
            
            return task
            
        except Exception as e:
            logger.error(f"Error creating task from Sentry issue: {e}", exc_info=True)
            return None
    
    def sync_all_items(self, hours_back: int = 24, dry_run: bool = False) -> Dict:
        """
        Sync Sentry errors for all items that have Sentry enabled
        
        Args:
            hours_back: Number of hours to look back
            dry_run: If True, don't actually create tasks
            
        Returns:
            Dictionary with overall statistics
        """
        # Find all items with Sentry enabled
        items = Item.objects.filter(
            enable_sentry_fetch=True
        ).exclude(
            sentry_dsn=''
        )
        
        logger.info(f"Found {items.count()} items with Sentry fetch enabled")
        
        total_issues = 0
        total_tasks = 0
        total_duplicates = 0
        items_processed = 0
        items_failed = 0
        
        for item in items:
            try:
                result = self.fetch_and_create_tasks(item, hours_back, dry_run)
                
                if result['success']:
                    items_processed += 1
                    total_issues += result['issues_fetched']
                    total_tasks += result['tasks_created']
                    total_duplicates += result['duplicates_skipped']
                else:
                    items_failed += 1
                    logger.warning(f"Failed to sync item {item.id}: {result.get('error')}")
                    
            except Exception as e:
                items_failed += 1
                logger.error(f"Error syncing item {item.id}: {e}", exc_info=True)
        
        summary = {
            'items_with_sentry': items.count(),
            'items_processed': items_processed,
            'items_failed': items_failed,
            'total_issues_fetched': total_issues,
            'total_tasks_created': total_tasks,
            'total_duplicates_skipped': total_duplicates
        }
        
        logger.info(f"Sentry sync completed: {summary}")
        return summary


class SentryTaskSyncServiceError(Exception):
    """Custom exception for Sentry Task Sync Service errors"""
    pass
