"""
Test for Google PSE Settings integration
"""
from django.test import TestCase
from main.models import Settings


class GooglePSESettingsTest(TestCase):
    """Test Google PSE settings configuration"""
    
    def test_google_pse_fields_exist(self):
        """
        Test that Google PSE fields exist in Settings model
        """
        settings = Settings.objects.create(
            google_pse_enabled=True,
            google_search_api_key='test_api_key',
            google_search_cx='test_cx'
        )
        
        self.assertTrue(settings.google_pse_enabled)
        self.assertEqual(settings.google_search_api_key, 'test_api_key')
        self.assertEqual(settings.google_search_cx, 'test_cx')
    
    def test_google_pse_fields_default_values(self):
        """
        Test that Google PSE fields have correct default values
        """
        settings = Settings.objects.create()
        
        self.assertFalse(settings.google_pse_enabled)
        self.assertEqual(settings.google_search_api_key, '')
        self.assertEqual(settings.google_search_cx, '')
    
    def test_google_pse_fields_can_be_empty(self):
        """
        Test that Google PSE fields can be empty strings
        """
        settings = Settings.objects.create(
            google_pse_enabled=False,
            google_search_api_key='',
            google_search_cx=''
        )
        
        self.assertFalse(settings.google_pse_enabled)
        self.assertEqual(settings.google_search_api_key, '')
        self.assertEqual(settings.google_search_cx, '')


class WebSearchAdapterTest(TestCase):
    """Test WebSearchAdapter with Settings integration"""
    
    def test_web_search_adapter_uses_settings(self):
        """
        Test that WebSearchAdapter reads configuration from Settings
        """
        from core.services.web_search_adapter import WebSearchAdapter
        
        settings = Settings.objects.create(
            google_search_api_key='test_key_123',
            google_search_cx='test_cx_456'
        )
        
        adapter = WebSearchAdapter(settings=settings)
        
        self.assertEqual(adapter.google_api_key, 'test_key_123')
        self.assertEqual(adapter.google_cx, 'test_cx_456')
    
    def test_web_search_adapter_falls_back_to_env(self):
        """
        Test that WebSearchAdapter falls back to environment variables
        if settings fields are empty
        """
        import os
        from core.services.web_search_adapter import WebSearchAdapter
        
        # Set environment variables
        os.environ['GOOGLE_SEARCH_API_KEY'] = 'env_key'
        os.environ['GOOGLE_SEARCH_CX'] = 'env_cx'
        
        settings = Settings.objects.create(
            google_search_api_key='',
            google_search_cx=''
        )
        
        adapter = WebSearchAdapter(settings=settings)
        
        self.assertEqual(adapter.google_api_key, 'env_key')
        self.assertEqual(adapter.google_cx, 'env_cx')
        
        # Clean up
        del os.environ['GOOGLE_SEARCH_API_KEY']
        del os.environ['GOOGLE_SEARCH_CX']
