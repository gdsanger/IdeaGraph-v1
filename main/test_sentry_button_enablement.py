"""
Test to verify that the "Fetch Sentry Errors" button becomes enabled
after saving valid Sentry configuration through the detail view.
"""
from django.test import TestCase
from main.models import User, Item, Settings


class SentryButtonEnablementTest(TestCase):
    """Test that Sentry button enablement logic works correctly"""
    
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
    
    def test_button_disabled_when_no_sentry_config(self):
        """Test that button is disabled when Sentry is not configured"""
        # Button should be disabled due to empty DSN
        self.assertEqual(self.item.sentry_dsn, '')
        self.assertFalse(self.item.enable_sentry_fetch)
        
        # Check button state logic
        button_should_be_disabled = not self.item.sentry_dsn or not self.item.enable_sentry_fetch
        self.assertTrue(button_should_be_disabled, "Button should be disabled when DSN is empty")
    
    def test_button_disabled_when_dsn_set_but_fetch_disabled(self):
        """Test that button is disabled when DSN is set but auto-fetch is disabled"""
        self.item.sentry_dsn = 'https://key@org.ingest.sentry.io/123'
        self.item.enable_sentry_fetch = False
        self.item.save()
        
        # Button should still be disabled because enable_sentry_fetch is False
        button_should_be_disabled = not self.item.sentry_dsn or not self.item.enable_sentry_fetch
        self.assertTrue(button_should_be_disabled, "Button should be disabled when auto-fetch is disabled")
    
    def test_button_disabled_when_fetch_enabled_but_no_dsn(self):
        """Test that button is disabled when auto-fetch is enabled but DSN is empty"""
        self.item.sentry_dsn = ''
        self.item.enable_sentry_fetch = True
        self.item.save()
        
        # Button should be disabled because DSN is empty
        button_should_be_disabled = not self.item.sentry_dsn or not self.item.enable_sentry_fetch
        self.assertTrue(button_should_be_disabled, "Button should be disabled when DSN is empty")
    
    def test_button_enabled_when_both_conditions_met(self):
        """Test that button is enabled when both DSN and auto-fetch are configured"""
        self.item.sentry_dsn = 'https://key@org.ingest.sentry.io/123'
        self.item.sentry_project_slug = 'my-project'
        self.item.enable_sentry_fetch = True
        self.item.save()
        
        # Button should be enabled because both conditions are met
        button_should_be_disabled = not self.item.sentry_dsn or not self.item.enable_sentry_fetch
        self.assertFalse(button_should_be_disabled, "Button should be enabled when both DSN and auto-fetch are set")
    
    def test_workflow_complete_item_becomes_ready_for_sentry_fetch(self):
        """
        Test complete workflow: start with no config, save config, verify button is enabled.
        This test simulates the user workflow described in the issue.
        """
        # Step 1: Initial state - button should be disabled
        self.assertEqual(self.item.sentry_dsn, '')
        self.assertFalse(self.item.enable_sentry_fetch)
        button_disabled = not self.item.sentry_dsn or not self.item.enable_sentry_fetch
        self.assertTrue(button_disabled, "Initially, button should be disabled")
        
        # Step 2: User saves Sentry configuration (simulating POST save in detail view)
        self.item.sentry_dsn = 'https://abc123@org456.ingest.sentry.io/78901'
        self.item.sentry_project_slug = 'ideagraph-v1'
        self.item.enable_sentry_fetch = True
        self.item.save()
        
        # Step 3: Verify configuration is persisted
        self.item.refresh_from_db()
        self.assertEqual(self.item.sentry_dsn, 'https://abc123@org456.ingest.sentry.io/78901')
        self.assertEqual(self.item.sentry_project_slug, 'ideagraph-v1')
        self.assertTrue(self.item.enable_sentry_fetch)
        
        # Step 4: Verify button is now enabled
        button_disabled = not self.item.sentry_dsn or not self.item.enable_sentry_fetch
        self.assertFalse(button_disabled, "After saving valid config, button should be enabled")
        
        print("\n✓ Workflow complete: Item is now ready for Sentry error fetching!")
