"""
Tests for Token Limits Settings
"""
from django.test import TestCase
from main.models import Settings


class TokenLimitsSettingsTestCase(TestCase):
    """Test cases for token limits settings"""
    
    def test_settings_model_has_token_limits_fields(self):
        """Test that Settings model has token limits fields"""
        settings = Settings.objects.create(
            openai_max_tokens=15000,
            kigate_max_tokens=12000
        )
        
        self.assertEqual(settings.openai_max_tokens, 15000)
        self.assertEqual(settings.kigate_max_tokens, 12000)
    
    def test_settings_model_token_limits_defaults(self):
        """Test that Settings model has correct default values for token limits"""
        settings = Settings.objects.create()
        
        # Check defaults
        self.assertEqual(settings.openai_max_tokens, 10000)
        self.assertEqual(settings.kigate_max_tokens, 10000)
    
    def test_settings_model_field_attributes(self):
        """Test that token limits fields have correct attributes"""
        # Get the model field
        openai_field = Settings._meta.get_field('openai_max_tokens')
        kigate_field = Settings._meta.get_field('kigate_max_tokens')
        
        # Verify field properties
        self.assertEqual(openai_field.default, 10000)
        self.assertEqual(kigate_field.default, 10000)
        self.assertIn('OpenAI Max Tokens', openai_field.verbose_name)
        self.assertIn('KiGate Max Tokens', kigate_field.verbose_name)
        self.assertIn('chunked', openai_field.help_text)
        self.assertIn('chunked', kigate_field.help_text)
