"""
Django management command to synchronize GitHub markdown documentation with IdeaGraph.

This command retrieves markdown files from GitHub repositories configured in Items
and synchronizes them to SharePoint and Weaviate for AI-powered search.

Usage:
    python manage.py sync_github_docs [--item <item_id>] [--all]

Example:
    # Sync documentation for a specific item
    python manage.py sync_github_docs --item 7d6b9aee-2e6f-4e7a-bae4-28face017a97
    
    # Sync documentation for all items with GitHub repositories
    python manage.py sync_github_docs --all
    
    # Cron job example (sync all items every 3 hours):
    0 */3 * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_docs --all >> logs/sync_github_docs.log 2>&1
"""

from django.core.management.base import BaseCommand, CommandError
from core.services.github_doc_sync_service import GitHubDocSyncService, GitHubDocSyncServiceError


class Command(BaseCommand):
    help = 'Synchronize GitHub markdown documentation with IdeaGraph'

    def add_arguments(self, parser):
        parser.add_argument(
            '--item',
            type=str,
            help='Sync documentation for a specific item by UUID',
            default=None
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync documentation for all items with GitHub repositories',
            default=False
        )

    def handle(self, *args, **options):
        item_id = options.get('item')
        sync_all = options.get('all')
        
        # Validate arguments
        if not item_id and not sync_all:
            raise CommandError('Please specify either --item <item_id> or --all')
        
        if item_id and sync_all:
            raise CommandError('Cannot specify both --item and --all')
        
        # Initialize service
        try:
            service = GitHubDocSyncService()
        except GitHubDocSyncServiceError as e:
            self.stdout.write(self.style.ERROR(f'Service initialization failed: {e.message}'))
            if e.details:
                self.stdout.write(self.style.ERROR(f'Details: {e.details}'))
            raise CommandError('GitHub Doc Sync service initialization failed')
        
        # Sync specific item
        if item_id:
            self.stdout.write(self.style.SUCCESS(f'Syncing documentation for item: {item_id}'))
            self.stdout.write('')
            
            try:
                result = service.sync_item(item_id=item_id)
                
                if result.get('success'):
                    self.stdout.write(self.style.SUCCESS('✓ Sync completed successfully!'))
                    self.stdout.write(f"Item: {result.get('item_title')}")
                    self.stdout.write(f"Files processed: {result.get('files_processed')}")
                    self.stdout.write(f"Files synced: {result.get('files_synced')}")
                    
                    if result.get('errors'):
                        self.stdout.write('')
                        self.stdout.write(self.style.WARNING('⚠ Errors occurred:'))
                        for error in result['errors']:
                            self.stdout.write(self.style.WARNING(f"  - {error}"))
                else:
                    self.stdout.write(self.style.ERROR('✗ Sync failed!'))
                    self.stdout.write(self.style.ERROR(f"Error: {result.get('error')}"))
                    raise CommandError('Sync failed')
                    
            except GitHubDocSyncServiceError as e:
                self.stdout.write(self.style.ERROR(f'Sync error: {e.message}'))
                if e.details:
                    self.stdout.write(self.style.ERROR(f'Details: {e.details}'))
                raise CommandError('Sync failed')
        
        # Sync all items
        if sync_all:
            self.stdout.write(self.style.SUCCESS('Syncing documentation for all items with GitHub repositories'))
            self.stdout.write('')
            
            try:
                result = service.sync_all_items()
                
                if result.get('success'):
                    self.stdout.write(self.style.SUCCESS('✓ Sync completed!'))
                    self.stdout.write(f"Items processed: {result.get('items_processed')}")
                    self.stdout.write(f"Items synced: {result.get('items_synced')}")
                    self.stdout.write(f"Total files synced: {result.get('total_files_synced')}")
                    
                    if result.get('errors'):
                        self.stdout.write('')
                        self.stdout.write(self.style.WARNING('⚠ Errors occurred:'))
                        for error in result['errors']:
                            self.stdout.write(self.style.WARNING(f"  - {error}"))
                else:
                    self.stdout.write(self.style.ERROR('✗ Sync failed!'))
                    raise CommandError('Sync failed')
                    
            except GitHubDocSyncServiceError as e:
                self.stdout.write(self.style.ERROR(f'Sync error: {e.message}'))
                if e.details:
                    self.stdout.write(self.style.ERROR(f'Details: {e.details}'))
                raise CommandError('Sync failed')
