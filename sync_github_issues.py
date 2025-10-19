#!/usr/bin/env python
"""
GitHub Issues and Tasks Synchronization Script

This script monitors GitHub issues and synchronizes them with IdeaGraph tasks.
It can be run manually or as a cron job.

Features:
- Monitors GitHub issues and updates task status when closed
- Stores issue descriptions and PR information in ChromaDB
- Supports filtering by repository and owner
- Configurable via command-line arguments or environment variables

Usage:
    # Run synchronization with default settings
    python sync_github_issues.py

    # Run with specific repository
    python sync_github_issues.py --owner gdsanger --repo IdeaGraph-v1

    # Run with verbose logging
    python sync_github_issues.py --verbose

    # Cron job example (run every hour):
    0 * * * * cd /path/to/IdeaGraph-v1 && python sync_github_issues.py >> logs/sync_github.log 2>&1
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

from core.services.github_issue_sync_service import GitHubIssueSyncService, GitHubIssueSyncServiceError


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
            logging.FileHandler(log_dir / 'github_sync.log')
        ]
    )


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description='Synchronize GitHub issues with IdeaGraph tasks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings from database
  python sync_github_issues.py

  # Specify repository
  python sync_github_issues.py --owner gdsanger --repo IdeaGraph-v1

  # Enable verbose logging
  python sync_github_issues.py --verbose

Environment Variables:
  GITHUB_SYNC_OWNER    - Default GitHub repository owner
  GITHUB_SYNC_REPO     - Default GitHub repository name
        """
    )
    
    parser.add_argument(
        '--owner',
        type=str,
        help='GitHub repository owner (overrides default from settings)',
        default=os.environ.get('GITHUB_SYNC_OWNER')
    )
    
    parser.add_argument(
        '--repo',
        type=str,
        help='GitHub repository name (overrides default from settings)',
        default=os.environ.get('GITHUB_SYNC_REPO')
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without updating tasks or ChromaDB'
    )
    
    return parser.parse_args()


def main():
    """Main execution function"""
    args = parse_arguments()
    setup_logging(args.verbose)
    
    logger = logging.getLogger('sync_github_issues')
    
    logger.info("=" * 80)
    logger.info("GitHub Issues and Tasks Synchronization")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    try:
        # Initialize sync service
        logger.info("Initializing GitHub Issue Sync Service...")
        sync_service = GitHubIssueSyncService()
        
        # Run synchronization
        logger.info("Starting synchronization...")
        result = sync_service.sync_tasks_with_github_issues(
            repo=args.repo,
            owner=args.owner
        )
        
        # Log results
        if result['success']:
            results = result['results']
            logger.info("=" * 80)
            logger.info("Synchronization Results:")
            logger.info(f"  Tasks checked: {results['tasks_checked']}")
            logger.info(f"  Tasks updated: {results['tasks_updated']}")
            logger.info(f"  Issues synced to ChromaDB: {results['issues_synced']}")
            logger.info(f"  Pull Requests synced to ChromaDB: {results['prs_synced']}")
            
            if results['errors']:
                logger.warning(f"  Errors encountered: {len(results['errors'])}")
                for error in results['errors']:
                    logger.warning(f"    - {error}")
            else:
                logger.info("  No errors encountered")
            
            logger.info("=" * 80)
            logger.info("Synchronization completed successfully!")
            return 0
        else:
            logger.error("Synchronization failed")
            return 1
            
    except GitHubIssueSyncServiceError as e:
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
