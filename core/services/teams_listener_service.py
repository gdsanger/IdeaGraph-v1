"""
Teams Listener Service for IdeaGraph

This service polls Teams channels for new messages and processes them.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .graph_service import GraphService, GraphServiceError


logger = logging.getLogger('teams_listener_service')


class TeamsListenerServiceError(Exception):
    """Base exception for Teams Listener Service errors"""
    
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


class TeamsListenerService:
    """
    Teams Listener Service
    
    Polls Teams channels for new messages and identifies messages that need processing.
    """
    
    IDEAGRAPH_BOT_NAME = 'IdeaGraph Bot'
    
    def __init__(self, settings=None):
        """
        Initialize TeamsListenerService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise TeamsListenerServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise TeamsListenerServiceError("No settings found in database")
        
        if not self.settings.teams_enabled:
            logger.error("Teams integration is not enabled in settings")
            raise TeamsListenerServiceError("Teams integration is not enabled in settings")
        
        if not self.settings.teams_team_id:
            logger.error("Teams Team ID not configured")
            raise TeamsListenerServiceError(
                "Teams Team ID not configured",
                details="teams_team_id must be set in settings"
            )
        
        self.team_id = self.settings.teams_team_id
        self.bot_upn = self.settings.default_mail_sender if self.settings.default_mail_sender else None
        self.bot_object_id = None  # Will be fetched if needed
        
        # Initialize Graph Service for API calls
        try:
            self.graph_service = GraphService(settings=settings)
        except GraphServiceError as e:
            logger.error(f"Failed to initialize Graph Service: {str(e)}")
            raise TeamsListenerServiceError(
                "Failed to initialize Graph Service",
                details=str(e)
            )
        
        # Fetch bot's object ID if UPN is configured
        # This allows us to filter bot messages even when UPN is empty in message
        if self.bot_upn:
            try:
                logger.info(f"Fetching bot user details for UPN: {self.bot_upn}")
                bot_user_result = self.graph_service.get_user_by_id(self.bot_upn)
                if bot_user_result.get('success'):
                    bot_user = bot_user_result.get('user', {})
                    self.bot_object_id = bot_user.get('id')
                    logger.info(f"Bot object ID retrieved: {self.bot_object_id}")
                else:
                    logger.warning(f"Could not fetch bot user details: {bot_user_result.get('error', 'Unknown error')}")
            except GraphServiceError as e:
                logger.warning(f"Failed to fetch bot object ID: {str(e)}")
                # Non-critical error, continue without object ID
            except Exception as e:
                # Catch any other exception (including test mock issues)
                logger.warning(f"Failed to fetch bot object ID: {str(e)}")
                # Non-critical error, continue without object ID
        
        # Log bot UPN configuration for debugging
        if self.bot_upn:
            logger.info(f"TeamsListenerService initialized with team_id: {self.team_id}")
            logger.info(f"DEBUG: Bot UPN configured as: '{self.bot_upn}' (will filter messages from this sender)")
            logger.info(f"DEBUG: Bot Object ID: '{self.bot_object_id or 'Not available'}'")
        else:
            logger.warning(f"TeamsListenerService initialized with team_id: {self.team_id}")
            logger.warning(f"DEBUG: Bot UPN is NOT configured (default_mail_sender is empty)! Bot messages will NOT be filtered!")
    
    def _enrich_message_sender_info(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich message with full sender information from Graph API
        
        This method addresses the known Microsoft Teams Graph API issue where
        the sender UPN can be empty in chat messages. It uses the user object ID
        to fetch complete user details including UPN, email, and name.
        
        Args:
            message: Teams message object from Graph API
            
        Returns:
            Enriched message object with full sender information
        """
        sender = message.get('from', {}).get('user', {})
        sender_upn = sender.get('userPrincipalName', '')
        sender_id = sender.get('id', '')
        
        # If UPN is empty but we have object ID, fetch full user details
        if not sender_upn and sender_id:
            logger.info(f"  - Sender UPN is empty, fetching user details by object ID: {sender_id}")
            try:
                user_result = self.graph_service.get_user_by_id(sender_id)
                if user_result.get('success'):
                    user_data = user_result.get('user', {})
                    # Enrich the message with full user information
                    message['from']['user']['userPrincipalName'] = user_data.get('userPrincipalName', '')
                    message['from']['user']['mail'] = user_data.get('mail', '')
                    message['from']['user']['displayName'] = user_data.get('displayName', sender.get('displayName', ''))
                    message['from']['user']['givenName'] = user_data.get('givenName', '')
                    message['from']['user']['surname'] = user_data.get('surname', '')
                    
                    logger.info(f"  ✓ Enriched sender info: UPN={user_data.get('userPrincipalName', 'N/A')}, "
                              f"Name={user_data.get('displayName', 'N/A')}")
                else:
                    logger.warning(f"  ⚠ Could not fetch user details: {user_result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.warning(f"  ⚠ Failed to enrich sender info: {str(e)}")
        
        return message
    
    def get_items_with_channels(self) -> List:
        """
        Get all items that have a Teams channel configured
        
        Returns:
            List of Item objects with channel_id set
        """
        from main.models import Item
        
        items = Item.objects.filter(channel_id__isnull=False).exclude(channel_id='')
        logger.info(f"Found {items.count()} items with Teams channels configured")
        return list(items)
    
    def get_new_messages_for_item(self, item) -> List[Dict[str, Any]]:
        """
        Get new messages from a Teams channel for a specific item
        
        Args:
            item: Item object with channel_id
            
        Returns:
            List of new messages that need processing
        """
        from main.models import Task
        
        if not item.channel_id:
            logger.debug(f"Item {item.id} has no channel_id, skipping")
            return []
        
        try:
            # Get messages from the channel
            result = self.graph_service.get_channel_messages(
                team_id=self.team_id,
                channel_id=item.channel_id,
                top=50
            )
            
            if not result.get('success'):
                logger.error(f"Failed to get messages for item {item.id}")
                return []
            
            messages = result.get('messages', [])
            logger.info(f"Retrieved {len(messages)} messages from channel {item.channel_id}")
            
            # Filter out messages that should not be processed
            new_messages = []
            for message in messages:
                message_id = message.get('id')
                if not message_id:
                    logger.warning(f"Message has no ID, skipping")
                    continue
                
                # Enrich message with full sender information if UPN is empty
                message = self._enrich_message_sender_info(message)
                
                # Extract sender information for detailed logging
                sender = message.get('from', {}).get('user', {})
                sender_upn = sender.get('userPrincipalName', '')
                sender_id = sender.get('id', '')
                sender_name = sender.get('displayName', '')
                
                # DEBUG: Log every message with sender details
                logger.info(f"DEBUG: Processing message {message_id}")
                logger.info(f"  - Sender Object ID: '{sender_id}' (empty: {not sender_id})")
                logger.info(f"  - Sender UPN: '{sender_upn}' (empty: {not sender_upn})")
                logger.info(f"  - Sender Name: '{sender_name}'")
                logger.info(f"  - Bot Object ID configured: '{self.bot_object_id}' (empty: {not self.bot_object_id})")
                logger.info(f"  - Bot UPN configured: '{self.bot_upn}' (empty: {not self.bot_upn})")
                
                # CRITICAL: Skip messages from IdeaGraph Bot to avoid infinite loops
                # Primary method: Check by Object ID (most reliable, works even when UPN is empty)
                if self.bot_object_id and sender_id:
                    if sender_id.lower() == self.bot_object_id.lower():
                        logger.info(f"  ✓ SKIPPED: Message {message_id} from bot itself (Object ID match)")
                        continue
                
                # Secondary method: Check by UPN (userPrincipalName) for backward compatibility
                if self.bot_upn and sender_upn:
                    bot_upn_normalized = self.bot_upn.strip().lower()
                    sender_upn_normalized = sender_upn.strip().lower()
                    logger.info(f"  - Comparing UPNs: '{sender_upn_normalized}' == '{bot_upn_normalized}' ? {sender_upn_normalized == bot_upn_normalized}")
                    if sender_upn_normalized == bot_upn_normalized:
                        logger.info(f"  ✓ SKIPPED: Message {message_id} from bot itself (UPN match)")
                        continue
                elif self.bot_upn and not sender_upn:
                    logger.warning(f"  ⚠ Cannot compare UPNs: sender_upn is empty for message {message_id} (but Object ID check already performed)")
                elif not self.bot_upn:
                    logger.warning(f"  ⚠ Cannot filter by UPN: bot_upn not configured (default_mail_sender is empty)")
                
                # Tertiary fallback: also check display name for backwards compatibility
                if sender_name == self.IDEAGRAPH_BOT_NAME:
                    logger.info(f"  ✓ SKIPPED: Message {message_id} from bot itself (display name match: '{sender_name}')")
                    continue
                
                # Check if we already have a task for this message (prevents re-processing)
                existing_task = Task.objects.filter(message_id=message_id).first()
                if existing_task:
                    logger.info(f"  ✓ SKIPPED: Task {existing_task.id} already exists for message {message_id}")
                    continue
                
                # This is a new message that needs processing
                logger.info(f"  → ACCEPTED: Message {message_id} from {sender_upn or sender_name} will be processed")
                new_messages.append(message)
            
            logger.info(f"Found {len(new_messages)} new messages to process for item {item.id}")
            return new_messages
            
        except GraphServiceError as e:
            logger.error(f"Graph API error getting messages for item {item.id}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting messages for item {item.id}: {str(e)}")
            return []
    
    def poll_all_channels(self) -> Dict[str, Any]:
        """
        Poll all configured Teams channels for new messages
        
        Returns:
            Dict with processing results
        """
        items = self.get_items_with_channels()
        
        results = {
            'success': True,
            'items_checked': len(items),
            'messages_found': 0,
            'items_with_messages': []
        }
        
        for item in items:
            try:
                new_messages = self.get_new_messages_for_item(item)
                
                if new_messages:
                    results['messages_found'] += len(new_messages)
                    results['items_with_messages'].append({
                        'item_id': str(item.id),
                        'item_title': item.title,
                        'channel_id': item.channel_id,
                        'message_count': len(new_messages),
                        'messages': new_messages
                    })
            except Exception as e:
                logger.error(f"Error processing item {item.id}: {str(e)}")
                continue
        
        logger.info(f"Polling complete: checked {results['items_checked']} items, found {results['messages_found']} new messages")
        return results
