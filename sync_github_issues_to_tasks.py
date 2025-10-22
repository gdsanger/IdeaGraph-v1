#!/usr/bin/env python
"""
GitHub Issues to Tasks Synchronization Script

This script synchronizes GitHub issues to IdeaGraph tasks for a specific item.
It creates tasks from GitHub issues that don't already exist, with duplicate detection.

Features:
- Creates tasks from GitHub issues (both open and closed)
- Detects duplicates by GitHub Issue ID
- Detects duplicates by title similarity
- Marks potential duplicates with "*** Duplikat? ***" prefix
- Can be run manually or as a cron job

Usage:
    # Sync issues for a specific item by ID
    python sync_github_issues_to_tasks.py --item-id <uuid>
    
    # Sync issues for all items with GitHub repositories
    python sync_github_issues_to_tasks.py --all-items
    
    # Sync with specific repository (overrides item's github_repo)
    python sync_github_issues_to_tasks.py --item-id <uuid> --owner gdsanger --repo IdeaGraph-v1
    
    # Sync only open issues
    python sync_github_issues_to_tasks.py --item-id <uuid> --state open
    
    # Run with verbose logging
    python sync_github_issues_to_tasks.py --item-id <uuid> --verbose
    
    # Dry run (no changes)
    python sync_github_issues_to_tasks.py --item-id <uuid> --dry-run
    
    # Cron job example (sync all items daily at 3 AM):
    0 3 * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues_to_tasks.py --all-items >> logs/sync_github_tasks.log 2>&1
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideagraph.settings')
import django
django.setup()

from core.services.github_task_sync_service import GitHubTaskSyncService, GitHubTaskSyncServiceError
from main.models import Item, User


def setup_logging(verbose: bool = False):
    """
    Setup logging configuration
    
    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory if it doesn't exist
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / 'sync_github_tasks.log')
        ]
    )


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Synchronize GitHub issues to IdeaGraph tasks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync issues for a specific item
  python sync_github_issues_to_tasks.py --item-id abc-123-def
  
  # Sync issues for all items with GitHub repos
  python sync_github_issues_to_tasks.py --all-items
  
  # Sync with specific repository
  python sync_github_issues_to_tasks.py --item-id abc-123-def --owner gdsanger --repo IdeaGraph-v1
  
  # Sync only open issues
  python sync_github_issues_to_tasks.py --item-id abc-123-def --state open
  
  # Enable verbose logging
  python sync_github_issues_to_tasks.py --item-id abc-123-def --verbose
  
