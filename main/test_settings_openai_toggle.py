"""
Tests for OpenAI API toggle in Settings
"""
from django.test import TestCase, Client
from django.urls import reverse
from main.models import Settings, User as AppUser


class SettingsOpenAIToggleTestCase(TestCase):
    """Test suite for OpenAI API enable/disable toggle in Settings"""
    
    def setUp(self):
        """Set up test data"""
        # Create test admin user
        self.admin_user = AppUser.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('admin123')
        self.admin_user.save()
        
        # Get auth token
        from main.auth_utils import generate_jwt_token
        self.token = generate_jwt_token(self.admin_user)
        
        self.client = Client()
    
    def test_settings_create_with_openai_enabled(self):
        """Test creating settings with OpenAI API enabled"""
        settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='sk-test-key-123',
            openai_org_id='org-test-123',
            openai_default_model='gpt-4',
            openai_api_base_url='https://api.openai.com/v1',
            openai_api_timeout=30
        )
        
        self.assertTrue(settings.openai_api_enabled)
        self.assertEqual(settings.openai_api_key, 'sk-test-key-123')
        self.assertEqual(settings.openai_org_id, 'org-test-123')
        self.assertEqual(settings.openai_default_model, 'gpt-4')
        self.assertEqual(settings.openai_api_base_url, 'https://api.openai.com/v1')
        self.assertEqual(settings.openai_api_timeout, 30)
    
    def test_settings_create_with_openai_disabled(self):
        """Test creating settings with OpenAI API disabled"""
        settings = Settings.objects.create(
            openai_api_enabled=False,
            openai_api_key='sk-test-key-123',
            openai_org_id='org-test-123'
        )
        
        self.assertFalse(settings.openai_api_enabled)
        self.assertEqual(settings.openai_api_key, 'sk-test-key-123')
    
    def test_settings_update_toggle_enabled(self):
        """Test updating settings to enable OpenAI API"""
        settings = Settings.objects.create(
            openai_api_enabled=False,
            openai_api_key='sk-test-key-123'
        )
        
        settings.openai_api_enabled = True
        settings.save()
        
        settings.refresh_from_db()
        self.assertTrue(settings.openai_api_enabled)
    
    def test_settings_update_toggle_disabled(self):
        """Test updating settings to disable OpenAI API"""
        settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='sk-test-key-123'
        )
        
        settings.openai_api_enabled = False
        settings.save()
        
        settings.refresh_from_db()
        self.assertFalse(settings.openai_api_enabled)
    
    def test_settings_defaults(self):
        """Test that settings have correct default values"""
        settings = Settings.objects.create()
        
        self.assertFalse(settings.openai_api_enabled)
        self.assertEqual(settings.openai_default_model, 'gpt-4')
        self.assertEqual(settings.openai_api_base_url, 'https://api.openai.com/v1')
        self.assertEqual(settings.openai_api_timeout, 30)
    
    def test_openai_service_respects_toggle_disabled(self):
        """Test that OpenAI service respects the enabled toggle when disabled"""
        from core.services.openai_service import OpenAIService, OpenAIServiceError
        
        settings = Settings.objects.create(
            openai_api_enabled=False,
            openai_api_key='sk-test-key-123'
        )
        
        with self.assertRaises(OpenAIServiceError) as context:
            OpenAIService(settings)
        
        self.assertIn("not enabled", str(context.exception))
    
    def test_openai_service_respects_toggle_enabled(self):
        """Test that OpenAI service works when enabled"""
        from core.services.openai_service import OpenAIService
        
        settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='sk-test-key-123',
            openai_api_base_url='https://api.openai.com/v1'
        )
        
        # Should not raise an exception
        service = OpenAIService(settings)
        self.assertIsNotNone(service)
        self.assertEqual(service.api_key, 'sk-test-key-123')
    
    def test_chroma_sync_respects_toggle(self):
        """Test that ChromaDB sync service respects OpenAI toggle"""
        from core.services.chroma_sync_service import ChromaItemSyncServiceError
        
        settings = Settings.objects.create(
            openai_api_enabled=False,
            openai_api_key='sk-test-key-123',
            chroma_api_key='test-chroma-key',
            chroma_database='test-db',
            chroma_tenant='test-tenant'
        )
        
        # The service should initialize (chroma doesn't check toggle in __init__)
        # but embedding generation should fail
        from unittest.mock import patch
        with patch('core.services.chroma_sync_service.chromadb.HttpClient'):
            from core.services.chroma_sync_service import ChromaItemSyncService
            service = ChromaItemSyncService(settings)
            
            # Try to generate embedding - should fail
            with self.assertRaises(ChromaItemSyncServiceError) as context:
                service._generate_embedding("test text")
            
            self.assertIn("not enabled", str(context.exception))


