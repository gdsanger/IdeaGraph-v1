"""
Management command to initialize default admin user.
"""
from django.core.management.base import BaseCommand
from main.models import User


class Command(BaseCommand):
    help = 'Initialize default admin user if no admin exists'

    def handle(self, *args, **options):
        # Check if any admin user exists
        admin_exists = User.objects.filter(role='admin').exists()
        
        if admin_exists:
            self.stdout.write(
                self.style.WARNING('Admin user already exists. Skipping initialization.')
            )
            return
        
        # Create default admin
        try:
            admin = User(
                username='admin',
                email='admin@local',
                role='admin',
                is_active=True
            )
            admin.set_password('admin1234')
            admin.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully created default admin user:\n'
                    '  Username: admin\n'
                    '  Password: admin1234\n'
                    '  Email: admin@local\n'
                    '\nPlease change the password after first login!'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to create admin user: {str(e)}')
            )
