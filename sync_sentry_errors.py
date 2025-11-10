#!/usr/bin/env python
"""
Sentry Error Synchronization Script

This script synchronizes errors from Sentry to IdeaGraph tasks for items
that have Sentry integration enabled.

Features:
- Creates Bug tasks from Sentry errors
- Detects duplicates by Sentry issue ID and title
- Filters errors from the last 24 hours (configurable)
- Can be run manually or as a cron job

Usage:
    # Sync errors for a specific item by ID
    python sync_sentry_errors.py --item-id <uuid>
    
    # Sync errors for all items with Sentry enabled
    python sync_sentry_errors.py --all-items
    
    # Sync errors from last 48 hours
    python sync_sentry_errors.py --all-items --hours 48
    
    # Run with verbose logging
    python sync_sentry_errors.py --all-items --verbose
    
    # Dry run (no changes)
    python sync_sentry_errors.py --all-items --dry-run
    
    # Cron job example (sync all items every hour):
    0 * * * * cd /path/to/IdeaGraph-v1 && python sync_sentry_errors.py --all-items >> logs/sync_sentry.log 2>&1
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

from core.services.sentry_task_sync_service import SentryTaskSyncService, SentryTaskSyncServiceError
from main.models import Item


def setup_logging(verbose: bool = False):
    """
    Setup logging configuration
    
    Args:
        verbose: Enable verbose (DEBUG) logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def sync_item(item_id: str, hours_back: int, dry_run: bool, verbose: bool) -> bool:
    """
    Sync Sentry errors for a specific item
    
    Args:
        item_id: UUID of the item
        hours_back: Number of hours to look back
        dry_run: If True, don't actually create tasks
        verbose: Enable verbose logging
        
    Returns:
        True if sync was successful
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Get the item
        item = Item.objects.get(id=item_id)
        logger.info(f"Starting Sentry sync for item: {item.title} ({item.id})")
        
        # Check if Sentry is configured for this item
        if not item.sentry_dsn:
            logger.error(f"Item {item.id} has no Sentry DSN configured")
            return False
        
        if not item.enable_sentry_fetch:
            logger.error(f"Sentry fetch is disabled for item {item.id}")
            return False
        
        # Initialize sync service
        sync_service = SentryTaskSyncService()
        
        # Perform sync
        result = sync_service.fetch_and_create_tasks(item, hours_back, dry_run)
        
        if result['success']:
            logger.info(f"✓ Sync completed successfully")
            logger.info(f"  - Issues fetched: {result['issues_fetched']}")
            logger.info(f"  - Tasks created: {result['tasks_created']}")
            logger.info(f"  - Duplicates skipped: {result['duplicates_skipped']}")
            return True
        else:
            logger.error(f"✗ Sync failed: {result.get('error')}")
            return False
            
    except Item.DoesNotExist:
        logger.error(f"Item with ID {item_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error syncing item {item_id}: {e}", exc_info=verbose)
        return False


def sync_all_items(hours_back: int, dry_run: bool, verbose: bool) -> bool:
    """
    Sync Sentry errors for all items with Sentry enabled
    
    Args:
        hours_back: Number of hours to look back
        dry_run: If True, don't actually create tasks
        verbose: Enable verbose logging
        
    Returns:
        True if sync was successful
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Sentry sync for all items with Sentry enabled")
        
        # Initialize sync service
        sync_service = SentryTaskSyncService()
        
        # Perform sync
        result = sync_service.sync_all_items(hours_back, dry_run)
        
        logger.info(f"✓ Sync completed")
        logger.info(f"  - Items with Sentry: {result['items_with_sentry']}")
        logger.info(f"  - Items processed: {result['items_processed']}")
        logger.info(f"  - Items failed: {result['items_failed']}")
        logger.info(f"  - Total issues fetched: {result['total_issues_fetched']}")
        logger.info(f"  - Total tasks created: {result['total_tasks_created']}")
        logger.info(f"  - Total duplicates skipped: {result['total_duplicates_skipped']}")
        
        return result['items_failed'] == 0
        
    except Exception as e:
        logger.error(f"Error syncing all items: {e}", exc_info=verbose)
        return False


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(
        description='Synchronize Sentry errors to IdeaGraph tasks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Item selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--item-id',
        type=str,
        help='Sync errors for a specific item (UUID)'
    )
    group.add_argument(
        '--all-items',
        action='store_true',
        help='Sync errors for all items with Sentry enabled'
    )
    
    # Options
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Number of hours to look back for errors (default: 24)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without creating tasks'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Print header
    logger.info("=" * 70)
    logger.info("Sentry Error Synchronization")
    logger.info("=" * 70)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Hours back: {args.hours}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 70)
    
    # Perform sync
    success = False
    if args.item_id:
        success = sync_item(args.item_id, args.hours, args.dry_run, args.verbose)
    elif args.all_items:
        success = sync_all_items(args.hours, args.dry_run, args.verbose)
    
    # Print footer
    logger.info("=" * 70)
    if success:
        logger.info("✓ Synchronization completed successfully")
    else:
        logger.info("✗ Synchronization completed with errors")
    logger.info(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
