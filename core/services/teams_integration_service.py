"""
Teams Integration Service for IdeaGraph

This service orchestrates the complete Teams integration workflow:
1. Poll Teams channels for new messages
2. Analyze messages with AI
3. Post responses to Teams
4. Create tasks if needed
5. Sync conversations to Weaviate
"""

import logging
from typing import Dict, Any, List

from .teams_listener_service import TeamsListenerService, TeamsListenerServiceError
from .message_processing_service import MessageProcessingService, MessageProcessingServiceError
from .graph_response_service import GraphResponseService, GraphResponseServiceError
from .weaviate_conversation_sync_service import WeaviateConversationSyncService, WeaviateConversationSyncServiceError


logger = logging.getLogger('teams_integration_service')


class TeamsIntegrationServiceError(Exception):
    """Base exception for Teams Integration Service errors"""
    
    def __init__(self, message: str, details: str = None):
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


class TeamsIntegrationService:
    """
    Teams Integration Service
    
    Orchestrates the complete Teams integration workflow.
    """
    
    def __init__(self, settings=None):
        """
        Initialize TeamsIntegrationService
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise TeamsIntegrationServiceError("Failed to load settings", str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise TeamsIntegrationServiceError("No settings found in database")
        
        # Initialize all required services
        try:
            self.listener_service = TeamsListenerService(settings=settings)
            self.processing_service = MessageProcessingService(settings=settings)
            self.response_service = GraphResponseService(settings=settings)
            self.weaviate_service = WeaviateConversationSyncService(settings=settings)
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}")
            raise TeamsIntegrationServiceError("Failed to initialize services", str(e))
        
        logger.info("TeamsIntegrationService initialized successfully")
    
    def process_message(
        self,
        item,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single message: analyze, respond, create task if needed, and sync
        
        Args:
            item: Item object
            message: Teams message object
            
        Returns:
            Dict with processing results
        """
        result = {
            'success': False,
            'message_id': message.get('id'),
            'item_id': str(item.id),
            'error': None,
            'task_created': False,
            'task_id': None,
            'response_posted': False,
            'weaviate_synced': False
        }
        
        try:
            # Step 1: Analyze the message with AI
            logger.info(f"Analyzing message {message.get('id')} for item {item.id}")
            analysis_result = self.processing_service.analyze_message(message, item)
            
            if not analysis_result.get('success'):
                result['error'] = analysis_result.get('error', 'Analysis failed')
                return result
            
            ai_response = analysis_result.get('ai_response', '')
            
            # Step 2: Create task if needed
            task = None
            task_url = None
            if analysis_result.get('should_create_task'):
                logger.info(f"Creating task for message {message.get('id')}")
                task = self.processing_service.create_task_from_analysis(
                    item, message, analysis_result
                )
                if task:
                    result['task_created'] = True
                    result['task_id'] = str(task.id)
                    # Build task URL
                    task_url = f"/tasks/{task.id}"
                    logger.info(f"Task created: {task.id}")
            
            # Step 3: Post response to Teams
            try:
                logger.info(f"Posting response to Teams for message {message.get('id')}")
                response_result = self.response_service.post_response(
                    channel_id=item.channel_id,
                    response_content=ai_response,
                    task_created=result['task_created'],
                    task_url=task_url
                )
                if response_result.get('success'):
                    result['response_posted'] = True
                    logger.info(f"Response posted to Teams")
            except GraphResponseServiceError as e:
                logger.error(f"Failed to post response to Teams: {str(e)}")
                # Continue processing even if response posting fails
            
            # Step 4: Sync conversation to Weaviate
            try:
                logger.info(f"Syncing conversation to Weaviate")
                weaviate_result = self.weaviate_service.sync_conversation(
                    message_content=analysis_result.get('message_content', ''),
                    ai_response=ai_response,
                    item_id=str(item.id),
                    item_title=item.title,
                    created_by=analysis_result.get('sender_upn', 'unknown')
                )
                if weaviate_result.get('success'):
                    result['weaviate_synced'] = True
                    logger.info(f"Conversation synced to Weaviate")
            except WeaviateConversationSyncServiceError as e:
                logger.error(f"Failed to sync to Weaviate: {str(e)}")
                # Continue even if Weaviate sync fails
            
            result['success'] = True
            return result
            
        except MessageProcessingServiceError as e:
            logger.error(f"Message processing error: {str(e)}")
            result['error'] = str(e)
            return result
        except Exception as e:
            logger.error(f"Unexpected error processing message: {str(e)}")
            result['error'] = f"Unexpected error: {str(e)}"
            return result
    
    def poll_and_process(self) -> Dict[str, Any]:
        """
        Poll all Teams channels and process new messages
        
        Returns:
            Dict with overall processing results
        """
        logger.info("Starting Teams integration poll and process cycle")
        
        overall_result = {
            'success': True,
            'items_checked': 0,
            'messages_found': 0,
            'messages_processed': 0,
            'tasks_created': 0,
            'responses_posted': 0,
            'errors': []
        }
        
        try:
            # Poll all channels
            poll_result = self.listener_service.poll_all_channels()
            
            overall_result['items_checked'] = poll_result.get('items_checked', 0)
            overall_result['messages_found'] = poll_result.get('messages_found', 0)
            
            # Process each item with messages
            for item_data in poll_result.get('items_with_messages', []):
                from main.models import Item
                
                try:
                    item = Item.objects.get(id=item_data['item_id'])
                except Item.DoesNotExist:
                    logger.error(f"Item {item_data['item_id']} not found")
                    continue
                
                # Process each message
                for message in item_data.get('messages', []):
                    logger.info(f"Processing message {message.get('id')} for item {item.id}")
                    
                    try:
                        result = self.process_message(item, message)
                        
                        if result.get('success'):
                            overall_result['messages_processed'] += 1
                            if result.get('task_created'):
                                overall_result['tasks_created'] += 1
                            if result.get('response_posted'):
                                overall_result['responses_posted'] += 1
                        else:
                            overall_result['errors'].append({
                                'message_id': message.get('id'),
                                'item_id': str(item.id),
                                'error': result.get('error')
                            })
                    except Exception as e:
                        logger.error(f"Error processing message {message.get('id')}: {str(e)}")
                        overall_result['errors'].append({
                            'message_id': message.get('id'),
                            'item_id': str(item.id),
                            'error': str(e)
                        })
            
            logger.info(
                f"Poll and process complete: "
                f"{overall_result['messages_processed']}/{overall_result['messages_found']} messages processed, "
                f"{overall_result['tasks_created']} tasks created, "
                f"{overall_result['responses_posted']} responses posted"
            )
            
            return overall_result
            
        except TeamsListenerServiceError as e:
            logger.error(f"Listener service error: {str(e)}")
            overall_result['success'] = False
            overall_result['errors'].append({'error': str(e)})
            return overall_result
        except Exception as e:
            logger.error(f"Unexpected error in poll_and_process: {str(e)}")
            overall_result['success'] = False
            overall_result['errors'].append({'error': str(e)})
            return overall_result
