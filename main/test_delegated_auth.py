"""
Test suite for Delegated Authentication Service
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock
from main.models import Settings
from core.services.delegated_auth_service import DelegatedAuthService, DelegatedAuthServiceError


class DelegatedAuthServiceTest(TestCase):
    """Test Delegated Auth Service functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with delegated auth configuration
        self.settings = Settings.objects.create(
            teams_use_delegated_auth=True,
            client_id='test-client-id',
            tenant_id='test-tenant-id'
        )
    
    def test_scopes_do_not_contain_reserved_values(self):
        """Test that SCOPES list does not contain reserved scope values"""
        # Reserved scopes that MSAL adds automatically
        reserved_scopes = ['offline_access', 'openid', 'profile']
        
        # Verify none of the reserved scopes are in the SCOPES list
        for scope in DelegatedAuthService.SCOPES:
            self.assertNotIn(scope, reserved_scopes,
                f"Reserved scope '{scope}' should not be in SCOPES list. MSAL adds it automatically.")
    
    def test_scopes_contain_required_graph_api_scopes(self):
        """Test that SCOPES list contains required Microsoft Graph API scopes"""
        required_scopes = [
            'https://graph.microsoft.com/ChannelMessage.Send',
            'https://graph.microsoft.com/Channel.ReadBasic.All',
            'https://graph.microsoft.com/Channel.Create',
            'https://graph.microsoft.com/Team.ReadBasic.All'
        ]
        
        for scope in required_scopes:
            self.assertIn(scope, DelegatedAuthService.SCOPES,
                f"Required scope '{scope}' should be in SCOPES list")
    
    @patch('core.services.delegated_auth_service.msal.PublicClientApplication')
    def test_service_initialization(self, mock_msal):
        """Test Delegated Auth Service initializes with settings"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        service = DelegatedAuthService()
        self.assertEqual(service.client_id, 'test-client-id')
        self.assertEqual(service.tenant_id, 'test-tenant-id')
        self.assertTrue(service.is_configured())
    
    @patch('core.services.delegated_auth_service.msal.PublicClientApplication')
    def test_service_not_configured_when_disabled(self, mock_msal):
        """Test service when delegated auth is disabled"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        self.settings.teams_use_delegated_auth = False
        self.settings.save()
        
        service = DelegatedAuthService()
        self.assertFalse(service.is_configured())
    
    @patch('core.services.delegated_auth_service.msal.PublicClientApplication')
    def test_initiate_device_flow_uses_correct_scopes(self, mock_msal):
        """Test that device flow initiation uses the correct scopes without reserved values"""
        mock_app = MagicMock()
        mock_msal.return_value = mock_app
        
        # Mock successful device flow initiation
        mock_app.initiate_device_flow.return_value = {
            'user_code': 'TEST123',
            'device_code': 'device123',
            'verification_uri': 'https://microsoft.com/devicelogin',
            'message': 'Test message',
            'expires_in': 900
        }
        
        service = DelegatedAuthService()
        flow = service.initiate_device_flow()
        
        # Verify that the scopes passed to MSAL don't contain reserved values
        call_args = mock_app.initiate_device_flow.call_args
        scopes_used = call_args.kwargs.get('scopes', [])
        
        reserved_scopes = ['offline_access', 'openid', 'profile']
        for reserved_scope in reserved_scopes:
            self.assertNotIn(reserved_scope, scopes_used,
                f"Reserved scope '{reserved_scope}' should not be passed to MSAL")
