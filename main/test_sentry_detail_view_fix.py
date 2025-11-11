"""
Test for Sentry DSN and Project Slug storage in item detail view.
This test verifies the fix for the issue where Sentry fields were not being saved
when editing an item through the detail view.
"""
from django.test import TestCase, Client
from main.models import User, Item, Settings


class SentryDetailViewSaveTest(TestCase):
    """Test that Sentry fields are properly saved in the item detail view"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create settings
        self.settings = Settings.objects.create(
            sentry_auth_token='test_sentry_token_123'
        )
        
        # Create test item without Sentry configured
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            created_by=self.user
        )
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in the test user"""
        self.client.post('/login/', {
            'username': self.user.username,
            'password': 'Test@123'
        })
    
    def test_detail_view_saves_sentry_dsn(self):
        """Test that posting to detail view saves Sentry DSN"""
        self.login_user()
        
        # Verify initial state
        self.assertEqual(self.item.sentry_dsn, '')
        
        # Post update with Sentry DSN
        response = self.client.post(f'/items/{self.item.id}/', {
            'title': 'Test Item',
            'description': 'Test description',
            'status': 'new',
            'sentry_dsn': 'https://key123@org456.ingest.sentry.io/78901'
        })
        
        # Reload item from database
        self.item.refresh_from_db()
        
        # Verify DSN was saved
        self.assertEqual(self.item.sentry_dsn, 'https://key123@org456.ingest.sentry.io/78901')
    
    def test_detail_view_saves_sentry_project_slug(self):
        """Test that posting to detail view saves Sentry project slug"""
        self.login_user()
        
        # Verify initial state
        self.assertEqual(self.item.sentry_project_slug, '')
        
        # Post update with Sentry fields
        response = self.client.post(f'/items/{self.item.id}/', {
            'title': 'Test Item',
            'description': 'Test description',
            'status': 'new',
            'sentry_dsn': 'https://key123@org456.ingest.sentry.io/78901',
            'sentry_project_slug': 'my-project-slug'
        })
        
        # Reload item from database
        self.item.refresh_from_db()
        
        # Verify project slug was saved
        self.assertEqual(self.item.sentry_project_slug, 'my-project-slug')
    
    def test_detail_view_saves_enable_sentry_fetch(self):
        """Test that posting to detail view saves enable_sentry_fetch flag"""
        self.login_user()
        
        # Verify initial state
        self.assertFalse(self.item.enable_sentry_fetch)
        
        # Post update with enable_sentry_fetch enabled
        response = self.client.post(f'/items/{self.item.id}/', {
            'title': 'Test Item',
            'description': 'Test description',
            'status': 'new',
            'sentry_dsn': 'https://key123@org456.ingest.sentry.io/78901',
            'sentry_project_slug': 'my-project',
            'enable_sentry_fetch': 'on'
        })
        
        # Reload item from database
        self.item.refresh_from_db()
        
        # Verify flag was saved
        self.assertTrue(self.item.enable_sentry_fetch)
    
    def test_detail_view_saves_all_sentry_fields_together(self):
        """Test that all Sentry fields are saved correctly together"""
        self.login_user()
        
        # Post update with all Sentry fields
        response = self.client.post(f'/items/{self.item.id}/', {
            'title': 'Updated Item',
            'description': 'Updated description',
            'status': 'working',
            'sentry_dsn': 'https://newkey@neworg.ingest.sentry.io/99999',
            'sentry_project_slug': 'updated-project',
            'enable_sentry_fetch': 'on'
        })
        
        # Reload item from database
        self.item.refresh_from_db()
        
        # Verify all Sentry fields were saved
        self.assertEqual(self.item.sentry_dsn, 'https://newkey@neworg.ingest.sentry.io/99999')
        self.assertEqual(self.item.sentry_project_slug, 'updated-project')
        self.assertTrue(self.item.enable_sentry_fetch)
        
        # Also verify other fields were updated
        self.assertEqual(self.item.title, 'Updated Item')
        self.assertEqual(self.item.status, 'working')
    
    def test_detail_view_clears_sentry_fields_when_empty(self):
        """Test that Sentry fields can be cleared by submitting empty values"""
        self.login_user()
        
        # First, set Sentry fields
        self.item.sentry_dsn = 'https://key@org.ingest.sentry.io/123'
        self.item.sentry_project_slug = 'test-project'
        self.item.enable_sentry_fetch = True
        self.item.save()
        
        # Now clear them via POST
        response = self.client.post(f'/items/{self.item.id}/', {
            'title': 'Test Item',
            'description': 'Test description',
            'status': 'new',
            'sentry_dsn': '',
            'sentry_project_slug': ''
            # enable_sentry_fetch not included means unchecked = False
        })
        
        # Reload item from database
        self.item.refresh_from_db()
        
        # Verify fields were cleared
        self.assertEqual(self.item.sentry_dsn, '')
        self.assertEqual(self.item.sentry_project_slug, '')
        self.assertFalse(self.item.enable_sentry_fetch)
    
    def test_detail_view_preserves_other_fields_when_updating_sentry(self):
        """Test that updating Sentry fields doesn't affect other fields"""
        self.login_user()
        
        # Set up item with various fields
        self.item.title = 'Original Title'
        self.item.description = 'Original Description'
        self.item.github_repo = 'owner/repo'
        self.item.save()
        
        # Update only Sentry fields
        response = self.client.post(f'/items/{self.item.id}/', {
            'title': 'Original Title',
            'description': 'Original Description',
            'status': 'new',
            'github_repo': 'owner/repo',
            'sentry_dsn': 'https://key@org.ingest.sentry.io/123',
            'enable_sentry_fetch': 'on'
        })
        
        # Reload item from database
        self.item.refresh_from_db()
        
        # Verify Sentry fields were updated
        self.assertEqual(self.item.sentry_dsn, 'https://key@org.ingest.sentry.io/123')
        self.assertTrue(self.item.enable_sentry_fetch)
        
        # Verify other fields were preserved
        self.assertEqual(self.item.title, 'Original Title')
        self.assertEqual(self.item.description, 'Original Description')
        self.assertEqual(self.item.github_repo, 'owner/repo')
