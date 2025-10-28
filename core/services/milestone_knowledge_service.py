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


def estimate_token_count(text: str) -> int:
    """
    Estimate the number of tokens in a text string.
    Uses a simple heuristic: ~4 characters per token (works well for English/German)
    
    Args:
        text: Input text string
        
    Returns:
        Estimated token count
    """
    return len(text) // 4


def chunk_text(text: str, max_tokens: int, overlap: int = 200) -> List[str]:
    """
    Split text into chunks that fit within token limit with overlap.
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk
        overlap: Number of tokens to overlap between chunks
        
    Returns:
        List of text chunks
    """
    # Convert max_tokens to approximate character count
    max_chars = max_tokens * 4
    overlap_chars = overlap * 4
    
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chars
        
        # If this is not the last chunk, try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the end of the chunk
            sentence_endings = ['. ', '.\n', '! ', '!\n', '? ', '?\n']
            best_break = end
            
            # Search backwards from end for a sentence boundary
            for i in range(end, max(start + max_chars // 2, end - 500), -1):
                if any(text[i:i+2] == ending for ending in sentence_endings):
                    best_break = i + 2
                    break
            
            end = best_break
        
        chunks.append(text[start:end])
        
        # Move start forward, accounting for overlap
        start = end - overlap_chars
        if start >= len(text):
            break
    
    return chunks


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
    
    # RAG search configuration constants
    RAG_SIMILARITY_THRESHOLD = 0.5  # Minimum similarity score for RAG results
    RAG_SEARCH_MULTIPLIER = 3  # Multiplier for initial search to filter different types
    RAG_QUERY_LENGTH = 1000  # Maximum characters to use from content for RAG query
    
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
    
    def search_similar_context(
        self,
        query_text: str,
        milestone=None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar knowledge objects using RAG (Weaviate)
        
        This method searches across all types of knowledge objects (Tasks, Items, Milestones)
        to provide relevant context for AI analysis.
        
        Args:
            query_text: Text to search for similar content
            milestone: Optional milestone to filter or reference
            max_results: Maximum number of results to return per type
            
        Returns:
            List of similar knowledge objects with metadata
        """
        similar_objects = []
        
        try:
            import weaviate
            from weaviate.classes.init import Auth
            from weaviate.classes.query import MetadataQuery, HybridFusion
            
            # Initialize Weaviate client
            if self.settings.weaviate_cloud_enabled:
                client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
                )
            else:
                client = weaviate.connect_to_local(
                    host="localhost",
                    port=8081
                )
            
            try:
                collection = client.collections.get('KnowledgeObject')
                
                # Search for similar objects using hybrid search
                response = collection.query.hybrid(
                    query=query_text,
                    limit=max_results * self.RAG_SEARCH_MULTIPLIER,  # Get extra results to account for similarity filtering
                    return_metadata=MetadataQuery(distance=True, score=True),
                    fusion_type=HybridFusion.RANKED
                )
                
                # Process and categorize results
                for obj in response.objects:
                    obj_type = obj.properties.get('type', '')
                    obj_id = str(obj.uuid)
                    
                    # Calculate similarity from distance
                    distance = obj.metadata.distance if obj.metadata else 1.0
                    similarity = max(0, 1 - distance)
                    
                    # Only include results with reasonable similarity
                    if similarity < self.RAG_SIMILARITY_THRESHOLD:
                        continue
                    
                    similar_objects.append({
                        'type': obj_type,  # Keep original capitalization from Weaviate
                        'id': obj_id,
                        'title': obj.properties.get('title', 'N/A'),
                        'description': obj.properties.get('description', '')[:300],
                        'similarity': similarity,
                        'distance': distance
                    })
                    
                    # Stop if we have enough results
                    if len(similar_objects) >= max_results:
                        break
                
                logger.info(f"Found {len(similar_objects)} similar objects via RAG for query")
                
            finally:
                client.close()
                
        except Exception as e:
            logger.warning(f"Could not search similar context via RAG: {str(e)}")
        
        return similar_objects
    
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
            
            # Sync context object to Weaviate
            try:
                sync_result = self.sync_context_object_to_weaviate(context_obj)
                result['weaviate_sync'] = sync_result
                logger.info(f"Context object {context_obj.id} synced to Weaviate")
            except Exception as e:
                logger.warning(f"Failed to sync context object {context_obj.id} to Weaviate: {str(e)}")
                result['weaviate_sync_error'] = str(e)
            
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
        4. Handles content chunking if it exceeds token limits
        
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
            
            # Get max tokens limit from settings
            max_tokens = getattr(self.settings, 'kigate_max_tokens', 10000)
            
            # Check if content needs chunking
            content_tokens = estimate_token_count(context_obj.content)
            needs_chunking = content_tokens > max_tokens
            
            if needs_chunking:
                logger.info(f"Content exceeds {max_tokens} tokens ({content_tokens} estimated), will chunk")
                chunks = chunk_text(context_obj.content, max_tokens)
                logger.info(f"Split content into {len(chunks)} chunks")
            else:
                chunks = [context_obj.content]
            
            # Step 1: Generate summary using text-summary-agent
            logger.info(f"Generating summary for context object {context_obj.id}")
            
            all_summaries = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} for summary")
                
                summary_result = kigate.execute_agent(
                    agent_name='text-summary-agent',
                    provider='openai',
                    model=default_model,
                    message=chunk,
                    user_id='system',
                    parameters={
                        'max_length': 500
                    }
                )
                
                if summary_result.get('success') and 'result' in summary_result:
                    if isinstance(summary_result['result'], dict):
                        chunk_summary = summary_result['result'].get('summary', '')
                    else:
                        chunk_summary = str(summary_result['result'])
                    
                    if chunk_summary:
                        all_summaries.append(chunk_summary)
            
            # Merge summaries
            if len(all_summaries) > 1:
                # If we have multiple summaries, combine them
                summary = "\n\n".join([f"Teil {i+1}: {s}" for i, s in enumerate(all_summaries)])
            elif all_summaries:
                summary = all_summaries[0]
            else:
                summary = ""
            
            # Step 2: Derive tasks using text-analysis-task-derivation-agent
            logger.info(f"Deriving tasks for context object {context_obj.id}")
            
            # Search for similar context using RAG
            rag_context = []
            try:
                similar_objects = self.search_similar_context(
                    query_text=context_obj.content[:self.RAG_QUERY_LENGTH],  # Use first N chars for search
                    milestone=context_obj.milestone,
                    max_results=3
                )
                
                if similar_objects:
                    logger.info(f"Found {len(similar_objects)} similar objects via RAG")
                    rag_context = [
                        f"- [{obj['type'].upper()}] {obj['title']}: {obj['description']}"
                        for obj in similar_objects
                    ]
            except Exception as e:
                logger.warning(f"Could not retrieve RAG context: {str(e)}")
            
            all_derived_tasks = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} for task derivation")
                
                # Build message with RAG context
                task_message = f"Milestone: {context_obj.milestone.name}\n\n"
                
                # Add RAG context if available
                if rag_context:
                    task_message += "--- Similar objects from knowledge base (RAG) ---\n"
                    task_message += "\n".join(rag_context)
                    task_message += "\n--- End of similar objects ---\n\n"
                
                task_message += f"Content:\n{chunk}"
                
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
                    
                    # Handle different response formats
                    if isinstance(result_data, dict):
                        # Response is a dict with 'tasks' key
                        derived_tasks = result_data.get('tasks', [])
                    elif isinstance(result_data, list):
                        # Response is directly a list of tasks
                        derived_tasks = result_data
                    elif isinstance(result_data, str):
                        # Try to parse as JSON if it's a string
                        try:
                            parsed = json.loads(result_data)
                            if isinstance(parsed, list):
                                derived_tasks = parsed
                            elif isinstance(parsed, dict):
                                derived_tasks = parsed.get('tasks', [])
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse task derivation result as JSON: {result_data}")
                
                all_derived_tasks.extend(derived_tasks)
            
            logger.info(f"Parsed {len(all_derived_tasks)} total derived tasks from all chunks")
            
            # Update context object
            context_obj.summary = summary
            context_obj.derived_tasks = all_derived_tasks
            context_obj.analyzed = True
            context_obj.save()
            
            # Re-sync to Weaviate with updated summary
            try:
                self.sync_context_object_to_weaviate(context_obj)
                logger.info(f"Context object {context_obj.id} re-synced to Weaviate with summary")
            except Exception as e:
                logger.warning(f"Failed to re-sync context object {context_obj.id} to Weaviate: {str(e)}")
            
            logger.info(f"Analysis complete for context object {context_obj.id}: "
                       f"{len(all_derived_tasks)} tasks derived")
            
            return {
                'success': True,
                'summary': summary,
                'derived_tasks': all_derived_tasks,
                'task_count': len(all_derived_tasks),
                'chunks_processed': len(chunks)
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
            
            # Search for similar context using RAG
            rag_context = []
            try:
                similar_objects = self.search_similar_context(
                    query_text=full_context[:self.RAG_QUERY_LENGTH],  # Use first N chars for search
                    milestone=milestone,
                    max_results=3
                )
                
                if similar_objects:
                    logger.info(f"Found {len(similar_objects)} similar objects via RAG for milestone summary")
                    rag_context = [
                        f"- [{obj['type'].upper()}] {obj['title']}: {obj['description']}"
                        for obj in similar_objects
                    ]
            except Exception as e:
                logger.warning(f"Could not retrieve RAG context for summary: {str(e)}")
            
            # Build message with milestone context and RAG
            summary_message = f"Zusammenfassung für Milestone: {milestone.name}\n\n"
            
            # Add RAG context if available
            if rag_context:
                summary_message += "--- Similar objects from knowledge base (RAG) ---\n"
                summary_message += "\n".join(rag_context)
                summary_message += "\n--- End of similar objects ---\n\n"
            
            summary_message += full_context
            
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
            from main.models import Settings
            from core.services.weaviate_sync_service import WeaviateItemSyncService
            
            # Get settings
            settings = Settings.objects.first()
            if not settings:
                raise MilestoneKnowledgeServiceError("Settings not configured")
            
            # Initialize Weaviate service
            weaviate_service = WeaviateItemSyncService(settings)
            
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
                
                # Prepare combined description
                description_parts = []
                if milestone.description:
                    description_parts.append(milestone.description)
                if milestone.summary:
                    description_parts.append(f"Summary: {milestone.summary}")
                if context_text:
                    description_parts.append(f"Context: {context_text}")
                
                combined_description = "\n\n".join(description_parts)
                
                # Get the collection
                collection = weaviate_service._client.collections.get('KnowledgeObject')
                
                # Get owner information
                owner = ''
                if milestone.item and milestone.item.created_by:
                    owner = milestone.item.created_by.username
                
                # Get tags from milestone's item
                tags = []
                if milestone.item:
                    tags = [tag.name for tag in milestone.item.tags.all()]
                
                # Create or update the milestone in Weaviate
                milestone_data = {
                    'type': 'Milestone',  # Capitalized to match TYPE_MAPPING in SemanticNetworkService
                    'title': milestone.name,
                    'description': combined_description,
                    'status': milestone.status,
                    'owner': owner,
                    'tags': tags,
                    'createdAt': milestone.created_at.isoformat() if milestone.created_at else None,
                    'url': f'/milestones/{milestone.id}/',
                    'itemId': str(milestone.item.id) if milestone.item else None,
                    'dueDate': milestone.due_date.isoformat() if milestone.due_date else None,
                }
                
                # Check if object already exists
                milestone_uuid = str(milestone.id)
                exists = collection.data.exists(milestone_uuid)
                
                if exists:
                    # Update existing object
                    logger.info(f"Milestone {milestone.id} already exists in Weaviate, updating...")
                    collection.data.update(
                        uuid=milestone_uuid,
                        properties=milestone_data
                    )
                else:
                    # Insert new object
                    logger.info(f"Milestone {milestone.id} is new, inserting into Weaviate...")
                    collection.data.insert(
                        properties=milestone_data,
                        uuid=milestone_uuid
                    )
                
                logger.info(f"Milestone {milestone.id} synced to Weaviate successfully")
                
                # Update weaviate_id on milestone if not set
                if not milestone.weaviate_id:
                    milestone.weaviate_id = milestone.id
                    milestone.save(update_fields=['weaviate_id'])
                
                return {
                    'success': True,
                    'message': f'Milestone "{milestone.name}" synced to Weaviate successfully'
                }
            finally:
                weaviate_service.close()
            
        except Exception as e:
            logger.error(f"Failed to sync milestone to Weaviate: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to sync to Weaviate",
                details=str(e)
            )
    
    def sync_context_object_to_weaviate(self, context_obj) -> Dict[str, Any]:
        """
        Sync a milestone context object to Weaviate as a separate KnowledgeObject
        
        This allows individual context objects (files, emails, transcripts, notes)
        to be searched and retrieved through the semantic network.
        
        Args:
            context_obj: MilestoneContextObject instance
        
        Returns:
            Dictionary with sync result
        
        Raises:
            MilestoneKnowledgeServiceError: If sync fails
        """
        try:
            from main.models import Settings
            from core.services.weaviate_sync_service import WeaviateItemSyncService
            
            # Get settings
            settings = Settings.objects.first()
            if not settings:
                raise MilestoneKnowledgeServiceError("Settings not configured")
            
            # Initialize Weaviate service
            weaviate_service = WeaviateItemSyncService(settings)
            
            try:
                # Get the collection
                collection = weaviate_service._client.collections.get('KnowledgeObject')
                
                # Map context object type to KnowledgeObject type
                type_mapping = {
                    'file': 'File',
                    'email': 'Email',
                    'transcript': 'Transcript',
                    'note': 'Note'
                }
                
                # Prepare context object data for Weaviate
                # Use summary if available, otherwise use content
                description = context_obj.summary if context_obj.summary else context_obj.content
                
                # Add metadata to description
                description_parts = []
                if context_obj.milestone:
                    description_parts.append(f"Milestone: {context_obj.milestone.name}")
                if description:
                    description_parts.append(description)
                
                combined_description = "\n\n".join(description_parts)
                
                # Get owner information
                owner = ''
                if context_obj.uploaded_by:
                    owner = context_obj.uploaded_by.username
                elif context_obj.milestone and context_obj.milestone.item and context_obj.milestone.item.created_by:
                    owner = context_obj.milestone.item.created_by.username
                
                # Get tags from context object or milestone's item
                tags = []
                if context_obj.tags:
                    tags = context_obj.tags if isinstance(context_obj.tags, list) else []
                elif context_obj.milestone and context_obj.milestone.item:
                    tags = [tag.name for tag in context_obj.milestone.item.tags.all()]
                
                context_data = {
                    'type': type_mapping.get(context_obj.type, 'File'),  # Capitalized for consistency
                    'title': context_obj.title,
                    'description': combined_description,
                    'owner': owner,
                    'tags': tags,
                    'status': '',  # Context objects don't have status, use empty string
                    'createdAt': context_obj.created_at.isoformat() if context_obj.created_at else None,
                    'url': context_obj.url if context_obj.url else '',
                    'milestoneId': str(context_obj.milestone.id) if context_obj.milestone else None,
                    'sourceId': context_obj.source_id if context_obj.source_id else None,
                }
                
                # Check if object already exists
                context_uuid = str(context_obj.id)
                exists = collection.data.exists(context_uuid)
                
                if exists:
                    # Update existing object
                    logger.info(f"Context object {context_obj.id} already exists in Weaviate, updating...")
                    collection.data.update(
                        uuid=context_uuid,
                        properties=context_data
                    )
                else:
                    # Insert new object
                    logger.info(f"Context object {context_obj.id} is new, inserting into Weaviate...")
                    collection.data.insert(
                        properties=context_data,
                        uuid=context_uuid
                    )
                
                logger.info(f"Context object {context_obj.id} synced to Weaviate successfully")
                
                return {
                    'success': True,
                    'message': f'Context object "{context_obj.title}" synced to Weaviate successfully'
                }
            finally:
                weaviate_service.close()
            
        except Exception as e:
            logger.error(f"Failed to sync context object to Weaviate: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to sync context object to Weaviate",
                details=str(e)
            )
    
    def enhance_summary(self, context_obj) -> Dict[str, Any]:
        """
        Enhance a context object's summary using the summary-enhancer-agent
        
        Args:
            context_obj: MilestoneContextObject instance with an existing summary
        
        Returns:
            Dictionary with enhanced summary
        
        Raises:
            MilestoneKnowledgeServiceError: If enhancement fails
        """
        try:
            if not context_obj.summary:
                raise MilestoneKnowledgeServiceError(
                    "Cannot enhance empty summary. Generate a summary first."
                )
            
            kigate = KiGateService(self.settings)
            
            # Get default model from settings
            default_model = getattr(self.settings, 'openai_default_model', 'gpt-4') or 'gpt-4'
            
            logger.info(f"Enhancing summary for context object {context_obj.id}")
            
            enhance_result = kigate.execute_agent(
                agent_name='summary-enhancer-agent',
                provider='openai',
                model=default_model,
                message=context_obj.summary,
                user_id='system',
                parameters={
                    'context': f"Milestone: {context_obj.milestone.name}"
                }
            )
            
            enhanced_summary = ""
            if enhance_result.get('success') and 'result' in enhance_result:
                if isinstance(enhance_result['result'], dict):
                    enhanced_summary = enhance_result['result'].get('enhanced_summary', '') or enhance_result['result'].get('summary', '')
                else:
                    enhanced_summary = str(enhance_result['result'])
            
            if not enhanced_summary:
                raise MilestoneKnowledgeServiceError(
                    "Summary enhancement returned empty result"
                )
            
            # Update context object with enhanced summary
            context_obj.summary = enhanced_summary
            context_obj.save()
            
            logger.info(f"Enhanced summary for context object {context_obj.id}")
            
            return {
                'success': True,
                'enhanced_summary': enhanced_summary
            }
            
        except KiGateServiceError as e:
            logger.error(f"KiGate error during summary enhancement: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "AI summary enhancement failed",
                details=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to enhance summary: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to enhance summary",
                details=str(e)
            )
    
    def accept_analysis_results(self, context_obj, summary: str = None, derived_tasks: list = None) -> Dict[str, Any]:
        """
        Accept and apply analysis results to a context object after user review/editing
        
        Args:
            context_obj: MilestoneContextObject instance
            summary: Optional edited summary (uses existing if None)
            derived_tasks: Optional edited task list (uses existing if None)
        
        Returns:
            Dictionary with acceptance result
        
        Raises:
            MilestoneKnowledgeServiceError: If acceptance fails
        """
        try:
            # Update summary if provided
            if summary is not None:
                context_obj.summary = summary
            
            # Update derived tasks if provided
            if derived_tasks is not None:
                context_obj.derived_tasks = derived_tasks
            
            # Mark as analyzed
            context_obj.analyzed = True
            context_obj.save()
            
            # Update milestone summary to include this context object's summary
            milestone = context_obj.milestone
            
            # Add source reference to the summary
            source_reference = f"\n\n– aus ContextObject [{context_obj.title}]"
            summary_with_reference = context_obj.summary + source_reference
            
            # Append to milestone summary or create new one
            if milestone.summary:
                milestone.summary += f"\n\n{summary_with_reference}"
            else:
                milestone.summary = summary_with_reference
            
            milestone.save()
            
            logger.info(f"Accepted analysis results for context object {context_obj.id}")
            
            return {
                'success': True,
                'message': 'Analysis results accepted and applied',
                'summary': context_obj.summary,
                'derived_tasks_count': len(context_obj.derived_tasks) if context_obj.derived_tasks else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to accept analysis results: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to accept analysis results",
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
                # Extract task information - support both German and English keys
                if isinstance(task_data, dict):
                    # Try German keys first (from text-analysis-task-derivation-agent)
                    title = task_data.get('Titel') or task_data.get('titel') or task_data.get('title', '')
                    description = task_data.get('Beschreibung') or task_data.get('beschreibung') or task_data.get('description', '')
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
    
    def optimize_summary(self, milestone, user=None) -> Dict[str, Any]:
        """
        Optimize milestone summary using AI (summary-enhancer-agent)
        
        This method:
        1. Takes the current milestone summary
        2. Sends it to the summary-enhancer-agent for optimization
        3. Returns the optimized text without saving it (user must confirm)
        
        Args:
            milestone: Milestone instance
            user: User requesting the optimization (for audit trail)
        
        Returns:
            Dictionary with optimized summary
        
        Raises:
            MilestoneKnowledgeServiceError: If optimization fails
        """
        try:
            # Check if there's a summary to optimize
            if not milestone.summary or not milestone.summary.strip():
                raise MilestoneKnowledgeServiceError(
                    "No summary text available to optimize"
                )
            
            kigate = KiGateService(self.settings)
            
            # Get default model from settings
            default_model = getattr(self.settings, 'openai_default_model', 'gpt-4') or 'gpt-4'
            
            # Build message for the summary enhancer agent
            optimization_message = f"Milestone: {milestone.name}\n\nAktueller Summary-Text:\n{milestone.summary}"
            
            logger.info(f"Optimizing summary for milestone {milestone.id}")
            
            # Execute the summary-enhancer-agent
            result = kigate.execute_agent(
                agent_name='summary-enhancer-agent',
                provider='openai',
                model=default_model,
                message=optimization_message,
                user_id=str(user.id) if user else 'system'
            )
            
            optimized_summary = ""
            if result.get('success') and 'result' in result:
                if isinstance(result['result'], dict):
                    optimized_summary = result['result'].get('summary', result['result'].get('optimized_text', ''))
                else:
                    optimized_summary = str(result['result'])
            
            if not optimized_summary:
                raise MilestoneKnowledgeServiceError(
                    "AI optimization returned empty result"
                )
            
            logger.info(f"Successfully optimized summary for milestone {milestone.id}")
            
            return {
                'success': True,
                'original_summary': milestone.summary,
                'optimized_summary': optimized_summary,
                'agent_name': 'summary-enhancer-agent',
                'model': default_model
            }
            
        except KiGateServiceError as e:
            logger.error(f"KiGate error during summary optimization: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "AI summary optimization failed",
                details=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to optimize summary: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to optimize summary",
                details=str(e)
            )
    
    def save_optimized_summary(
        self, 
        milestone, 
        optimized_summary: str, 
        user=None,
        agent_name: str = 'summary-enhancer-agent',
        model_name: str = 'gpt-4'
    ) -> Dict[str, Any]:
        """
        Save an optimized summary to the milestone and create a version history entry
        
        Args:
            milestone: Milestone instance
            optimized_summary: The optimized summary text to save
            user: User who confirmed the optimization
            agent_name: Name of the AI agent used
            model_name: Name of the AI model used
        
        Returns:
            Dictionary with save result
        
        Raises:
            MilestoneKnowledgeServiceError: If save fails
        """
        from main.models import MilestoneSummaryVersion
        
        try:
            # Store old summary as a version before updating
            if milestone.summary:
                # Get the next version number
                last_version = milestone.summary_versions.order_by('-version_number').first()
                next_version = (last_version.version_number + 1) if last_version else 1
                
                # Create version entry for the optimized summary
                MilestoneSummaryVersion.objects.create(
                    milestone=milestone,
                    summary_text=optimized_summary,
                    version_number=next_version,
                    optimized_by_ai=True,
                    agent_name=agent_name,
                    model_name=model_name,
                    created_by=user
                )
            
            # Update milestone with optimized summary
            milestone.summary = optimized_summary
            milestone.save()
            
            logger.info(f"Saved optimized summary for milestone {milestone.id}")
            
            return {
                'success': True,
                'summary': optimized_summary,
                'message': 'Optimized summary saved successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to save optimized summary: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to save optimized summary",
                details=str(e)
            )
    
    def get_summary_history(self, milestone) -> Dict[str, Any]:
        """
        Get version history of milestone summaries
        
        Args:
            milestone: Milestone instance
        
        Returns:
            Dictionary with version history
        """
        try:
            versions = milestone.summary_versions.all()
            
            version_list = []
            for version in versions:
                version_list.append({
                    'id': str(version.id),
                    'version_number': version.version_number,
                    'summary_text': version.summary_text,
                    'optimized_by_ai': version.optimized_by_ai,
                    'agent_name': version.agent_name,
                    'model_name': version.model_name,
                    'created_by': version.created_by.username if version.created_by else None,
                    'created_at': version.created_at.isoformat()
                })
            
            return {
                'success': True,
                'versions': version_list,
                'total_versions': len(version_list),
                'current_summary': milestone.summary
            }
            
        except Exception as e:
            logger.error(f"Failed to get summary history: {str(e)}")
            raise MilestoneKnowledgeServiceError(
                "Failed to retrieve summary history",
                details=str(e)
            )
