"""
Message Processing Service for IdeaGraph

This service analyzes Teams messages using KIGate AI agents and creates tasks.
"""

import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime

from .kigate_service import KiGateService, KiGateServiceError


logger = logging.getLogger('message_processing_service')


class MessageProcessingServiceError(Exception):
    """Base exception for Message Processing Service errors"""
    
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


class MessageProcessingService:
    """
    Message Processing Service
    
    Analyzes Teams messages using KIGate AI agents and determines if tasks should be created.
    """
    
    TEAMS_SUPPORT_ANALYSIS_AGENT = 'teams-support-analysis-agent'
    
    def __init__(self, settings=None):
        """
        Initialize MessageProcessingService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise MessageProcessingServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise MessageProcessingServiceError("No settings found in database")
        
        # Initialize KiGate Service for AI analysis
        try:
            self.kigate_service = KiGateService(settings=settings)
        except KiGateServiceError as e:
            logger.error(f"Failed to initialize KiGate Service: {str(e)}")
            raise MessageProcessingServiceError(
                "Failed to initialize KiGate Service",
                details=str(e)
            )
        
        logger.debug("MessageProcessingService initialized")
    
    def extract_message_content(self, message: Dict[str, Any]) -> str:
        """
        Extract text content from a Teams message
        
        Args:
            message: Teams message object from Graph API
            
        Returns:
            Extracted text content
        """
        # Get the message body
        body = message.get('body', {})
        content = body.get('content', '')
        
        # If content is HTML, strip HTML tags for cleaner analysis
        content_type = body.get('contentType', 'text')
        if content_type == 'html':
            # Simple HTML tag removal
            content = re.sub(r'<[^>]+>', '', content)
            # Decode common HTML entities
            content = content.replace('&nbsp;', ' ')
            content = content.replace('&lt;', '<')
            content = content.replace('&gt;', '>')
            content = content.replace('&amp;', '&')
        
        return content.strip()
    
    def get_or_create_user_from_upn(self, upn: str, display_name: str = '') -> Any:
        """
        Get or create a user based on UserPrincipalName (UPN)
        
        Args:
            upn: User Principal Name (email)
            display_name: Display name of the user
            
        Returns:
            User object
        """
        from main.models import User
        
        # Try to find existing user by UPN (used as both username and email)
        user = User.objects.filter(username=upn).first()
        
        if user:
            logger.debug(f"Found existing user: {upn}")
            return user
        
        # User doesn't exist, create new user
        logger.info(f"Creating new user from UPN: {upn}")
        
        # Extract first and last name from display name
        first_name = ''
        last_name = ''
        if display_name:
            name_parts = display_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            elif len(name_parts) == 1:
                first_name = name_parts[0]
        
        # Create new user with 'user' role
        user = User.objects.create(
            username=upn,
            email=upn,
            first_name=first_name,
            last_name=last_name,
            role='user',
            is_active=True,
            auth_type='msauth'  # Mark as Microsoft authenticated user
        )
        
        logger.info(f"Created new user: {upn} ({first_name} {last_name})")
        return user
    
    def analyze_message(self, message: Dict[str, Any], item) -> Dict[str, Any]:
        """
        Analyze a Teams message using KIGate AI agent
        
        Args:
            message: Teams message object
            item: Item object the message belongs to
            
        Returns:
            Dict with analysis result and AI response
        """
        # Extract message content
        content = self.extract_message_content(message)
        
        if not content:
            logger.warning(f"Message {message.get('id')} has no content, skipping analysis")
            return {
                'success': False,
                'error': 'No message content to analyze'
            }
        
        # Get sender information
        sender = message.get('from', {}).get('user', {})
        sender_upn = sender.get('userPrincipalName', 'unknown@example.com')
        sender_name = sender.get('displayName', 'Unknown User')
        
        # Prepare context for AI agent
        ai_prompt = f"""Item: {item.title}
Item Description: {item.description[:500] if item.description else 'No description'}

User Message from {sender_name}:
{content}