Environment Variables:
  GITHUB_SYNC_ITEM_ID   - Default item ID to sync
  GITHUB_SYNC_OWNER     - Default GitHub repository owner
  GITHUB_SYNC_REPO      - Default GitHub repository name
  GITHUB_SYNC_STATE     - Default state filter ('open', 'closed', 'all')
        """
    )
    
    parser.add_argument(
        '--item-id',
        type=str,
        help='Item UUID to sync GitHub issues for',
        default=os.environ.get('GITHUB_SYNC_ITEM_ID')
    )
    
    parser.add_argument(
        '--all-items',
        action='store_true',
        help='Sync GitHub issues for all items with github_repo set'
    )
    
    parser.add_argument(
        '--owner',
        type=str,
        help='GitHub repository owner (overrides item setting)',
        default=os.environ.get('GITHUB_SYNC_OWNER')
    )
    
    parser.add_argument(
        '--repo',
        type=str,
        help='GitHub repository name (overrides item setting)',
        default=os.environ.get('GITHUB_SYNC_REPO')
    )
    
    parser.add_argument(
        '--state',
        type=str,
        choices=['open', 'closed', 'all'],
        default=os.environ.get('GITHUB_SYNC_STATE', 'all'),
        help='Filter by issue state (default: all)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without creating tasks'
    )
    
    return parser.parse_args()


def sync_item(sync_service, item, owner, repo, state, dry_run, logger):
    """
    Sync GitHub issues to tasks for a single item
    
    Args:
        sync_service: GitHubTaskSyncService instance
        item: Item model instance
        owner: GitHub repository owner
        repo: GitHub repository name
        state: Issue state filter
        dry_run: If True, don't create tasks
        logger: Logger instance
    
    Returns:
        Dict with sync results
    """
    logger.info(f"Syncing GitHub issues for item: {item.title} (ID: {item.id})")
    
    if dry_run:
        logger.info("DRY RUN MODE - No tasks will be created")
        return {
            'success': True,
            'issues_checked': 0,
            'tasks_created': 0,
            'duplicates_by_id': 0,
            'duplicates_by_title': 0,
            'errors': []
        }
    
    # Get admin user for task creation (use first admin user)
    admin_user = User.objects.filter(role='admin').first()
    if not admin_user:
        logger.error("No admin user found - cannot create tasks")
        return {
            'success': False,
            'error': 'No admin user found'
        }
    
    result = sync_service.sync_github_issues_to_tasks(
        item=item,
        owner=owner,
        repo=repo,
        state=state,
        created_by=admin_user
    )
    
    return result


def main():
    """Main execution function"""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    logger = logging.getLogger('sync_github_issues_to_tasks')
    
    logger.info("=" * 80)
    logger.info("GitHub Issues to Tasks Synchronization")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    # Validate arguments
    if not args.item_id and not args.all_items:
        logger.error("Either --item-id or --all-items must be specified")
        return 1
    
    if args.item_id and args.all_items:
        logger.error("Cannot specify both --item-id and --all-items")
        return 1
    
    try:
        # Initialize sync service
        logger.info("Initializing GitHub Task Sync Service...")
        sync_service = GitHubTaskSyncService()
        
        # Collect items to sync
        items_to_sync = []
        
        if args.all_items:
            # Get all items with github_repo set
            items_to_sync = Item.objects.exclude(github_repo='').exclude(github_repo__isnull=True)
            logger.info(f"Found {len(items_to_sync)} items with GitHub repositories")
        else:
            # Get specific item
            try:
                item = Item.objects.get(id=args.item_id)
                items_to_sync = [item]
            except Item.DoesNotExist:
                logger.error(f"Item with ID {args.item_id} not found")
                return 1
        
        if not items_to_sync:
            logger.warning("No items to sync")
            return 0
        
        # Track overall results
        total_results = {
            'items_processed': 0,
            'items_succeeded': 0,
            'items_failed': 0,
            'total_issues_checked': 0,
            'total_tasks_created': 0,
            'total_duplicates_by_id': 0,
            'total_duplicates_by_title': 0,
            'errors': []
        }
        
        # Sync each item
        for item in items_to_sync:
            total_results['items_processed'] += 1
            
            try:
                result = sync_item(
                    sync_service=sync_service,
                    item=item,
                    owner=args.owner,
                    repo=args.repo,
                    state=args.state,
                    dry_run=args.dry_run,
                    logger=logger
                )
                
                if result.get('success'):
                    total_results['items_succeeded'] += 1
                    total_results['total_issues_checked'] += result.get('issues_checked', 0)
                    total_results['total_tasks_created'] += result.get('tasks_created', 0)
                    total_results['total_duplicates_by_id'] += result.get('duplicates_by_id', 0)
                    total_results['total_duplicates_by_title'] += result.get('duplicates_by_title', 0)
                    
                    logger.info(f"✓ Item '{item.title}': {result.get('tasks_created', 0)} tasks created from {result.get('issues_checked', 0)} issues")
                    
                    if result.get('errors'):
                        total_results['errors'].extend(result['errors'])
                else:
                    total_results['items_failed'] += 1
                    error_msg = f"✗ Item '{item.title}': {result.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    total_results['errors'].append(error_msg)
            
            except Exception as e:
                total_results['items_failed'] += 1
                error_msg = f"✗ Item '{item.title}': {str(e)}"
                logger.exception(error_msg)
                total_results['errors'].append(error_msg)
        
        # Log overall results
        logger.info("=" * 80)
        logger.info("Synchronization Results:")
        logger.info(f"  Items processed: {total_results['items_processed']}")
        logger.info(f"  Items succeeded: {total_results['items_succeeded']}")
        logger.info(f"  Items failed: {total_results['items_failed']}")
        logger.info(f"  Total issues checked: {total_results['total_issues_checked']}")
        logger.info(f"  Total tasks created: {total_results['total_tasks_created']}")
        logger.info(f"  Total duplicates by ID: {total_results['total_duplicates_by_id']}")
        logger.info(f"  Total duplicates by title: {total_results['total_duplicates_by_title']}")
        
        if total_results['errors']:
            logger.warning(f"  Errors encountered: {len(total_results['errors'])}")
            for error in total_results['errors']:
                logger.warning(f"    - {error}")
        else:
            logger.info("  No errors encountered")
        
        logger.info("=" * 80)
        logger.info("Synchronization completed successfully!")
        
        return 0 if total_results['items_failed'] == 0 else 1
        
    except GitHubTaskSyncServiceError as e:
        logger.error(f"Sync service error: {e.message}")
        if e.details:
            logger.error(f"Details: {e.details}")
        return 1
        
    except Exception as e:
        logger.exception(f"Unexpected error during synchronization: {str(e)}")
        return 1
    
    finally:
        logger.info(f"Finished at: {datetime.now().isoformat()}")
        logger.info("=" * 80)


if __name__ == '__main__':
    sys.exit(main())
