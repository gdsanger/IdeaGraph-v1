"""
Task Move Service for IdeaGraph

This module provides functionality to move tasks between items,
including handling SharePoint folder relocation for task files.
"""

import logging
from typing import Optional, Dict, Any
from django.db import transaction

from core.services.graph_service import GraphService, GraphServiceError
from core.services.task_file_service import TaskFileService


logger = logging.getLogger('task_move_service')


class TaskMoveServiceError(Exception):
    """Base exception for Task Move Service errors"""
    
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


class TaskMoveService:
    """
    Task Move Service
    
    Handles moving tasks between items:
    - Validates task and target item
    - Moves task files in SharePoint
    - Updates task's item reference
    - Handles folder creation if needed
    """
    
    def __init__(self, settings=None):
        """
        Initialize TaskMoveService
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise TaskMoveServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise TaskMoveServiceError("No settings found in database")
        
        self.graph_service = None
        self.task_file_service = TaskFileService(settings)
    
    def _get_graph_service(self) -> GraphService:
        """Get or create Graph Service instance"""
        if self.graph_service is None:
            try:
                self.graph_service = GraphService(self.settings)
            except GraphServiceError as e:
                raise TaskMoveServiceError(
                    f"Failed to initialize Graph service: {e.message}",
                    details=e.details
                )
        return self.graph_service
    
    def _normalize_folder_name(self, name: str) -> str:
        """
        Normalize folder name for SharePoint
        Uses the same logic as TaskFileService
        """
        return self.task_file_service.normalize_folder_name(name)
    
    def _get_task_folder_path(self, task, item=None) -> str:
        """
        Get the SharePoint folder path for a task
        
        Args:
            task: Task object
            item: Optional Item object (uses task.item if not provided)
            
        Returns:
            str: Folder path
        """
        target_item = item or task.item
        
        if target_item:
            normalized_item_name = self._normalize_folder_name(target_item.title)
            return f"{self.task_file_service.IDEAGRAPH_FOLDER}/{normalized_item_name}/{task.id}"
        else:
            return f"{self.task_file_service.IDEAGRAPH_FOLDER}/Tasks/{task.id}"
    
    def _ensure_item_folder_exists(self, item) -> Dict[str, Any]:
        """
        Ensure the item folder exists in SharePoint
        
        Args:
            item: Item object
            
        Returns:
            Dict with success status and folder_id
        """
        try:
            graph_service = self._get_graph_service()
            normalized_item_name = self._normalize_folder_name(item.title)
            item_folder_path = f"{self.task_file_service.IDEAGRAPH_FOLDER}/{normalized_item_name}"
            
            # Check if folder exists
            folder_result = graph_service.get_folder_by_path(item_folder_path)
            
            if folder_result['exists']:
                logger.info(f"Item folder already exists: {item_folder_path}")
                return {
                    'success': True,
                    'folder_id': folder_result['folder_id'],
                    'created': False
                }
            
            # Folder doesn't exist, create it
            logger.info(f"Creating item folder: {item_folder_path}")
            create_result = graph_service.create_folder(
                parent_path=self.task_file_service.IDEAGRAPH_FOLDER,
                folder_name=normalized_item_name
            )
            
            return {
                'success': True,
                'folder_id': create_result['folder_id'],
                'created': True
            }
            
        except GraphServiceError as e:
            logger.error(f"Failed to ensure item folder exists: {e.message}")
            raise TaskMoveServiceError(
                f"Failed to ensure item folder exists: {e.message}",
                details=e.details
            )
    
    def move_task(self, task_id: str, target_item_id: str, user) -> Dict[str, Any]:
        """
        Move a task to a different item
        
        Args:
            task_id: UUID of the task to move
            target_item_id: UUID of the target item
            user: User performing the move
            
        Returns:
            Dict with success status and move details
        """
        from main.models import Task, Item, TaskFile
        
        try:
            # Load task and validate
            try:
                task = Task.objects.select_related('item').get(id=task_id)
            except Task.DoesNotExist:
                raise TaskMoveServiceError("Task not found")
            
            # Load target item and validate
            try:
                target_item = Item.objects.get(id=target_item_id)
            except Item.DoesNotExist:
                raise TaskMoveServiceError("Target item not found")
            
            # Get the source item (if any)
            source_item = task.item
            
            # Check if task is already in the target item
            if source_item and str(source_item.id) == str(target_item_id):
                return {
                    'success': True,
                    'message': 'Task is already in the target item',
                    'moved': False
                }
            
            logger.info(f"Moving task {task.id} ({task.title}) to item {target_item.id} ({target_item.title})")
            if source_item:
                logger.info(f"Source item: {source_item.id} ({source_item.title})")
            else:
                logger.info("Source: standalone task")
            
            # Check if task has files that need to be moved
            task_files = TaskFile.objects.filter(task=task)
            files_to_move = task_files.count()
            
            logger.info(f"Task has {files_to_move} file(s) to move")
            
            # Move files in SharePoint if any exist
            files_moved = False
            if files_to_move > 0:
                # Ensure target item folder exists
                folder_result = self._ensure_item_folder_exists(target_item)
                target_item_folder_id = folder_result['folder_id']
                
                # Get the task folder path in the source location
                source_folder_path = self._get_task_folder_path(task, source_item)
                
                # Try to get the task folder ID in the source location
                try:
                    graph_service = self._get_graph_service()
                    source_folder_result = graph_service.get_folder_by_path(source_folder_path)
                    
                    if source_folder_result['exists']:
                        source_folder_id = source_folder_result['folder_id']
                        
                        # Move the folder
                        logger.info(f"Moving folder from {source_folder_path} to item folder")
                        move_result = graph_service.move_folder(
                            folder_id=source_folder_id,
                            destination_folder_id=target_item_folder_id,
                            new_name=str(task.id)
                        )
                        
                        logger.info(f"Folder moved successfully")
                        files_moved = True
                    else:
                        logger.warning(f"Source task folder not found: {source_folder_path}")
                        # Files may have been stored differently, we'll continue anyway
                        
                except GraphServiceError as e:
                    logger.warning(f"Could not move task folder: {e.message}")
                    # Continue with database update even if folder move fails
            
            # Update task in database
            with transaction.atomic():
                task.item = target_item
                task.save(update_fields=['item'])
                
                logger.info(f"Task database record updated successfully")
            
            return {
                'success': True,
                'message': f'Task moved successfully to {target_item.title}',
                'moved': True,
                'files_moved': files_moved,
                'files_count': files_to_move,
                'task_id': str(task.id),
                'source_item_id': str(source_item.id) if source_item else None,
                'target_item_id': str(target_item.id)
            }
            
        except TaskMoveServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error moving task: {str(e)}")
            raise TaskMoveServiceError("Failed to move task", details=str(e))
