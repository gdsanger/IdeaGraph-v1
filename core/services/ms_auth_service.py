"""
Microsoft Authentication Service for SSO integration.

This service handles Microsoft Identity authentication using MSAL (Microsoft Authentication Library).
It supports OAuth 2.0 authorization code flow for user authentication and profile retrieval.
"""

import logging
import msal
import requests
from typing import Dict, Optional, Tuple
from django.conf import settings

logger = logging.getLogger('ms_auth_service')


class MSAuthServiceError(Exception):
    """Base exception for MS Auth Service errors"""
    pass


class MSAuthService:
    """
    Service for handling Microsoft Identity authentication.
    
    This service provides methods to:
    - Generate authorization URLs for user login
    - Exchange authorization codes for access tokens
    - Retrieve user profile information from Microsoft Graph
    - Retrieve user avatar/photo from Microsoft Graph
    """
    
    GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
    AUTHORITY_BASE = 'https://login.microsoftonline.com'
    # Note: 'openid', 'profile', and 'email' are reserved scopes automatically handled by MSAL
    # Only specify the Graph API scopes needed
    SCOPES = ['User.Read']
    
    def __init__(self, client_id: str = None, tenant_id: str = None, client_secret: str = None):
        """
        Initialize MS Auth Service with configuration.
        
        Args:
            client_id: Microsoft Azure AD Application (Client) ID
            tenant_id: Microsoft Azure AD Tenant ID
            client_secret: Microsoft Azure AD Client Secret (optional)
        """
        from main.models import Settings
        
        # Get settings from database or use provided values
        try:
            settings_obj = Settings.objects.first()
            self.client_id = client_id or (settings_obj.ms_sso_client_id if settings_obj else '')
            self.tenant_id = tenant_id or (settings_obj.ms_sso_tenant_id if settings_obj else '')
            self.client_secret = client_secret or (settings_obj.ms_sso_client_secret if settings_obj else '')
            self.enabled = settings_obj.ms_sso_enabled if settings_obj else False
        except Exception as e:
            logger.warning(f'Failed to load MS SSO settings from database: {e}')
            self.client_id = client_id or ''
            self.tenant_id = tenant_id or ''
            self.client_secret = client_secret or ''
            self.enabled = False
        
        if not self.client_id or not self.tenant_id:
            logger.warning('MS SSO not configured - client_id or tenant_id missing')
        
        self.authority = f'{self.AUTHORITY_BASE}/{self.tenant_id}'
        self.msal_app = None
        
        if self.client_id and self.tenant_id:
            try:
                self.msal_app = msal.ConfidentialClientApplication(
                    self.client_id,
                    authority=self.authority,
                    client_credential=self.client_secret if self.client_secret else None,
                )
            except Exception as e:
                logger.error(f'Failed to initialize MSAL application: {e}')
                raise MSAuthServiceError(f'Failed to initialize MSAL: {e}')
    
    def is_configured(self) -> bool:
        """Check if MS SSO is properly configured."""
        return bool(self.enabled and self.client_id and self.tenant_id and self.msal_app)
    
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> Tuple[str, Dict]:
        """
        Generate the authorization URL for user login using the recommended auth code flow.
        
        Args:
            redirect_uri: The URI to redirect to after authentication
            state: Optional state parameter for CSRF protection
            
        Returns:
            Tuple of (authorization_url, flow_dict) where flow_dict contains the flow 
            information needed for token acquisition
            
        Raises:
            MSAuthServiceError: If the service is not configured
        """
        if not self.is_configured():
            raise MSAuthServiceError('MS SSO is not properly configured')
        
        try:
            # Use initiate_auth_code_flow instead of deprecated get_authorization_request_url
            # This method automatically handles reserved scopes (openid, profile, offline_access)
            flow = self.msal_app.initiate_auth_code_flow(
                scopes=self.SCOPES,
                redirect_uri=redirect_uri,
                state=state
            )
            
            if 'error' in flow:
                error_desc = flow.get('error_description', 'Unknown error')
                logger.error(f'Failed to initiate auth code flow: {error_desc}')
                raise MSAuthServiceError(f'Failed to initiate auth code flow: {error_desc}')
            
            auth_url = flow.get('auth_uri')
            if not auth_url:
                raise MSAuthServiceError('No authorization URL in flow response')
            
            return auth_url, flow
        except MSAuthServiceError:
            raise
        except Exception as e:
            logger.error(f'Failed to generate authorization URL: {e}')
            raise MSAuthServiceError(f'Failed to generate authorization URL: {e}')
    
    def acquire_token_by_authorization_code(
        self, 
        authorization_code: str, 
        flow: Dict = None
    ) -> Dict:
        """
        Exchange authorization code for access token using the auth code flow.
        
        Args:
            authorization_code: The authorization code from the callback
            flow: The flow dictionary returned from initiate_auth_code_flow (optional)
                  If not provided, will use basic token acquisition
            
        Returns:
            Token response dictionary containing access_token, id_token, etc.
            
        Raises:
            MSAuthServiceError: If token acquisition fails
        """
        if not self.is_configured():
            raise MSAuthServiceError('MS SSO is not properly configured')
        
        try:
            # Use acquire_token_by_auth_code_flow if flow is provided (recommended)
            # Otherwise fall back to acquire_token_by_authorization_code
            if flow:
                result = self.msal_app.acquire_token_by_auth_code_flow(
                    auth_code_flow=flow,
                    auth_response={'code': authorization_code}
                )
            else:
                # Fallback for backward compatibility
                logger.warning('Using acquire_token_by_authorization_code without flow - consider passing flow parameter')
                result = self.msal_app.acquire_token_by_authorization_code(
                    code=authorization_code,
                    scopes=self.SCOPES
                )
            
            if 'error' in result:
                error_desc = result.get('error_description', 'Unknown error')
                logger.error(f'Token acquisition failed: {error_desc}')
                raise MSAuthServiceError(f'Token acquisition failed: {error_desc}')
            
            return result
        except MSAuthServiceError:
            raise
        except Exception as e:
            logger.error(f'Failed to acquire token: {e}')
            raise MSAuthServiceError(f'Failed to acquire token: {e}')
    
    def get_user_profile(self, access_token: str) -> Dict:
        """
        Retrieve user profile information from Microsoft Graph.
        
        Args:
            access_token: Valid access token for Microsoft Graph API
            
        Returns:
            Dictionary containing user profile data:
            - id: Microsoft user ID (OID)
            - userPrincipalName: User's UPN (username)
            - displayName: User's display name
            - mail: User's email address
            - givenName: First name
            - surname: Last name
            
        Raises:
            MSAuthServiceError: If profile retrieval fails
        """
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f'{self.GRAPH_API_ENDPOINT}/me',
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f'Failed to get user profile: {response.status_code} - {response.text}')
                raise MSAuthServiceError(f'Failed to get user profile: {response.status_code}')
            
            return response.json()
        except requests.RequestException as e:
            logger.error(f'Failed to retrieve user profile: {e}')
            raise MSAuthServiceError(f'Failed to retrieve user profile: {e}')
    
    def get_user_avatar(self, access_token: str) -> Optional[str]:
        """
        Retrieve user avatar/photo URL from Microsoft Graph.
        
        Args:
            access_token: Valid access token for Microsoft Graph API
            
        Returns:
            URL to user's avatar photo, or None if not available
        """
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # First check if photo exists
            response = requests.get(
                f'{self.GRAPH_API_ENDPOINT}/me/photo',
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                # Photo exists, return the URL to get photo value
                return f'{self.GRAPH_API_ENDPOINT}/me/photo/$value'
            else:
                logger.info('User has no avatar photo in Microsoft profile')
                return None
                
        except requests.RequestException as e:
            logger.warning(f'Failed to retrieve user avatar: {e}')
            return None
    
    def create_or_update_user(self, token_response: Dict) -> 'User':
        """
        Create or update a user based on Microsoft authentication response.
        
        Args:
            token_response: Token response from acquire_token_by_authorization_code
            
        Returns:
            User object (created or updated)
            
        Raises:
            MSAuthServiceError: If user creation/update fails
        """
        from main.models import User
        from django.utils import timezone
        
        try:
            access_token = token_response.get('access_token')
            if not access_token:
                raise MSAuthServiceError('No access token in response')
            
            # Get user profile from Microsoft Graph
            profile = self.get_user_profile(access_token)
            
            # Extract user information
            ms_user_id = profile.get('id')
            upn = profile.get('userPrincipalName', '')
            email = profile.get('mail') or profile.get('userPrincipalName', '')
            display_name = profile.get('displayName', '')
            
            if not ms_user_id or not upn:
                raise MSAuthServiceError('Invalid user profile data from Microsoft')
            
            # Get avatar URL
            avatar_url = self.get_user_avatar(access_token) or ''
            
            # Check if user exists by UPN or ms_user_id
            user = None
            try:
                user = User.objects.get(username=upn)
            except User.DoesNotExist:
                try:
                    user = User.objects.get(ms_user_id=ms_user_id)
                except User.DoesNotExist:
                    pass
            
            if user:
                # Update existing user
                logger.info(f'Updating existing user: {upn}')
                user.email = email
                user.auth_type = 'msauth'
                user.ms_user_id = ms_user_id
                user.avatar_url = avatar_url
                user.last_login = timezone.now()
                
                # Update display name if provided
                if display_name and not user.username.startswith('admin'):
                    # Keep username as UPN for consistency
                    pass
                
                user.save()
            else:
                # Create new user
                logger.info(f'Creating new MS Auth user: {upn}')
                user = User.objects.create(
                    username=upn,
                    email=email,
                    password_hash='',  # No password for MS Auth users
                    role='user',  # Default role
                    is_active=True,
                    auth_type='msauth',
                    ms_user_id=ms_user_id,
                    avatar_url=avatar_url,
                    last_login=timezone.now()
                )
            
            return user
            
        except MSAuthServiceError:
            raise
        except Exception as e:
            logger.error(f'Failed to create/update user: {e}')
            raise MSAuthServiceError(f'Failed to create/update user: {e}')
