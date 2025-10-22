"""
Milestone Knowledge Hub Service for IdeaGraph

This module provides functionality for managing milestone knowledge hubs:
- Adding and managing context objects (files, emails, transcripts, notes)
- AI-powered summarization using KiGate text-summary-agent
- Task derivation using KiGate text-analysis-task-derivation-agent
- Weaviate integration for semantic search
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.services.kigate_service import KiGateService, KiGateServiceError
from core.services.weaviate_sync_service import WeaviateItemSyncService, WeaviateItemSyncServiceError


logger = logging.getLogger('milestone_knowledge_service')


class MilestoneKnowledgeServiceError(Exception):
    """Base exception for Milestone Knowledge Service errors"""
    
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


class MilestoneKnowledgeService:
    """
    Milestone Knowledge Hub Service
    
    Provides methods for:
    - Adding context objects to milestones
    - Generating AI summaries via KiGate
    - Deriving tasks from context using AI
    - Syncing milestone knowledge to Weaviate
    """
    
    def __init__(self, settings=None):
        """
        Initialize MilestoneKnowledgeService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise MilestoneKnowledgeServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise MilestoneKnowledgeServiceError("No settings found in database")
    
    def add_context_object(
        self,
        milestone,
        context_type: str,
        title: str,
        content: str = "",
        source_id: str = "",
        url: str = "",
        user = None,
        auto_analyze: bool = True
    ) -> Dict[str, Any]:
        """
        Add a context object to a milestone
        
        Args:
            milestone: Milestone instance
            context_type: Type of context ('file', 'email', 'transcript', 'note')
            title: Title of the context object
            content: Text content of the context object
            source_id: Optional source identifier (GUID or path)
            url: Optional URL to the source
            user: User who added the context
            auto_analyze: Whether to automatically analyze the context with AI
        
        Returns:
            Dictionary with context object data and analysis results
        
        Raises:
            MilestoneKnowledgeServiceError: If context addition fails
        """
        from main.models import MilestoneContextObject
        
        try:
            # Validate context type
            valid_types = ['file', 'email', 'transcript', 'note']
            if context_type not in valid_types:
                raise MilestoneKnowledgeServiceError(
                    f"Invalid context type. Must be one of: {', '.join(valid_types)}"
                )
            
            # Create context object
            context_obj = MilestoneContextObject.objects.create(
                milestone=milestone,
                type=context_type,
                title=title,
                content=content,
                source_id=source_id,
                url=url,
                uploaded_by=user
            )
            
            logger.info(f"Created context object {context_obj.id} for milestone {milestone.id}")
            
            result = {
                'success': True,
                'context_object_id': str(context_obj.id),
                'title': context_obj.title,
                'type': context_obj.type
            }
            
            # Auto-analyze if requested and content is available
            if auto_analyze and content.strip():
                try:
                    analysis_result = self.analyze_context_object(context_obj)
                    result['analysis'] = analysis_result
                except Exception as e:
                    logger.warning(f"Auto-analysis failed for context {context_obj.id}: {str(e)}")
                    result['analysis_error'] = str(e)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to add context object: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to add context object",
                details=str(e)
            )
    
    def analyze_context_object(self, context_obj) -> Dict[str, Any]:
        """
        Analyze a context object using KiGate AI agents
        
        This method:
        1. Generates a summary using text-summary-agent
        2. Derives tasks using text-analysis-task-derivation-agent
        3. Updates the context object with results
        
        Args:
            context_obj: MilestoneContextObject instance
        
        Returns:
            Dictionary with analysis results
        
        Raises:
            MilestoneKnowledgeServiceError: If analysis fails
        """
        try:
            if not context_obj.content.strip():
                raise MilestoneKnowledgeServiceError(
                    "Cannot analyze empty content"
                )
            
            kigate = KiGateService(self.settings)
            
            # Get default model from settings
            default_model = getattr(self.settings, 'openai_default_model', 'gpt-4') or 'gpt-4'
            
            # Step 1: Generate summary using text-summary-agent
            logger.info(f"Generating summary for context object {context_obj.id}")
            summary_result = kigate.execute_agent(
                agent_name='text-summary-agent',
                provider='openai',
                model=default_model,
                message=context_obj.content,
                user_id='system',
                parameters={
                    'max_length': 500
                }
            )
            
            summary = ""
            if summary_result.get('success') and 'result' in summary_result:
                if isinstance(summary_result['result'], dict):
                    summary = summary_result['result'].get('summary', '')
                else:
                    summary = str(summary_result['result'])
            
            # Step 2: Derive tasks using text-analysis-task-derivation-agent
            logger.info(f"Deriving tasks for context object {context_obj.id}")
            
            # Build message with context
            task_message = f"Milestone: {context_obj.milestone.name}\n\nContent:\n{context_obj.content}"
            
            task_derivation_result = kigate.execute_agent(
                agent_name='text-analysis-task-derivation-agent',
                provider='openai',
                model=default_model,
                message=task_message,
                user_id='system'
            )
            
            derived_tasks = []
            if task_derivation_result.get('success') and 'result' in task_derivation_result:
                result_data = task_derivation_result['result']
                if isinstance(result_data, dict):
                    derived_tasks = result_data.get('tasks', [])
                elif isinstance(result_data, list):
                    derived_tasks = result_data
            
            # Update context object
            context_obj.summary = summary
            context_obj.derived_tasks = derived_tasks
            context_obj.analyzed = True
            context_obj.save()
            
            logger.info(f"Analysis complete for context object {context_obj.id}: "
                       f"{len(derived_tasks)} tasks derived")
            
            return {
                'success': True,
                'summary': summary,
                'derived_tasks': derived_tasks,
                'task_count': len(derived_tasks)
            }
            
        except KiGateServiceError as e:
            logger.error(f"KiGate error during analysis: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "AI analysis failed",
                details=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to analyze context object: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to analyze context object",
                details=str(e)
            )
    
    def generate_milestone_summary(self, milestone) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of a milestone from all context objects
        
        Args:
            milestone: Milestone instance
        
        Returns:
            Dictionary with summary result
        
        Raises:
            MilestoneKnowledgeServiceError: If summary generation fails
        """
        try:
            # Collect all context from the milestone
            context_objects = milestone.context_objects.all()
            
            if not context_objects.exists():
                return {
                    'success': True,
                    'summary': '',
                    'message': 'No context objects to summarize'
                }
            
            # Combine all content and summaries
            combined_content = []
            for ctx in context_objects:
                if ctx.summary:
                    combined_content.append(f"[{ctx.get_type_display()}] {ctx.title}: {ctx.summary}")
                elif ctx.content:
                    combined_content.append(f"[{ctx.get_type_display()}] {ctx.title}: {ctx.content[:500]}")
            
            full_context = "\n\n".join(combined_content)
            
            if not full_context.strip():
                return {
                    'success': True,
                    'summary': '',
                    'message': 'No content available to summarize'
                }
            
            # Generate overall summary using KiGate
            kigate = KiGateService(self.settings)
            
            # Get default model from settings
            default_model = getattr(self.settings, 'openai_default_model', 'gpt-4') or 'gpt-4'
            
            # Build message with milestone context
            summary_message = f"Zusammenfassung für Milestone: {milestone.name}\n\n{full_context}"
            
            logger.info(f"Generating milestone summary for {milestone.id}")
            summary_result = kigate.execute_agent(
                agent_name='text-summary-agent',
                provider='openai',
                model=default_model,
                message=summary_message,
                user_id='system',
                parameters={
                    'max_length': 1000
                }
            )
            
            summary = ""
            if summary_result.get('success') and 'result' in summary_result:
                if isinstance(summary_result['result'], dict):
                    summary = summary_result['result'].get('summary', '')
                else:
                    summary = str(summary_result['result'])
            
            # Update milestone with summary
            milestone.summary = summary
            milestone.save()
            
            logger.info(f"Generated summary for milestone {milestone.id}")
            
            return {
                'success': True,
                'summary': summary,
                'context_count': context_objects.count()
            }
            
        except KiGateServiceError as e:
            logger.error(f"KiGate error during milestone summary: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "AI summary generation failed",
                details=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to generate milestone summary: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to generate milestone summary",
                details=str(e)
            )
    
    def sync_to_weaviate(self, milestone) -> Dict[str, Any]:
        """
        Sync milestone knowledge to Weaviate as a KnowledgeObject
        
        Args:
            milestone: Milestone instance
        
        Returns:
            Dictionary with sync result
        
        Raises:
            MilestoneKnowledgeServiceError: If sync fails
        """
        try:
            # Prepare milestone data for Weaviate
            context_objects = milestone.context_objects.all()
            
            # Combine all context
            all_context = []
            all_tags = set()
            
            for ctx in context_objects:
                all_context.append(f"{ctx.title}: {ctx.content or ctx.summary}")
                if ctx.tags:
                    all_tags.update(ctx.tags)
            
            context_text = "\n\n".join(all_context)
            
            # Prepare data for Weaviate
            weaviate_data = {
                'type': 'milestone',
                'title': milestone.name,
                'description': milestone.description or milestone.summary,
                'context': context_text,
                'tags': list(all_tags),
                'status': milestone.status,
                'due_date': milestone.due_date.isoformat() if milestone.due_date else None,
                'item_id': str(milestone.item.id) if milestone.item else None,
                'milestone_id': str(milestone.id)
            }
            
            # Use Weaviate sync service
            # Note: This assumes WeaviateItemSyncService can handle milestone objects
            # You may need to create a dedicated WeaviateMilestoneSyncService
            logger.info(f"Syncing milestone {milestone.id} to Weaviate")
            
            # For now, we'll log that this would sync to Weaviate
            # Full implementation would require extending Weaviate service
            logger.info(f"Milestone {milestone.id} ready for Weaviate sync with data: {weaviate_data}")
            
            return {
                'success': True,
                'message': 'Milestone prepared for Weaviate sync',
                'weaviate_data': weaviate_data
            }
            
        except Exception as e:
            logger.error(f"Failed to sync milestone to Weaviate: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to sync to Weaviate",
                details=str(e)
            )
    
    def create_tasks_from_context(self, context_obj, milestone, user=None) -> Dict[str, Any]:
        """
        Create actual Task objects from derived tasks in a context object
        
        Args:
            context_obj: MilestoneContextObject instance
            milestone: Milestone instance
            user: User creating the tasks
        
        Returns:
            Dictionary with created task information
        
        Raises:
            MilestoneKnowledgeServiceError: If task creation fails
        """
        from main.models import Task
        
        try:
            if not context_obj.derived_tasks:
                return {
                    'success': True,
                    'tasks_created': 0,
                    'message': 'No derived tasks to create'
                }
            
            created_tasks = []
            
            for task_data in context_obj.derived_tasks:
                # Extract task information
                if isinstance(task_data, dict):
                    title = task_data.get('title', '')
                    description = task_data.get('description', '')
                else:
                    title = str(task_data)
                    description = f"Abgeleitet aus: {context_obj.title}"
                
                if not title:
                    continue
                
                # Create task
                task = Task.objects.create(
                    title=title,
                    description=description,
                    item=milestone.item,
                    milestone=milestone,
                    created_by=user,
                    ai_generated=True,
                    status='new'
                )
                
                created_tasks.append({
                    'id': str(task.id),
                    'title': task.title
                })
            
            logger.info(f"Created {len(created_tasks)} tasks from context object {context_obj.id}")
            
            return {
                'success': True,
                'tasks_created': len(created_tasks),
                'tasks': created_tasks
            }
            
        except Exception as e:
            logger.error(f"Failed to create tasks from context: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to create tasks",
                details=str(e)
            )
