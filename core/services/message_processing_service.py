"""
Message Processing Service for IdeaGraph

This service analyzes Teams messages using KIGate AI agents and creates tasks.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from .kigate_service import KiGateService, KiGateServiceError
from .weaviate_sync_service import WeaviateItemSyncService, WeaviateItemSyncServiceError
from .weaviate_task_sync_service import WeaviateTaskSyncService, WeaviateTaskSyncServiceError


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
        
        # Initialize Weaviate services for RAG
        try:
            self.weaviate_item_service = WeaviateItemSyncService(settings=settings)
            self.weaviate_task_service = WeaviateTaskSyncService(settings=settings)
        except (WeaviateItemSyncServiceError, WeaviateTaskSyncServiceError, Exception) as e:
            # Log warning but don't fail - RAG is optional enhancement
            logger.warning(f"Failed to initialize Weaviate services for RAG: {str(e)}")
            self.weaviate_item_service = None
            self.weaviate_task_service = None
        
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
    
    def search_similar_context(
        self,
        query_text: str,
        item_id: str = None,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for similar knowledge objects using RAG (Weaviate)
        
        Args:
            query_text: Text to search for similar content
            item_id: Optional item ID to filter results
            max_results: Maximum number of results to return
            
        Returns:
            List of similar knowledge objects with metadata
        """
        similar_objects = []
        
        # Return empty if Weaviate services are not available
        if not self.weaviate_item_service or not self.weaviate_task_service:
            logger.debug("Weaviate services not available, skipping RAG context search")
            return similar_objects
        
        try:
            # Search for similar tasks
            try:
                task_results = self.weaviate_task_service.search_similar(
                    query_text,
                    n_results=max_results
                )
                
                if task_results.get('success') and task_results.get('results'):
                    for result in task_results['results']:
                        metadata = result.get('metadata', {})
                        similar_objects.append({
                            'type': 'task',
                            'id': metadata.get('task_id', ''),
                            'title': metadata.get('title', 'N/A'),
                            'description': result.get('document', '')[:300],
                            'similarity': result.get('distance', 0)
                        })
                    logger.info(f"Found {len(task_results['results'])} similar tasks via RAG")
            except Exception as e:
                logger.warning(f"Could not search similar tasks: {str(e)}")
            
            # Search for similar items
            try:
                item_results = self.weaviate_item_service.search_similar(
                    query_text,
                    n_results=max_results
                )
                
                if item_results.get('success') and item_results.get('results'):
                    for result in item_results['results']:
                        metadata = result.get('metadata', {})
                        similar_objects.append({
                            'type': 'item',
                            'id': result.get('id', ''),
                            'title': metadata.get('title', 'N/A'),
                            'description': result.get('document', '')[:300],
                            'similarity': result.get('distance', 0)
                        })
                    logger.info(f"Found {len(item_results['results'])} similar items via RAG")
            except Exception as e:
                logger.warning(f"Could not search similar items: {str(e)}")
            
            # Sort by similarity (lower distance is better)
            similar_objects.sort(key=lambda x: x.get('similarity', float('inf')))
            
            # Return top results
            return similar_objects[:max_results]
            
        except Exception as e:
            logger.warning(f"RAG context search failed: {str(e)}")
            return []
    
    def _format_rag_context(self, similar_objects: List[Dict[str, Any]]) -> str:
        """
        Format similar objects from RAG into context text for AI
        
        Args:
            similar_objects: List of similar knowledge objects
            
        Returns:
            Formatted context string
        """
        if not similar_objects:
            return ""
        
        context_items = []
        for idx, obj in enumerate(similar_objects, 1):
            obj_type = obj['type'].capitalize()
            context_items.append(
                f"{obj_type} {idx}: {obj['title']}\n"
                f"Beschreibung: {obj['description']}..."
            )
        
        context_text = "\n\n".join(context_items)
        
        return f"""
--- Ähnliche Objekte aus der Wissensbasis (RAG) ---
{context_text}
--- Ende der ähnlichen Objekte ---
"""
    
    def get_or_create_user_from_sender(
        self,
        sender: Dict[str, Any]
    ) -> Any:
        """
        Get or create a user based on sender information from a Teams message
        
        This method handles the enriched sender information including object ID,
        UPN, email, and name fields. It uses object ID as the primary identifier
        and falls back to UPN/email if needed.
        
        Args:
            sender: Sender user object from Teams message (message.from.user)
                Expected fields:
                - id: Microsoft User Object ID
                - userPrincipalName: User's UPN (may be empty)
                - mail: User's email address
                - displayName: User's display name
                - givenName: User's first name
                - surname: User's last name
            
        Returns:
            User object
        """
        from main.models import User
        
        # Extract information from sender
        user_object_id = sender.get('id', '')
        upn = sender.get('userPrincipalName', '')
        email = sender.get('mail', '')
        display_name = sender.get('displayName', '')
        given_name = sender.get('givenName', '')
        surname = sender.get('surname', '')
        
        # Use UPN as primary identifier, fall back to email
        user_identifier = upn or email
        
        if not user_identifier:
            logger.error(f"Cannot create user: no UPN or email available. Object ID: {user_object_id}")
            raise ValueError("Cannot create user without UPN or email")
        
        # Try to find existing user by ms_user_id (object ID) first
        user = None
        if user_object_id:
            user = User.objects.filter(ms_user_id=user_object_id).first()
            if user:
                logger.debug(f"Found existing user by Object ID: {user_identifier} (ID: {user_object_id})")
                return user
        
        # Try to find by username (UPN)
        user = User.objects.filter(username=user_identifier).first()
        
        if user:
            logger.debug(f"Found existing user by username: {user_identifier}")
            # Update ms_user_id if not set
            if user_object_id and not user.ms_user_id:
                user.ms_user_id = user_object_id
                user.save(update_fields=['ms_user_id'])
                logger.info(f"Updated user {user_identifier} with Object ID: {user_object_id}")
            return user
        
        # User doesn't exist, create new user
        logger.info(f"Creating new user from sender info: {user_identifier}")
        
        # Use provided first/last name, or extract from display name as fallback
        first_name = given_name
        last_name = surname
        
        if not first_name and not last_name and display_name:
            # Extract from display name
            name_parts = display_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            elif len(name_parts) == 1:
                first_name = name_parts[0]
        
        # Create new user with 'user' role
        user = User.objects.create(
            username=user_identifier,
            email=email or user_identifier,
            first_name=first_name or '',
            last_name=last_name or '',
            ms_user_id=user_object_id or '',
            role='user',
            is_active=True,
            auth_type='msauth'  # Mark as Microsoft authenticated user
        )
        
        logger.info(f"Created new user: {user_identifier} ({first_name} {last_name}, Object ID: {user_object_id})")
        return user
    
    def analyze_message(self, message: Dict[str, Any], item) -> Dict[str, Any]:
        """
        Analyze a Teams message using KIGate AI agent with RAG-enhanced context
        
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
        sender_id = sender.get('id', '')
        sender_upn = sender.get('userPrincipalName', 'unknown@example.com')
        sender_name = sender.get('displayName', 'Unknown User')
        
        # DEBUG: Log message analysis attempt
        logger.info(f"DEBUG: Analyzing message from sender:")
        logger.info(f"  - Sender Object ID: '{sender_id}'")
        logger.info(f"  - Sender UPN: '{sender_upn}'")
        logger.info(f"  - Sender Name: '{sender_name}'")
        
        # CRITICAL: Double-check we're not analyzing our own messages
        # This should have been filtered earlier, but add defensive check
        # Normalize both values: strip whitespace and convert to lowercase
        bot_upn = self.settings.default_mail_sender
        if bot_upn and sender_upn:
            bot_upn_normalized = bot_upn.strip().lower()
            sender_upn_normalized = sender_upn.strip().lower()
            logger.info(f"  - Bot UPN check: comparing '{sender_upn_normalized}' vs '{bot_upn_normalized}'")
            if sender_upn_normalized == bot_upn_normalized:
                logger.error(f"CRITICAL: Attempted to analyze message from bot itself! Message ID: {message.get('id')}, Sender: {sender_upn}")
                logger.error(f"  This message should have been filtered in TeamsListenerService!")
                return {
                    'success': False,
                    'error': 'Cannot analyze message from bot itself (infinite loop prevention)'
                }
        elif not bot_upn:
            logger.warning(f"  ⚠ Bot UPN not configured (default_mail_sender is empty) - cannot verify sender is not bot")
        
        logger.info(f"  → Proceeding with analysis (sender is not the bot)")
        
        # Search for similar context using RAG
        search_query = f"{item.title}\n{content}"
        similar_objects = self.search_similar_context(
            query_text=search_query,
            item_id=str(item.id),
            max_results=3
        )
        
        # Format RAG context for AI prompt
        rag_context = self._format_rag_context(similar_objects)
        
        # Prepare context for AI agent with RAG enhancement
        ai_prompt = f"""Item: {item.title}
