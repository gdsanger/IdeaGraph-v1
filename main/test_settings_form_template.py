"""
Test for settings form template to ensure no TemplateSyntaxError
"""
from django.test import TestCase
from django.template import Context, Template
from django.template.loader import get_template
from main.models import Settings
import uuid


class SettingsFormTemplateTest(TestCase):
    """Test that the settings form template renders correctly without TemplateSyntaxError"""
    
    def test_template_loads_without_syntax_error(self):
        """Test that the template can be loaded without TemplateSyntaxError"""
        try:
            template = get_template('main/settings_form.html')
            self.assertIsNotNone(template)
        except Exception as e:
            self.fail(f'Template failed to load with error: {e}')
    
    def test_template_renders_with_default_team_welcome_post(self):
        """Test that the template renders with default team_welcome_post value"""
        settings = Settings.objects.create()
        template = get_template('main/settings_form.html')
        
        context = {
            'settings': settings,
            'action': 'Update'
        }
        
        try:
            rendered = template.render(context)
            self.assertIsNotNone(rendered)
            # Check that the default value is used
            self.assertIn('team_welcome_post', rendered)
            # Check that placeholder is present
            self.assertIn('Willkommen im Channel für {{Item}}!', rendered)
        except Exception as e:
            self.fail(f'Template failed to render with error: {e}')
    
    def test_template_renders_with_empty_team_welcome_post(self):
        """Test that the template renders when team_welcome_post is empty"""
        settings = Settings.objects.create()
        settings.team_welcome_post = ''
        settings.save()
        
        template = get_template('main/settings_form.html')
        
        context = {
            'settings': settings,
            'action': 'Update'
        }
        
        try:
            rendered = template.render(context)
            self.assertIsNotNone(rendered)
            self.assertIn('team_welcome_post', rendered)
        except Exception as e:
            self.fail(f'Template failed to render with error: {e}')
    
    def test_template_renders_with_custom_team_welcome_post(self):
        """Test that the template renders when team_welcome_post has a custom value"""
        settings = Settings.objects.create()
        custom_value = 'Custom welcome message for {{Item}}'
        settings.team_welcome_post = custom_value
        settings.save()
        
        template = get_template('main/settings_form.html')
        
        context = {
            'settings': settings,
            'action': 'Update'
        }
        
        try:
            rendered = template.render(context)
            self.assertIsNotNone(rendered)
            # Check that the custom value is in the rendered template
            self.assertIn(custom_value, rendered)
        except Exception as e:
            self.fail(f'Template failed to render with error: {e}')
