"""
Django management command to authenticate with Microsoft using device code flow.

This command initiates the device code flow for delegated authentication,
which is required for posting messages to Teams channels.
"""

from django.core.management.base import BaseCommand
from core.services.delegated_auth_service import DelegatedAuthService, DelegatedAuthServiceError


class Command(BaseCommand):
    help = 'Authenticate with Microsoft using device code flow for Teams channel posting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check current authentication status without initiating new flow',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear cached tokens (requires re-authentication)',
        )

    def handle(self, *args, **options):
        try:
            auth_service = DelegatedAuthService()
            
            # Check if configured
            if not auth_service.is_configured():
                self.stdout.write(self.style.ERROR(
                    'Delegated authentication is not configured.\n'
                    'Please ensure teams_use_delegated_auth is enabled in Settings.'
                ))
                return
            
            # Handle --clear flag
            if options['clear']:
                self.stdout.write('Clearing token cache...')
                auth_service.clear_token_cache()
                self.stdout.write(self.style.SUCCESS('Token cache cleared successfully.'))
                self.stdout.write('Run this command again without --clear to re-authenticate.')
                return
            
            # Handle --check flag
            if options['check']:
                self.stdout.write('Checking authentication status...\n')
                token_info = auth_service.get_token_info()
                
                if token_info.get('authenticated'):
                    self.stdout.write(self.style.SUCCESS('✓ Authenticated'))
                    self.stdout.write(f'  User: {token_info.get("username")}')
                    self.stdout.write(f'  Account ID: {token_info.get("account_id")}')
                    
                    if token_info.get('has_valid_token'):
                        self.stdout.write(self.style.SUCCESS('  ✓ Valid token available'))
                    else:
                        self.stdout.write(self.style.WARNING('  ⚠ Token needs refresh (will happen automatically)'))
                else:
                    self.stdout.write(self.style.ERROR('✗ Not authenticated'))
                    self.stdout.write('  Run this command without --check to authenticate.')
                return
            
            # Check if already authenticated
            if auth_service.has_valid_token():
                self.stdout.write(self.style.SUCCESS(
                    'Already authenticated! Token is valid.\n'
                ))
                token_info = auth_service.get_token_info()
                self.stdout.write(f'Authenticated as: {token_info.get("username")}\n')
                self.stdout.write('Use --clear flag to clear tokens and re-authenticate.')
                return
            
            # Initiate device code flow
            self.stdout.write(self.style.WARNING(
                '\n' + '='*60 + '\n'
                'Microsoft Device Code Authentication\n'
                '='*60 + '\n'
            ))
            
            flow = auth_service.initiate_device_flow()
            
            # Display instructions to user
            self.stdout.write(self.style.SUCCESS('\nPlease follow these steps:\n'))
            self.stdout.write(f'1. Open a browser and go to: {flow.get("verification_uri")}')
            self.stdout.write(f'2. Enter this code: {self.style.SUCCESS(flow.get("user_code"))}')
            self.stdout.write(f'3. Sign in with your Microsoft account')
            self.stdout.write(f'\nExpires in: {flow.get("expires_in")} seconds')
            self.stdout.write('\nWaiting for authentication...\n')
            
            # Wait for user to complete authentication
            result = auth_service.acquire_token_by_device_flow(flow)
            
            # Success!
            self.stdout.write(self.style.SUCCESS(
                '\n' + '='*60 + '\n'
                '✓ Authentication successful!\n'
                '='*60 + '\n'
            ))
            
            token_info = auth_service.get_token_info()
            self.stdout.write(f'Authenticated as: {token_info.get("username")}')
            self.stdout.write('\nToken has been cached and will be automatically refreshed.')
            self.stdout.write('The token will remain valid for approximately 90 days with regular use.')
            self.stdout.write('\nYou can now post messages to Teams channels!')
            
        except DelegatedAuthServiceError as e:
            self.stdout.write(self.style.ERROR(f'\nAuthentication failed: {str(e)}'))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nAuthentication cancelled by user.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nUnexpected error: {str(e)}'))
