"""
Email Reply RAG Service for IdeaGraph

This service implements a 3-tier retrieval system for generating AI email replies:
- Tier A: Thread context (recent comments in the same task)
- Tier B: Item context (tasks, comments, files in the same item)
- Tier C: Global context (similar cases across the system)
"""

import logging
import hashlib
import re
from typing import List, Dict, Any, Optional
from django.core.cache import cache
from main.models import TaskComment, Task, Item, ItemFile, TaskFile

logger = logging.getLogger('email_reply_rag')


class EmailReplyRAGService:
    """
    RAG Service for email reply generation with 3-tier retrieval
    """
    
    # Configuration
    TIER_A_MAX_COMMENTS = 10  # Last N comments in thread
    TIER_B_TOP_N = 5  # Top N similar objects in item
    TIER_C_TOP_N = 3  # Top N similar cases globally
    MAX_SNIPPET_LENGTH = 500  # Characters per snippet
    CACHE_TTL = 600  # 10 minutes in seconds
    
    # PII/Secret patterns to mask
    PII_PATTERNS = [
        (r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[EMAIL]'),  # Email addresses (except in headers)
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]'),  # Phone numbers
        (r'\b\d{3,4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD]'),  # Credit cards
        (r'\b(?:password|token|secret|api[_-]?key|bearer)[\s:=]+[\w\-\.]+\b', '[SECRET]', re.IGNORECASE),
    ]
    
    def __init__(self, settings=None):
        """
        Initialize RAG service with settings
        
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
    
    def _mask_pii(self, text: str) -> str:
        """
        Mask PII and sensitive data in text
        
        Args:
            text: Text to mask
            
        Returns:
            Masked text
        """
        masked = text
        for pattern, replacement, *flags in self.PII_PATTERNS:
            flag = flags[0] if flags else 0
            masked = re.sub(pattern, replacement, masked, flags=flag)
        return masked
    
    def _truncate_snippet(self, text: str, max_length: int = None) -> str:
        """
        Truncate text to maximum length while preserving word boundaries
        
        Args:
            text: Text to truncate
            max_length: Maximum length (default: MAX_SNIPPET_LENGTH)
            
        Returns:
            Truncated text
        """
        if max_length is None:
            max_length = self.MAX_SNIPPET_LENGTH
        
        if len(text) <= max_length:
            return text
        
        # Truncate at word boundary
        truncated = text[:max_length].rsplit(' ', 1)[0]
        return truncated + '...'
    
    def _generate_cache_key(self, comment_id: str, item_id: str) -> str:
        """
        Generate cache key for retrieval results
        
        Args:
            comment_id: Comment UUID
            item_id: Item UUID
            
        Returns:
            Cache key string
        """
        key_data = f"{comment_id}:{item_id}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"rag:email_reply:{key_hash}"
    
    def retrieve_tier_a(self, task: Task, current_comment: TaskComment) -> List[Dict[str, Any]]:
        """
        Tier A: Retrieve recent comments from the same task/thread
        Email comments are weighted higher
        
        Args:
            task: Task object
            current_comment: Current comment being replied to
            
        Returns:
            List of context items with tier marker
        """
        logger.info(f"Retrieving Tier A context for task {task.id}")
        
        # Get recent comments, excluding the current one
        recent_comments = task.comments.exclude(id=current_comment.id).order_by('-created_at')[:self.TIER_A_MAX_COMMENTS]
        
        results = []
        for idx, comment in enumerate(recent_comments, 1):
            # Give email comments higher priority in ordering
            weight = 2 if comment.source == 'email' else 1
            
            # Build snippet
            snippet = comment.text
            if comment.source == 'email' and comment.email_subject:
                snippet = f"Subject: {comment.email_subject}\n\n{snippet}"
            
            # Mask and truncate
            snippet = self._mask_pii(snippet)
            snippet = self._truncate_snippet(snippet)
            
            results.append({
                'tier': 'A',
                'marker': f'#A-{idx}',
                'type': 'comment',
                'id': str(comment.id),
                'excerpt': snippet,
                'author': comment.get_author_display(),
                'created_at': comment.created_at.isoformat(),
                'weight': weight,
                'source': comment.source
            })
        
        logger.info(f"Retrieved {len(results)} Tier A items")
        return results
    
    def retrieve_tier_b(self, item: Item, task: Task, exclude_task_id: str = None) -> List[Dict[str, Any]]:
        """
        Tier B: Retrieve content from the same item (tasks, comments, files)
        
        Args:
            item: Item object
            task: Current task
            exclude_task_id: Task ID to exclude (current task)
            
        Returns:
            List of context items with tier marker
        """
        logger.info(f"Retrieving Tier B context for item {item.id}")
        
        results = []
        idx = 1
        
        # Add item description
        if item.description:
            snippet = self._mask_pii(item.description)
            snippet = self._truncate_snippet(snippet)
            results.append({
                'tier': 'B',
                'marker': f'#B-{idx}',
                'type': 'item',
                'id': str(item.id),
                'title': item.title,
                'excerpt': snippet,
                'created_at': item.created_at.isoformat(),
            })
            idx += 1
        
        # Add other tasks in the item (limited)
        other_tasks = item.tasks.exclude(id=task.id).order_by('-created_at')[:3]
        for other_task in other_tasks:
            if other_task.description:
                snippet = f"Task: {other_task.title}\n{other_task.description}"
                snippet = self._mask_pii(snippet)
                snippet = self._truncate_snippet(snippet)
                results.append({
                    'tier': 'B',
                    'marker': f'#B-{idx}',
                    'type': 'task',
                    'id': str(other_task.id),
                    'title': other_task.title,
                    'excerpt': snippet,
                    'created_at': other_task.created_at.isoformat(),
                })
                idx += 1
        
        # Limit Tier B results
        results = results[:self.TIER_B_TOP_N]
        
        logger.info(f"Retrieved {len(results)} Tier B items")
        return results
    
    def retrieve_tier_c(self, item: Item, task: Task) -> List[Dict[str, Any]]:
        """
        Tier C: Retrieve similar cases globally (placeholder for now)
        This would use semantic search in a production system
        
        Args:
            item: Item object
            task: Current task
            
        Returns:
            List of context items with tier marker
        """
        logger.info(f"Retrieving Tier C context for item {item.id}")
        
        results = []
        
        # In a full implementation, this would use Weaviate semantic search
        # For now, we'll return similar items by tags
        if item.tags.exists():
            item_tags = set(item.tags.values_list('id', flat=True))
            
            # Find items with overlapping tags
            similar_items = Item.objects.filter(
                tags__in=item_tags
            ).exclude(
                id=item.id
            ).distinct()[:self.TIER_C_TOP_N]
            
            for idx, similar_item in enumerate(similar_items, 1):
                if similar_item.description:
                    snippet = self._mask_pii(similar_item.description)
                    snippet = self._truncate_snippet(snippet, max_length=300)  # Shorter for global context
                    results.append({
                        'tier': 'C',
                        'marker': f'#C-{idx}',
                        'type': 'item',
                        'id': str(similar_item.id),
                        'title': similar_item.title,
                        'excerpt': snippet,
                        'created_at': similar_item.created_at.isoformat(),
                    })
        
        logger.info(f"Retrieved {len(results)} Tier C items")
        return results
    
    def retrieve_context(
        self, 
        comment: TaskComment, 
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve full 3-tier context for email reply generation
        
        Args:
            comment: TaskComment object (inbound email)
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Dictionary with context and metadata
        """
        task = comment.task
        item = task.item
        
        # Check cache
        cache_key = self._generate_cache_key(str(comment.id), str(item.id))
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                logger.info(f"Using cached context for comment {comment.id}")
                return cached
        
        # Retrieve all tiers
        tier_a = self.retrieve_tier_a(task, comment)
        tier_b = self.retrieve_tier_b(item, task)
        tier_c = self.retrieve_tier_c(item, task)
        
        # Combine results
        all_sources = tier_a + tier_b + tier_c
        
        result = {
            'sources': all_sources,
            'tier_a_count': len(tier_a),
            'tier_b_count': len(tier_b),
            'tier_c_count': len(tier_c),
            'total_count': len(all_sources),
            'comment_id': str(comment.id),
            'task_id': str(task.id),
            'item_id': str(item.id),
        }
        
        # Cache results
        if use_cache:
            cache.set(cache_key, result, self.CACHE_TTL)
            logger.info(f"Cached context for comment {comment.id} (TTL: {self.CACHE_TTL}s)")
        
        return result
    
    def format_context_for_kigate(self, context: Dict[str, Any]) -> str:
        """
        Format retrieved context for KiGate agent
        
        Args:
            context: Context dictionary from retrieve_context
            
        Returns:
            Formatted context string with markers
        """
        sources = context['sources']
        
        lines = []
        for source in sources:
            marker = source['marker']
            excerpt = source['excerpt']
            
            # Add metadata if available
            metadata = []
            if 'title' in source:
                metadata.append(f"Title: {source['title']}")
            if 'author' in source:
                metadata.append(f"Author: {source['author']}")
            
            # Format source
            if metadata:
                lines.append(f"[{marker}] {' | '.join(metadata)}")
                lines.append(excerpt)
            else:
                lines.append(f"[{marker}] {excerpt}")
            
            lines.append('')  # Empty line between sources
        
        return '\n'.join(lines)
