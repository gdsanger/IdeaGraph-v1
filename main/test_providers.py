"""
Tests for Provider and ProviderModel functionality
"""
from django.test import TestCase, Client as TestClient
from django.urls import reverse
from main.models import Provider, ProviderModel, User
import uuid


class ProviderModelTest(TestCase):
    """Test Provider model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.provider = Provider.objects.create(
            name='Test OpenAI Provider',
            provider_type='openai',
            api_key='test_key_123',
            api_base_url='https://api.openai.com/v1',
            openai_org_id='org-test123'
        )
    
    def test_provider_creation(self):
        """Test that a provider can be created"""
        self.assertEqual(self.provider.name, 'Test OpenAI Provider')
        self.assertEqual(self.provider.provider_type, 'openai')
        self.assertTrue(self.provider.is_active)
    
    def test_provider_str_representation(self):
        """Test provider string representation"""
        expected = f"{self.provider.name} (OpenAI)"
        self.assertEqual(str(self.provider), expected)
    
    def test_get_default_base_url(self):
        """Test getting default base URL for different provider types"""
        # OpenAI
        openai_provider = Provider(provider_type='openai')
        self.assertEqual(openai_provider.get_default_base_url(), 'https://api.openai.com/v1')
        
        # Gemini
        gemini_provider = Provider(provider_type='gemini')
        self.assertEqual(gemini_provider.get_default_base_url(), 'https://generativelanguage.googleapis.com/v1beta')
        
        # Claude
        claude_provider = Provider(provider_type='claude')
        self.assertEqual(claude_provider.get_default_base_url(), 'https://api.anthropic.com/v1')
        
        # Ollama
        ollama_provider = Provider(provider_type='ollama')
        self.assertEqual(ollama_provider.get_default_base_url(), 'http://localhost:11434/api')


class ProviderModelModelTest(TestCase):
    """Test ProviderModel model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.provider = Provider.objects.create(
            name='Test Provider',
            provider_type='openai',
            api_key='test_key'
        )
        
        self.model = ProviderModel.objects.create(
            provider=self.provider,
            model_id='gpt-4',
            display_name='GPT-4',
            description='Advanced AI model',
            context_length=8192
        )
    
    def test_provider_model_creation(self):
        """Test that a provider model can be created"""
        self.assertEqual(self.model.model_id, 'gpt-4')
        self.assertEqual(self.model.display_name, 'GPT-4')
        self.assertTrue(self.model.is_active)
        self.assertEqual(self.model.context_length, 8192)
    
    def test_provider_model_str_representation(self):
        """Test provider model string representation"""
        expected = f"GPT-4 ({self.provider.name})"
        self.assertEqual(str(self.model), expected)
    
    def test_provider_model_relationship(self):
        """Test relationship between Provider and ProviderModel"""
        self.assertEqual(self.model.provider, self.provider)
        self.assertIn(self.model, self.provider.models.all())


class ProviderViewsTest(TestCase):
    """Test Provider views"""
    
    def setUp(self):
        """Set up test client and user"""
        self.client = TestClient()
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Log in
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session['user_role'] = self.user.role
        session.save()
        
        self.provider = Provider.objects.create(
            name='Test Provider',
            provider_type='openai',
            api_key='test_key'
        )
    
    def test_provider_list_view(self):
        """Test provider list view"""
        url = reverse('main:provider_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Provider')
    
    def test_provider_create_view_get(self):
        """Test provider create view GET request"""
        url = reverse('main:provider_create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Provider')
    
    def test_provider_create_view_post(self):
        """Test provider create view POST request"""
        url = reverse('main:provider_create')
        data = {
            'name': 'New Provider',
            'provider_type': 'gemini',
            'is_active': 'on',
            'api_key': 'new_key_123',
            'api_base_url': 'https://generativelanguage.googleapis.com/v1beta',
            'api_timeout': 30
        }
        response = self.client.post(url, data)
        
        # Should redirect to provider list
        self.assertEqual(response.status_code, 302)
        
        # Check provider was created
        provider = Provider.objects.get(name='New Provider')
        self.assertEqual(provider.provider_type, 'gemini')
        self.assertTrue(provider.is_active)
    
    def test_provider_edit_view_get(self):
        """Test provider edit view GET request"""
        url = reverse('main:provider_edit', args=[self.provider.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Provider')
        self.assertContains(response, 'Edit Provider')
    
    def test_provider_edit_view_post(self):
        """Test provider edit view POST request"""
        url = reverse('main:provider_edit', args=[self.provider.id])
        data = {
            'name': 'Updated Provider',
            'provider_type': 'openai',
            'is_active': 'on',
            'api_key': 'updated_key',
            'api_base_url': 'https://api.openai.com/v1',
            'api_timeout': 60
        }
        response = self.client.post(url, data)
        
        # Should redirect to provider list
        self.assertEqual(response.status_code, 302)
        
        # Check provider was updated
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.name, 'Updated Provider')
        self.assertEqual(self.provider.api_timeout, 60)
    
    def test_provider_delete_view_get(self):
        """Test provider delete view GET request"""
        url = reverse('main:provider_delete', args=[self.provider.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Provider')
        self.assertContains(response, 'Test Provider')
    
    def test_provider_delete_view_post(self):
        """Test provider delete view POST request"""
        provider_id = self.provider.id
        url = reverse('main:provider_delete', args=[provider_id])
        response = self.client.post(url)
        
        # Should redirect to provider list
        self.assertEqual(response.status_code, 302)
        
        # Check provider was deleted
        with self.assertRaises(Provider.DoesNotExist):
            Provider.objects.get(id=provider_id)
    
    def test_provider_models_view(self):
        """Test provider models view"""
        # Create some models for the provider
        ProviderModel.objects.create(
            provider=self.provider,
            model_id='gpt-4',
            display_name='GPT-4'
        )
        ProviderModel.objects.create(
            provider=self.provider,
            model_id='gpt-3.5-turbo',
            display_name='GPT-3.5 Turbo'
        )
        
        url = reverse('main:provider_models', args=[self.provider.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'gpt-4')
        self.assertContains(response, 'gpt-3.5-turbo')
    
    def test_provider_model_toggle(self):
        """Test toggling provider model activation status"""
        model = ProviderModel.objects.create(
            provider=self.provider,
            model_id='gpt-4',
            is_active=True
        )
        
        url = reverse('main:provider_model_toggle', args=[model.id])
        response = self.client.post(url)
        
        # Should redirect to provider models view
        self.assertEqual(response.status_code, 302)
        
        # Check model was toggled
        model.refresh_from_db()
        self.assertFalse(model.is_active)
        
        # Toggle again
        response = self.client.post(url)
        model.refresh_from_db()
        self.assertTrue(model.is_active)


class ProviderViewsAuthTest(TestCase):
    """Test authentication for Provider views"""
    
    def test_provider_list_requires_authentication(self):
        """Test that provider list requires authentication"""
        client = TestClient()
        url = reverse('main:provider_list')
        response = client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login'))
    
    def test_provider_create_requires_authentication(self):
        """Test that provider create requires authentication"""
        client = TestClient()
        url = reverse('main:provider_create')
        response = client.get(url)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login'))
