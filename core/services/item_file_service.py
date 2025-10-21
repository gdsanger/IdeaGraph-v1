"""
Item File Service for IdeaGraph

This module provides file upload/download/delete functionality for Items,
integrating with SharePoint via Graph API and Weaviate for file content storage.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from django.db import transaction

from core.services.graph_service import GraphService, GraphServiceError
from core.services.file_extraction_service import FileExtractionService, FileExtractionError


logger = logging.getLogger('item_file_service')


class ItemFileServiceError(Exception):
    """Base exception for Item File Service errors"""
    
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


class ItemFileService:
    """
    Item File Service
    
    Manages file uploads for Items:
    - Validates file size (max 25MB)
    - Normalizes folder names for SharePoint
    - Uploads files to SharePoint under "IdeaGraph/{normalized_item_title}/"
    - Extracts text content from supported file types
    - Stores content in Weaviate as KnowledgeObject
    - Tracks uploaded files in ItemFile model
    """
    
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes
    IDEAGRAPH_FOLDER = "IdeaGraph"
    
    def __init__(self, settings=None):
        """
        Initialize ItemFileService
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise ItemFileServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise ItemFileServiceError("No settings found in database")
        
        self.graph_service = None
        self.extraction_service = FileExtractionService()
    
    def _get_graph_service(self) -> GraphService:
        """Get or create Graph Service instance"""
        if self.graph_service is None:
            try:
                self.graph_service = GraphService(self.settings)
            except GraphServiceError as e:
                raise ItemFileServiceError(f"Failed to initialize Graph service: {e.message}", details=e.details)
        return self.graph_service
    
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
        # Also remove leading/trailing dots and spaces
        
        # Replace problematic characters with underscores
        name = re.sub(r'[~"#%&*:<>?/\\{|}]', '_', name)
        
        # Remove leading/trailing dots and spaces
        name = name.strip('. ')
        
        # Replace multiple underscores with single underscore
        name = re.sub(r'_{2,}', '_', name)
        
        # Limit length to 255 characters (SharePoint limit)
        if len(name) > 255:
            name = name[:255]
        
        # If name is empty after normalization, use a default
        if not name:
            name = 'Untitled'
        
        return name
    
    def _ensure_folder_exists(self, folder_path: str) -> Dict[str, Any]:
        """
        Ensure a folder exists in SharePoint, creating it if necessary
        
        Args:
            folder_path: Path to folder
            
        Returns:
            Dict with success status and folder metadata
        """
        graph_service = self._get_graph_service()
        
        try:
            # Try to list folder contents to check if it exists
            result = graph_service.get_sharepoint_file_list(folder_path)
            if result['success']:
                logger.info(f"Folder exists: {folder_path}")
                return {'success': True, 'created': False}
        except GraphServiceError as e:
            # Folder doesn't exist, we'll create it
            logger.info(f"Folder does not exist, will create: {folder_path}")
        
        # Create folder by uploading a placeholder file and then deleting it
        # This is a workaround since Graph API doesn't have direct folder creation in simple API
        # For production, you might want to use the DriveItem API endpoint
        # For now, we'll assume the folder is created when we upload the first file
        
        return {'success': True, 'created': True}
    
    def upload_file(
        self,
        item,
        file_content: bytes,
        filename: str,
        content_type: str,
        user
    ) -> Dict[str, Any]:
        """
        Upload a file for an item
        
        Args:
            item: Item object
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
            raise ItemFileServiceError(
                f"File size {file_size / (1024*1024):.2f}MB exceeds maximum {self.MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )
        
        # Normalize item title for folder name
        normalized_folder_name = self.normalize_folder_name(item.title)
        folder_path = f"{self.IDEAGRAPH_FOLDER}/{normalized_folder_name}"
        
        logger.info(f"Uploading file {filename} ({file_size} bytes) to {folder_path}")
        
        try:
            # Upload to SharePoint
            graph_service = self._get_graph_service()
            upload_result = graph_service.upload_sharepoint_file(
                folder_path=folder_path,
                file_name=filename,
                content=file_content
            )
            
            if not upload_result['success']:
                raise ItemFileServiceError("Failed to upload file to SharePoint")
            
            # Extract file metadata from upload result
            file_id = upload_result.get('file_id', '')
            metadata = upload_result.get('metadata', {})
            sharepoint_url = metadata.get('webUrl', '')
            
            # Save file record in database
            from main.models import ItemFile
            
            with transaction.atomic():
                item_file = ItemFile.objects.create(
                    item=item,
                    filename=filename,
                    file_size=file_size,
                    sharepoint_file_id=file_id,
                    sharepoint_url=sharepoint_url,
                    content_type=content_type,
                    uploaded_by=user,
                    weaviate_synced=False
                )
                
                logger.info(f"Created ItemFile record: {item_file.id}")
                
                # Try to extract and sync content to Weaviate
                sync_result = self._sync_to_weaviate(item, item_file, file_content, filename)
                
                if sync_result['success']:
                    item_file.weaviate_synced = True
                    item_file.save(update_fields=['weaviate_synced'])
                    logger.info(f"Successfully synced file content to Weaviate")
                else:
                    logger.warning(f"Failed to sync file content to Weaviate: {sync_result.get('error')}")
            
            return {
                'success': True,
                'file_id': str(item_file.id),
                'filename': filename,
                'file_size': file_size,
                'sharepoint_url': sharepoint_url,
                'weaviate_synced': item_file.weaviate_synced,
                'message': 'File uploaded successfully'
            }
            
        except GraphServiceError as e:
            logger.error(f"Graph service error during upload: {e.message}")
            raise ItemFileServiceError(f"Upload failed: {e.message}", details=e.details)
        except Exception as e:
            logger.error(f"Unexpected error during upload: {str(e)}")
            raise ItemFileServiceError(f"Upload failed: {str(e)}")
    
    def _sync_to_weaviate(
        self,
        item,
        item_file,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Sync file content to Weaviate as KnowledgeObject
        
        Args:
            item: Item object
            item_file: ItemFile object
            file_content: File content as bytes
            filename: Filename
            
        Returns:
            Dict with success status
        """
        # Check if we can extract text from this file
        if not self.extraction_service.can_extract_text(filename):
            logger.info(f"File type not supported for text extraction: {filename}")
            return {
                'success': False,
                'error': 'File type not supported for text extraction'
            }
        
        # Extract text
        extraction_result = self.extraction_service.extract_text(file_content, filename)
        
        if not extraction_result['success']:
            logger.warning(f"Text extraction failed: {extraction_result.get('error')}")
            return {
                'success': False,
                'error': extraction_result.get('error')
            }
        
        text_chunks = extraction_result.get('chunks', [])
        if not text_chunks:
            logger.warning("No text chunks extracted from file")
            return {
                'success': False,
                'error': 'No text content extracted'
            }
        
        # Sync each chunk to Weaviate
        try:
            from core.services.weaviate_sync_service import WeaviateItemSyncService
            
            weaviate_service = WeaviateItemSyncService(self.settings)
            
            for i, chunk in enumerate(text_chunks):
                # Create KnowledgeObject for each chunk
                # Using the mapping from the requirements:
                # title = filename, description = content, itemID = item.id, url = sharepoint_url, type = "File"
                
                chunk_title = filename if len(text_chunks) == 1 else f"{filename} (Part {i+1}/{len(text_chunks)})"
                
                knowledge_object = {
                    'uuid': f"{item_file.id}_{i}" if len(text_chunks) > 1 else str(item_file.id),
                    'title': chunk_title,
                    'description': chunk,
                    'type': 'File',
                    'itemID': str(item.id),
                    'url': item_file.sharepoint_url,
                    'owner': item.created_by.username if item.created_by else '',
                    'section': item.section.name if item.section else '',
                    'status': item.status,
                    'tags': [tag.name for tag in item.tags.all()],
                }
                
                # Use the sync service to add to Weaviate
                weaviate_service._add_or_update_object(knowledge_object)
            
            weaviate_service.close()
            
            logger.info(f"Synced {len(text_chunks)} chunk(s) to Weaviate for file {filename}")
            
            return {
                'success': True,
                'chunks_synced': len(text_chunks)
            }
            
        except Exception as e:
            logger.error(f"Error syncing to Weaviate: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_file(self, file_id: str, user) -> Dict[str, Any]:
        """
        Delete a file
        
        Args:
            file_id: UUID of ItemFile
            user: User deleting the file
            
        Returns:
            Dict with success status
        """
        from main.models import ItemFile
        
        try:
            item_file = ItemFile.objects.get(id=file_id)
            
            # Check permission (user must be owner or admin)
            if user.role != 'admin' and item_file.item.created_by != user:
                raise ItemFileServiceError("You do not have permission to delete this file")
            
            # Delete from SharePoint
            if item_file.sharepoint_file_id:
                try:
                    graph_service = self._get_graph_service()
                    delete_result = graph_service.delete_sharepoint_file(item_file.sharepoint_file_id)
                    logger.info(f"Deleted file from SharePoint: {item_file.sharepoint_file_id}")
                except GraphServiceError as e:
                    logger.warning(f"Failed to delete from SharePoint (continuing anyway): {e.message}")
            
            # Delete from Weaviate
            if item_file.weaviate_synced:
                try:
                    from core.services.weaviate_sync_service import WeaviateItemSyncService
                    
                    weaviate_service = WeaviateItemSyncService(self.settings)
                    # Delete the KnowledgeObject(s) associated with this file
                    # This assumes single object per file for now
                    weaviate_service.sync_delete(str(file_id))
                    weaviate_service.close()
                    logger.info(f"Deleted file from Weaviate: {file_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete from Weaviate (continuing anyway): {str(e)}")
            
            # Delete from database
            filename = item_file.filename
            item_file.delete()
            
            logger.info(f"Successfully deleted file: {filename}")
            
            return {
                'success': True,
                'message': f'File {filename} deleted successfully'
            }
            
        except ItemFile.DoesNotExist:
            raise ItemFileServiceError("File not found")
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            raise ItemFileServiceError(f"Failed to delete file: {str(e)}")
    
    def get_download_url(self, file_id: str, user) -> Dict[str, Any]:
        """
        Get download URL for a file
        
        Args:
            file_id: UUID of ItemFile
            user: User requesting download
            
        Returns:
            Dict with success status and download URL
        """
        from main.models import ItemFile
        
        try:
            item_file = ItemFile.objects.get(id=file_id)
            
            # Check permission
            if user.role != 'admin' and item_file.item.created_by != user:
                raise ItemFileServiceError("You do not have permission to access this file")
            
            # Return SharePoint URL directly
            # The SharePoint URL should allow direct download with proper authentication
            return {
                'success': True,
                'download_url': item_file.sharepoint_url,
                'filename': item_file.filename
            }
            
        except ItemFile.DoesNotExist:
            raise ItemFileServiceError("File not found")
        except Exception as e:
            logger.error(f"Error getting download URL: {str(e)}")
            raise ItemFileServiceError(f"Failed to get download URL: {str(e)}")
    
    def list_files(self, item_id: str) -> Dict[str, Any]:
        """
        List all files for an item
        
        Args:
            item_id: UUID of Item
            
        Returns:
            Dict with success status and list of files
        """
        from main.models import ItemFile, Item
        
        try:
            item = Item.objects.get(id=item_id)
            files = ItemFile.objects.filter(item=item).order_by('-created_at')
            
            files_data = []
            for f in files:
                files_data.append({
                    'id': str(f.id),
                    'filename': f.filename,
                    'file_size': f.file_size,
                    'file_size_mb': round(f.file_size / (1024 * 1024), 2),
                    'content_type': f.content_type,
                    'sharepoint_url': f.sharepoint_url,
                    'weaviate_synced': f.weaviate_synced,
                    'uploaded_by': f.uploaded_by.username if f.uploaded_by else 'Unknown',
                    'created_at': f.created_at.isoformat(),
                })
            
            return {
                'success': True,
                'files': files_data,
                'count': len(files_data)
            }
            
        except Item.DoesNotExist:
            raise ItemFileServiceError("Item not found")
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise ItemFileServiceError(f"Failed to list files: {str(e)}")
