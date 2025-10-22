"""
Tests for Zammad configuration in settings form
"""
from django.test import TestCase
from main.models import Settings


class ZammadSettingsTest(TestCase):
    """Test cases for Zammad settings configuration"""
    
    def test_settings_create_with_zammad_enabled(self):
        """Test creating settings with Zammad integration enabled"""
        settings = Settings.objects.create(
            zammad_enabled=True,
            zammad_api_url='https://test-zammad.com',
            zammad_api_token='test_token_123',
            zammad_groups='Support, Development',
            zammad_sync_interval=30
        )
        
        self.assertTrue(settings.zammad_enabled)
        self.assertEqual(settings.zammad_api_url, 'https://test-zammad.com')
        self.assertEqual(settings.zammad_api_token, 'test_token_123')
        self.assertEqual(settings.zammad_groups, 'Support, Development')
        self.assertEqual(settings.zammad_sync_interval, 30)
    
    def test_settings_create_with_zammad_disabled(self):
        """Test creating settings with Zammad integration disabled"""
        settings = Settings.objects.create(
            zammad_enabled=False,
            zammad_api_url='',
            zammad_api_token='',
            zammad_groups='',
            zammad_sync_interval=15
        )
        
        self.assertFalse(settings.zammad_enabled)
        self.assertEqual(settings.zammad_api_url, '')
        self.assertEqual(settings.zammad_api_token, '')
        self.assertEqual(settings.zammad_groups, '')
        self.assertEqual(settings.zammad_sync_interval, 15)
    
    def test_settings_update_toggle_zammad_enabled(self):
        """Test updating settings to enable Zammad integration"""
        settings = Settings.objects.create(
            zammad_enabled=False,
            zammad_api_url='',
            zammad_api_token='',
            zammad_groups='',
            zammad_sync_interval=15
        )
        
        settings.zammad_enabled = True
        settings.zammad_api_url = 'https://new-zammad.com'
        settings.zammad_api_token = 'new_token_456'
        settings.zammad_groups = 'IT, Support'
        settings.zammad_sync_interval = 20
        settings.save()
        
        settings.refresh_from_db()
        self.assertTrue(settings.zammad_enabled)
        self.assertEqual(settings.zammad_api_url, 'https://new-zammad.com')
        self.assertEqual(settings.zammad_api_token, 'new_token_456')
        self.assertEqual(settings.zammad_groups, 'IT, Support')
        self.assertEqual(settings.zammad_sync_interval, 20)
    
    def test_settings_update_toggle_zammad_disabled(self):
        """Test updating settings to disable Zammad integration"""
        settings = Settings.objects.create(
            zammad_enabled=True,
            zammad_api_url='https://old-zammad.com',
            zammad_api_token='old_token',
            zammad_groups='Support',
            zammad_sync_interval=15
        )
        
        settings.zammad_enabled = False
        settings.save()
        
        settings.refresh_from_db()
        self.assertFalse(settings.zammad_enabled)
    
    def test_settings_defaults(self):
        """Test that Zammad settings have correct default values"""
        settings = Settings.objects.create()
        
        self.assertFalse(settings.zammad_enabled)
        self.assertEqual(settings.zammad_api_url, '')
        self.assertEqual(settings.zammad_api_token, '')
        self.assertEqual(settings.zammad_groups, '')
        self.assertEqual(settings.zammad_sync_interval, 15)


