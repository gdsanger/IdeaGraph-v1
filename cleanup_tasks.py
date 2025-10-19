#!/usr/bin/env python
"""
Task Cleanup CLI Script

This script identifies and removes tasks that have no owner (assigned_to) 
and/or no item assigned to them. These tasks were created due to a bug 
in the application and need to be removed.

Features:
- Identifies all tasks without owner and/or without item
- Removes all identified tasks from the system
- Provides summary of actions taken
- Handles errors gracefully with appropriate error messages

Usage:
    # Preview tasks that would be deleted (dry run)
    python cleanup_tasks.py --dry-run

    # Delete tasks without owner and/or item
    python cleanup_tasks.py

    # Delete only tasks without owner
    python cleanup_tasks.py --no-owner-only

    # Delete only tasks without item
    python cleanup_tasks.py --no-item-only

    # Enable verbose logging
    python cleanup_tasks.py --verbose
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

from main.models import Task
from django.db import transaction


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
            logging.FileHandler(log_dir / 'cleanup_tasks.log')
        ]
    )


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Clean up tasks without owner and/or item',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview tasks that would be deleted
  python cleanup_tasks.py --dry-run

  # Delete tasks without owner and/or item
  python cleanup_tasks.py

  # Delete only tasks without owner
  python cleanup_tasks.py --no-owner-only

  # Delete only tasks without item
  python cleanup_tasks.py --no-item-only

  # Enable verbose logging
  python cleanup_tasks.py --verbose
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview tasks that would be deleted without actually deleting them'
    )
    
    parser.add_argument(
        '--no-owner-only',
        action='store_true',
        help='Only delete tasks without owner (assigned_to is NULL)'
    )
    
    parser.add_argument(
        '--no-item-only',
        action='store_true',
        help='Only delete tasks without item (item is NULL)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    return parser.parse_args()


def identify_tasks_to_cleanup(no_owner_only: bool = False, no_item_only: bool = False):
    """
    Identify tasks that need to be cleaned up
    
    Args:
        no_owner_only: Only identify tasks without owner
        no_item_only: Only identify tasks without item
        
    Returns:
        QuerySet of tasks to be cleaned up
    """
    logger = logging.getLogger('cleanup_tasks')
    
    try:
        if no_owner_only:
            # Only tasks without owner
            logger.debug("Identifying tasks without owner (assigned_to is NULL)")
            tasks = Task.objects.filter(assigned_to__isnull=True)
        elif no_item_only:
            # Only tasks without item
            logger.debug("Identifying tasks without item (item is NULL)")
            tasks = Task.objects.filter(item__isnull=True)
        else:
            # Tasks without owner AND/OR without item (default)
            logger.debug("Identifying tasks without owner AND/OR without item")
            tasks = Task.objects.filter(assigned_to__isnull=True) | Task.objects.filter(item__isnull=True)
        
        return tasks
    except Exception as e:
        logger.error(f"Error identifying tasks: {str(e)}")
        raise


def delete_tasks(tasks, dry_run: bool = False):
    """
    Delete identified tasks
    
    Args:
        tasks: QuerySet of tasks to delete
        dry_run: If True, don't actually delete tasks
        
    Returns:
        Tuple of (deleted_count, errors)
    """
    logger = logging.getLogger('cleanup_tasks')
    deleted_count = 0
    errors = []
    
    if dry_run:
        logger.info("DRY RUN MODE - No tasks will be deleted")
        return len(tasks), errors
    
    try:
        with transaction.atomic():
            task_ids = list(tasks.values_list('id', flat=True))
            
            for task_id in task_ids:
                try:
                    task = Task.objects.get(id=task_id)
                    task_title = task.title
                    logger.debug(f"Deleting task: {task_title} (ID: {task_id})")
                    task.delete()
                    deleted_count += 1
                except Task.DoesNotExist:
                    error_msg = f"Task with ID {task_id} not found"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Error deleting task {task_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        logger.info(f"Successfully deleted {deleted_count} tasks")
        
    except Exception as e:
        error_msg = f"Transaction error during deletion: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    
    return deleted_count, errors


def print_task_summary(tasks, verbose: bool = False):
    """
    Print summary of tasks to be deleted
    
    Args:
        tasks: QuerySet of tasks
        verbose: Print detailed task information
    """
    logger = logging.getLogger('cleanup_tasks')
    
    print("\n" + "=" * 80)
    print("  Tasks Identified for Cleanup")
    print("=" * 80)
    
    for task in tasks:
        has_owner = task.assigned_to is not None
        has_item = task.item is not None
        
        print(f"\nTask ID: {task.id}")
        print(f"  Title: {task.title}")
        print(f"  Status: {task.status}")
        print(f"  Has Owner: {'Yes' if has_owner else 'No'}")
        print(f"  Has Item: {'Yes' if has_item else 'No'}")
        print(f"  Created At: {task.created_at}")
        
        if verbose:
            print(f"  Created By: {task.created_by.username if task.created_by else 'N/A'}")
            if task.description:
                print(f"  Description: {task.description[:100]}...")
    
    print("\n" + "=" * 80)


def main():
    """Main execution function"""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    logger = logging.getLogger('cleanup_tasks')
    
    logger.info("=" * 80)
    logger.info("Task Cleanup Script")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No tasks will be deleted")
    
    if args.no_owner_only and args.no_item_only:
        logger.error("Cannot use both --no-owner-only and --no-item-only flags")
        return 1
    
    try:
        # Step 1: Identify tasks to cleanup
        logger.info("Step 1: Identifying tasks to cleanup...")
        
        tasks = identify_tasks_to_cleanup(
            no_owner_only=args.no_owner_only,
            no_item_only=args.no_item_only
        )
        
        identified_count = tasks.count()
        logger.info(f"Found {identified_count} task(s) to cleanup")
        
        if identified_count == 0:
            logger.info("No tasks found that need cleanup")
            logger.info("=" * 80)
            return 0
        
        # Step 2: Print task summary
        logger.info("\nStep 2: Task Summary")
        print_task_summary(tasks, verbose=args.verbose)
        
        # Step 3: Delete tasks
        if not args.dry_run:
            logger.info("\nStep 3: Deleting tasks...")
            
            # Ask for confirmation
            print("\n" + "=" * 80)
            print(f"WARNING: This will delete {identified_count} task(s)")
            print("=" * 80)
            response = input("\nDo you want to proceed? (yes/no): ")
            
            if response.lower() not in ['yes', 'y']:
                logger.info("Cleanup cancelled by user")
                return 0
            
            deleted_count, errors = delete_tasks(tasks, dry_run=False)
        else:
            # Dry run
            deleted_count, errors = delete_tasks(tasks, dry_run=True)
        
        # Step 4: Print results
        logger.info("\n" + "=" * 80)
        logger.info("Cleanup Results:")
        logger.info(f"  Tasks identified: {identified_count}")
        logger.info(f"  Tasks deleted: {deleted_count}")
        
        if errors:
            logger.warning(f"  Errors encountered: {len(errors)}")
            for error in errors:
                logger.warning(f"    - {error}")
        else:
            logger.info("  No errors encountered")
        
        logger.info("=" * 80)
        
        if args.dry_run:
            logger.info("DRY RUN COMPLETED - No tasks were actually deleted")
        else:
            logger.info("Cleanup completed successfully!")
        
        return 0
        
    except Exception as e:
        logger.exception(f"Unexpected error during cleanup: {str(e)}")
        return 1
    
    finally:
        logger.info(f"Finished at: {datetime.now().isoformat()}")
        logger.info("=" * 80)


if __name__ == '__main__':
    sys.exit(main())
