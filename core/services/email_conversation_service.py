"""
Email Conversation Service for IdeaGraph

This module provides email conversation threading functionality:
- Sends emails from tasks with Short-ID in subject
- Maintains email thread continuity with Message-ID, In-Reply-To, References headers
- Processes incoming emails and assigns them to tasks based on Short-ID
- Creates comments from email replies
"""

import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4

from core.services.graph_service import GraphService, GraphServiceError
from main.models import Task, TaskComment, User


logger = logging.getLogger('email_conversation_service')


class EmailConversationServiceError(Exception):
    """Base exception for Email Conversation Service errors"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to structured dictionary"""
        return {
            'success': False,
            'error': self.message,
            'details': self.details or ''
        }


class EmailConversationService:
    """
    Email Conversation Service
    
    Handles email threading for tasks:
    1. Sending emails from task context with Short-ID in subject
    2. Setting proper email headers for threading
    3. Parsing incoming emails to extract Short-ID
    4. Assigning incoming emails to correct task
    5. Creating comments from email replies
    """
    
    # Pattern to extract Short-ID from subject: [IG-TASK:#XXXXXX]
    # Must be exactly 6 hexadecimal characters (0-9, A-F)
    SHORT_ID_PATTERN = re.compile(r'\[IG-TASK:#([0-9A-F]{6})\]', re.IGNORECASE)
    
    def __init__(self, settings=None):
        """
        Initialize EmailConversationService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise EmailConversationServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise EmailConversationServiceError("No settings found in database")
        
        # Initialize Graph service
        try:
            self.graph_service = GraphService(settings)
        except Exception as e:
            logger.error(f"Failed to initialize GraphService: {str(e)}")
            raise EmailConversationServiceError("Failed to initialize GraphService", details=str(e))
    
    def generate_message_id(self, task: Task, domain: str = "ideagraph.local") -> str:
        """
        Generate a unique Message-ID for an email
        
        Args:
            task: Task object
            domain: Domain for the Message-ID (default: ideagraph.local)
            
        Returns:
            Message-ID string in format: <uuid@domain>
        """
        unique_id = str(uuid4())
        return f"<{unique_id}@{domain}>"
    
    def format_subject_with_short_id(self, task: Task, subject: str) -> str:
        """
        Format email subject with Task Short-ID
        
        Args:
            task: Task object
            subject: Original subject line
            
        Returns:
            Subject line with Short-ID appended: "Subject [IG-TASK:#XXXXXX]"
        """
        short_id = task.short_id
        
        # Check if subject already contains a Short-ID
        if self.SHORT_ID_PATTERN.search(subject):
            # Replace existing Short-ID with the correct one
            subject = self.SHORT_ID_PATTERN.sub(f'[IG-TASK:#{short_id}]', subject)
        else:
            # Append Short-ID
            subject = f"{subject} [IG-TASK:#{short_id}]"
        
        return subject
    
    def extract_short_id_from_subject(self, subject: str) -> Optional[str]:
        """
        Extract Short-ID from email subject line
        
        Args:
            subject: Email subject line
            
        Returns:
            Short-ID string (6 characters) if found, None otherwise
        """
        match = self.SHORT_ID_PATTERN.search(subject)
        if match:
            return match.group(1).upper()
        return None
    
    def find_task_by_short_id(self, short_id: str) -> Optional[Task]:
        """
        Find a task by its Short-ID
        
        Args:
            short_id: 6-character Short-ID (case-insensitive)
            
        Returns:
            Task object if found, None otherwise
        """
        try:
            # Convert short_id to lowercase for matching
            short_id_lower = short_id.lower()
            
            # Query all tasks and filter by short_id
            # This is necessary because short_id is a property, not a database field
            all_tasks = Task.objects.all()
            for task in all_tasks:
                if task.id.hex[:6].lower() == short_id_lower:
                    return task
            
            logger.warning(f"No task found with Short-ID: {short_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding task by Short-ID {short_id}: {str(e)}")
            return None
    
    def _simple_html_to_markdown(self, html_content: str) -> str:
        """
        Simple HTML to Markdown converter for email bodies
        
        Args:
            html_content: HTML string
            
        Returns:
            Markdown string
        """
        import re
        
        # Remove HTML tags but preserve basic formatting
        text = html_content
        
        # Convert <br> to newlines - use non-greedy match
        text = re.sub(r'<br\s*?/?>', '\n', text, flags=re.IGNORECASE)
        
        # Convert <p> tags to double newlines - use non-greedy match
        text = re.sub(r'<p[^>]*?>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '', text, flags=re.IGNORECASE)
        
        # Convert <strong> and <b> to markdown bold - limit backtracking
        text = re.sub(r'<(?:strong|b)[^>]*?>((?:(?!</).){0,1000}?)</(?:strong|b)>', r'**\1**', text, flags=re.IGNORECASE)
        
        # Convert <em> and <i> to markdown italic - limit backtracking
        text = re.sub(r'<(?:em|i)[^>]*?>((?:(?!</).){0,1000}?)</(?:em|i)>', r'*\1*', text, flags=re.IGNORECASE)
        
        # Remove all other HTML tags - more efficient pattern
        text = re.sub(r'<[^>]{1,100}>', '', text)
        
        # Clean up excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def send_task_email(
        self,
        task: Task,
        to: List[str],
        subject: str,
        body: str,
        author: Optional[User] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        cc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send an email from a task context with proper threading
        
        Args:
            task: Task object
            to: List of recipient email addresses
            subject: Email subject (Short-ID will be appended automatically)
            body: Email body (HTML)
            author: User sending the email (optional)
            in_reply_to: Message-ID this email is replying to (optional, tracked in database)
            references: Space-separated Message-IDs for threading (optional, tracked in database)
            cc: List of CC recipient email addresses (optional)
            
        Returns:
            Dictionary with success status and message details
            
        Note:
            Microsoft Graph API does not support custom email headers like Message-ID, In-Reply-To,
            or References. These headers are automatically generated by Microsoft's email system.
            We track conversation threading in our database using TaskComment fields.
        """
        try:
            # Format subject with Short-ID
            formatted_subject = self.format_subject_with_short_id(task, subject)
            
            # Generate Message-ID for database tracking purposes
            # Note: Microsoft Graph will assign its own Message-ID when sending
            message_id = self.generate_message_id(task)
            
            # Send email via Graph API without custom headers
            # Microsoft Graph API requires custom headers to start with 'x-' or 'X-'
            # Standard headers like Message-ID, In-Reply-To, References are not supported
            result = self.graph_service.send_mail(
                to=to,
                subject=formatted_subject,
                body=body,
                cc=cc
            )
            
            if result.get('success'):
                # Create a comment in the task to track this sent email
                recipients_text = ', '.join(to)
                comment_text = f"**E-Mail gesendet an {recipients_text}:**\n\n**Betreff:** {formatted_subject}\n\n{body}"
                
                if cc:
                    comment_text = f"**E-Mail gesendet an {recipients_text}** (Cc: {', '.join(cc)}):\n\n**Betreff:** {formatted_subject}\n\n{body}"
                
                TaskComment.objects.create(
                    task=task,
                    author=author,
                    author_name=author.username if author else 'System',
                    text=comment_text,
                    source='email',
                    email_message_id=message_id,
                    email_in_reply_to=in_reply_to or '',
                    email_references=references or '',
                    email_from=self.settings.default_mail_sender or '',
                    email_to=', '.join(to),
                    email_cc=', '.join(cc) if cc else '',
                    email_subject=formatted_subject,
                    email_direction='outbound'
                )
                
                logger.info(f"Email sent successfully for task {task.id} with Short-ID {task.short_id}")
                
                return {
                    'success': True,
                    'message': 'Email sent successfully',
                    'message_id': message_id,
                    'short_id': task.short_id,
                    'subject': formatted_subject
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to send email'
                }
                
        except GraphServiceError as e:
            logger.error(f"Graph service error sending task email: {e.message}")
            return {
                'success': False,
                'message': f'Graph service error: {e.message}',
                'details': e.details
            }
        except Exception as e:
            logger.error(f"Error sending task email: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def process_incoming_email(
        self,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process an incoming email and assign to task if Short-ID found
        
        Args:
            message: Email message dict from Graph API with fields:
                - id: Message ID
                - subject: Subject line
                - body: Body content
                - from: Sender info
                - internetMessageHeaders: Email headers (optional)
                
        Returns:
            Dictionary with processing result
        """
        try:
            # Extract message details
            message_id = message.get('id', '')
            subject = message.get('subject', '')
            body_data = message.get('body', {})
            body_content = body_data.get('content', '')
            
            sender = message.get('from', {}).get('emailAddress', {})
            sender_email = sender.get('address', '')
            sender_name = sender.get('name', '')
            
            # Extract email headers
            headers = message.get('internetMessageHeaders', [])
            internet_message_id = ''
            in_reply_to = ''
            references = ''
            
            for header in headers:
                header_name = header.get('name', '').lower()
                header_value = header.get('value', '')
                
                if header_name == 'message-id':
                    internet_message_id = header_value
                elif header_name == 'in-reply-to':
                    in_reply_to = header_value
                elif header_name == 'references':
                    references = header_value
            
            logger.info(f"Processing incoming email: {subject} from {sender_email}")
            
            # Extract Short-ID from subject
            short_id = self.extract_short_id_from_subject(subject)
            
            if not short_id:
                logger.info(f"No Short-ID found in subject: {subject}")
                return {
                    'success': False,
                    'message': 'No Short-ID found in subject',
                    'subject': subject
                }
            
            # Find task by Short-ID
            task = self.find_task_by_short_id(short_id)
            
            if not task:
                logger.warning(f"Task not found for Short-ID: {short_id}")
                return {
                    'success': False,
                    'message': f'Task not found for Short-ID: {short_id}',
                    'short_id': short_id,
                    'subject': subject
                }
            
            logger.info(f"Email matched to task: {task.title} ({task.id})")
            
            # Find or create user for sender
            try:
                user = User.objects.get(email=sender_email)
            except User.DoesNotExist:
                # Create new user
                logger.info(f"Creating new user for email: {sender_email}")
                
                first_name = ''
                last_name = ''
                if sender_name:
                    name_parts = sender_name.strip().split()
                    if len(name_parts) >= 2:
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:])
                    elif len(name_parts) == 1:
                        first_name = name_parts[0]
                
                user = User.objects.create(
                    username=sender_email,
                    email=sender_email,
                    first_name=first_name,
                    last_name=last_name,
                    role='user',
                    is_active=True
                )
            
            # Convert HTML body to markdown (simple conversion)
            body_markdown = self._simple_html_to_markdown(body_content)
            
            # Create comment from email
            comment_text = f"**E-Mail-Antwort von {sender_name}:**\n\n{body_markdown}"
            
            TaskComment.objects.create(
                task=task,
                author=user,
                author_name=sender_name,
                text=comment_text,
                source='email',
                email_message_id=internet_message_id,
                email_in_reply_to=in_reply_to,
                email_references=references,
                email_from=sender_email,
                email_to=self.settings.default_mail_sender or '',
                email_subject=subject,
                email_direction='inbound'
            )
            
            logger.info(f"Created comment from email for task {task.id}")
            
            return {
                'success': True,
                'message': 'Email processed and comment created',
                'task_id': str(task.id),
                'task_title': task.title,
                'short_id': short_id,
                'sender': sender_email
            }
            
        except Exception as e:
            logger.error(f"Error processing incoming email: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing email: {str(e)}',
                'subject': message.get('subject', '')
            }
