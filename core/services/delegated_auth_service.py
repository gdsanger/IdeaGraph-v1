"""
Delegated Authentication Service for Microsoft Graph API

This service handles user-delegated authentication using MSAL's device code flow.
It supports persistent token caching with automatic refresh.
"""

import logging
import os
import msal
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger('delegated_auth_service')


class DelegatedAuthServiceError(Exception):
    """Base exception for Delegated Auth Service errors"""
    pass


class DelegatedAuthService:
    """
    Service for handling user-delegated authentication with device code flow.
    
    This service provides methods to:
    - Initiate device code flow for user authentication
    - Acquire and cache access tokens with refresh tokens
    - Automatically refresh tokens (MSAL handles offline_access internally)
    - Persist tokens to disk for long-term use (90-day sliding window)
    """
    
    AUTHORITY_BASE = 'https://login.microsoftonline.com'
    # Scopes needed for Teams channel operations (read/write)
    # Note: Reserved scopes like 'offline_access', 'openid', 'profile' are automatically added by MSAL
    SCOPES = [
        'https://graph.microsoft.com/ChannelMessage.Send',
        'https://graph.microsoft.com/Channel.ReadBasic.All',
        'https://graph.microsoft.com/Channel.Create',
        'https://graph.microsoft.com/Team.ReadBasic.All'
    ]
    
    def __init__(self, client_id: str = None, tenant_id: str = None, token_cache_path: str = None):
        """
        Initialize Delegated Auth Service with configuration.
        
        Args:
            client_id: Microsoft Azure AD Application (Client) ID
            tenant_id: Microsoft Azure AD Tenant ID
            token_cache_path: Path to store the token cache (default: data/msal_token_cache.bin)
        """
        from main.models import Settings
        
        # Get settings from database or use provided values
        try:
            settings_obj = Settings.objects.first()
            self.client_id = client_id or (settings_obj.client_id if settings_obj else '')
            self.tenant_id = tenant_id or (settings_obj.tenant_id if settings_obj else '')
            self.enabled = settings_obj.teams_use_delegated_auth if settings_obj else False
        except Exception as e:
            logger.warning(f'Failed to load settings from database: {e}')
            self.client_id = client_id or ''
            self.tenant_id = tenant_id or ''
            self.enabled = False
        
        if not self.client_id or not self.tenant_id:
            logger.warning('Delegated auth not configured - client_id or tenant_id missing')
        
        self.authority = f'{self.AUTHORITY_BASE}/{self.tenant_id}'
        
        # Set up token cache path
        if token_cache_path is None:
            # Use data directory in project root
            project_root = Path(__file__).parent.parent.parent
            cache_dir = project_root / 'data'
            cache_dir.mkdir(exist_ok=True)
            token_cache_path = str(cache_dir / 'msal_token_cache.bin')
        
        self.token_cache_path = token_cache_path
        
        # Initialize token cache
        self.token_cache = msal.SerializableTokenCache()
        if os.path.exists(self.token_cache_path):
            try:
                with open(self.token_cache_path, 'r') as f:
                    self.token_cache.deserialize(f.read())
                logger.info(f'Loaded token cache from {self.token_cache_path}')
            except Exception as e:
                logger.warning(f'Failed to load token cache: {e}')
        
        # Initialize MSAL Public Client Application (for device code flow)
        try:
            self.msal_app = msal.PublicClientApplication(
                self.client_id,
                authority=self.authority,
                token_cache=self.token_cache
            )
            logger.info('Delegated auth service initialized')
        except Exception as e:
            logger.error(f'Failed to initialize MSAL application: {e}')
            raise DelegatedAuthServiceError(f'Failed to initialize MSAL: {e}')
    
    def _save_cache(self):
        """Save token cache to disk"""
        if self.token_cache.has_state_changed:
            try:
                with open(self.token_cache_path, 'w') as f:
                    f.write(self.token_cache.serialize())
                logger.debug(f'Token cache saved to {self.token_cache_path}')
            except Exception as e:
                logger.error(f'Failed to save token cache: {e}')
    
    def is_configured(self) -> bool:
        """Check if delegated auth is properly configured."""
        return bool(self.enabled and self.client_id and self.tenant_id and self.msal_app)
    
    def initiate_device_flow(self) -> Dict[str, Any]:
        """
        Initiate device code flow for user authentication.
        
        Returns:
            Dict containing device code flow information including:
            - user_code: Code for user to enter
            - device_code: Code for token acquisition
            - verification_uri: URL where user enters code
            - message: Complete message to display to user
            - expires_in: Expiration time in seconds
            
        Raises:
            DelegatedAuthServiceError: If flow initiation fails
        """
        if not self.is_configured():
            raise DelegatedAuthServiceError('Delegated auth is not properly configured')
        
        try:
            logger.info('Initiating device code flow')
            flow = self.msal_app.initiate_device_flow(scopes=self.SCOPES)
            
            if 'error' in flow:
                error_desc = flow.get('error_description', 'Unknown error')
                logger.error(f'Failed to initiate device flow: {error_desc}')
                raise DelegatedAuthServiceError(f'Failed to initiate device flow: {error_desc}')
            
            logger.info('Device flow initiated successfully')
            logger.info(f'User code: {flow.get("user_code")}')
            logger.info(f'Verification URI: {flow.get("verification_uri")}')
            
            return flow
        except DelegatedAuthServiceError:
            raise
        except Exception as e:
            logger.error(f'Failed to initiate device flow: {e}')
            raise DelegatedAuthServiceError(f'Failed to initiate device flow: {e}')
    
    def acquire_token_by_device_flow(self, flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete device code flow and acquire token.
        
        This method polls Microsoft's authorization server until the user
        completes authentication or the flow expires.
        
        Args:
            flow: Device flow dict from initiate_device_flow
            
        Returns:
            Token response dictionary containing access_token, refresh_token, etc.
            
        Raises:
            DelegatedAuthServiceError: If token acquisition fails
        """
        if not self.is_configured():
            raise DelegatedAuthServiceError('Delegated auth is not properly configured')
        
        try:
            logger.info('Waiting for user to complete device code authentication...')
            result = self.msal_app.acquire_token_by_device_flow(flow)
            
            if 'error' in result:
                error_desc = result.get('error_description', 'Unknown error')
                logger.error(f'Token acquisition failed: {error_desc}')
                raise DelegatedAuthServiceError(f'Token acquisition failed: {error_desc}')
            
            # Save the token cache
            self._save_cache()
            
            logger.info('Successfully acquired token via device flow')
            logger.info(f'Token expires in: {result.get("expires_in", "unknown")} seconds')
            
            return result
        except DelegatedAuthServiceError:
            raise
        except Exception as e:
            logger.error(f'Failed to acquire token: {e}')
            raise DelegatedAuthServiceError(f'Failed to acquire token: {e}')
    
    def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """
        Get a valid access token, using cached token or refresh token if available.
        
        This method will:
        1. Check for cached valid token
        2. Use refresh token if cached token is expired
        3. Return None if no valid token and user needs to re-authenticate
        
        Args:
            force_refresh: Force token refresh even if cached token is valid
            
        Returns:
            Access token string or None if authentication required
        """
        if not self.is_configured():
            logger.warning('Delegated auth not configured')
            return None
        
        try:
            # Get accounts from cache
            accounts = self.msal_app.get_accounts()
            
            if not accounts:
                logger.info('No accounts in token cache - device flow authentication required')
                return None
            
            # Use first account (typically there's only one for device flow)
            account = accounts[0]
            logger.debug(f'Using account: {account.get("username")}')
            
            # Try to get token silently (from cache or using refresh token)
            result = self.msal_app.acquire_token_silent(
                scopes=self.SCOPES,
                account=account,
                force_refresh=force_refresh
            )
            
            if result and 'access_token' in result:
                # Save cache if refresh was used
                self._save_cache()
                logger.debug('Successfully acquired token (from cache or refresh)')
                return result['access_token']
            else:
                logger.warning('Failed to acquire token silently - re-authentication required')
                if result:
                    logger.debug(f'Silent token result: {result}')
                return None
                
        except Exception as e:
            logger.error(f'Error getting access token: {e}')
            return None
    
    def has_valid_token(self) -> bool:
        """
        Check if we have a valid cached token or refresh token.
        
        Returns:
            True if we can obtain a valid token without user interaction
        """
        token = self.get_access_token()
        return token is not None
    
    def clear_token_cache(self):
        """Clear the token cache (requires re-authentication)"""
        try:
            if os.path.exists(self.token_cache_path):
                os.remove(self.token_cache_path)
                logger.info('Token cache cleared')
            self.token_cache = msal.SerializableTokenCache()
            self.msal_app = msal.PublicClientApplication(
                self.client_id,
                authority=self.authority,
                token_cache=self.token_cache
            )
        except Exception as e:
            logger.error(f'Failed to clear token cache: {e}')
            raise DelegatedAuthServiceError(f'Failed to clear token cache: {e}')
    
    def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about the current token state.
        
        Returns:
            Dict with token information including account details and expiry
        """
        try:
            accounts = self.msal_app.get_accounts()
            
            if not accounts:
                return {
                    'authenticated': False,
                    'message': 'No authenticated account found'
                }
            
            account = accounts[0]
            
            return {
                'authenticated': True,
                'username': account.get('username', 'Unknown'),
                'account_id': account.get('local_account_id', 'Unknown'),
                'environment': account.get('environment', 'Unknown'),
                'has_valid_token': self.has_valid_token()
            }
        except Exception as e:
            logger.error(f'Error getting token info: {e}')
            return {
                'authenticated': False,
                'error': str(e)
            }
