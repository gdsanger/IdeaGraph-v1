"""
Management command to synchronize tags to Weaviate

This command synchronizes all tags from the database to Weaviate.
Can be run as a cron job to keep tags in sync.

Usage:
    python manage.py sync_tags_to_weaviate
"""

from django.core.management.base import BaseCommand
from core.services.weaviate_tag_sync_service import WeaviateTagSyncService, WeaviateTagSyncServiceError


class Command(BaseCommand):
    help = 'Synchronize all tags to Weaviate vector database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tag-id',
            type=str,
            help='Sync only a specific tag by UUID',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def handle(self, *args, **options):
        tag_id = options.get('tag_id')
        verbose = options.get('verbose', False)

        try:
            # Initialize service
            service = WeaviateTagSyncService()
            
            if tag_id:
                # Sync single tag
                from main.models import Tag
                try:
                    tag = Tag.objects.get(id=tag_id)
                    self.stdout.write(f"Syncing tag: {tag.name} ({tag.id})")
                    
                    result = service.sync_update(tag)
                    
                    if result['success']:
                        self.stdout.write(self.style.SUCCESS(f"✓ {result['message']}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"✗ {result.get('error', 'Unknown error')}"))
                        
                except Tag.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"Tag with ID {tag_id} not found"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to sync tag: {str(e)}"))
            else:
                # Sync all tags
                self.stdout.write("Syncing all tags to Weaviate...")
                
                result = service.sync_all_tags()
                
                if result['success']:
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ Successfully synced {result['synced_count']}/{result['total_count']} tags"
                    ))
                    
                    if result['failed_count'] > 0:
                        self.stdout.write(self.style.WARNING(
                            f"⚠ {result['failed_count']} tags failed to sync"
                        ))
                    
                    if verbose:
                        self.stdout.write(f"Total tags: {result['total_count']}")
                        self.stdout.write(f"Synced: {result['synced_count']}")
                        self.stdout.write(f"Failed: {result['failed_count']}")
                else:
                    self.stdout.write(self.style.ERROR(
                        f"✗ Sync failed: {result.get('error', 'Unknown error')}"
                    ))
            
            # Close connection
            service.close()
            
        except WeaviateTagSyncServiceError as e:
            self.stdout.write(self.style.ERROR(f"✗ Service error: {e.message}"))
            if e.details and verbose:
                self.stdout.write(self.style.ERROR(f"  Details: {e.details}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Unexpected error: {str(e)}"))
            if verbose:
                import traceback
                self.stdout.write(traceback.format_exc())
