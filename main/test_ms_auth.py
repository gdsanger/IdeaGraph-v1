"""
Test suite for Microsoft SSO authentication.
"""
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, Mock, MagicMock
from main.models import User, Settings
from core.services.ms_auth_service import MSAuthService, MSAuthServiceError


class MSAuthServiceTest(TestCase):
    """Test MS Auth Service functionality"""
    
    def setUp(self):
        # Create settings with MS SSO configuration
        self.settings = Settings.objects.create(
            ms_sso_enabled=True,
            ms_sso_client_id='test-client-id',
            ms_sso_tenant_id='test-tenant-id',
            ms_sso_client_secret='test-client-secret'
        )
    
    @patch('core.services.ms_auth_service.msal.ConfidentialClientApplication')
    def test_service_initialization(self, mock_msal):
        """Test MS Auth Service initializes with settings"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        service = MSAuthService()
        self.assertEqual(service.client_id, 'test-client-id')
        self.assertEqual(service.tenant_id, 'test-tenant-id')
        self.assertTrue(service.is_configured())
    
    @patch('core.services.ms_auth_service.msal.ConfidentialClientApplication')
    def test_service_not_configured(self, mock_msal):
        """Test MS Auth Service when SSO is disabled"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        self.settings.ms_sso_enabled = False
        self.settings.save()
        
        service = MSAuthService()
        self.assertFalse(service.is_configured())
    
    @patch('core.services.ms_auth_service.msal.ConfidentialClientApplication')
    def test_get_authorization_url(self, mock_msal):
        """Test authorization URL generation using initiate_auth_code_flow"""
        mock_app = MagicMock()
        mock_app.initiate_auth_code_flow.return_value = {
            'auth_uri': 'https://login.microsoft.com/authorize',
            'state': 'test-state',
            'nonce': 'test-nonce'
        }
        mock_msal.return_value = mock_app
        
        service = MSAuthService()
        redirect_uri = 'http://localhost:8000/callback'
        auth_url, flow = service.get_authorization_url(redirect_uri, 'test-state')
        
        self.assertEqual(auth_url, 'https://login.microsoft.com/authorize')
        self.assertIsInstance(flow, dict)
        self.assertIn('auth_uri', flow)
        mock_app.initiate_auth_code_flow.assert_called_once()
    
    @patch('core.services.ms_auth_service.msal.ConfidentialClientApplication')
    @patch('core.services.ms_auth_service.requests.get')
    def test_get_user_profile(self, mock_get, mock_msal):
        """Test retrieving user profile from Microsoft Graph"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'test-user-id',
            'userPrincipalName': 'testuser@example.com',
            'displayName': 'Test User',
            'mail': 'testuser@example.com'
        }
        mock_get.return_value = mock_response
        
        service = MSAuthService()
        profile = service.get_user_profile('test-access-token')
        
        self.assertEqual(profile['id'], 'test-user-id')
        self.assertEqual(profile['userPrincipalName'], 'testuser@example.com')
        mock_get.assert_called_once()
    
    @patch('core.services.ms_auth_service.msal.ConfidentialClientApplication')
    @patch('core.services.ms_auth_service.requests.get')
    def test_get_user_avatar(self, mock_get, mock_msal):
        """Test retrieving user avatar URL"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        service = MSAuthService()
        avatar_url = service.get_user_avatar('test-access-token')
        
        self.assertIsNotNone(avatar_url)
        self.assertIn('/me/photo/$value', avatar_url)
    
    @patch('core.services.ms_auth_service.msal.ConfidentialClientApplication')
    @patch('core.services.ms_auth_service.requests.get')
    def test_get_user_avatar_not_found(self, mock_get, mock_msal):
        """Test handling when user has no avatar"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        service = MSAuthService()
        avatar_url = service.get_user_avatar('test-access-token')
        
        self.assertIsNone(avatar_url)


class UserMSAuthTest(TestCase):
    """Test User model with MS Auth"""
    
    def test_create_msauth_user(self):
        """Test creating a user with MS Auth type"""
        user = User.objects.create(
            username='testuser@example.com',
            email='testuser@example.com',
            auth_type='msauth',
            ms_user_id='test-ms-user-id',
            role='user',
            is_active=True
        )
        
        self.assertEqual(user.auth_type, 'msauth')
        self.assertEqual(user.ms_user_id, 'test-ms-user-id')
        self.assertEqual(user.password_hash, '')
    
    def test_local_user_default(self):
        """Test local auth is default for new users"""
        user = User.objects.create(
            username='localuser',
            email='local@example.com',
            role='user'
        )
        
        self.assertEqual(user.auth_type, 'local')


class MSAuthViewTest(TestCase):
    """Test MS Auth views"""
    
    def setUp(self):
        self.client = Client()
        self.settings = Settings.objects.create(
            ms_sso_enabled=True,
            ms_sso_client_id='test-client-id',
            ms_sso_tenant_id='test-tenant-id'
        )
    
    def test_ms_sso_login_redirects_when_disabled(self):
        """Test MS SSO login redirects when SSO is disabled"""
        self.settings.ms_sso_enabled = False
        self.settings.save()
        
        response = self.client.get(reverse('main:ms_sso_login'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('main:login')))
    
    @patch('main.auth_views.MSAuthService')
    def test_ms_sso_login_initiates_flow(self, mock_service_class):
        """Test MS SSO login initiates OAuth flow"""
        mock_service = MagicMock()
        mock_service.is_configured.return_value = True
        mock_service.get_authorization_url.return_value = (
            'https://login.microsoft.com/authorize',
            {'auth_uri': 'https://login.microsoft.com/authorize', 'state': 'test-state'}
        )
        mock_service_class.return_value = mock_service
        
        response = self.client.get(reverse('main:ms_sso_login'))
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('login.microsoft.com', response.url)
    
    def test_ms_sso_callback_requires_code(self):
        """Test MS SSO callback requires authorization code"""
        response = self.client.get(reverse('main:ms_sso_callback'))
        self.assertEqual(response.status_code, 302)
        
    def test_login_page_shows_ms_sso_button(self):
        """Test login page shows MS SSO button when enabled"""
        response = self.client.get(reverse('main:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in with Microsoft')
    
    def test_login_page_no_ms_sso_button_when_disabled(self):
        """Test login page hides MS SSO button when disabled"""
        self.settings.ms_sso_enabled = False
        self.settings.save()
        
        response = self.client.get(reverse('main:login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Sign in with Microsoft')


class PasswordChangeDisabledTest(TestCase):
    """Test password change is disabled for MS Auth users"""
    
    def setUp(self):
        self.client = Client()
        self.ms_user = User.objects.create(
            username='msuser@example.com',
            email='msuser@example.com',
            auth_type='msauth',
            role='user',
            is_active=True
        )
        self.local_user = User.objects.create(
            username='localuser',
            email='local@example.com',
            auth_type='local',
            role='user',
            is_active=True
        )
        self.local_user.set_password('Test@1234')
        self.local_user.save()
    
    def test_ms_auth_user_cannot_change_password(self):
        """Test MS Auth user is redirected when trying to change password"""
        # Create a session with MS Auth user info
        session = self.client.session
        session['user_id'] = str(self.ms_user.id)
        session['username'] = self.ms_user.username
        session['user_role'] = self.ms_user.role
        session.save()
        
        response = self.client.get(reverse('main:change_password'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('main:home')))
    
    def test_local_user_can_change_password(self):
        """Test local user can access password change page"""
        # Create a session with user info
        session = self.client.session
        session['user_id'] = str(self.local_user.id)
        session['username'] = self.local_user.username
        session['user_role'] = self.local_user.role
        session.save()
        
        response = self.client.get(reverse('main:change_password'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change Password')


class SettingsUITest(TestCase):
    """Test Settings UI includes MS SSO fields"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('Admin@1234')
        self.admin_user.save()
        
        self.settings = Settings.objects.create(
            ms_sso_enabled=True,
            ms_sso_client_id='test-client-id',
            ms_sso_tenant_id='test-tenant-id'
        )
    
    def test_settings_form_shows_ms_sso_fields(self):
        """Test settings form shows MS SSO configuration fields"""
        # Create a session with admin user info
        session = self.client.session
        session['user_id'] = str(self.admin_user.id)
        session['username'] = self.admin_user.username
        session['user_role'] = self.admin_user.role
        session.save()
        
        response = self.client.get(reverse('main:settings_update', kwargs={'pk': self.settings.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SSO Microsoft Authentication')
        self.assertContains(response, 'ms_sso_enabled')
        self.assertContains(response, 'ms_sso_client_id')
        self.assertContains(response, 'ms_sso_tenant_id')
