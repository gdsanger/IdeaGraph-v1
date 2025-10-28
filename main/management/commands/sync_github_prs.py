"""
Django management command to synchronize GitHub Pull Requests with IdeaGraph.

This command retrieves pull requests from GitHub repositories configured in Items
and synchronizes them to the local database and Weaviate for AI-powered search.

Usage:
    # Sync PRs for a specific item (incremental - last hour)
    python manage.py sync_github_prs --item <item_id>
    
    # Initial load - fetch all PRs for an item
    python manage.py sync_github_prs --item <item_id> --initial
    
    # Sync PRs for all items with GitHub repositories (incremental)
    python manage.py sync_github_prs --all
    
    # Sync with SharePoint export
    python manage.py sync_github_prs --item <item_id> --export-sharepoint
    
    # Verbose output
    python manage.py sync_github_prs --item <item_id> --verbose

Example:
    # Incremental sync for specific item
    python manage.py sync_github_prs --item 7d6b9aee-2e6f-4e7a-bae4-28face017a97
    
    # Initial load for all items
    python manage.py sync_github_prs --all --initial
    
    # Cron job example (incremental sync every hour):
    0 * * * * cd /path/to/IdeaGraph-v1 && python manage.py sync_github_prs --all >> logs/sync_github_prs.log 2>&1
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from main.models import Item
from core.services.github_pr_sync_service import GitHubPRSyncService, GitHubPRSyncServiceError


class Command(BaseCommand):
    help = 'Synchronize GitHub Pull Requests with IdeaGraph'

    def add_arguments(self, parser):
        parser.add_argument(
            '--item',
            type=str,
            help='Sync PRs for a specific item by UUID',
            default=None
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync PRs for all items with GitHub repositories',
            default=False
        )
        parser.add_argument(
            '--initial',
            action='store_true',
            help='Initial load - fetch all PRs instead of just recent ones',
            default=False
        )
        parser.add_argument(
            '--export-sharepoint',
            action='store_true',
            help='Export PR data to SharePoint folder as JSON',
            default=False
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
            default=False
        )

    def handle(self, *args, **options):
        item_id = options.get('item')
        sync_all = options.get('all')
        initial_load = options.get('initial')
        export_sharepoint = options.get('export_sharepoint')
        verbose = options.get('verbose')
        
        # Validate arguments
        if not item_id and not sync_all:
            raise CommandError('Please specify either --item <item_id> or --all')
        
        if item_id and sync_all:
            raise CommandError('Cannot specify both --item and --all')
        
        # Set verbosity
        if verbose:
            self.stdout.write(self.style.SUCCESS('Verbose mode enabled'))
        
        # Initialize service
        try:
            service = GitHubPRSyncService()
        except GitHubPRSyncServiceError as e:
            self.stdout.write(self.style.ERROR(f'Service initialization failed: {e.message}'))
            if e.details:
                self.stdout.write(self.style.ERROR(f'Details: {e.details}'))
            raise CommandError('GitHub PR Sync service initialization failed')
        
        # Display sync mode
        mode = 'Initial Load (all PRs)' if initial_load else 'Incremental Sync (last hour)'
        self.stdout.write(self.style.SUCCESS(f'Sync mode: {mode}'))
        self.stdout.write('')
        
        # Sync specific item
        if item_id:
            self._sync_item(
                service=service,
                item_id=item_id,
                initial_load=initial_load,
                export_sharepoint=export_sharepoint,
                verbose=verbose
            )
        
        # Sync all items
        if sync_all:
            self._sync_all_items(
                service=service,
                initial_load=initial_load,
                export_sharepoint=export_sharepoint,
                verbose=verbose
            )
    
    def _sync_item(self, service, item_id, initial_load, export_sharepoint, verbose):
        """Sync PRs for a specific item"""
        self.stdout.write(self.style.SUCCESS(f'Syncing PRs for item: {item_id}'))
        self.stdout.write('')
        
        try:
            # Get item
            try:
                item = Item.objects.get(id=item_id)
            except Item.DoesNotExist:
                raise CommandError(f'Item with ID {item_id} not found')
            
            # Check if item has GitHub repo
            if not item.github_repo:
                raise CommandError(f'Item "{item.title}" has no GitHub repository configured')
            
            if verbose:
                self.stdout.write(f'Item: {item.title}')
                self.stdout.write(f'Repository: {item.github_repo}')
                self.stdout.write('')
            
            # Requirement 2: Skip PRs that already exist in Weaviate
            # Requirement 3: For --all --initial, enable SharePoint export and skip existing
            skip_existing = initial_load
            
            # Sync PRs
            result = service.sync_pull_requests(
                item=item,
                initial_load=initial_load,
                export_to_sharepoint=export_sharepoint,
                skip_existing_in_weaviate=skip_existing
            )
            
            if result.get('success'):
                self.stdout.write(self.style.SUCCESS('✓ Sync completed successfully!'))
                self.stdout.write(f"Item: {item.title}")
                self.stdout.write(f"PRs checked: {result.get('prs_checked', 0)}")
                self.stdout.write(f"PRs created: {result.get('prs_created', 0)}")
                self.stdout.write(f"PRs updated: {result.get('prs_updated', 0)}")
                self.stdout.write(f"PRs synced to Weaviate: {result.get('prs_synced_to_weaviate', 0)}")
                self.stdout.write(f"PRs skipped in Weaviate: {result.get('prs_skipped_in_weaviate', 0)}")
                
                if export_sharepoint:
                    self.stdout.write(f"PRs exported to SharePoint: {result.get('prs_exported_to_sharepoint', 0)}")
                
                if result.get('errors'):
                    self.stdout.write('')
                    self.stdout.write(self.style.WARNING('⚠ Errors occurred:'))
                    for error in result['errors']:
                        self.stdout.write(self.style.WARNING(f"  - {error}"))
            else:
                self.stdout.write(self.style.ERROR('✗ Sync failed!'))
                self.stdout.write(self.style.ERROR(f"Error: {result.get('error')}"))
                if result.get('details'):
                    self.stdout.write(self.style.ERROR(f"Details: {result.get('details')}"))
                raise CommandError('Sync failed')
                
        except GitHubPRSyncServiceError as e:
            self.stdout.write(self.style.ERROR(f'Sync error: {e.message}'))
            if e.details:
                self.stdout.write(self.style.ERROR(f'Details: {e.details}'))
            raise CommandError('Sync failed')
    
    def _sync_all_items(self, service, initial_load, export_sharepoint, verbose):
        """Sync PRs for all items with GitHub repositories"""
        self.stdout.write(self.style.SUCCESS('Syncing PRs for all items with GitHub repositories'))
        self.stdout.write('')
        
        # Requirement 3: For --all --initial, always enable SharePoint export
        if initial_load:
            export_sharepoint = True
            self.stdout.write(self.style.SUCCESS('SharePoint export enabled for initial load'))
            self.stdout.write('')
        
        try:
            # Get all items with github_repo set
            items = Item.objects.exclude(github_repo='').exclude(github_repo__isnull=True)
            
            if not items.exists():
                self.stdout.write(self.style.WARNING('No items with GitHub repositories found'))
                return
            
            self.stdout.write(f"Found {items.count()} items with GitHub repositories")
            self.stdout.write('')
            
            # Track overall results
            total_results = {
                'items_processed': 0,
                'items_succeeded': 0,
                'items_failed': 0,
                'total_prs_checked': 0,
                'total_prs_created': 0,
                'total_prs_updated': 0,
                'total_prs_synced_to_weaviate': 0,
                'total_prs_skipped_in_weaviate': 0,
                'total_prs_exported_to_sharepoint': 0,
                'errors': []
            }
            
            # Requirement 2: Skip PRs that already exist in Weaviate for initial load
            skip_existing = initial_load
            
            # Sync each item
            for item in items:
                total_results['items_processed'] += 1
                
                if verbose:
                    self.stdout.write(f"Processing item: {item.title} ({item.github_repo})")
                
                try:
                    result = service.sync_pull_requests(
                        item=item,
                        initial_load=initial_load,
                        export_to_sharepoint=export_sharepoint,
                        skip_existing_in_weaviate=skip_existing
                    )
                    
                    if result.get('success'):
                        total_results['items_succeeded'] += 1
                        total_results['total_prs_checked'] += result.get('prs_checked', 0)
                        total_results['total_prs_created'] += result.get('prs_created', 0)
                        total_results['total_prs_updated'] += result.get('prs_updated', 0)
                        total_results['total_prs_synced_to_weaviate'] += result.get('prs_synced_to_weaviate', 0)
                        total_results['total_prs_skipped_in_weaviate'] += result.get('prs_skipped_in_weaviate', 0)
                        total_results['total_prs_exported_to_sharepoint'] += result.get('prs_exported_to_sharepoint', 0)
                        
                        prs_created = result.get('prs_created', 0)
                        prs_updated = result.get('prs_updated', 0)
                        
                        if prs_created > 0 or prs_updated > 0 or verbose:
                            self.stdout.write(
                                f"✓ {item.title}: {prs_created} created, {prs_updated} updated"
                            )
                        
                        if result.get('errors'):
                            total_results['errors'].extend(result['errors'])
                    else:
                        total_results['items_failed'] += 1
                        error_msg = f"✗ {item.title}: {result.get('error', 'Unknown error')}"
                        self.stdout.write(self.style.ERROR(error_msg))
                        total_results['errors'].append(error_msg)
                
                except Exception as e:
                    total_results['items_failed'] += 1
                    error_msg = f"✗ {item.title}: {str(e)}"
                    self.stdout.write(self.style.ERROR(error_msg))
                    total_results['errors'].append(error_msg)
            
            # Display overall results
            self.stdout.write('')
            self.stdout.write('=' * 80)
            self.stdout.write(self.style.SUCCESS('Synchronization Results:'))
            self.stdout.write(f"Items processed: {total_results['items_processed']}")
            self.stdout.write(f"Items succeeded: {total_results['items_succeeded']}")
            self.stdout.write(f"Items failed: {total_results['items_failed']}")
            self.stdout.write(f"Total PRs checked: {total_results['total_prs_checked']}")
            self.stdout.write(f"Total PRs created: {total_results['total_prs_created']}")
            self.stdout.write(f"Total PRs updated: {total_results['total_prs_updated']}")
            self.stdout.write(f"Total PRs synced to Weaviate: {total_results['total_prs_synced_to_weaviate']}")
            self.stdout.write(f"Total PRs skipped in Weaviate: {total_results['total_prs_skipped_in_weaviate']}")
            
            if export_sharepoint:
                self.stdout.write(f"Total PRs exported to SharePoint: {total_results['total_prs_exported_to_sharepoint']}")
            
            if total_results['errors']:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING(f"Errors encountered: {len(total_results['errors'])}"))
                if verbose:
                    for error in total_results['errors']:
                        self.stdout.write(self.style.WARNING(f"  - {error}"))
            else:
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('No errors encountered'))
            
            self.stdout.write('=' * 80)
            
            if total_results['items_failed'] > 0:
                raise CommandError('Some items failed to sync')
                
        except GitHubPRSyncServiceError as e:
            self.stdout.write(self.style.ERROR(f'Sync error: {e.message}'))
            if e.details:
                self.stdout.write(self.style.ERROR(f'Details: {e.details}'))
            raise CommandError('Sync failed')
