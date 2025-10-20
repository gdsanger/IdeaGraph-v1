#!/usr/bin/env python
"""
Unused Tag Cleanup CLI Script

This script identifies and removes tags that are no longer in use (usage_count = 0).
Tags with usage_count of 0 are not assigned to any items or tasks and can be safely removed.

Features:
- Identifies all tags with usage_count = 0
- Provides preview mode (dry run) to see tags before deletion
- Asks for user confirmation before deleting
- Provides detailed feedback on actions taken
- Handles errors gracefully with appropriate error messages
- Supports verbose logging for debugging

Usage:
    # Preview tags that would be deleted (dry run)
    python cleanup_unused_tags.py --dry-run

    # Delete unused tags (with confirmation prompt)
    python cleanup_unused_tags.py

    # Delete unused tags without confirmation
    python cleanup_unused_tags.py --yes

    # Enable verbose logging
    python cleanup_unused_tags.py --verbose
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

from main.models import Tag
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
            logging.FileHandler(log_dir / 'cleanup_unused_tags.log')
        ]
    )


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Clean up unused tags (usage_count = 0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview tags that would be deleted
  python cleanup_unused_tags.py --dry-run

  # Delete unused tags (with confirmation prompt)
  python cleanup_unused_tags.py

  # Delete unused tags without confirmation
  python cleanup_unused_tags.py --yes

  # Enable verbose logging
  python cleanup_unused_tags.py --verbose
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview tags that would be deleted without actually deleting them'
    )
    
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompt and delete tags automatically'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    return parser.parse_args()


def identify_unused_tags():
    """
    Identify tags that are not in use (usage_count = 0)
    
    Returns:
        QuerySet of unused tags
    """
    logger = logging.getLogger('cleanup_unused_tags')
    
    try:
        logger.debug("Identifying tags with usage_count = 0")
        unused_tags = Tag.objects.filter(usage_count=0)
        return unused_tags
    except Exception as e:
        logger.error(f"Error identifying unused tags: {str(e)}")
        raise


def verify_tag_usage(tag):
    """
    Verify that a tag actually has no usage by checking items and tasks
    
    Args:
        tag: Tag instance to verify
        
    Returns:
        Boolean indicating if tag is truly unused
    """
    logger = logging.getLogger('cleanup_unused_tags')
    
    try:
        # Double-check by counting actual relationships
        items_count = tag.items.count()
        tasks_count = tag.tasks.count()
        
        if items_count > 0 or tasks_count > 0:
            logger.warning(
                f"Tag '{tag.name}' has usage_count=0 but is actually used by "
                f"{items_count} items and {tasks_count} tasks"
            )
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error verifying tag usage for '{tag.name}': {str(e)}")
        return False


def delete_tags(tags, dry_run: bool = False):
    """
    Delete identified unused tags
    
    Args:
        tags: QuerySet of tags to delete
        dry_run: If True, don't actually delete tags
        
    Returns:
        Tuple of (deleted_count, skipped_count, errors)
    """
    logger = logging.getLogger('cleanup_unused_tags')
    deleted_count = 0
    skipped_count = 0
    errors = []
    
    if dry_run:
        logger.info("DRY RUN MODE - No tags will be deleted")
        return len(tags), 0, errors
    
    try:
        with transaction.atomic():
            tag_ids = list(tags.values_list('id', flat=True))
            
            for tag_id in tag_ids:
                try:
                    tag = Tag.objects.get(id=tag_id)
                    tag_name = tag.name
                    
                    # Verify tag is actually unused before deletion
                    if not verify_tag_usage(tag):
                        logger.warning(
                            f"Skipping tag '{tag_name}' - verification failed"
                        )
                        skipped_count += 1
                        continue
                    
                    logger.debug(
                        f"Deleting tag: {tag_name} (ID: {tag_id}, "
                        f"usage_count: {tag.usage_count})"
                    )
                    tag.delete()
                    logger.info(f"✓ Deleted tag: {tag_name}")
                    deleted_count += 1
                    
                except Tag.DoesNotExist:
                    error_msg = f"Tag with ID {tag_id} not found"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Error deleting tag {tag_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        logger.info(f"Successfully deleted {deleted_count} tag(s)")
        
    except Exception as e:
        error_msg = f"Transaction error during deletion: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)
    
    return deleted_count, skipped_count, errors


def print_tag_summary(tags, verbose: bool = False):
    """
    Print summary of tags to be deleted
    
    Args:
        tags: QuerySet of tags
        verbose: Print detailed tag information
    """
    logger = logging.getLogger('cleanup_unused_tags')
    
    print("\n" + "=" * 80)
    print("  Unused Tags Identified for Cleanup")
    print("=" * 80)
    
    for tag in tags:
        print(f"\nTag: {tag.name}")
        print(f"  ID: {tag.id}")
        print(f"  Color: {tag.color}")
        print(f"  Usage Count: {tag.usage_count}")
        print(f"  Created At: {tag.created_at}")
        
        if verbose:
            # Double-check actual usage
            items_count = tag.items.count()
            tasks_count = tag.tasks.count()
            print(f"  Actual Items Using Tag: {items_count}")
            print(f"  Actual Tasks Using Tag: {tasks_count}")
            print(f"  Updated At: {tag.updated_at}")
    
    print("\n" + "=" * 80)


def main():
    """Main execution function"""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    logger = logging.getLogger('cleanup_unused_tags')
    
    logger.info("=" * 80)
    logger.info("Unused Tag Cleanup Script")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No tags will be deleted")
    
    try:
        # Step 1: Identify unused tags
        logger.info("Step 1: Identifying unused tags...")
        
        unused_tags = identify_unused_tags()
        
        identified_count = unused_tags.count()
        logger.info(f"Found {identified_count} unused tag(s)")
        
        if identified_count == 0:
            logger.info("No unused tags found - nothing to cleanup")
            logger.info("=" * 80)
            return 0
        
        # Step 2: Print tag summary
        logger.info("\nStep 2: Tag Summary")
        print_tag_summary(unused_tags, verbose=args.verbose)
        
        # Step 3: Delete tags
        if not args.dry_run:
            logger.info("\nStep 3: Deleting unused tags...")
            
            # Ask for confirmation unless --yes flag is used
            if not args.yes:
                print("\n" + "=" * 80)
                print(f"WARNING: This will delete {identified_count} unused tag(s)")
                print("=" * 80)
                response = input("\nDo you want to proceed? (yes/no): ")
                
                if response.lower() not in ['yes', 'y']:
                    logger.info("Cleanup cancelled by user")
                    return 0
            
            deleted_count, skipped_count, errors = delete_tags(
                unused_tags, dry_run=False
            )
        else:
            # Dry run
            deleted_count, skipped_count, errors = delete_tags(
                unused_tags, dry_run=True
            )
        
        # Step 4: Print results
        logger.info("\n" + "=" * 80)
        logger.info("Cleanup Results:")
        logger.info(f"  Tags identified: {identified_count}")
        logger.info(f"  Tags deleted: {deleted_count}")
        
        if skipped_count > 0:
            logger.warning(f"  Tags skipped: {skipped_count}")
        
        if errors:
            logger.warning(f"  Errors encountered: {len(errors)}")
            for error in errors:
                logger.warning(f"    - {error}")
        else:
            logger.info("  No errors encountered")
        
        logger.info("=" * 80)
        
        if args.dry_run:
            logger.info("DRY RUN COMPLETED - No tags were actually deleted")
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