class ZammadSettingsViewIntegrationTest(TestCase):
    """Test suite for Settings views with Zammad toggle - simulating view logic"""
    
    def test_settings_view_integration_create_enabled(self):
        """Integration test: Create settings with Zammad enabled via view logic simulation"""
        post_data = {
            'zammad_enabled': 'on',
            'zammad_api_url': 'https://test-zammad.com',
            'zammad_api_token': 'test_token_123',
            'zammad_groups': 'Support, Development',
            'zammad_sync_interval': '30',
            'max_tags_per_idea': '5'
        }
        
        # Create settings object as the view does
        settings = Settings.objects.create(
            zammad_enabled=post_data.get('zammad_enabled') == 'on',
            zammad_api_url=post_data.get('zammad_api_url', ''),
            zammad_api_token=post_data.get('zammad_api_token', ''),
            zammad_groups=post_data.get('zammad_groups', ''),
            zammad_sync_interval=int(post_data.get('zammad_sync_interval') or 15),
            max_tags_per_idea=int(post_data.get('max_tags_per_idea') or 5)
        )
        
        # Verify results
        self.assertTrue(settings.zammad_enabled)
        self.assertEqual(settings.zammad_api_url, 'https://test-zammad.com')
        self.assertEqual(settings.zammad_api_token, 'test_token_123')
        self.assertEqual(settings.zammad_groups, 'Support, Development')
        self.assertEqual(settings.zammad_sync_interval, 30)
    
    def test_settings_view_integration_create_disabled(self):
        """Integration test: Create settings with Zammad disabled via view logic simulation"""
        post_data = {
            'max_tags_per_idea': '5'
        }
        
        # Create settings object as the view does
        settings = Settings.objects.create(
            zammad_enabled=post_data.get('zammad_enabled') == 'on',  # False when not present
            zammad_api_url=post_data.get('zammad_api_url', ''),
            zammad_api_token=post_data.get('zammad_api_token', ''),
            zammad_groups=post_data.get('zammad_groups', ''),
            zammad_sync_interval=int(post_data.get('zammad_sync_interval') or 15),
            max_tags_per_idea=int(post_data.get('max_tags_per_idea') or 5)
        )
        
        # Verify toggle is disabled
        self.assertFalse(settings.zammad_enabled)
        self.assertEqual(settings.zammad_api_url, '')
        self.assertEqual(settings.zammad_api_token, '')
        self.assertEqual(settings.zammad_groups, '')
        self.assertEqual(settings.zammad_sync_interval, 15)
    
    def test_settings_view_integration_update_enabled(self):
        """Integration test: Update settings to enable Zammad via view logic simulation"""
        settings = Settings.objects.create(
            zammad_enabled=False,
            zammad_api_url='',
            zammad_api_token='',
            zammad_groups='',
            zammad_sync_interval=15
        )
        
        post_data = {
            'zammad_enabled': 'on',
            'zammad_api_url': 'https://new-zammad.com',
            'zammad_api_token': 'new_token_456',
            'zammad_groups': 'IT, Support',
            'zammad_sync_interval': '20',
            'max_tags_per_idea': '5'
        }
        
        # Update as the view does
        settings.zammad_enabled = post_data.get('zammad_enabled') == 'on'
        settings.zammad_api_url = post_data.get('zammad_api_url', '')
        settings.zammad_api_token = post_data.get('zammad_api_token', '')
        settings.zammad_groups = post_data.get('zammad_groups', '')
        settings.zammad_sync_interval = int(post_data.get('zammad_sync_interval') or 15)
        settings.save()
        
        # Verify update
        settings.refresh_from_db()
        self.assertTrue(settings.zammad_enabled)
        self.assertEqual(settings.zammad_api_url, 'https://new-zammad.com')
        self.assertEqual(settings.zammad_api_token, 'new_token_456')
        self.assertEqual(settings.zammad_groups, 'IT, Support')
        self.assertEqual(settings.zammad_sync_interval, 20)
    
    def test_settings_view_integration_update_disabled(self):
        """Integration test: Update settings to disable Zammad via view logic simulation"""
        settings = Settings.objects.create(
            zammad_enabled=True,
            zammad_api_url='https://old-zammad.com',
            zammad_api_token='old_token',
            zammad_groups='Support',
            zammad_sync_interval=15
        )
        
        post_data = {
            'max_tags_per_idea': '5'
        }
        
        # Update as the view does (unchecked checkbox means not in POST data)
        settings.zammad_enabled = post_data.get('zammad_enabled') == 'on'
        settings.zammad_api_url = post_data.get('zammad_api_url', '')
        settings.zammad_api_token = post_data.get('zammad_api_token', '')
        settings.zammad_groups = post_data.get('zammad_groups', '')
        settings.zammad_sync_interval = int(post_data.get('zammad_sync_interval') or 15)
        settings.save()
        
        # Verify toggle is disabled
        settings.refresh_from_db()
        self.assertFalse(settings.zammad_enabled)