class SettingsViewOpenAIToggleTestCase(TestCase):
    """Test suite for Settings views with OpenAI toggle"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
    
    def test_settings_view_integration_create_enabled(self):
        """Integration test: Create settings with OpenAI enabled via view logic simulation"""
        # Simulate what the view does
        post_data = {
            'openai_api_enabled': 'on',
            'openai_api_key': 'sk-test-123',
            'openai_org_id': 'org-123',
            'openai_default_model': 'gpt-4',
            'openai_api_base_url': 'https://api.openai.com/v1',
            'openai_api_timeout': '30',
            'max_tags_per_idea': '5'
        }
        
        # Create settings object as the view does
        settings = Settings.objects.create(
            openai_api_enabled=post_data.get('openai_api_enabled') == 'on',
            openai_api_key=post_data.get('openai_api_key', ''),
            openai_org_id=post_data.get('openai_org_id', ''),
            openai_default_model=post_data.get('openai_default_model', 'gpt-4'),
            openai_api_base_url=post_data.get('openai_api_base_url', 'https://api.openai.com/v1'),
            openai_api_timeout=int(post_data.get('openai_api_timeout') or 30),
            max_tags_per_idea=int(post_data.get('max_tags_per_idea') or 5)
        )
        
        # Verify results
        self.assertTrue(settings.openai_api_enabled)
        self.assertEqual(settings.openai_api_key, 'sk-test-123')
        self.assertEqual(settings.openai_default_model, 'gpt-4')
        self.assertEqual(settings.openai_api_timeout, 30)
    
    def test_settings_view_integration_create_disabled(self):
        """Integration test: Create settings with OpenAI disabled via view logic simulation"""
        # Simulate what the view does when checkbox is unchecked
        post_data = {
            'openai_api_key': 'sk-test-123',
            'max_tags_per_idea': '5'
        }
        
        # Create settings object as the view does
        settings = Settings.objects.create(
            openai_api_enabled=post_data.get('openai_api_enabled') == 'on',  # False when not present
            openai_api_key=post_data.get('openai_api_key', ''),
            openai_org_id=post_data.get('openai_org_id', ''),
            openai_default_model=post_data.get('openai_default_model', 'gpt-4'),
            openai_api_base_url=post_data.get('openai_api_base_url', 'https://api.openai.com/v1'),
            openai_api_timeout=int(post_data.get('openai_api_timeout') or 30),
            max_tags_per_idea=int(post_data.get('max_tags_per_idea') or 5)
        )
        
        # Verify toggle is disabled
        self.assertFalse(settings.openai_api_enabled)
        self.assertEqual(settings.openai_api_key, 'sk-test-123')
    
    def test_settings_view_integration_update_enabled(self):
        """Integration test: Update settings to enable OpenAI via view logic simulation"""
        settings = Settings.objects.create(
            openai_api_enabled=False,
            openai_api_key='sk-old-key'
        )
        
        post_data = {
            'openai_api_enabled': 'on',
            'openai_api_key': 'sk-new-key',
            'openai_default_model': 'gpt-4',
            'openai_api_base_url': 'https://api.openai.com/v1',
            'openai_api_timeout': '45',
            'max_tags_per_idea': '5'
        }
        
        # Update as the view does
        settings.openai_api_enabled = post_data.get('openai_api_enabled') == 'on'
        settings.openai_api_key = post_data.get('openai_api_key', '')
        settings.openai_org_id = post_data.get('openai_org_id', '')
        settings.openai_default_model = post_data.get('openai_default_model', 'gpt-4')
        settings.openai_api_base_url = post_data.get('openai_api_base_url', 'https://api.openai.com/v1')
        settings.openai_api_timeout = int(post_data.get('openai_api_timeout') or 30)
        settings.save()
        
        # Verify update
        settings.refresh_from_db()
        self.assertTrue(settings.openai_api_enabled)
        self.assertEqual(settings.openai_api_key, 'sk-new-key')
        self.assertEqual(settings.openai_api_timeout, 45)
    
    def test_settings_view_integration_update_disabled(self):
        """Integration test: Update settings to disable OpenAI via view logic simulation"""
        settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='sk-test-key'
        )
        
        post_data = {
            'openai_api_key': 'sk-test-key',
            'max_tags_per_idea': '5'
        }
        
        # Update as the view does (unchecked checkbox means not in POST data)
        settings.openai_api_enabled = post_data.get('openai_api_enabled') == 'on'
        settings.openai_api_key = post_data.get('openai_api_key', '')
        settings.save()
        
        # Verify toggle is disabled
        settings.refresh_from_db()
        self.assertFalse(settings.openai_api_enabled)
