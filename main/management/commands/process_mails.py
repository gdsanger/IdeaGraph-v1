"""
Django management command to process incoming emails and create tasks.

This command retrieves unread emails from a configured mailbox, uses AI and RAG
to match them to Items, generates normalized task descriptions, and sends
confirmation emails to senders.

Usage:
    python manage.py process_mails [--mailbox EMAIL] [--folder FOLDER] [--max-messages N]

Example:
    python manage.py process_mails --mailbox idea@angermeier.net --max-messages 20
"""

from django.core.management.base import BaseCommand, CommandError
from core.services.mail_processing_service import MailProcessingService, MailProcessingServiceError


class Command(BaseCommand):
    help = 'Process incoming emails and create tasks automatically'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mailbox',
            type=str,
            help='Email address of the mailbox to process (uses default from settings if not provided)',
            default=None
        )
        parser.add_argument(
            '--folder',
            type=str,
            help='Mail folder to process (default: inbox)',
            default='inbox'
        )
        parser.add_argument(
            '--max-messages',
            type=int,
            help='Maximum number of messages to process (default: 10)',
            default=10
        )

    def handle(self, *args, **options):
        mailbox = options.get('mailbox')
        folder = options.get('folder')
        max_messages = options.get('max_messages')

        self.stdout.write(self.style.SUCCESS('Starting mail processing...'))
        
        if mailbox:
            self.stdout.write(f'Mailbox: {mailbox}')
        else:
            self.stdout.write('Using default mailbox from settings')
        
        self.stdout.write(f'Folder: {folder}')
        self.stdout.write(f'Max messages: {max_messages}')
        self.stdout.write('')

        try:
            # Initialize service
            service = MailProcessingService()
            
            # Process mailbox
            result = service.process_mailbox(
                mailbox=mailbox,
                folder=folder,
                max_messages=max_messages
            )
            
            if not result.get('success'):
                self.stdout.write(self.style.ERROR(f"Error: {result.get('message')}"))
                raise CommandError('Mail processing failed')
            
            # Display results
            total = result.get('total_messages', 0)
            processed = result.get('processed', 0)
            failed = result.get('failed', 0)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS(f'Mail processing completed!'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(f'Total messages found: {total}')
            self.stdout.write(self.style.SUCCESS(f'Successfully processed: {processed}'))
            
            if failed > 0:
                self.stdout.write(self.style.WARNING(f'Failed: {failed}'))
            
            # Display details for each message
            if result.get('results'):
                self.stdout.write('')
                self.stdout.write('Details:')
                self.stdout.write('-' * 60)
                
                for i, msg_result in enumerate(result['results'], 1):
                    subject = msg_result.get('mail_subject', '(No Subject)')
                    success = msg_result.get('success', False)
                    
                    if success:
                        item_title = msg_result.get('item_title', 'N/A')
                        task_id = msg_result.get('task_id', 'N/A')
                        confirmation_sent = msg_result.get('confirmation_sent', False)
                        archived = msg_result.get('archived', False)
                        
                        self.stdout.write(self.style.SUCCESS(f'\n{i}. ✓ {subject}'))
                        self.stdout.write(f'   Item: {item_title}')
                        self.stdout.write(f'   Task ID: {task_id}')
                        self.stdout.write(f'   Confirmation sent: {"Yes" if confirmation_sent else "No"}')
                        self.stdout.write(f'   Archived: {"Yes" if archived else "No"}')
                    else:
                        message = msg_result.get('message', 'Unknown error')
                        self.stdout.write(self.style.ERROR(f'\n{i}. ✗ {subject}'))
                        self.stdout.write(self.style.ERROR(f'   Error: {message}'))
            
            self.stdout.write('')
            
        except MailProcessingServiceError as e:
            self.stdout.write(self.style.ERROR(f'Service error: {e.message}'))
            if e.details:
                self.stdout.write(self.style.ERROR(f'Details: {e.details}'))
            raise CommandError('Mail processing service error')
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Unexpected error: {str(e)}'))
            raise CommandError('Mail processing failed with unexpected error')
