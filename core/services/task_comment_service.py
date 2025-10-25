"""
Task Comment Service for IdeaGraph

This module provides utilities for creating automated comments on tasks,
particularly for GitHub integration events.
"""

import logging
from typing import Optional
from django.utils import timezone


logger = logging.getLogger('task_comment_service')


class TaskCommentService:
    """
    Service for creating automated task comments
    """
    
    # AI Agent Bot configuration
    AI_AGENT_BOT_USERNAME = 'ai-agent-bot'
    AI_AGENT_BOT_NAME = 'AI Agent Bot'
    AI_AGENT_BOT_EMAIL = 'ai-agent-bot@ideagraph.local'
    AI_AGENT_BOT_AVATAR_URL = '🤖'  # Robot emoji as fallback, can be replaced with actual URL
    
    @classmethod
    def get_or_create_ai_agent_bot(cls):
        """
        Get or create the AI Agent Bot user
        
        Returns:
            User: The AI Agent Bot user instance
        """
        from main.models import User
        
        try:
            bot_user = User.objects.get(username=cls.AI_AGENT_BOT_USERNAME)
            logger.debug(f"AI Agent Bot user found: {bot_user.id}")
        except User.DoesNotExist:
            # Create the AI Agent Bot user
            bot_user = User.objects.create(
                username=cls.AI_AGENT_BOT_USERNAME,
                email=cls.AI_AGENT_BOT_EMAIL,
                first_name='AI Agent',
                last_name='Bot',
                role='user',
                is_active=True,
                auth_type='local',
                avatar_url=cls.AI_AGENT_BOT_AVATAR_URL
            )
            logger.info(f"AI Agent Bot user created: {bot_user.id}")
        
        return bot_user
    
    @classmethod
    def create_github_issue_created_comment(cls, task, issue_number: int, issue_url: str) -> Optional[object]:
        """
        Create a comment when a GitHub issue is created from a task
        
        Args:
            task: Task instance
            issue_number: GitHub issue number
            issue_url: URL to the GitHub issue
            
        Returns:
            TaskComment instance or None if creation fails
        """
        from main.models import TaskComment
        
        try:
            # Get or create AI Agent Bot user
            bot_user = cls.get_or_create_ai_agent_bot()
            
            # Create comment text
            comment_text = (
                f"🚀 **GitHub Issue Created**\n\n"
                f"A GitHub issue has been created for this task:\n"
                f"- Issue: #{issue_number}\n"
                f"- URL: {issue_url}"
            )
            
            # Create the comment
            comment = TaskComment.objects.create(
                task=task,
                author=bot_user,
                author_name=cls.AI_AGENT_BOT_NAME,
                text=comment_text,
                source='agent'
            )
            
            logger.info(f"GitHub issue created comment added to task {task.id}")
            return comment
            
        except Exception as e:
            logger.error(f"Failed to create GitHub issue created comment: {str(e)}")
            return None
    
    @classmethod
    def create_github_issue_completed_comment(cls, task, issue_number: int) -> Optional[object]:
        """
        Create a comment when a GitHub issue is marked as completed
        
        Args:
            task: Task instance
            issue_number: GitHub issue number
            
        Returns:
            TaskComment instance or None if creation fails
        """
        from main.models import TaskComment
        
        try:
            # Get or create AI Agent Bot user
            bot_user = cls.get_or_create_ai_agent_bot()
            
            # Create comment text
            comment_text = (
                f"✅ **GitHub Issue Completed**\n\n"
                f"The GitHub issue #{issue_number} has been closed and this task has been marked as done."
            )
            
            # Create the comment
            comment = TaskComment.objects.create(
                task=task,
                author=bot_user,
                author_name=cls.AI_AGENT_BOT_NAME,
                text=comment_text,
                source='agent'
            )
            
            logger.info(f"GitHub issue completed comment added to task {task.id}")
            return comment
            
        except Exception as e:
            logger.error(f"Failed to create GitHub issue completed comment: {str(e)}")
            return None
