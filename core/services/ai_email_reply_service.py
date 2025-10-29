"""
AI Email Reply Service for IdeaGraph

This service generates AI-powered email replies using KiGate's answers-draft-agent
and handles the complete reply workflow including sending.
"""

import logging
import re
from typing import Dict, Any, Optional
from django.utils import timezone
from main.models import TaskComment, Task, User
from core.services.kigate_service import KiGateService, KiGateServiceError
from core.services.email_reply_rag_service import EmailReplyRAGService
from main.mail_utils import send_task_email

logger = logging.getLogger('ai_email_reply')


class AIEmailReplyService:
    """
    Service for generating and sending AI-powered email replies
    """
    
    # Domain allowlist for sending emails (empty = allow all)
    DOMAIN_ALLOWLIST = []  # e.g., ['example.com', 'angermeier.net']
    
    # Patterns to filter from draft (security)
    SECRET_PATTERNS = [
        r'(?i)(?:api[_-]?key|token|secret|password|bearer)[\s:=]+[\w\-\.]+',
        r'https?://(?:localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+)',  # Internal URLs
    ]
    
    def __init__(self, settings=None):
        """
        Initialize AI Email Reply Service
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise ValueError("Failed to load settings")
        
        self.settings = settings
        self.kigate_service = KiGateService(settings)
        self.rag_service = EmailReplyRAGService(settings)
    
    def _validate_email_domain(self, email: str) -> bool:
        """
        Validate email domain against allowlist
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not self.DOMAIN_ALLOWLIST:
            # Empty allowlist = allow all
            return True
        
        domain = email.split('@')[-1].lower()
        return domain in self.DOMAIN_ALLOWLIST
    
    def _filter_secrets(self, text: str) -> str:
        """
        Filter secrets and internal links from text
        
        Args:
            text: Text to filter
            
        Returns:
            Filtered text
        """
        filtered = text
        for pattern in self.SECRET_PATTERNS:
            filtered = re.sub(pattern, '[REDACTED]', filtered, flags=re.IGNORECASE)
        return filtered
    
    def _build_kigate_message(self, query: str, context: str) -> str:
        """
        Build message for KiGate agent
        
        Args:
            query: User query (incoming email)
            context: Retrieved context with markers
            
        Returns:
            Formatted message
        """
        return f"""QUERY:
{query}

CONTEXT:
{context}"""
    
    def generate_draft(
        self, 
        comment: TaskComment,
        user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Generate AI draft reply for an incoming email comment
        
        Args:
            comment: TaskComment object (must be inbound email)
            user: User generating the draft (optional)
            
        Returns:
            Dictionary with draft data including:
            - success: bool
            - subject: str
            - body: str
            - sources: list
            - confidence: str/float
            - language: str
            - latency_ms: int
        """
        start_time = timezone.now()
        
        # Validate comment is inbound email
        if comment.source != 'email' or comment.email_direction != 'inbound':
            logger.error(f"Comment {comment.id} is not an inbound email")
            return {
                'success': False,
                'error': 'Comment is not an inbound email'
            }
        
        # Validate sender email domain
        if comment.email_from and not self._validate_email_domain(comment.email_from):
            logger.warning(f"Email domain not in allowlist: {comment.email_from}")
            return {
                'success': False,
                'error': 'Email domain not allowed'
            }
        
        try:
            # Retrieve context
            logger.info(f"Retrieving context for comment {comment.id}")
            context_data = self.rag_service.retrieve_context(comment)
            context_formatted = self.rag_service.format_context_for_kigate(context_data)
            
            # Build query from incoming email
            query = comment.text
            if comment.email_subject:
                query = f"Subject: {comment.email_subject}\n\n{query}"
            
            # Build KiGate message
            kigate_message = self._build_kigate_message(query, context_formatted)
            
            # Call KiGate answers-draft-agent
            logger.info(f"Calling KiGate answers-draft-agent for comment {comment.id}")
            kigate_result = self.kigate_service.execute_agent(
                agent_name='answers-draft-agent',
                provider='openai',
                model='gpt-4o-mini',
                message=kigate_message,
                user_id=str(user.id) if user else 'system'
            )
            
            if not kigate_result.get('success'):
                logger.error(f"KiGate execution failed: {kigate_result}")
                return {
                    'success': False,
                    'error': 'Failed to generate draft',
                    'details': kigate_result
                }
            
            # Parse KiGate response
            result_text = kigate_result.get('result', '')
            
            # Extract subject and body from result
            # Expected format: subject line followed by blank line, then body
            parts = result_text.split('\n\n', 1)
            if len(parts) == 2:
                subject = parts[0].strip()
                body = parts[1].strip()
            else:
                # Fallback: use Re: prefix
                subject = f"Re: {comment.email_subject or comment.task.title}"
                body = result_text.strip()
            
            # Remove "Subject: " prefix if present
            if subject.lower().startswith('subject:'):
                subject = subject[8:].strip()
            
            # Filter secrets from body
            body = self._filter_secrets(body)
            
            # Calculate latency
            latency_ms = int((timezone.now() - start_time).total_seconds() * 1000)
            
            # Build response
            response = {
                'success': True,
                'subject': subject,
                'body': body,
                'sources': context_data['sources'],
                'confidence': 'high',  # Could be enhanced with actual confidence scoring
                'language': 'de',  # Could be detected from content
                'latency_ms': latency_ms,
                'tier_a_count': context_data['tier_a_count'],
                'tier_b_count': context_data['tier_b_count'],
                'tier_c_count': context_data['tier_c_count'],
                'total_sources': context_data['total_count'],
            }
            
            # Log structured info
            logger.info(
                f"Draft generated successfully | "
                f"comment_id={comment.id} | "
                f"task_id={comment.task.id} | "
                f"item_id={comment.task.item.id} | "
                f"latency_ms={latency_ms} | "
                f"sources_n={context_data['total_count']} | "
                f"confidence=high"
            )
            
            return response
            
        except KiGateServiceError as e:
            logger.error(f"KiGate error generating draft: {e.message}")
            return {
                'success': False,
                'error': 'KiGate service error',
                'details': e.message
            }
        except Exception as e:
            logger.error(f"Unexpected error generating draft: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Unexpected error',
                'details': str(e)
            }
    
    def send_reply(
        self,
        comment: TaskComment,
        subject: str,
        body: str,
        user: Optional[User] = None,
        cc: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send AI-generated email reply
        
        Args:
            comment: Original TaskComment (inbound email)
            subject: Email subject
            body: Email body
            user: User sending the reply
            cc: CC email addresses (comma-separated)
            
        Returns:
            Dictionary with send result
        """
        # Validate comment
        if comment.source != 'email' or comment.email_direction != 'inbound':
            logger.error(f"Comment {comment.id} is not an inbound email")
            return {
                'success': False,
                'error': 'Comment is not an inbound email'
            }
        
        # Validate recipient
        recipient = comment.email_from
        if not recipient:
            logger.error(f"Comment {comment.id} has no sender email")
            return {
                'success': False,
                'error': 'No recipient email available'
            }
        
        if not self._validate_email_domain(recipient):
            logger.warning(f"Email domain not in allowlist: {recipient}")
            return {
                'success': False,
                'error': 'Email domain not allowed'
            }
        
        try:
            # Send email via mail_utils
            logger.info(f"Sending AI reply to {recipient} for comment {comment.id}")
            
            success, result = send_task_email(
                task_id=comment.task.id,
                recipient_email=recipient,
                subject=subject,
                body=body,
                user=user,
                in_reply_to=comment.email_message_id,
                cc=cc
            )
            
            if not success:
                logger.error(f"Failed to send email: {result}")
                return {
                    'success': False,
                    'error': 'Failed to send email',
                    'details': result
                }
            
            # Extract comment_id from result if available
            comment_id = None
            if isinstance(result, dict):
                comment_id = result.get('comment_id')
            
            # Log structured info
            logger.info(
                f"AI reply sent successfully | "
                f"original_comment_id={comment.id} | "
                f"new_comment_id={comment_id} | "
                f"task_id={comment.task.id} | "
                f"recipient={recipient} | "
                f"send_success=True"
            )
            
            return {
                'success': True,
                'message': 'Email sent successfully',
                'comment_id': comment_id,
                'recipient': recipient
            }
            
        except Exception as e:
            logger.error(f"Unexpected error sending reply: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': 'Unexpected error',
                'details': str(e)
            }
