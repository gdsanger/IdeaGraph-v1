"""
Microsoft Teams Service for IdeaGraph

This module provides integration with Microsoft Teams via Graph API for channel operations.
"""

import logging
from typing import Optional, Dict, Any, List

from .graph_service import GraphService, GraphServiceError


logger = logging.getLogger('teams_service')


class TeamsServiceError(Exception):
    """Base exception for Teams Service errors"""
    
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


class TeamsService:
    """
    Microsoft Teams Service
    
    Provides methods for:
    - Creating channels in Teams workspaces
    - Posting messages to channels
    - Pinning messages in channels
    - Managing channel members
    """
    
    def __init__(self, settings=None):
        """
        Initialize TeamsService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise TeamsServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise TeamsServiceError("No settings found in database")
        
        if not self.settings.teams_enabled:
            logger.error("Teams integration is not enabled in settings")
            raise TeamsServiceError("Teams integration is not enabled in settings")
        
        if not self.settings.teams_team_id:
            logger.error("Teams Team ID not configured")
            raise TeamsServiceError(
                "Teams Team ID not configured",
                details="teams_team_id must be set in settings"
            )
        
        self.team_id = self.settings.teams_team_id
        self.welcome_post_template = self.settings.team_welcome_post or 'Willkommen im Channel für {{Item}}!'
        
        # Initialize Graph Service for API calls
        try:
            self.graph_service = GraphService(settings=settings)
        except GraphServiceError as e:
            logger.error(f"Failed to initialize Graph Service: {str(e)}")
            raise TeamsServiceError(
                "Failed to initialize Graph Service",
                details=str(e)
            )
        
        logger.debug(f"TeamsService initialized with team_id: {self.team_id}")
    
    def create_channel(self, display_name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new channel in the Teams workspace
        
        Args:
            display_name: Name of the channel
            description: Optional description of the channel (max 1024 characters)
            
        Returns:
            Dict with success status and channel details including channel_id
            
        Raises:
            TeamsServiceError: If channel creation fails
        """
        endpoint = f"teams/{self.team_id}/channels"
        
        # Ensure description doesn't exceed Microsoft's 1024 character limit
        channel_description = description or f"Channel für {display_name}"
        if len(channel_description) > 1024:
            logger.warning(f"Channel description exceeds 1024 characters, truncating from {len(channel_description)} chars")
            channel_description = channel_description[:1021] + "..."
        
        channel_data = {
            "displayName": display_name,
            "description": channel_description,
            "membershipType": "standard"  # standard channels are accessible to all team members
        }
        
        try:
            logger.info(f"Creating channel '{display_name}' in team {self.team_id}")
            response = self.graph_service._make_request(
                method='POST',
                endpoint=endpoint,
                json_data=channel_data
            )
            
            if response.status_code in [200, 201]:
                channel_info = response.json()
                channel_id = channel_info.get('id')
                web_url = channel_info.get('webUrl', '')
                
                logger.info(f"Successfully created channel '{display_name}' with ID: {channel_id}")
                
                return {
                    'success': True,
                    'channel_id': channel_id,
                    'display_name': channel_info.get('displayName'),
                    'web_url': web_url,
                    'description': channel_info.get('description')
                }
            else:
                error_msg = f"Failed to create channel: {response.status_code}"
                logger.error(f"{error_msg} - {response.text}")
                raise TeamsServiceError(
                    error_msg,
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError as e:
            logger.error(f"Graph API error while creating channel: {str(e)}")
            raise TeamsServiceError(
                "Failed to create channel",
                status_code=e.status_code,
                details=str(e)
            )
    
    def post_message_to_channel(self, channel_id: str, message_content: str) -> Dict[str, Any]:
        """
        Post a message to a Teams channel
        
        Args:
            channel_id: ID of the channel
            message_content: Content of the message (supports HTML)
            
        Returns:
            Dict with success status and message details including message_id
            
        Raises:
            TeamsServiceError: If posting message fails
        """
        endpoint = f"teams/{self.team_id}/channels/{channel_id}/messages"
        
        message_data = {
            "body": {
                "contentType": "html",
                "content": message_content
            }
        }
        
        try:
            logger.info(f"Posting message to channel {channel_id} in team {self.team_id}")
            response = self.graph_service._make_request(
                method='POST',
                endpoint=endpoint,
                json_data=message_data
            )
            
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
                error_msg = f"Failed to post message: {response.status_code}"
                logger.error(f"{error_msg} - {response.text}")
                raise TeamsServiceError(
                    error_msg,
                    status_code=response.status_code,
                    details=response.text
                )
                
        except GraphServiceError as e:
            logger.error(f"Graph API error while posting message: {str(e)}")
            raise TeamsServiceError(
                "Failed to post message",
                status_code=e.status_code,
                details=str(e)
            )
    
    def get_channel_web_url(self, channel_id: str) -> Optional[str]:
        """
        Get the web URL for a Teams channel
        
        Args:
            channel_id: ID of the channel
            
        Returns:
            Web URL of the channel or None if not found
        """
        endpoint = f"teams/{self.team_id}/channels/{channel_id}"
        
        try:
            logger.info(f"Fetching channel details for {channel_id}")
            response = self.graph_service._make_request(
                method='GET',
                endpoint=endpoint
            )
            
            if response.status_code == 200:
                channel_info = response.json()
                web_url = channel_info.get('webUrl', '')
                logger.info(f"Successfully retrieved web URL for channel {channel_id}")
                return web_url
            else:
                logger.warning(f"Failed to get channel details: {response.status_code}")
                return None
                
        except (GraphServiceError, Exception) as e:
            logger.error(f"Error getting channel web URL: {str(e)}")
            return None
    
    def create_channel_for_item(self, item_title: str, item_description: str = "") -> Dict[str, Any]:
        """
        Create a complete channel setup for an item:
        1. Create the channel
        2. Post welcome message
        
        Note: Pinning messages and adding members programmatically requires special permissions
        and may not be available in all Microsoft 365 configurations. These features are documented
        but may need to be done manually or require additional app permissions.
        
        Args:
            item_title: Title of the item (used as channel name)
            item_description: Description of the item (not used for channel description to avoid length limits)
            
        Returns:
            Dict with success status and channel details
            
        Raises:
            TeamsServiceError: If any step fails
        """
        try:
            # Step 1: Create the channel
            # Use a simple, short description to avoid Microsoft's 1024 character limit
            logger.info(f"Creating Teams channel for item: {item_title}")
            channel_result = self.create_channel(
                display_name=item_title,
                description=f"Projekt Channel für {item_title}"
            )
            
            if not channel_result.get('success'):
                raise TeamsServiceError("Failed to create channel")
            
            channel_id = channel_result['channel_id']
            web_url = channel_result.get('web_url', '')
            
            # Step 2: Post welcome message
            welcome_message = self.welcome_post_template.replace('{{Item}}', item_title)
            logger.info(f"Posting welcome message to channel {channel_id}")
            
            try:
                message_result = self.post_message_to_channel(channel_id, welcome_message)
                
                if not message_result.get('success'):
                    logger.warning("Failed to post welcome message, but channel was created")
            except TeamsServiceError as e:
                logger.warning(f"Failed to post welcome message: {str(e)}")
                # Don't fail the entire operation if just the message posting fails
            
            # Note: Pinning messages requires special permissions (ChannelMessage.UpdatePolicyViolation.All)
            # This is typically not available for standard app registrations and would need to be done
            # manually or with elevated permissions
            
            logger.info(f"Successfully created channel setup for item: {item_title}")
            
            return {
                'success': True,
                'channel_id': channel_id,
                'display_name': channel_result['display_name'],
                'web_url': web_url,
                'message': f"Channel '{item_title}' created successfully"
            }
            
        except TeamsServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating channel for item: {str(e)}")
            raise TeamsServiceError(
                "Unexpected error during channel creation",
                details=str(e)
            )
