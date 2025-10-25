"""
Task File Service for IdeaGraph

This module provides file upload/download/delete functionality for Tasks,
integrating with SharePoint via Graph API and Weaviate for file content storage.
Files are stored in SharePoint under: IdeaGraph/{normalized_item_title}/{task_uuid}/
"""

import logging
import os
import re
from typing import Optional, Dict, Any, List
from django.db import transaction

from core.services.graph_service import GraphService, GraphServiceError
from core.services.file_extraction_service import FileExtractionService, FileExtractionError


logger = logging.getLogger('task_file_service')


class TaskFileServiceError(Exception):
    """Base exception for Task File Service errors"""
    
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


class TaskFileService:
    """
    Task File Service
    
    Manages file uploads for Tasks:
    - Validates file size (max 25MB)
    - Normalizes folder names for SharePoint
    - Uploads files to SharePoint under "IdeaGraph/{normalized_item_title}/{task_uuid}/"
    - Extracts text content from supported file types
    - Stores content in Weaviate as KnowledgeObject
    - Tracks uploaded files in TaskFile model
    """
    
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes
    IDEAGRAPH_FOLDER = "IdeaGraph"
    
    def __init__(self, settings=None):
        """
        Initialize TaskFileService
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise TaskFileServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise TaskFileServiceError("No settings found in database")
        
        self.graph_service = None
        self.extraction_service = FileExtractionService()
    
    def _get_graph_service(self) -> GraphService:
        """Get or create Graph Service instance"""
        if self.graph_service is None:
            try:
                self.graph_service = GraphService(self.settings)
            except GraphServiceError as e:
                raise TaskFileServiceError(f"Failed to initialize Graph service: {e.message}", details=e.details)
        return self.graph_service
    
    def normalize_folder_name(self, name: str) -> str:
        """
        Normalize folder name for SharePoint and local filesystem
        
        Removes or replaces special characters that are not allowed in SharePoint folder names
        or that could cause issues in local filesystems.
        
        Args:
            name: Original name
            
        Returns:
            str: Normalized name safe for SharePoint and local filesystem
        """
        # SharePoint doesn't allow these characters: ~ " # % & * : < > ? / \ { | }
        # Also remove @ and ! for better compatibility
        # Replace problematic characters with underscores
        name = re.sub(r'[~"#%&*:<>?/\\{|}!@]', '_', name)
        
        # Remove leading/trailing dots and spaces
        name = name.strip('. ')
        
        # Replace multiple underscores with single underscore
        name = re.sub(r'_{2,}', '_', name)
        
        # Remove leading/trailing underscores
        name = name.strip('_')
        
        # Limit length to 255 characters (SharePoint limit)
        if len(name) > 255:
            name = name[:255]
        
        # If name is empty after normalization, use a default
        if not name:
            name = 'Untitled'
        
        return name
    
    def _save_file_locally(
        self,
        task,
        file_content: bytes,
        filename: str
    ) -> str:
        """
        Save file to local filesystem
        
        Saves files in structure:
        - media/task_files/{item_title}/{task_uuid}/ for tasks with items
        - media/task_files/Tasks/{task_uuid}/ for standalone tasks
        
        Args:
            task: Task object
            file_content: File content as bytes
            filename: Original filename
            
        Returns:
            str: Local file path
        """
        # Determine local folder path
        if task.item:
            # Task belongs to an item: media/task_files/{item_title}/{task_uuid}/
            normalized_item_name = self.normalize_folder_name(task.item.title)
            folder_path = os.path.join('media', 'task_files', normalized_item_name, str(task.id))
        else:
            # Standalone task: media/task_files/Tasks/{task_uuid}/
            folder_path = os.path.join('media', 'task_files', 'Tasks', str(task.id))
        
        # Create the directory structure
        # Get absolute path from project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        full_folder_path = os.path.join(base_dir, folder_path)
        os.makedirs(full_folder_path, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(folder_path, filename)
        full_file_path = os.path.join(base_dir, file_path)
        
        with open(full_file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Saved file locally to: {file_path}")
        
        return file_path
    
    def upload_file(
        self,
        task,
        file_content: bytes,
        filename: str,
        content_type: str,
        user
    ) -> Dict[str, Any]:
        """
        Upload a file for a task
        
        Args:
            task: Task object
            file_content: File content as bytes
            filename: Original filename
            content_type: MIME type of the file
            user: User uploading the file
            
        Returns:
            Dict with success status and file metadata
        """
        # Validate file size
        file_size = len(file_content)
        if file_size > self.MAX_FILE_SIZE:
            raise TaskFileServiceError(
                f"File size {file_size / (1024*1024):.2f}MB exceeds maximum {self.MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )
        
        # Determine folder path based on whether task has an item
        if task.item:
            # Task belongs to an item: IdeaGraph/{item_title}/{task_uuid}/
            normalized_item_name = self.normalize_folder_name(task.item.title)
            folder_path = f"{self.IDEAGRAPH_FOLDER}/{normalized_item_name}/{task.id}"
        else:
            # Standalone task: IdeaGraph/Tasks/{task_uuid}/
            folder_path = f"{self.IDEAGRAPH_FOLDER}/Tasks/{task.id}"
        
        logger.info(f"Uploading file {filename} ({file_size} bytes) to {folder_path}")
        logger.debug(f"Task ID: {task.id}, Task title: {task.title}")
        logger.debug(f"Content type: {content_type}")
        
        # Save file locally to filesystem (always do this)
        local_file_path = self._save_file_locally(task, file_content, filename)
        logger.info(f"File saved locally to: {local_file_path}")
        
        # Initialize SharePoint variables
        file_id = ''
        sharepoint_url = ''
        
        try:
            # Try to upload to SharePoint if enabled
            graph_service = self._get_graph_service()
            logger.debug(f"Graph service initialized with base URL: {graph_service.base_url}")
            logger.debug(f"SharePoint site ID: {graph_service.sharepoint_site_id}")
            
            upload_result = graph_service.upload_sharepoint_file(
                folder_path=folder_path,
                file_name=filename,
                content=file_content
            )
            
            if upload_result['success']:
                # Extract file metadata from upload result
                file_id = upload_result.get('file_id', '')
                metadata = upload_result.get('metadata', {})
                sharepoint_url = metadata.get('webUrl', '')
                logger.info(f"File uploaded to SharePoint: {sharepoint_url}")
            else:
                logger.warning(f"SharePoint upload failed for {filename}, but file is saved locally")
                
        except (GraphServiceError, TaskFileServiceError) as e:
            # Log SharePoint errors but continue since we have local copy
            logger.warning(f"SharePoint upload failed: {str(e)}, file is saved locally at {local_file_path}")
        
        try:
            # Save file record in database
            from main.models import TaskFile
            
            with transaction.atomic():
                task_file = TaskFile.objects.create(
                    task=task,
                    filename=filename,
                    file_size=file_size,
                    file_path=local_file_path,
                    sharepoint_file_id=file_id,
                    sharepoint_url=sharepoint_url,
                    content_type=content_type,
                    uploaded_by=user,
                    weaviate_synced=False
                )
                
                logger.info(f"Created TaskFile record: {task_file.id}")
                
                # Try to extract and sync content to Weaviate
                sync_result = self._sync_to_weaviate(task, task_file, file_content, filename)
                
                if sync_result['success']:
                    task_file.weaviate_synced = True
                    task_file.save(update_fields=['weaviate_synced'])
                    logger.info(f"Successfully synced file content to Weaviate")
                else:
                    logger.warning(f"Failed to sync file content to Weaviate: {sync_result.get('error')}")
            
            return {
                'success': True,
                'file_id': str(task_file.id),
                'filename': filename,
                'file_size': file_size,
                'file_path': local_file_path,
                'sharepoint_url': sharepoint_url,
                'weaviate_synced': task_file.weaviate_synced,
                'message': 'File uploaded successfully'
            }
            
        except Exception as e:
            logger.error(f"Error saving file record to database: {str(e)}")
            # Try to clean up local file if database save fails
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                full_file_path = os.path.join(base_dir, local_file_path)
                if os.path.exists(full_file_path):
                    os.remove(full_file_path)
                    logger.info(f"Cleaned up local file after database error: {full_file_path}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up local file: {str(cleanup_error)}")
            raise TaskFileServiceError("File upload failed", details=str(e))
    
    def _sync_to_weaviate(
        self,
        task,
        task_file,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract content from file and sync to Weaviate
        
        Args:
            task: Task object
            task_file: TaskFile object
            file_content: File content as bytes
            filename: Filename
            
        Returns:
            Dict with success status
        """
        try:
            # Extract text content from file
            extraction_result = self.extraction_service.extract_text(file_content, filename)
            
            if not extraction_result['success']:
                logger.warning(f"Could not extract text from {filename}: {extraction_result.get('error')}")
                return {'success': False, 'error': 'Text extraction failed'}
            
            text_content = extraction_result.get('text', '')
            if not text_content or len(text_content.strip()) < 10:
                logger.info(f"No meaningful text content extracted from {filename}")
                return {'success': False, 'error': 'No text content'}
            
            # Sync to Weaviate
            from core.services.weaviate_sync_service import WeaviateSyncService
            
            weaviate_service = WeaviateSyncService(self.settings)
            
            # Create metadata for Weaviate
            metadata = {
                'task_id': str(task.id),
                'task_title': task.title,
                'filename': filename,
                'file_id': str(task_file.id),
                'content_type': task_file.content_type,
                'object_type': 'task_file'
            }
            
            if task.item:
                metadata['item_id'] = str(task.item.id)
                metadata['item_title'] = task.item.title
            
            sync_result = weaviate_service.sync_knowledge_object(
                title=f"{task.title} - {filename}",
                content=text_content,
                metadata=metadata
            )
            
            return sync_result
            
        except FileExtractionError as e:
            logger.error(f"File extraction error: {e.message}")
            return {'success': False, 'error': e.message}
        
        except Exception as e:
            logger.error(f"Error syncing to Weaviate: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def list_files(self, task_id: str) -> Dict[str, Any]:
        """
        List all files for a task
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict with success status and list of files
        """
        try:
            from main.models import Task, TaskFile
            
            task = Task.objects.get(id=task_id)
            files = TaskFile.objects.filter(task=task).order_by('-created_at')
            
            file_list = []
            for f in files:
                file_list.append({
                    'id': str(f.id),
                    'filename': f.filename,
                    'file_size': f.file_size,
                    'file_size_mb': f.file_size / (1024 * 1024),
                    'sharepoint_url': f.sharepoint_url,
                    'content_type': f.content_type,
                    'weaviate_synced': f.weaviate_synced,
                    'uploaded_by': f.uploaded_by.username if f.uploaded_by else 'Unknown',
                    'created_at': f.created_at.isoformat()
                })
            
            return {
                'success': True,
                'files': file_list,
                'count': len(file_list)
            }
            
        except Task.DoesNotExist:
            raise TaskFileServiceError("Task not found")
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise TaskFileServiceError("Failed to list files", details=str(e))
    
    def delete_file(self, file_id: str, user) -> Dict[str, Any]:
        """
        Delete a file
        
        Args:
            file_id: TaskFile ID
            user: User deleting the file
            
        Returns:
            Dict with success status
        """
        try:
            from main.models import TaskFile
            
            task_file = TaskFile.objects.get(id=file_id)
            task_id = str(task_file.task.id)
            
            # Delete from SharePoint
            if task_file.sharepoint_file_id:
                try:
                    graph_service = self._get_graph_service()
                    delete_result = graph_service.delete_sharepoint_file(task_file.sharepoint_file_id)
                    if not delete_result['success']:
                        logger.warning(f"Failed to delete file from SharePoint: {delete_result.get('error')}")
                except GraphServiceError as e:
                    logger.warning(f"SharePoint deletion failed: {e.message}")
            
            # Delete from local filesystem
            if task_file.file_path:
                try:
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    full_file_path = os.path.join(base_dir, task_file.file_path)
                    if os.path.exists(full_file_path):
                        os.remove(full_file_path)
                        logger.info(f"Deleted local file: {full_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete local file: {str(e)}")
            
            # Delete from database
            filename = task_file.filename
            task_file.delete()
            
            logger.info(f"Deleted file {filename} (ID: {file_id})")
            
            return {
                'success': True,
                'message': 'File deleted successfully',
                'task_id': task_id
            }
            
        except TaskFile.DoesNotExist:
            raise TaskFileServiceError("File not found")
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise TaskFileServiceError("Failed to delete file", details=str(e))
    
    def get_download_url(self, file_id: str, user) -> Dict[str, Any]:
        """
        Get download URL for a file
        
        Args:
            file_id: TaskFile ID
            user: User requesting the download
            
        Returns:
            Dict with success status and download URL
        """
        try:
            from main.models import TaskFile
            
            task_file = TaskFile.objects.get(id=file_id)
            
            return {
                'success': True,
                'filename': task_file.filename,
                'sharepoint_url': task_file.sharepoint_url,
                'download_url': task_file.sharepoint_url  # SharePoint URL serves as download link
            }
            
        except TaskFile.DoesNotExist:
            raise TaskFileServiceError("File not found")
        except Exception as e:
            logger.error(f"Error getting download URL: {str(e)}")
            raise TaskFileServiceError("Failed to get download URL", details=str(e))
