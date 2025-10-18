from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Settings
import uuid

User = get_user_model()


class SettingsModelTest(TestCase):
    """Test the Settings model"""
    
    def test_create_settings(self):
        """Test creating a settings entry"""
        settings = Settings.objects.create(
            openai_api_key='test-key',
            max_tags_per_idea=10
        )
        self.assertIsInstance(settings.id, uuid.UUID)
        self.assertEqual(settings.openai_api_key, 'test-key')
        self.assertEqual(settings.max_tags_per_idea, 10)
    
    def test_settings_string_representation(self):
        """Test the string representation of settings"""
        settings = Settings.objects.create()
        self.assertTrue(str(settings).startswith('Settings - '))


class SettingsViewTest(TestCase):
    """Test the Settings views"""
    
    def setUp(self):
        """Set up test client and admin user"""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.settings = Settings.objects.create(
            openai_api_key='test-key',
            max_tags_per_idea=5
        )
    
    def test_settings_list_requires_staff(self):
        """Test that settings list requires staff access"""
        response = self.client.get(reverse('main:settings_list'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_settings_list_accessible_by_staff(self):
        """Test that staff can access settings list"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('main:settings_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Settings Management')
    
    def test_settings_create_get(self):
        """Test settings create form display"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('main:settings_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Settings')
    
    def test_settings_create_post(self):
        """Test creating settings via POST"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('main:settings_create'), {
            'openai_api_key': 'new-key',
            'max_tags_per_idea': 15
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(Settings.objects.count(), 2)  # One from setUp, one new
    
    def test_settings_update_get(self):
        """Test settings update form display"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('main:settings_update', kwargs={'pk': self.settings.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Update Settings')
        self.assertContains(response, 'test-key')
    
    def test_settings_update_post(self):
        """Test updating settings via POST"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(
            reverse('main:settings_update', kwargs={'pk': self.settings.id}),
            {
                'openai_api_key': 'updated-key',
                'max_tags_per_idea': 20
            }
        )
        self.assertEqual(response.status_code, 302)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.openai_api_key, 'updated-key')
        self.assertEqual(self.settings.max_tags_per_idea, 20)
    
    def test_settings_delete_get(self):
        """Test settings delete confirmation display"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('main:settings_delete', kwargs={'pk': self.settings.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm Deletion')
    
    def test_settings_delete_post(self):
        """Test deleting settings via POST"""
        self.client.login(username='admin', password='testpass123')
        settings_id = self.settings.id
        response = self.client.post(
            reverse('main:settings_delete', kwargs={'pk': settings_id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Settings.objects.filter(id=settings_id).exists())
