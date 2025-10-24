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
        
        # Initialize Graph Service for API calls
        try:
            self.graph_service = GraphService(settings=settings)
        except GraphServiceError as e:
            logger.error(f"Failed to initialize Graph Service: {str(e)}")
            raise TeamsListenerServiceError(
                "Failed to initialize Graph Service",
                details=str(e)
            )
        
        logger.debug(f"TeamsListenerService initialized with team_id: {self.team_id}, bot_upn: {self.bot_upn}")
    
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
                
                # CRITICAL: Skip messages from IdeaGraph Bot to avoid infinite loops
                # Check by UPN (userPrincipalName) which is the most reliable method
                sender_upn = message.get('from', {}).get('user', {}).get('userPrincipalName', '')
                
                # Always skip if sender matches bot UPN (case-insensitive)
                if self.bot_upn and sender_upn:
                    if sender_upn.lower() == self.bot_upn.lower():
                        logger.info(f"SKIPPED: Message {message_id} from bot itself (UPN: {sender_upn})")
                        continue
                
                # Fallback: also check display name for backwards compatibility
                sender_name = message.get('from', {}).get('user', {}).get('displayName', '')
                if sender_name == self.IDEAGRAPH_BOT_NAME:
                    logger.info(f"SKIPPED: Message {message_id} from bot itself (display name: {sender_name})")
                    continue
                
                # Check if we already have a task for this message (prevents re-processing)
                existing_task = Task.objects.filter(message_id=message_id).first()
                if existing_task:
                    logger.debug(f"SKIPPED: Task {existing_task.id} already exists for message {message_id}")
                    continue
                
                # This is a new message that needs processing
                logger.debug(f"New message to process: {message_id} from {sender_upn or sender_name}")
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
