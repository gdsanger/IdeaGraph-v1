"""
Management command to poll Teams channels for new messages and process them
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

from core.services.teams_integration_service import TeamsIntegrationService, TeamsIntegrationServiceError
from main.models import Settings


logger = logging.getLogger('poll_teams_messages')


class Command(BaseCommand):
    help = 'Poll Teams channels for new messages and process them with AI'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once and exit instead of continuous polling',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=None,
            help='Override poll interval in seconds',
        )
    
    def handle(self, *args, **options):
        """Execute the command"""
        self.stdout.write(self.style.SUCCESS('Starting Teams message polling...'))
        
        # Load settings
        try:
            settings = Settings.objects.first()
            if not settings:
                self.stdout.write(self.style.ERROR('No settings found in database'))
                return
            
            if not settings.teams_enabled:
                self.stdout.write(self.style.WARNING('Teams integration is not enabled'))
                return
            
            # Determine poll interval
            interval = options['interval'] or settings.graph_poll_interval
            self.stdout.write(f'Poll interval: {interval} seconds')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to load settings: {str(e)}'))
            return
        
        # Initialize the integration service
        try:
            integration_service = TeamsIntegrationService(settings=settings)
        except TeamsIntegrationServiceError as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize service: {str(e)}'))
            return
        
        # Run polling
        if options['once']:
            # Run once and exit
            self._poll_once(integration_service)
        else:
            # Continuous polling
            self._poll_continuously(integration_service, interval)
    
    def _poll_once(self, service):
        """Poll once and exit"""
        self.stdout.write('Polling Teams channels (once)...')
        
        try:
            result = service.poll_and_process()
            
            self.stdout.write(self.style.SUCCESS(f'✓ Poll complete'))
            self.stdout.write(f"  Items checked: {result.get('items_checked', 0)}")
            self.stdout.write(f"  Messages found: {result.get('messages_found', 0)}")
            self.stdout.write(f"  Messages processed: {result.get('messages_processed', 0)}")
            self.stdout.write(f"  Tasks created: {result.get('tasks_created', 0)}")
            self.stdout.write(f"  Responses posted: {result.get('responses_posted', 0)}")
            
            if result.get('errors'):
                self.stdout.write(self.style.WARNING(f"  Errors: {len(result['errors'])}"))
                for error in result['errors'][:5]:  # Show first 5 errors
                    self.stdout.write(f"    - {error}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Polling failed: {str(e)}'))
            logger.exception("Polling failed")
    
    def _poll_continuously(self, service, interval):
        """Poll continuously with interval"""
        import time
        
        self.stdout.write(f'Polling continuously every {interval} seconds...')
        self.stdout.write('Press Ctrl+C to stop')
        
        cycle = 0
        try:
            while True:
                cycle += 1
                self.stdout.write(f'\n--- Polling cycle {cycle} at {timezone.now()} ---')
                
                try:
                    result = service.poll_and_process()
                    
                    self.stdout.write(self.style.SUCCESS(f'✓ Cycle {cycle} complete'))
                    self.stdout.write(f"  Items checked: {result.get('items_checked', 0)}")
                    self.stdout.write(f"  Messages found: {result.get('messages_found', 0)}")
                    self.stdout.write(f"  Messages processed: {result.get('messages_processed', 0)}")
                    self.stdout.write(f"  Tasks created: {result.get('tasks_created', 0)}")
                    self.stdout.write(f"  Responses posted: {result.get('responses_posted', 0)}")
                    
                    if result.get('errors'):
                        self.stdout.write(self.style.WARNING(f"  Errors: {len(result['errors'])}"))
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Cycle {cycle} failed: {str(e)}'))
                    logger.exception(f"Cycle {cycle} failed")
                
                # Wait for next cycle
                self.stdout.write(f'Waiting {interval} seconds until next cycle...')
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\nStopping polling (interrupted by user)'))