Item Description: {item.description[:500] if item.description else 'No description'}

User Message from {sender_name}:
{content}
{rag_context}

Analyze this message and provide:
1. A helpful response to the user
2. Whether a task should be created (yes/no)
3. If yes, suggest a task title and description

Use the similar objects from the knowledge base (if provided) to give more informed and contextually relevant recommendations."""
        
        try:
            logger.info(f"Analyzing message with KIGate agent: {self.TEAMS_SUPPORT_ANALYSIS_AGENT} (RAG-enhanced)")
            
            # Execute KIGate agent
            result = self.kigate_service.execute_agent(
                agent_name=self.TEAMS_SUPPORT_ANALYSIS_AGENT,
                provider='openai',  # Default provider
                model='gpt-4',  # GPT-4 model
                message=ai_prompt,
                user_id=sender_upn,
                parameters={
                    'item_id': str(item.id),
                    'item_title': item.title,
                    'message_id': message.get('id'),
                    'rag_enabled': bool(similar_objects),
                    'similar_objects_count': len(similar_objects)
                }
            )
            
            if not result.get('success'):
                logger.error(f"KIGate agent execution failed")
                return {
                    'success': False,
                    'error': 'AI analysis failed'
                }
            
            ai_response = result.get('result', '')
            
            logger.info(f"AI analysis complete for message {message.get('id')} with {len(similar_objects)} RAG context objects")
            
            return {
                'success': True,
                'ai_response': ai_response,
                'message_content': content,
                'sender': sender,  # Full sender object with all enriched information
                'sender_upn': sender_upn,
                'sender_name': sender_name,
                'should_create_task': self._should_create_task(ai_response),
                'rag_context_used': bool(similar_objects),
                'similar_objects_count': len(similar_objects)
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
        
        # Get or create user from full sender information
        sender = analysis_result.get('sender', {})
        
        try:
            requester = self.get_or_create_user_from_sender(sender)
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
