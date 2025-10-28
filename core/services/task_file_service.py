"""
Task File Service for IdeaGraph

This module provides file upload/download/delete functionality for Tasks,
integrating with SharePoint via Graph API and Weaviate for file content storage.
Files are stored in SharePoint under: IdeaGraph/{normalized_item_title}/{task_uuid}/
"""

import logging
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
    
    def get_file_extension(self, filename: str) -> str:
        """
        Extract file extension from filename
        
        Args:
            filename: Name of the file
            
        Returns:
            str: Uppercase file extension without dot (e.g., 'PDF', 'DOCX') or empty string if no extension
        """
        if not filename or not isinstance(filename, str):
            return ''
        
        filename = filename.strip()
        if not filename or filename in ['.', '..'] or not '.' in filename:
            return ''
        
        extension = filename.rsplit('.', 1)[-1]
        # Ensure we actually got an extension (not an empty string after the dot)
        if extension and extension != filename:
            return extension.upper()
        return ''
    
    def normalize_folder_name(self, name: str) -> str:
        """
        Normalize folder name for SharePoint
        
        Removes or replaces special characters that are not allowed in SharePoint folder names.
        
        Args:
            name: Original name
            
        Returns:
            str: Normalized name safe for SharePoint
        """
        # SharePoint doesn't allow these characters: ~ " # % & * : < > ? / \ { | }
        # Replace problematic characters with underscores
        name = re.sub(r'[~"#%&*:<>?/\\{|}]', '_', name)
        
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
        
        try:
            # Upload to SharePoint
            graph_service = self._get_graph_service()
            logger.debug(f"Graph service initialized with base URL: {graph_service.base_url}")
            logger.debug(f"SharePoint site ID: {graph_service.sharepoint_site_id}")
            
            upload_result = graph_service.upload_sharepoint_file(
                folder_path=folder_path,
                file_name=filename,
                content=file_content
            )
            
            if not upload_result['success']:
                logger.error(f"SharePoint upload failed for {filename}")
                logger.error(f"Upload result: {upload_result}")
                raise TaskFileServiceError("Failed to upload file to SharePoint")
            
            # Extract file metadata from upload result
            file_id = upload_result.get('file_id', '')
            metadata = upload_result.get('metadata', {})
            sharepoint_url = metadata.get('webUrl', '')
            
            # Save file record in database
            from main.models import TaskFile
            
            with transaction.atomic():
                task_file = TaskFile.objects.create(
                    task=task,
                    filename=filename,
                    file_size=file_size,
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
                'sharepoint_url': sharepoint_url,
                'weaviate_synced': task_file.weaviate_synced,
                'message': 'File uploaded successfully'
            }
            
        except GraphServiceError as e:
            logger.error(f"Graph service error during upload: {e.message}")
            logger.error(f"Status code: {e.status_code}")
            raise TaskFileServiceError(f"SharePoint upload failed: {e.message}", details=e.details)
        
        except Exception as e:
            logger.error(f"Unexpected error during file upload: {str(e)}")
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
                    'file_extension': self.get_file_extension(f.filename),
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
    
    def get_markdown_content(self, file_id: str, user) -> Dict[str, Any]:
        """
        Get markdown file content for inline viewing
        
        Args:
            file_id: TaskFile ID
            user: User requesting the content
            
        Returns:
            Dict with success status and markdown content
        """
        try:
            from main.models import TaskFile
            
            task_file = TaskFile.objects.get(id=file_id)
            
            # Check if file is markdown
            if not task_file.filename.lower().endswith('.md'):
                raise TaskFileServiceError("File is not a markdown file")
            
            # Get SharePoint file ID from the file
            if not task_file.sharepoint_file_id:
                raise TaskFileServiceError("SharePoint file ID not found")
            
            # Download file content from SharePoint
            graph_service = self._get_graph_service()
            result = graph_service.get_sharepoint_file(task_file.sharepoint_file_id)
            
            if not result.get('success'):
                raise TaskFileServiceError("Failed to download file from SharePoint")
            
            # Decode content as UTF-8 text
            content = result.get('content', b'')
            try:
                markdown_text = content.decode('utf-8')
            except UnicodeDecodeError:
                # Try with other encodings if UTF-8 fails
                try:
                    markdown_text = content.decode('latin-1')
                except Exception:
                    raise TaskFileServiceError("Failed to decode file content")
            
            return {
                'success': True,
                'filename': task_file.filename,
                'content': markdown_text,
                'sharepoint_url': task_file.sharepoint_url
            }
            
        except TaskFile.DoesNotExist:
            raise TaskFileServiceError("File not found")
        except TaskFileServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting markdown content: {str(e)}")
            raise TaskFileServiceError("Failed to get markdown content", details=str(e))
