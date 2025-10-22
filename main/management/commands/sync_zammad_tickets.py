"""
Django management command to synchronize Zammad tickets with IdeaGraph tasks.

This command retrieves open tickets from configured Zammad groups and creates
or updates corresponding tasks in IdeaGraph.

Usage:
    python manage.py sync_zammad_tickets [--groups GROUP1,GROUP2] [--test-connection]

Example:
    python manage.py sync_zammad_tickets --groups "Support,Development"
    python manage.py sync_zammad_tickets --test-connection
"""

from django.core.management.base import BaseCommand, CommandError
from core.services.zammad_sync_service import ZammadSyncService, ZammadSyncServiceError


class Command(BaseCommand):
    help = 'Synchronize Zammad tickets with IdeaGraph tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--groups',
            type=str,
            help='Comma-separated list of Zammad groups to sync (uses configured groups if not provided)',
            default=None
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test connection to Zammad API and exit',
            default=False
        )

    def handle(self, *args, **options):
        test_connection = options.get('test_connection')
        groups = options.get('groups')
        
        if test_connection:
            self.stdout.write(self.style.SUCCESS('Testing Zammad API connection...'))
            self.stdout.write('')
            
            try:
                service = ZammadSyncService()
                result = service.test_connection()
                
                if result.get('success'):
                    self.stdout.write(self.style.SUCCESS('✓ Connection successful!'))
                    self.stdout.write(f"API URL: {result.get('api_url')}")
                    self.stdout.write(f"Authenticated as: {result.get('user')}")
                else:
                    self.stdout.write(self.style.ERROR('✗ Connection failed!'))
                    self.stdout.write(self.style.ERROR(f"Error: {result.get('error')}"))
                    if result.get('details'):
                        self.stdout.write(self.style.ERROR(f"Details: {result.get('details')}"))
                    raise CommandError('Connection test failed')
                    
            except ZammadSyncServiceError as e:
                self.stdout.write(self.style.ERROR(f'Service error: {e.message}'))
                if e.details:
                    self.stdout.write(self.style.ERROR(f'Details: {e.details}'))
                raise CommandError('Zammad service initialization failed')
            
            return

        # Normal sync operation
        self.stdout.write(self.style.SUCCESS('Starting Zammad ticket synchronization...'))
        
        if groups:
            group_list = [g.strip() for g in groups.split(',')]
            self.stdout.write(f'Groups: {", ".join(group_list)}')
        else:
            self.stdout.write('Using configured groups from settings')
        
        self.stdout.write('')

        try:
            # Initialize service
            service = ZammadSyncService()
            
            # Sync tickets
            if groups:
                group_list = [g.strip() for g in groups.split(',')]
                tickets = service.fetch_open_tickets(group_list)
                
                # Process tickets manually
                results = {
                    'success': True,
                    'total_tickets': len(tickets),
                    'created': 0,
                    'updated': 0,
                    'failed': 0,
                    'errors': []
                }
                
                for ticket in tickets:
                    result = service.sync_ticket_to_task(ticket)
                    if result.get('success'):
                        if result.get('action') == 'created':
                            results['created'] += 1
                        elif result.get('action') == 'updated':
                            results['updated'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'ticket_id': result.get('ticket_id'),
                            'error': result.get('error')
                        })
            else:
                results = service.sync_all_tickets()
            
            if not results.get('success'):
                self.stdout.write(self.style.ERROR(f"Error: {results.get('message')}"))
                raise CommandError('Ticket synchronization failed')
            
            # Display results
            total = results.get('total_tickets', 0)
            created = results.get('created', 0)
            updated = results.get('updated', 0)
            failed = results.get('failed', 0)
            duration = results.get('duration_seconds', 0)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS('Synchronization completed!'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(f'Total tickets found: {total}')
            self.stdout.write(self.style.SUCCESS(f'Tasks created: {created}'))
            self.stdout.write(self.style.SUCCESS(f'Tasks updated: {updated}'))
            
            if failed > 0:
                self.stdout.write(self.style.WARNING(f'Failed: {failed}'))
            
            if duration:
                self.stdout.write(f'Duration: {duration:.2f} seconds')
            
            # Display errors if any
            if results.get('errors'):
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('Errors:'))
                self.stdout.write('-' * 60)
                
                for error in results['errors']:
                    ticket_id = error.get('ticket_id', 'Unknown')
                    error_msg = error.get('error', 'Unknown error')
                    self.stdout.write(self.style.ERROR(f'Ticket {ticket_id}: {error_msg}'))
            
            self.stdout.write('')
            
        except ZammadSyncServiceError as e:
            self.stdout.write(self.style.ERROR(f'Service error: {e.message}'))
            if e.details:
                self.stdout.write(self.style.ERROR(f'Details: {e.details}'))
            raise CommandError('Zammad synchronization service error')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {str(e)}'))
            raise CommandError('Synchronization failed with unexpected error')
