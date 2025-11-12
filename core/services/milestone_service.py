"""
Milestone Service for Actions API

Provides milestone operations including AI-powered summaries and changelogs.
"""
import logging
from typing import List, Dict, Any, Optional
from django.db.models import Q
from main.models import Milestone, Item
from core.services.kigate_service import KiGateService, KiGateServiceError

logger = logging.getLogger(__name__)


class MilestoneServiceError(Exception):
    """Exception for MilestoneService errors"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class MilestoneService:
    """
    Milestone Service
    
    Provides:
    - list_milestones: List milestones with filtering
    - get_milestone: Get single milestone details
    - summarize_milestone: Generate AI summary from context objects
    - changelog_milestone: Generate changelog markdown
    """
    
    def __init__(self, settings=None):
        """Initialize the service"""
        self.settings = settings
        try:
            self.kigate_service = KiGateService(settings=settings)
        except KiGateServiceError as e:
            logger.warning(f"KiGate service not available: {e.message}")
            self.kigate_service = None
    
    def list_milestones(
        self,
        item_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Milestone]:
        """
        List milestones with optional filtering
        
        Args:
            item_id: Filter by item ID
            status: Filter by status (planned, in_progress, completed)
            limit: Maximum number of results
        
        Returns:
            List of Milestone objects
        """
        queryset = Milestone.objects.select_related('item').prefetch_related('tasks')
        
        # Apply filters
        if item_id:
            queryset = queryset.filter(item_id=item_id)
        
        if status:
            queryset = queryset.filter(status=status)
        
        # Order by due date
        queryset = queryset.order_by('due_date')
        
        return list(queryset[:limit])
    
    def get_milestone(self, milestone_id: str) -> Milestone:
        """
        Get single milestone by ID
        
        Args:
            milestone_id: Milestone UUID
        
        Returns:
            Milestone object
        
        Raises:
            MilestoneServiceError: If milestone not found
        """
        try:
            return Milestone.objects.select_related('item').prefetch_related(
                'tasks', 'context_objects'
            ).get(id=milestone_id)
        except Milestone.DoesNotExist:
            raise MilestoneServiceError(
                f"Milestone not found: {milestone_id}",
                details="No milestone exists with this ID"
            )
    
    def summarize_milestone(self, milestone_id: str) -> Dict[str, Any]:
        """
        Generate AI summary for milestone from context objects
        
        Uses KiGate agents to analyze context objects and generate summary
        
        Args:
            milestone_id: Milestone UUID
        
        Returns:
            Dictionary with summary text and metadata
        
        Raises:
            MilestoneServiceError: If summarization fails
        """
        try:
            milestone = self.get_milestone(milestone_id)
            
            # Check if KiGate is available
            if not self.kigate_service:
                raise MilestoneServiceError(
                    "AI summarization not available",
                    details="KiGate service is not configured"
                )
            
            # Get context objects
            context_objects = milestone.context_objects.all()
            
            if not context_objects:
                return {
                    'summary': 'No context objects available for summarization.',
                    'context_count': 0
                }
            
            # Prepare context for AI
            context_data = []
            for ctx in context_objects:
                context_data.append({
                    'type': ctx.type,
                    'title': ctx.title,
                    'content': ctx.content[:2000]  # Limit content length
                })
            
            # Call KiGate summarization agent
            # Agent name: 'milestone-summarizer' or similar
            try:
                result = self.kigate_service.execute_agent(
                    agent_name='milestone-summarizer',
                    parameters={
                        'milestone_name': milestone.name,
                        'milestone_description': milestone.description,
                        'context_objects': context_data
                    }
                )
                
                summary_text = result.get('summary', '')
                
                # Update milestone summary
                milestone.summary = summary_text
                milestone.save(update_fields=['summary'])
                
                return {
                    'summary': summary_text,
                    'context_count': len(context_objects),
                    'agent_used': result.get('agent_name', 'milestone-summarizer')
                }
                
            except KiGateServiceError as e:
                logger.error(f"KiGate summarization failed: {e.message}")
                raise MilestoneServiceError(
                    "AI summarization failed",
                    details=e.details or str(e)
                )
        
        except Milestone.DoesNotExist:
            raise MilestoneServiceError(
                f"Milestone not found: {milestone_id}"
            )
        except MilestoneServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in summarize_milestone: {str(e)}")
            raise MilestoneServiceError(
                "Summarization failed",
                details=str(e)
            )
    
    def changelog_milestone(self, milestone_id: str) -> Dict[str, Any]:
        """
        Generate changelog markdown for milestone
        
        Uses KiGate agents to generate structured changelog from tasks and context
        
        Args:
            milestone_id: Milestone UUID
        
        Returns:
            Dictionary with changelog markdown and metadata
        
        Raises:
            MilestoneServiceError: If changelog generation fails
        """
        try:
            milestone = self.get_milestone(milestone_id)
            
            # Check if KiGate is available
            if not self.kigate_service:
                raise MilestoneServiceError(
                    "Changelog generation not available",
                    details="KiGate service is not configured"
                )
            
            # Get tasks
            tasks = milestone.tasks.all()
            
            # Prepare task data for AI
            task_data = []
            for task in tasks:
                task_data.append({
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'type': task.type
                })
            
            # Call KiGate changelog generator agent
            try:
                result = self.kigate_service.execute_agent(
                    agent_name='changelog-generator',
                    parameters={
                        'milestone_name': milestone.name,
                        'milestone_description': milestone.description,
                        'tasks': task_data,
                        'summary': milestone.summary
                    }
                )
                
                changelog_markdown = result.get('changelog', '')
                
                # Update milestone changelog
                milestone.changelog = changelog_markdown
                milestone.save(update_fields=['changelog'])
                
                return {
                    'changelog': changelog_markdown,
                    'task_count': len(tasks),
                    'agent_used': result.get('agent_name', 'changelog-generator')
                }
                
            except KiGateServiceError as e:
                logger.error(f"KiGate changelog generation failed: {e.message}")
                raise MilestoneServiceError(
                    "Changelog generation failed",
                    details=e.details or str(e)
                )
        
        except Milestone.DoesNotExist:
            raise MilestoneServiceError(
                f"Milestone not found: {milestone_id}"
            )
        except MilestoneServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in changelog_milestone: {str(e)}")
            raise MilestoneServiceError(
                "Changelog generation failed",
                details=str(e)
            )
