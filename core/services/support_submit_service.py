"""
Support Submit Service

This service handles submission of support requests by creating
tasks with appropriate metadata and enriched descriptions.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger('support_submit_service')


class SupportSubmitService:
    """
    Service to submit support requests as tasks
    
    Creates tasks with enriched metadata including:
    - Source tracking (support embed)
    - Reporter information
    - Auto-answer details
    - Duplicate references
    """
    
    def __init__(self):
        """Initialize SupportSubmitService"""
        pass
    
    def submit(
        self,
        item_id: str,
        title: str,
        description: str,
        task_type: str = 'support',
        reporter_email: Optional[str] = None,
        reporter_referrer: Optional[str] = None,
        auto_answer: Optional[Dict[str, Any]] = None,
        duplicate_of_task_id: Optional[str] = None,
        client_fingerprint: Optional[str] = None,
        chat_history: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Submit a support request as a task
        
        Args:
            item_id: UUID of the item
            title: Task title
            description: Task description
            task_type: Type of task (support, bug, feature, etc.)
            reporter_email: Email of reporter (optional)
            reporter_referrer: Referrer URL (optional)
            auto_answer: Dict with 'offered', 'accepted', 'summary' (optional)
            duplicate_of_task_id: UUID of potential duplicate task (optional)
            client_fingerprint: Hash for rate limiting (optional)
            chat_history: Recent chat messages to include in description (optional)
        
        Returns:
            {
                'success': bool,
                'task_id': str,
                'url': str,
                'error': str (if success=False)
            }
        """
        from main.models import Item, Task
        
        try:
            # Get the item
            try:
                item = Item.objects.get(id=item_id)
            except Item.DoesNotExist:
                logger.error(f"Item not found: {item_id}")
                return {
                    'success': False,
                    'error': 'Item not found'
                }
            
            # Enrich description with metadata
            enriched_description = self._enrich_description(
                description=description,
                chat_history=chat_history,
                auto_answer=auto_answer,
                duplicate_of_task_id=duplicate_of_task_id
            )
            
            # Create task
            task = Task.objects.create(
                item=item,
                title=title,
                description=enriched_description,
                type=task_type,
                status='new',
                source='support',
                reporter_email=reporter_email or '',
                reporter_referrer=reporter_referrer or '',
                auto_answer_offered=auto_answer is not None and auto_answer.get('offered', False),
                auto_answer_accepted=auto_answer is not None and auto_answer.get('accepted', False),
                auto_answer_text=auto_answer.get('summary', '') if auto_answer else '',
                duplicate_of_task_id=duplicate_of_task_id if duplicate_of_task_id else None,
                client_fingerprint=client_fingerprint or ''
            )
            
            logger.info(f"Created support task {task.id} for item {item_id}")
            
            return {
                'success': True,
                'task_id': str(task.id),
                'url': f'/items/{item_id}/tasks/',  # Redirect to task list
                'task': {
                    'id': str(task.id),
                    'title': task.title,
                    'type': task.type,
                    'status': task.status,
                    'created_at': task.created_at.isoformat()
                }
            }
        
        except Exception as e:
            logger.error(f"Error creating support task: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to create task: {str(e)}'
            }
    
    def _enrich_description(
        self,
        description: str,
        chat_history: Optional[list] = None,
        auto_answer: Optional[Dict[str, Any]] = None,
        duplicate_of_task_id: Optional[str] = None
    ) -> str:
        """
        Enrich task description with metadata
        
        Args:
            description: Original description
            chat_history: Recent chat messages (optional)
            auto_answer: Auto-answer details (optional)
            duplicate_of_task_id: UUID of potential duplicate (optional)
        
        Returns:
            Enriched markdown description
        """
        parts = []
        
        # Original description
        if description:
            parts.append("## Beschreibung\n\n" + description)
        
        # Chat history (last 3 messages)
        if chat_history and len(chat_history) > 0:
            parts.append("\n\n## Chat-Verlauf\n")
            for msg in chat_history[-3:]:  # Last 3 messages
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                parts.append(f"\n**{role.capitalize()}:** {content}")
        
        # Auto-answer that was offered
        if auto_answer and auto_answer.get('offered'):
            accepted = auto_answer.get('accepted', False)
            summary = auto_answer.get('summary', '')
            
            parts.append("\n\n## Automatische Antwort\n")
            parts.append(f"**Status:** {'✓ Akzeptiert' if accepted else '✗ Abgelehnt'}\n")
            if summary:
                parts.append(f"\n{summary}")
        
        # Similar tasks
        if duplicate_of_task_id:
            parts.append("\n\n## Ähnliche Tasks\n")
            parts.append(f"Möglicherweise Duplikat von: `/tasks/{duplicate_of_task_id}/`")
        
        # Add metadata footer
        parts.append("\n\n---\n*Erstellt via Support-Formular*")
        
        return '\n'.join(parts)