Analyze this message and provide:
1. A helpful response to the user
2. Whether a task should be created (yes/no)
3. If yes, suggest a task title and description"""
        
        try:
            logger.info(f"Analyzing message with KIGate agent: {self.TEAMS_SUPPORT_ANALYSIS_AGENT}")
            
            # Execute KIGate agent
            result = self.kigate_service.execute_agent(
                agent_name=self.TEAMS_SUPPORT_ANALYSIS_AGENT,
                provider='openai',  # Default provider
                model='gpt-4',  # Default model
                message=ai_prompt,
                user_id=sender_upn,
                parameters={
                    'item_id': str(item.id),
                    'item_title': item.title,
                    'message_id': message.get('id')
                }
            )
            
            if not result.get('success'):
                logger.error(f"KIGate agent execution failed")
                return {
                    'success': False,
                    'error': 'AI analysis failed'
                }
            
            ai_response = result.get('result', '')
            
            logger.info(f"AI analysis complete for message {message.get('id')}")
            
            return {
                'success': True,
                'ai_response': ai_response,
                'message_content': content,
                'sender_upn': sender_upn,
                'sender_name': sender_name,
                'should_create_task': self._should_create_task(ai_response)
            }
            
        except KiGateServiceError as e:
            logger.error(f"KiGate error analyzing message: {str(e)}")
            return {
                'success': False,
                'error': f'AI service error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error analyzing message: {str(e)}")
            return {
                'success': False,
                'error': f'Analysis error: {str(e)}'
            }
    
    def _should_create_task(self, ai_response: str) -> bool:
        """
        Determine if a task should be created based on AI response
        
        Args:
            ai_response: Response from AI agent
            
        Returns:
            True if task should be created, False otherwise
        """
        # Look for keywords indicating task creation
        response_lower = ai_response.lower()
        
        # Positive indicators
        task_indicators = [
            'create task',
            'task:',
            'aufgabe:',
            'titel:',
            'title:',
            'beschreibung:',
            'description:',
            'should create: yes',
            'task should be created'
        ]
        
        # Negative indicators
        no_task_indicators = [
            'no task needed',
            'keine aufgabe',
            'should create: no',
            'no task should be created',
            'information only',
            'nur information'
        ]
        
        # Check for negative indicators first
        for indicator in no_task_indicators:
            if indicator in response_lower:
                logger.debug(f"Found no-task indicator: {indicator}")
                return False
        
        # Check for positive indicators
        for indicator in task_indicators:
            if indicator in response_lower:
                logger.debug(f"Found task indicator: {indicator}")
                return True
        
        # Default: if response is substantial, create a task
        if len(ai_response) > 100:
            logger.debug("Response is substantial, defaulting to create task")
            return True
        
        logger.debug("No clear indicators, defaulting to no task")
        return False
    
    def create_task_from_analysis(
        self,
        item,
        message: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Create a task based on message analysis
        
        Args:
            item: Item object
            message: Teams message object
            analysis_result: Result from analyze_message
            
        Returns:
            Created Task object or None
        """
        from main.models import Task
        
        if not analysis_result.get('success'):
            logger.error("Cannot create task from failed analysis")
            return None
        
        # Get or create user
        sender_upn = analysis_result.get('sender_upn')
        sender_name = analysis_result.get('sender_name', '')
        
        try:
            requester = self.get_or_create_user_from_upn(sender_upn, sender_name)
        except Exception as e:
            logger.error(f"Failed to get/create user: {str(e)}")
            requester = None
        
        # Build task description from AI response and original message
        ai_response = analysis_result.get('ai_response', '')
        original_message = analysis_result.get('message_content', '')
        
        task_description = f"""{ai_response}

---

**Original Message from {sender_name}:**
{original_message}"""
        
        # Extract task title from AI response or use default
        task_title = self._extract_task_title(ai_response) or f"Support Request from {sender_name}"
        
        # Create the task
        try:
            task = Task.objects.create(
                title=task_title,
                description=task_description,
                item=item,
                requester=requester,
                status='new',
                type='task',
                message_id=message.get('id'),  # Store Teams message ID
                ai_generated=True
            )
            
            logger.info(f"Created task {task.id} from Teams message {message.get('id')}")
            return task
            
        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}")
            return None
    
    def _extract_task_title(self, ai_response: str) -> Optional[str]:
        """
        Extract task title from AI response
        
        Args:
            ai_response: Response from AI agent
            
        Returns:
            Extracted title or None
        """
        # Look for common title patterns
        patterns = [
            r'(?:title|titel):\s*(.+?)(?:\n|$)',
            r'(?:task|aufgabe):\s*(.+?)(?:\n|$)',
            r'^(.+?)(?:\n|$)'  # First line as fallback
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ai_response, re.IGNORECASE | re.MULTILINE)
            if match:
                title = match.group(1).strip()
                # Clean up title
                title = re.sub(r'[*#]', '', title).strip()
                if 10 <= len(title) <= 200:
                    return title
        
        return None
