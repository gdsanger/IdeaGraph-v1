"""
Graph Response Service for IdeaGraph

This service posts AI-generated responses back to Teams channels.
"""

import logging
from typing import Optional, Dict, Any

from .graph_service import GraphService, GraphServiceError


logger = logging.getLogger('graph_response_service')


class GraphResponseServiceError(Exception):
    """Base exception for Graph Response Service errors"""
    
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


class GraphResponseService:
    """
    Graph Response Service
    
    Posts AI-generated responses back to Teams channels.
    """
    
    def __init__(self, settings=None):
        """
        Initialize GraphResponseService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise GraphResponseServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise GraphResponseServiceError("No settings found in database")
        
        if not self.settings.teams_enabled:
            logger.error("Teams integration is not enabled in settings")
            raise GraphResponseServiceError("Teams integration is not enabled in settings")
        
        if not self.settings.teams_team_id:
            logger.error("Teams Team ID not configured")
            raise GraphResponseServiceError(
                "Teams Team ID not configured",
                details="teams_team_id must be set in settings"
            )
        
        self.team_id = self.settings.teams_team_id
        
        # Initialize Graph Service for API calls
        try:
            self.graph_service = GraphService(settings=settings)
        except GraphServiceError as e:
            logger.error(f"Failed to initialize Graph Service: {str(e)}")
            raise GraphResponseServiceError(
                "Failed to initialize Graph Service",
                details=str(e)
            )
        
        logger.debug(f"GraphResponseService initialized with team_id: {self.team_id}")
    
    def post_response(
        self,
        channel_id: str,
        response_content: str,
        task_created: bool = False,
        task_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Post a response to a Teams channel
        
        Args:
            channel_id: ID of the Teams channel
            response_content: Content of the response message
            task_created: Whether a task was created
            task_url: Optional URL to the created task
            
        Returns:
            Dict with success status and message details
        """
        # Format the message with HTML for better presentation
        message_html = f"""<div>
<p>{self._format_text_to_html(response_content)}</p>"""
        
        # Add task information if applicable
        if task_created and task_url:
            message_html += f"""
<hr>
<p><strong>✅ Task erstellt:</strong> <a href="{task_url}">Zum Task</a></p>"""
        
        message_html += "</div>"
        
        try:
            logger.info(f"Posting response to channel {channel_id}")
            
            result = self.graph_service.post_channel_message(
                team_id=self.team_id,
                channel_id=channel_id,
                message_content=message_html
            )
            
            if result.get('success'):
                logger.info(f"Successfully posted response to channel {channel_id}")
                return {
                    'success': True,
                    'message_id': result.get('message_id'),
                    'created_at': result.get('created_at')
                }
            else:
                logger.error(f"Failed to post response to channel {channel_id}")
                return {
                    'success': False,
                    'error': 'Failed to post message'
                }
            
        except GraphServiceError as e:
            logger.error(f"Graph API error posting response: {str(e)}")
            raise GraphResponseServiceError(
                "Failed to post response to Teams",
                status_code=e.status_code,
                details=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error posting response: {str(e)}")
            raise GraphResponseServiceError(
                "Unexpected error posting response",
                details=str(e)
            )
    
    def _format_text_to_html(self, text: str) -> str:
        """
        Convert plain text to basic HTML
        
        Args:
            text: Plain text content
            
        Returns:
            HTML formatted text
        """
        # Replace newlines with <br> tags
        html = text.replace('\n', '<br>')
        
        # Escape HTML entities (but preserve our <br> tags)
        html = html.replace('&', '&amp;')
        html = html.replace('<br>', '|||BR|||')
        html = html.replace('<', '&lt;')
        html = html.replace('>', '&gt;')
        html = html.replace('|||BR|||', '<br>')
        
        return html
