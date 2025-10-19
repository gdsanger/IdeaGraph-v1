"""
Auto-Task Creator Service for IdeaGraph

This service automatically creates tasks from error analyses
and optionally creates GitHub issues for confirmed errors.
"""

from typing import Optional, List
from django.utils import timezone
from core.logger_config import get_logger
from core.services.github_service import GitHubService

logger = get_logger('auto_task_creator_service')


class AutoTaskCreatorService:
    """Service to automatically create tasks from error analyses"""
    
    def __init__(self):
        """Initialize the auto-task creator service"""
        # GitHub service is optional - only used for issue creation
        try:
            self.github_service = GitHubService()
        except Exception as e:
            logger.warning(f"GitHub service not available: {e}")
            self.github_service = None
        
        logger.info("Auto-Task Creator Service initialized")
    
    def create_task_from_analysis(
        self,
        error_analysis,
        assigned_to=None,
        create_github_issue: bool = False
    ) -> Optional['Task']:
        """
        Create a task from an error analysis
        
        Args:
            error_analysis: ErrorAnalysis model instance
            assigned_to: User to assign the task to (optional)
            create_github_issue: Whether to create a GitHub issue
            
        Returns:
            Created Task instance or None
        """
        from main.models import Task, Tag
        
        try:
            # Build task title
            title = self._generate_task_title(error_analysis)
            
            # Build task description
            description = self._generate_task_description(error_analysis)
            
            # Create the task
            task = Task.objects.create(
                title=title,
                description=description,
                status='new',
                assigned_to=assigned_to,
                ai_generated=True,
            )
            
            # Add tags
            self._add_tags_to_task(task, error_analysis)
            
            # Link to error analysis
            error_analysis.task = task
            error_analysis.status = 'task_created'
            error_analysis.save()
            
            logger.info(f"Created task {task.id} from error analysis {error_analysis.id}")
            
            # Create GitHub issue if requested
            if create_github_issue:
                self._create_github_issue(task, error_analysis)
            
            return task
            
        except Exception as e:
            logger.error(f"Error creating task from analysis: {e}", exc_info=True)
            return None
    
    def _generate_task_title(self, error_analysis) -> str:
        """
        Generate a task title from error analysis
        
        Args:
            error_analysis: ErrorAnalysis instance
            
        Returns:
            Task title string
        """
        log_entry = error_analysis.log_entry
        
        # Use AI summary if available and concise
        if error_analysis.summary and len(error_analysis.summary) < 100:
            return f"🐛 {error_analysis.summary}"
        
        # Use exception type if available
        if log_entry.exception_type:
            return f"🐛 Fix {log_entry.exception_type}"
        
        # Use truncated message
        message = log_entry.message[:80]
        if len(log_entry.message) > 80:
            message += "..."
        
        return f"🐛 {message}"
    
    def _generate_task_description(self, error_analysis) -> str:
        """
        Generate task description from error analysis
        
        Args:
            error_analysis: ErrorAnalysis instance
            
        Returns:
            Task description in markdown format
        """
        log_entry = error_analysis.log_entry
        
        description_parts = [
            "# 🐛 Fehlerbehebung",
            "",
            "Dieser Task wurde automatisch aus einem Fehler-Log erstellt.",
            "",
            "## 📊 Fehler-Details",
            "",
            f"- **Severity:** {error_analysis.get_severity_display()}",
            f"- **Source:** {log_entry.get_source_display()}",
            f"- **Level:** {log_entry.level}",
            f"- **Logger:** {log_entry.logger_name}",
            f"- **Timestamp:** {log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **AI Confidence:** {error_analysis.ai_confidence:.0%}",
            "",
        ]
        
        # Add AI analysis
        if error_analysis.summary:
            description_parts.extend([
                "## 🤖 KI-Analyse",
                "",
                f"**Zusammenfassung:** {error_analysis.summary}",
                "",
            ])
        
        if error_analysis.root_cause:
            description_parts.extend([
                f"**Ursache:** {error_analysis.root_cause}",
                "",
            ])
        
        if error_analysis.recommended_action:
            description_parts.extend([
                "## ✅ Empfohlene Maßnahmen",
                "",
                error_analysis.recommended_action,
                "",
            ])
        
        # Add original error message
        description_parts.extend([
            "## 📝 Original-Fehlermeldung",
            "",
            f"```",
            log_entry.message,
            "```",
            "",
        ])
        
        # Add exception info if available
        if log_entry.exception_type:
            description_parts.extend([
                "## 🔍 Exception Details",
                "",
                f"**Type:** `{log_entry.exception_type}`",
                "",
            ])
            
            if log_entry.exception_value:
                description_parts.extend([
                    f"**Value:** {log_entry.exception_value}",
                    "",
                ])
            
            if log_entry.stack_trace:
                # Limit stack trace length
                stack_trace = log_entry.stack_trace[:2000]
                if len(log_entry.stack_trace) > 2000:
                    stack_trace += "\n... (truncated)"
                
                description_parts.extend([
                    "**Stack Trace:**",
                    "```",
                    stack_trace,
                    "```",
                    "",
                ])
        
        # Add link to log entry
        description_parts.extend([
            "---",
            f"**Log Entry ID:** `{log_entry.id}`",
            f"**Analysis ID:** `{error_analysis.id}`",
        ])
        
        return "\n".join(description_parts)
    
    def _add_tags_to_task(self, task, error_analysis):
        """Add relevant tags to the task"""
        from main.models import Tag
        
        tag_names = ['bug', 'auto-generated']
        
        # Add severity tag
        severity = error_analysis.severity
        if severity in ['high', 'critical']:
            tag_names.append('urgent')
        
        # Add source tag
        source = error_analysis.log_entry.source
        if source == 'sentry':
            tag_names.append('sentry')
        
        # Create or get tags and add to task
        for tag_name in tag_names:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            task.tags.add(tag)
        
        logger.debug(f"Added tags {tag_names} to task {task.id}")
    
    def _create_github_issue(self, task, error_analysis):
        """
        Create a GitHub issue for the task
        
        Args:
            task: Task instance
            error_analysis: ErrorAnalysis instance
        """
        if not self.github_service:
            logger.warning("GitHub service not available, skipping issue creation")
            return
        
        try:
            # Build issue body
            issue_body = task.description + "\n\n---\n*Automatisch erstellt von IdeaGraph*"
            
            # Get labels
            labels = ['bug', 'automated']
            if error_analysis.severity in ['high', 'critical']:
                labels.append('priority:high')
            
            # Create the issue
            issue = self.github_service.create_issue(
                title=task.title,
                body=issue_body,
                labels=labels,
            )
            
            if issue:
                # Update task with GitHub info
                task.github_issue_id = issue.get('number')
                task.github_issue_url = issue.get('html_url')
                task.github_synced_at = timezone.now()
                task.save()
                
                # Update error analysis
                error_analysis.github_issue_url = issue.get('html_url')
                error_analysis.status = 'issue_created'
                error_analysis.save()
                
                logger.info(f"Created GitHub issue #{issue.get('number')} for task {task.id}")
            else:
                logger.error(f"Failed to create GitHub issue for task {task.id}")
                
        except Exception as e:
            logger.error(f"Error creating GitHub issue: {e}", exc_info=True)
    
    def process_pending_analyses(
        self,
        min_severity: str = 'medium',
        min_confidence: float = 0.7,
        auto_create_github: bool = False,
        limit: int = 10
    ) -> List['Task']:
        """
        Process pending error analyses and create tasks
        
        Args:
            min_severity: Minimum severity to process ('low', 'medium', 'high', 'critical')
            min_confidence: Minimum AI confidence threshold (0.0-1.0)
            auto_create_github: Automatically create GitHub issues for high/critical errors
            limit: Maximum number of analyses to process
            
        Returns:
            List of created tasks
        """
        from main.models import ErrorAnalysis
        
        severity_priority = {
            'low': 0,
            'medium': 1,
            'high': 2,
            'critical': 3,
        }
        
        min_priority = severity_priority.get(min_severity, 1)
        
        # Get pending analyses that meet criteria
        analyses = ErrorAnalysis.objects.filter(
            status='pending',
            is_actionable=True,
            ai_confidence__gte=min_confidence,
        ).order_by('-created_at')[:limit * 2]  # Get more to filter by severity
        
        # Filter by severity
        analyses = [
            a for a in analyses
            if severity_priority.get(a.severity, 0) >= min_priority
        ][:limit]
        
        logger.info(f"Processing {len(analyses)} pending error analyses")
        
        created_tasks = []
        
        for analysis in analyses:
            # Determine if GitHub issue should be created
            create_github = auto_create_github and analysis.severity in ['high', 'critical']
            
            # Create task
            task = self.create_task_from_analysis(
                analysis,
                create_github_issue=create_github
            )
            
            if task:
                created_tasks.append(task)
        
        logger.info(f"Created {len(created_tasks)} tasks from error analyses")
        return created_tasks
    
    def approve_and_create_task(
        self,
        error_analysis,
        user,
        create_github_issue: bool = False
    ) -> Optional['Task']:
        """
        Manually approve an error analysis and create a task
        
        Args:
            error_analysis: ErrorAnalysis instance
            user: User approving the analysis
            create_github_issue: Whether to create a GitHub issue
            
        Returns:
            Created Task or None
        """
        # Mark as approved
        error_analysis.status = 'approved'
        error_analysis.reviewed_by = user
        error_analysis.reviewed_at = timezone.now()
        error_analysis.save()
        
        logger.info(f"Error analysis {error_analysis.id} approved by {user.username}")
        
        # Create task
        return self.create_task_from_analysis(
            error_analysis,
            assigned_to=user,
            create_github_issue=create_github_issue
        )
