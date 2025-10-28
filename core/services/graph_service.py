"""
Microsoft Graph API Service for IdeaGraph

This module provides integration with Microsoft Graph API for SharePoint and Mail operations.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import requests
from django.core.cache import cache


logger = logging.getLogger('graph_service')


class GraphServiceError(Exception):
    """Base exception for Graph Service errors"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to structured dictionary"""
        return {
            'success': False,
            'error': self.message,
            'details': self.details or ''
        }


class GraphService:
    """
    Microsoft Graph API Service
    
    Provides methods for:
    - SharePoint file operations (list, get, upload, delete)
    - Mail operations (send mail)
    - OAuth2 token management with caching
    """
    
    TOKEN_CACHE_KEY = 'graph_token_cache'
    TOKEN_CACHE_DURATION = 3300  # 55 minutes (tokens expire in 60 minutes)
    REQUEST_TIMEOUT = 15  # seconds
    
    def __init__(self, settings=None, use_delegated_auth=False):
        """
        Initialize GraphService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
            use_delegated_auth: If True, use delegated user authentication instead of app-only
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise GraphServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise GraphServiceError("No settings found in database")
        
        if not self.settings.graph_api_enabled:
            logger.error("Graph API is not enabled in settings")
            raise GraphServiceError("Graph API is not enabled in settings")
        
        # Validate required configuration
        if not all([
            self.settings.tenant_id,
            self.settings.client_id,
            self.settings.client_secret
        ]):
            logger.error("Graph API configuration incomplete")
            logger.error(f"tenant_id present: {bool(self.settings.tenant_id)}")
            logger.error(f"client_id present: {bool(self.settings.client_id)}")
            logger.error(f"client_secret present: {bool(self.settings.client_secret)}")
            raise GraphServiceError(
                "Graph API configuration incomplete",
                details="tenant_id, client_id, and client_secret are required"
            )
        
        self.tenant_id = self.settings.tenant_id
        self.client_id = self.settings.client_id
        self.client_secret = self.settings.client_secret
        self.base_url = self.settings.graph_api_base_url or 'https://graph.microsoft.com/v1.0'
        self.scopes = self.settings.graph_api_scopes or 'https://graph.microsoft.com/.default'
        self.sharepoint_site_id = self.settings.sharepoint_site_id
        self.default_sender = self.settings.default_mail_sender
        
        # Delegated authentication support
        self.use_delegated_auth = use_delegated_auth
        self.delegated_auth_service = None
        if use_delegated_auth:
            from .delegated_auth_service import DelegatedAuthService
            try:
                self.delegated_auth_service = DelegatedAuthService(
                    client_id=self.client_id,
                    tenant_id=self.tenant_id
                )
                logger.info("GraphService initialized with delegated authentication")
            except Exception as e:
                logger.warning(f"Failed to initialize delegated auth service: {e}")
                # Fall back to app-only if delegated auth fails
                self.use_delegated_auth = False
        
        logger.debug(f"GraphService initialized with base_url: {self.base_url}")
        logger.debug(f"SharePoint site ID: {self.sharepoint_site_id}")
        logger.debug(f"Tenant ID: {self.tenant_id}")
        logger.debug(f"Using delegated auth: {self.use_delegated_auth}")
        
        self._token = None
        self._token_expires_at = None
    
    def _get_token_from_cache(self) -> Optional[str]:
        """Get token from cache"""
        cached_data = cache.get(self.TOKEN_CACHE_KEY)
        if cached_data and isinstance(cached_data, dict):
            expires_at = cached_data.get('expires_at')
            if expires_at and datetime.now() < expires_at:
                return cached_data.get('token')
        return None
    
    def _set_token_in_cache(self, token: str, expires_in: int):
        """Store token in cache"""
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        cache.set(
            self.TOKEN_CACHE_KEY,
            {'token': token, 'expires_at': expires_at},
            timeout=expires_in
        )
    
    def _get_access_token(self) -> str:
        """
        Get OAuth2 access token using either delegated or client credentials flow
        
        Returns:
            str: Access token
            
        Raises:
            GraphServiceError: If token acquisition fails
        """
        # Use delegated authentication if enabled
        if self.use_delegated_auth and self.delegated_auth_service:
            token = self.delegated_auth_service.get_access_token()
            if token:
                logger.debug("Using delegated user access token")
                return token
            else:
                raise GraphServiceError(
                    "Delegated authentication token not available",
                    details="Run 'python manage.py auth_teams' to authenticate"
                )
        
        # Fall back to client credentials flow (app-only)
        # Check cache first
        cached_token = self._get_token_from_cache()
        if cached_token:
            logger.debug("Using cached access token")
            return cached_token
        
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scopes,
            'grant_type': 'client_credentials'
        }
        
        try:
            logger.info(f"Requesting new access token from Microsoft (tenant_id: {self.tenant_id})")
            logger.debug(f"Token endpoint: {token_url}")
            logger.debug(f"Scopes: {self.scopes}")
            response = requests.post(
                token_url,
                data=data,
                timeout=self.REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                logger.error(f"Token request failed: {response.status_code} - {response.text}")
                logger.error(f"Token URL: {token_url}")
                logger.error(f"Client ID: {self.client_id}")
                raise GraphServiceError(
                    "Failed to acquire access token",
                    status_code=response.status_code,
                    details=response.text
                )
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            
            if not access_token:
                raise GraphServiceError("No access token in response")
            
            # Cache the token
            self._set_token_in_cache(access_token, expires_in)
            
            logger.info(f"Successfully acquired access token (expires in {expires_in}s)")
            return access_token
            
        except requests.RequestException as e:
            logger.error(f"Request error while acquiring token: {str(e)}")
            logger.error(f"Token URL: {token_url}")
            raise GraphServiceError("Network error while acquiring token", details=str(e))
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        retry_on_401: bool = True
    ) -> requests.Response:
        """
        Make authenticated request to Graph API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base_url)
            data: Form data
            json_data: JSON data
            files: Files to upload
            retry_on_401: Whether to retry once on 401 error
            
        Returns:
            Response object
            
        Raises:
            GraphServiceError: On request failure
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        token = self._get_access_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
        }
        
        if json_data:
            headers['Content-Type'] = 'application/json'
        
        try:
            logger.info(f"{method} {url}")
            logger.debug(f"Request headers: {dict((k, v[:20] + '...' if k == 'Authorization' else v) for k, v in headers.items())}")
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json_data,
                files=files,
                timeout=self.REQUEST_TIMEOUT
            )
            
            # Handle 401 (unauthorized) by refreshing token and retrying once
            if response.status_code == 401 and retry_on_401:
                logger.warning("Received 401 (Unauthorized), clearing cache and retrying")
                # Safely log response body (handle Mock objects in tests)
                try:
                    logger.debug(f"Response body: {response.text[:500]}")
                except (TypeError, AttributeError):
                    logger.debug("Response body: (unable to retrieve)")
                cache.delete(self.TOKEN_CACHE_KEY)
                return self._make_request(
                    method, endpoint, data, json_data, files, retry_on_401=False
                )
            
            logger.info(f"Response: {response.status_code}")
            if response.status_code >= 400:
                logger.error(f"Error response body: {response.text}")
            
            return response
            
        except requests.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            logger.error(f"Request URL: {url}")
            logger.error(f"Request method: {method}")
            raise GraphServiceError("Network error during API request", details=str(e))
    
    # SharePoint Methods
    
    def get_sharepoint_file_list(self, folder_path: str = "") -> Dict[str, Any]:
        """
        List files in a SharePoint folder
        
        Args:
            folder_path: Path to folder (relative to site root)
            
        Returns:
            Dict with success status and list of files
        """
        if not self.sharepoint_site_id:
            raise GraphServiceError(
                "SharePoint site ID not configured",
                details="sharepoint_site_id must be set in settings"
            )
        
        # Build endpoint
        if folder_path:
            endpoint = f"sites/{self.sharepoint_site_id}/drive/root:/{folder_path}:/children"
        else:
            endpoint = f"sites/{self.sharepoint_site_id}/drive/root/children"
        
        try:
            response = self._make_request('GET', endpoint)
            
            if response.status_code == 200:
                data = response.json()
                files = data.get('value', [])
                return {
                    'success': True,
                    'files': files,
                    'count': len(files)
                }
            else:
                raise GraphServiceError(
                    "Failed to list files",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise GraphServiceError("Error listing files", details=str(e))
    
    def get_sharepoint_file(self, file_id: str) -> Dict[str, Any]:
        """
        Download a file from SharePoint
        
        Args:
            file_id: ID of the file to download
            
        Returns:
            Dict with success status, file content and metadata
        """
        if not self.sharepoint_site_id:
            raise GraphServiceError(
                "SharePoint site ID not configured",
                details="sharepoint_site_id must be set in settings"
            )
        
        endpoint = f"sites/{self.sharepoint_site_id}/drive/items/{file_id}"
        
        try:
            # Get file metadata first
            response = self._make_request('GET', endpoint)
            
            if response.status_code != 200:
                raise GraphServiceError(
                    "Failed to get file metadata",
                    status_code=response.status_code,
                    details=response.text
                )
            
            metadata = response.json()
            download_url = metadata.get('@microsoft.graph.downloadUrl')
            
            if not download_url:
                raise GraphServiceError("No download URL in file metadata")
            
            # Download file content
            content_response = requests.get(download_url, timeout=self.REQUEST_TIMEOUT)
            
            if content_response.status_code != 200:
                raise GraphServiceError(
                    "Failed to download file content",
                    status_code=content_response.status_code
                )
            
            return {
                'success': True,
                'file_name': metadata.get('name'),
                'size': metadata.get('size'),
                'content': content_response.content,
                'metadata': metadata
            }
            
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting file: {str(e)}")
            raise GraphServiceError("Error getting file", details=str(e))
    
    def upload_sharepoint_file(
        self,
        folder_path: str,
        file_name: str,
        content: bytes
    ) -> Dict[str, Any]:
        """
        Upload a file to SharePoint
        
        Args:
            folder_path: Destination folder path
            file_name: Name of the file
            content: File content as bytes
            
        Returns:
            Dict with success status and file metadata
        """
        if not self.sharepoint_site_id:
            logger.error("SharePoint site ID not configured")
            raise GraphServiceError(
                "SharePoint site ID not configured",
                details="sharepoint_site_id must be set in settings"
            )
        
        # For files <= 4MB, use simple upload
        file_size = len(content)
        
        logger.info(f"Uploading file: {file_name} ({file_size} bytes)")
        logger.debug(f"SharePoint site ID: {self.sharepoint_site_id}")
        logger.debug(f"Folder path: {folder_path}")
        logger.debug(f"Base URL: {self.base_url}")
        
        if file_size > 4 * 1024 * 1024:
            logger.error(f"File size {file_size} bytes exceeds 4MB limit")
            logger.warning(f"File size {file_size} bytes exceeds 4MB, large file upload not implemented")
            raise GraphServiceError(
                "File too large",
                details="Files larger than 4MB require chunk upload (not yet implemented)"
            )
        
        # Build endpoint
        if folder_path:
            endpoint = f"sites/{self.sharepoint_site_id}/drive/root:/{folder_path}/{file_name}:/content"
        else:
            endpoint = f"sites/{self.sharepoint_site_id}/drive/root:/{file_name}:/content"
        
        logger.debug(f"Upload endpoint: {endpoint}")
        
        try:
            token = self._get_access_token()
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/octet-stream'
            }
            
            logger.info(f"Uploading file: {file_name} ({file_size} bytes)")
            logger.debug(f"Full upload URL: {url}")
            logger.debug(f"Request headers (auth truncated): Authorization: Bearer {token[:20]}...")
            
            response = requests.put(
                url,
                headers=headers,
                data=content,
                timeout=self.REQUEST_TIMEOUT
            )
            
            logger.info(f"Upload response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                metadata = response.json()
                logger.info(f"File uploaded successfully: {file_name}")
                logger.debug(f"Response metadata: file_id={metadata.get('id')}, size={metadata.get('size')}")
                return {
                    'success': True,
                    'file_id': metadata.get('id'),
                    'file_name': metadata.get('name'),
                    'size': metadata.get('size'),
                    'metadata': metadata
                }
            else:
                error_msg = f"Failed to upload file (HTTP {response.status_code})"
                logger.error(error_msg)
                logger.error(f"Response body: {response.text}")
                logger.error(f"Request URL: {url}")
                logger.error(f"SharePoint site ID: {self.sharepoint_site_id}")
                logger.error(f"Folder path: {folder_path}")
                logger.error(f"File name: {file_name}")
                raise GraphServiceError(
                    "Failed to upload file",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            logger.error(f"File: {file_name}, Size: {file_size}, Folder: {folder_path}")
            logger.error(f"SharePoint site ID: {self.sharepoint_site_id}")
            raise GraphServiceError("Error uploading file", details=str(e))
    
    def upload_file_to_sharepoint(
        self,
        file_content: bytes,
        filename: str,
        folder_path: str
    ) -> Dict[str, Any]:
        """
        Upload a file to SharePoint (alias method providing backward compatibility with alternative parameter names)
        
        This is an alias method that provides backward compatibility for code using
        different parameter names (file_content instead of content, filename instead of file_name).
        
        Args:
            file_content: File content as bytes
            filename: Name of the file
            folder_path: Destination folder path
            
        Returns:
            Dict with success status and file metadata including:
            - success: bool
            - file_id: str
            - web_url: str (if available in metadata)
        """
        # Call the main upload method with correct parameter mapping
        result = self.upload_sharepoint_file(
            folder_path=folder_path,
            file_name=filename,
            content=file_content
        )
        
        # Add web_url to result if available in metadata
        if 'metadata' in result:
            metadata = result['metadata']
            if 'webUrl' in metadata:
                result['web_url'] = metadata['webUrl']
            elif '@microsoft.graph.downloadUrl' in metadata:
                # Use download URL as fallback
                result['web_url'] = metadata['@microsoft.graph.downloadUrl']
            else:
                result['web_url'] = ''
        else:
            result['web_url'] = ''
        
        return result
    
    def delete_sharepoint_file(self, file_id: str) -> Dict[str, Any]:
        """
        Delete a file from SharePoint
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            Dict with success status
        """
        if not self.sharepoint_site_id:
            raise GraphServiceError(
                "SharePoint site ID not configured",
                details="sharepoint_site_id must be set in settings"
            )
        
        endpoint = f"sites/{self.sharepoint_site_id}/drive/items/{file_id}"
        
        try:
            response = self._make_request('DELETE', endpoint)
            
            if response.status_code in [204, 200]:
                logger.info(f"File deleted successfully: {file_id}")
                return {
                    'success': True,
                    'message': 'File deleted successfully'
                }
            else:
                raise GraphServiceError(
                    "Failed to delete file",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise GraphServiceError("Error deleting file", details=str(e))
    
    def get_folder_by_path(self, folder_path: str) -> Dict[str, Any]:
        """
        Get folder metadata by path
        
        Args:
            folder_path: Path to folder (relative to site root)
            
        Returns:
            Dict with success status and folder metadata
        """
        if not self.sharepoint_site_id:
            raise GraphServiceError(
                "SharePoint site ID not configured",
                details="sharepoint_site_id must be set in settings"
            )
        
        endpoint = f"sites/{self.sharepoint_site_id}/drive/root:/{folder_path}"
        
        try:
            response = self._make_request('GET', endpoint)
            
            if response.status_code == 200:
                metadata = response.json()
                return {
                    'success': True,
                    'exists': True,
                    'folder_id': metadata.get('id'),
                    'metadata': metadata
                }
            elif response.status_code == 404:
                return {
                    'success': True,
                    'exists': False
                }
            else:
                raise GraphServiceError(
                    "Failed to get folder",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting folder: {str(e)}")
            raise GraphServiceError("Error getting folder", details=str(e))
    
    def create_folder(self, parent_path: str, folder_name: str) -> Dict[str, Any]:
        """
        Create a folder in SharePoint
        
        Args:
            parent_path: Path to parent folder (empty string for root)
            folder_name: Name of the folder to create
            
        Returns:
            Dict with success status and folder metadata
        """
        if not self.sharepoint_site_id:
            raise GraphServiceError(
                "SharePoint site ID not configured",
                details="sharepoint_site_id must be set in settings"
            )
        
        # Build endpoint
        if parent_path:
            endpoint = f"sites/{self.sharepoint_site_id}/drive/root:/{parent_path}:/children"
        else:
            endpoint = f"sites/{self.sharepoint_site_id}/drive/root/children"
        
        folder_data = {
            'name': folder_name,
            'folder': {},
            '@microsoft.graph.conflictBehavior': 'fail'
        }
        
        try:
            response = self._make_request('POST', endpoint, json_data=folder_data)
            
            if response.status_code in [200, 201]:
                metadata = response.json()
                logger.info(f"Folder created successfully: {folder_name}")
                return {
                    'success': True,
                    'folder_id': metadata.get('id'),
                    'folder_name': metadata.get('name'),
                    'metadata': metadata
                }
            else:
                raise GraphServiceError(
                    "Failed to create folder",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error creating folder: {str(e)}")
            raise GraphServiceError("Error creating folder", details=str(e))
    
    def move_folder(self, folder_id: str, destination_folder_id: str, new_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Move a folder to a new location in SharePoint
        
        Args:
            folder_id: ID of the folder to move
            destination_folder_id: ID of the destination parent folder
            new_name: Optional new name for the folder
            
        Returns:
            Dict with success status and folder metadata
        """
        if not self.sharepoint_site_id:
            raise GraphServiceError(
                "SharePoint site ID not configured",
                details="sharepoint_site_id must be set in settings"
            )
        
        endpoint = f"sites/{self.sharepoint_site_id}/drive/items/{folder_id}"
        
        update_data = {
            'parentReference': {
                'id': destination_folder_id
            }
        }
        
        if new_name:
            update_data['name'] = new_name
        
        try:
            response = self._make_request('PATCH', endpoint, json_data=update_data)
            
            if response.status_code == 200:
                metadata = response.json()
                logger.info(f"Folder moved successfully: {folder_id}")
                return {
                    'success': True,
                    'folder_id': metadata.get('id'),
                    'folder_name': metadata.get('name'),
                    'metadata': metadata
                }
            else:
                raise GraphServiceError(
                    "Failed to move folder",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error moving folder: {str(e)}")
            raise GraphServiceError("Error moving folder", details=str(e))
    
    # Mail Methods
    
    def send_mail(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_address: Optional[str] = None,
        internet_message_headers: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Send an email via Microsoft Graph API
        
        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body (HTML supported)
            attachments: List of attachments (each with 'name' and 'content' as base64)
            from_address: Sender email (uses default if not provided)
            internet_message_headers: List of custom email headers (each with 'name' and 'value')
            
        Returns:
            Dict with success status and message_id if available
        """
        sender = from_address or self.default_sender
        
        if not sender:
            raise GraphServiceError(
                "No sender email configured",
                details="default_mail_sender must be set in settings or from_address provided"
            )
        
        if not to:
            raise GraphServiceError("No recipients specified")
        
        # Build email message
        message = {
            'message': {
                'subject': subject,
                'body': {
                    'contentType': 'HTML',
                    'content': body
                },
                'toRecipients': [
                    {'emailAddress': {'address': email}} for email in to
                ]
            },
            'saveToSentItems': 'true'
        }
        
        # Add custom internet message headers if provided
        if internet_message_headers:
            message['message']['internetMessageHeaders'] = internet_message_headers
        
        # Add attachments if provided
        if attachments:
            message['message']['attachments'] = attachments
        
        endpoint = f"users/{sender}/sendMail"
        
        try:
            response = self._make_request('POST', endpoint, json_data=message)
            
            if response.status_code in [202, 200]:
                logger.info(f"Email sent successfully to {', '.join(to)}")
                return {
                    'success': True,
                    'message': 'Email sent successfully'
                }
            else:
                raise GraphServiceError(
                    "Failed to send email",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            raise GraphServiceError("Error sending email", details=str(e))
    
    def send_system_mail(self, template: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send internal system notification email
        
        Args:
            template: Template name/type (e.g., 'user_created', 'error_alert')
            context: Template context with variables
            
        Returns:
            Dict with success status
        """
        # Basic template rendering (could be extended with proper template engine)
        subject = context.get('subject', f'System Notification: {template}')
        
        # Simple template rendering
        body_lines = [f"<h2>{template.replace('_', ' ').title()}</h2>"]
        body_lines.append("<ul>")
        for key, value in context.items():
            if key != 'subject' and key != 'recipients':
                body_lines.append(f"<li><strong>{key}:</strong> {value}</li>")
        body_lines.append("</ul>")
        
        body = "".join(body_lines)
        recipients = context.get('recipients', [])
        
        if not recipients:
            raise GraphServiceError("No recipients specified in context")
        
        return self.send_mail(
            to=recipients,
            subject=subject,
            body=body
        )
    
    def get_mailbox_messages(
        self,
        mailbox: Optional[str] = None,
        folder: str = 'inbox',
        top: int = 10,
        unread_only: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve messages from a mailbox via Microsoft Graph API
        
        Args:
            mailbox: Email address of the mailbox (uses default_sender if not provided)
            folder: Folder to retrieve from (default: 'inbox')
            top: Number of messages to retrieve (default: 10)
            unread_only: Only retrieve unread messages (default: True)
            
        Returns:
            Dict with success status and list of messages
        """
        mailbox_address = mailbox or self.default_sender
        
        if not mailbox_address:
            raise GraphServiceError(
                "No mailbox specified",
                details="mailbox parameter or default_mail_sender must be set"
            )
        
        # Build endpoint
        endpoint = f"users/{mailbox_address}/mailFolders/{folder}/messages"
        
        # Build query parameters
        params = {
            '$top': top,
            '$orderby': 'receivedDateTime desc',
            '$select': 'id,subject,bodyPreview,body,from,toRecipients,receivedDateTime,isRead,hasAttachments'
        }
        
        if unread_only:
            params['$filter'] = 'isRead eq false'
        
        try:
            response = self._make_request('GET', endpoint)
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get('value', [])
                logger.info(f"Retrieved {len(messages)} messages from mailbox {mailbox_address}")
                return {
                    'success': True,
                    'messages': messages,
                    'count': len(messages)
                }
            else:
                raise GraphServiceError(
                    "Failed to retrieve messages",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving messages: {str(e)}")
            raise GraphServiceError("Error retrieving messages", details=str(e))
    
    def mark_message_as_read(
        self,
        message_id: str,
        mailbox: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a message as read
        
        Args:
            message_id: ID of the message to mark as read
            mailbox: Email address of the mailbox (uses default_sender if not provided)
            
        Returns:
            Dict with success status
        """
        mailbox_address = mailbox or self.default_sender
        
        if not mailbox_address:
            raise GraphServiceError(
                "No mailbox specified",
                details="mailbox parameter or default_mail_sender must be set"
            )
        
        endpoint = f"users/{mailbox_address}/messages/{message_id}"
        data = {'isRead': True}
        
        try:
            response = self._make_request('PATCH', endpoint, json_data=data)
            
            if response.status_code in [200, 204]:
                logger.info(f"Message {message_id} marked as read")
                return {
                    'success': True,
                    'message': 'Message marked as read'
                }
            else:
                raise GraphServiceError(
                    "Failed to mark message as read",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error marking message as read: {str(e)}")
            raise GraphServiceError("Error marking message as read", details=str(e))
    
    def move_message(
        self,
        message_id: str,
        destination_folder: str = 'archive',
        mailbox: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Move a message to a different folder
        
        Args:
            message_id: ID of the message to move
            destination_folder: Destination folder name (default: 'archive')
            mailbox: Email address of the mailbox (uses default_sender if not provided)
            
        Returns:
            Dict with success status
        """
        mailbox_address = mailbox or self.default_sender
        
        if not mailbox_address:
            raise GraphServiceError(
                "No mailbox specified",
                details="mailbox parameter or default_mail_sender must be set"
            )
        
        endpoint = f"users/{mailbox_address}/messages/{message_id}/move"
        data = {'destinationId': destination_folder}
        
        try:
            response = self._make_request('POST', endpoint, json_data=data)
            
            if response.status_code in [200, 201]:
                logger.info(f"Message {message_id} moved to {destination_folder}")
                return {
                    'success': True,
                    'message': f'Message moved to {destination_folder}'
                }
            else:
                raise GraphServiceError(
                    "Failed to move message",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error moving message: {str(e)}")
            raise GraphServiceError("Error moving message", details=str(e))
    
    def get_message_attachments(
        self,
        message_id: str,
        mailbox: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get attachments from a message
        
        Args:
            message_id: ID of the message
            mailbox: Email address of the mailbox (uses default_sender if not provided)
            
        Returns:
            Dict with success status and list of attachments
        """
        mailbox_address = mailbox or self.default_sender
        
        if not mailbox_address:
            raise GraphServiceError(
                "No mailbox specified",
                details="mailbox parameter or default_mail_sender must be set"
            )
        
        endpoint = f"users/{mailbox_address}/messages/{message_id}/attachments"
        
        try:
            response = self._make_request('GET', endpoint)
            
            if response.status_code == 200:
                data = response.json()
                attachments = data.get('value', [])
                logger.info(f"Retrieved {len(attachments)} attachments from message {message_id}")
                return {
                    'success': True,
                    'attachments': attachments,
                    'count': len(attachments)
                }
            else:
                raise GraphServiceError(
                    "Failed to retrieve attachments",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving attachments: {str(e)}")
            raise GraphServiceError("Error retrieving attachments", details=str(e))
    
    def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        mailbox: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download a specific attachment from a message
        
        Args:
            message_id: ID of the message
            attachment_id: ID of the attachment
            mailbox: Email address of the mailbox (uses default_sender if not provided)
            
        Returns:
            Dict with success status, filename, content_type, and file content as bytes
        """
        mailbox_address = mailbox or self.default_sender
        
        if not mailbox_address:
            raise GraphServiceError(
                "No mailbox specified",
                details="mailbox parameter or default_mail_sender must be set"
            )
        
        endpoint = f"users/{mailbox_address}/messages/{message_id}/attachments/{attachment_id}"
        
        try:
            response = self._make_request('GET', endpoint)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract attachment details
                filename = data.get('name', 'attachment')
                content_type = data.get('contentType', 'application/octet-stream')
                content_bytes_base64 = data.get('contentBytes', '')
                
                # Decode base64 content
                import base64
                content = base64.b64decode(content_bytes_base64)
                
                logger.info(f"Downloaded attachment {filename} ({len(content)} bytes)")
                
                return {
                    'success': True,
                    'filename': filename,
                    'content_type': content_type,
                    'content': content,
                    'size': len(content)
                }
            else:
                raise GraphServiceError(
                    "Failed to download attachment",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error downloading attachment: {str(e)}")
            raise GraphServiceError("Error downloading attachment", details=str(e))
    
    # Teams Channel Methods
    
    def get_channel_messages(
        self,
        team_id: str,
        channel_id: str,
        top: int = 50
    ) -> Dict[str, Any]:
        """
        Get messages from a Teams channel
        
        Args:
            team_id: ID of the Teams team
            channel_id: ID of the channel
            top: Maximum number of messages to retrieve (default: 50)
            
        Returns:
            Dict with success status and list of messages
            
        Raises:
            GraphServiceError: If request fails
        """
        endpoint = f"teams/{team_id}/channels/{channel_id}/messages?$top={top}"
        
        try:
            logger.info(f"Getting messages from channel {channel_id} in team {team_id}")
            response = self._make_request('GET', endpoint)
            
            if response.status_code == 200:
                data = response.json()
                all_messages = data.get('value', [])
                
                # Filter messages to only include those from the last 30 minutes
                cutoff_time = datetime.utcnow() - timedelta(minutes=30)
                messages = []
                
                for message in all_messages:
                    created_at_str = message.get('createdDateTime')
                    if created_at_str:
                        try:
                            # Parse ISO 8601 datetime (remove 'Z' and parse)
                            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                            # Make timezone-naive for comparison
                            created_at_naive = created_at.replace(tzinfo=None)
                            
                            if created_at_naive >= cutoff_time:
                                messages.append(message)
                            else:
                                logger.debug(f"Skipping message {message.get('id')} - older than 30 minutes")
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"Could not parse message timestamp: {created_at_str}, error: {e}")
                            # Include message if we can't parse timestamp (defensive behavior)
                            messages.append(message)
                    else:
                        # Include message if no timestamp (defensive behavior)
                        messages.append(message)
                
                logger.info(f"Retrieved {len(messages)} messages from channel (filtered from {len(all_messages)} total, last 30 minutes only)")
                
                return {
                    'success': True,
                    'messages': messages,
                    'count': len(messages)
                }
            else:
                raise GraphServiceError(
                    "Failed to get channel messages",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting channel messages: {str(e)}")
            raise GraphServiceError("Error getting channel messages", details=str(e))
    
    def post_channel_message(
        self,
        team_id: str,
        channel_id: str,
        message_content: str
    ) -> Dict[str, Any]:
        """
        Post a message to a Teams channel
        
        Args:
            team_id: ID of the Teams team
            channel_id: ID of the channel
            message_content: Content of the message (supports HTML)
            
        Returns:
            Dict with success status and message details
            
        Raises:
            GraphServiceError: If request fails
        """
        endpoint = f"teams/{team_id}/channels/{channel_id}/messages"
        
        message_data = {
            "body": {
                "contentType": "html",
                "content": message_content
            }
        }
        
        try:
            logger.info(f"Posting message to channel {channel_id} in team {team_id}")
            response = self._make_request('POST', endpoint, json_data=message_data)
            
            if response.status_code in [200, 201]:
                message_info = response.json()
                message_id = message_info.get('id')
                logger.info(f"Successfully posted message with ID: {message_id}")
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'created_at': message_info.get('createdDateTime'),
                    'web_url': message_info.get('webUrl', '')
                }
            else:
                raise GraphServiceError(
                    "Failed to post channel message",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error posting channel message: {str(e)}")
            raise GraphServiceError("Error posting channel message", details=str(e))
    
    def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """
        Get user details by object ID
        
        This method is used to retrieve full user information including UPN,
        email, and display name when the UPN is not available in the message.
        This is a known issue with Microsoft Teams Graph API where the sender
        UPN can be empty in chat messages.
        
        Args:
            user_id: Microsoft User Object ID (from message.from.user.id)
            
        Returns:
            Dict with success status and user details including:
            - id: User object ID
            - userPrincipalName: User's UPN (email)
            - mail: User's email address
            - displayName: User's display name
            - givenName: User's first name
            - surname: User's last name
            
        Raises:
            GraphServiceError: If request fails
        """
        if not user_id:
            raise GraphServiceError("User ID is required")
        
        endpoint = f"users/{user_id}"
        
        try:
            logger.info(f"Getting user details for user ID: {user_id}")
            response = self._make_request('GET', endpoint)
            
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"Retrieved user details for: {user_data.get('userPrincipalName', 'N/A')}")
                
                return {
                    'success': True,
                    'user': {
                        'id': user_data.get('id'),
                        'userPrincipalName': user_data.get('userPrincipalName', ''),
                        'mail': user_data.get('mail', ''),
                        'displayName': user_data.get('displayName', ''),
                        'givenName': user_data.get('givenName', ''),
                        'surname': user_data.get('surname', '')
                    }
                }
            else:
                raise GraphServiceError(
                    "Failed to get user details",
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting user details: {str(e)}")
            raise GraphServiceError("Error getting user details", details=str(e))
