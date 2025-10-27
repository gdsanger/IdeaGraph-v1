"""
GitHub Documentation Synchronization Service for IdeaGraph

This module provides automatic synchronization of Markdown documentation (.md files)
from GitHub repositories to IdeaGraph Items, including:
- Downloading .md files from GitHub repositories
- Uploading to SharePoint in Item folders
- Registering as ItemFile records
- Syncing to Weaviate as KnowledgeObjects
"""

import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from django.db import transaction

from core.services.github_service import GitHubService, GitHubServiceError
from core.services.graph_service import GraphService, GraphServiceError
from core.services.weaviate_sync_service import WeaviateItemSyncService, WeaviateItemSyncServiceError


logger = logging.getLogger('github_doc_sync_service')


class GitHubDocSyncServiceError(Exception):
    """Base exception for GitHub Doc Sync Service errors"""
    
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


class GitHubDocSyncService:
    """
    GitHub Documentation Synchronization Service
    
    Synchronizes Markdown documentation from GitHub repositories to IdeaGraph:
    - Scans repository for .md files
    - Downloads file content
    - Uploads to SharePoint in Item folder
    - Creates ItemFile records
    - Syncs to Weaviate as KnowledgeObjects (type: "documentation")
    """
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit for documentation files
    IDEAGRAPH_FOLDER = "IdeaGraph"
    
    def __init__(self, settings=None):
        """
        Initialize GitHubDocSyncService
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise GitHubDocSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise GitHubDocSyncServiceError("No settings found in database")
        
        # Initialize services
        try:
            self.github_service = GitHubService(self.settings)
            self.graph_service = None  # Lazy load
            self.weaviate_service = None  # Lazy load
        except Exception as e:
            raise GitHubDocSyncServiceError(f"Failed to initialize services: {str(e)}")
    
    def _get_graph_service(self) -> GraphService:
        """Get or create Graph Service instance (lazy loading)"""
        if self.graph_service is None:
            try:
                self.graph_service = GraphService(self.settings)
            except GraphServiceError as e:
                raise GitHubDocSyncServiceError(f"Failed to initialize Graph service: {e.message}", details=e.details)
        return self.graph_service
    
    def _get_weaviate_service(self) -> WeaviateItemSyncService:
        """Get or create Weaviate Service instance (lazy loading)"""
        if self.weaviate_service is None:
            try:
                self.weaviate_service = WeaviateItemSyncService(self.settings)
            except WeaviateItemSyncServiceError as e:
                raise GitHubDocSyncServiceError(f"Failed to initialize Weaviate service: {e.message}", details=e.details)
        return self.weaviate_service
    
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
        
        # Replace multiple underscores with single
        name = re.sub(r'_+', '_', name)
        
        # Limit length to 200 characters
        if len(name) > 200:
            name = name[:200]
        
        return name
    
    def parse_github_repo_url(self, repo_url: str) -> Dict[str, str]:
        """
        Parse GitHub repository URL to extract owner and repo name
        
        Args:
            repo_url: GitHub repository URL (e.g., 'https://github.com/owner/repo' or 'owner/repo')
            
        Returns:
            Dict with 'owner' and 'repo' keys
            
        Raises:
            GitHubDocSyncServiceError: If URL format is invalid
        """
        if not repo_url or not repo_url.strip():
            raise GitHubDocSyncServiceError("Empty repository URL")
        
        repo_url = repo_url.strip()
        
        # Handle full URLs like https://github.com/owner/repo
        if repo_url.startswith('http'):
            # Use string operations instead of regex to avoid ReDoS
            # Parse URL to ensure it's actually a GitHub URL
            url_lower = repo_url.lower()
            
            # Strict validation: must start with https://github.com/ or http://github.com/
            if not (url_lower.startswith('https://github.com/') or url_lower.startswith('http://github.com/')):
                raise GitHubDocSyncServiceError(
                    f"URL must be a GitHub repository URL",
                    details=f"URL: {repo_url}"
                )
            
            # Extract path after github.com/
            if url_lower.startswith('https://'):
                path_part = repo_url[19:]  # len('https://github.com/') = 19
            else:
                path_part = repo_url[18:]  # len('http://github.com/') = 18
            
            # Remove .git suffix if present
            if path_part.endswith('.git'):
                path_part = path_part[:-4]
            
            # Split by slash to get owner/repo
            parts = path_part.split('/')
            if len(parts) >= 2:
                owner = parts[0].strip()
                repo = parts[1].strip()
                
                # Validate owner and repo are not empty and contain only valid characters
                if owner and repo and self._is_valid_github_name(owner) and self._is_valid_github_name(repo):
                    return {
                        'owner': owner,
                        'repo': repo
                    }
        else:
            # Handle short format like owner/repo
            parts = repo_url.split('/')
            if len(parts) == 2:
                owner = parts[0].strip()
                repo = parts[1].strip()
                
                # Validate owner and repo are not empty and contain only valid characters
                if owner and repo and self._is_valid_github_name(owner) and self._is_valid_github_name(repo):
                    return {
                        'owner': owner,
                        'repo': repo
                    }
        
        raise GitHubDocSyncServiceError(
            f"Invalid GitHub repository URL format: {repo_url}",
            details="Expected format: 'https://github.com/owner/repo' or 'owner/repo'"
        )
    
    def _is_valid_github_name(self, name: str) -> bool:
        """
        Validate GitHub owner/repo name
        
        GitHub names can contain alphanumeric characters, hyphens, and underscores.
        They cannot start with a hyphen.
        
        Args:
            name: Owner or repository name to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not name or len(name) > 100:  # Reasonable length limit
            return False
        
        # Check first character is alphanumeric
        if not name[0].isalnum():
            return False
        
        # Check all characters are alphanumeric, hyphen, underscore, or dot
        for char in name:
            if not (char.isalnum() or char in '-_.'):
                return False
        
        return True
    
    def scan_repository(
        self,
        owner: str,
        repo: str,
        path: str = '',
        ref: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Recursively scan repository for .md files
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Current path in repository (empty for root)
            ref: Git reference (branch, tag, or commit SHA)
            
        Returns:
            List of dictionaries containing file information:
                - name: filename
                - path: full path in repository
                - download_url: direct download URL
                - size: file size in bytes
                - sha: Git SHA of the file
        """
        markdown_files = []
        
        try:
            logger.info(f"Scanning {owner}/{repo} path: '{path}'")
            result = self.github_service.get_repository_contents(
                path=path,
                owner=owner,
                repo=repo,
                ref=ref
            )
            
            contents = result.get('contents', [])
            
            # Handle single file response (contents is a dict)
            if isinstance(contents, dict):
                contents = [contents]
            
            for item in contents:
                item_type = item.get('type')
                item_path = item.get('path', '')
                item_name = item.get('name', '')
                
                if item_type == 'file' and item_name.endswith('.md'):
                    # Found a markdown file
                    markdown_files.append({
                        'name': item_name,
                        'path': item_path,
                        'download_url': item.get('download_url'),
                        'size': item.get('size', 0),
                        'sha': item.get('sha', '')
                    })
                    logger.info(f"Found markdown file: {item_path}")
                    
                elif item_type == 'dir':
                    # Recursively scan subdirectory
                    logger.debug(f"Scanning subdirectory: {item_path}")
                    subdir_files = self.scan_repository(
                        owner=owner,
                        repo=repo,
                        path=item_path,
                        ref=ref
                    )
                    markdown_files.extend(subdir_files)
            
            return markdown_files
            
        except GitHubServiceError as e:
            logger.error(f"GitHub API error while scanning {owner}/{repo}/{path}: {e.message}")
            raise GitHubDocSyncServiceError(
                f"Failed to scan repository",
                details=f"{e.message}: {e.details}"
            )
        except Exception as e:
            logger.error(f"Unexpected error while scanning {owner}/{repo}/{path}: {str(e)}")
            raise GitHubDocSyncServiceError(
                "Unexpected error while scanning repository",
                details=str(e)
            )
    
    def download_markdown_file(
        self,
        download_url: str,
        file_path: str
    ) -> Dict[str, Any]:
        """
        Download markdown file content from GitHub
        
        Args:
            download_url: Direct download URL from GitHub API
            file_path: File path in repository (for logging)
            
        Returns:
            Dict with 'content' (str) and 'size' (int)
        """
        try:
            logger.info(f"Downloading {file_path} from {download_url}")
            result = self.github_service.get_file_raw(download_url)
            
            if not result.get('success'):
                raise GitHubDocSyncServiceError(f"Failed to download {file_path}")
            
            content = result.get('content', '')
            size = result.get('size', len(content.encode('utf-8')))
            
            # Check file size
            if size > self.MAX_FILE_SIZE:
                raise GitHubDocSyncServiceError(
                    f"File {file_path} is too large",
                    details=f"Size: {size} bytes, Max: {self.MAX_FILE_SIZE} bytes"
                )
            
            logger.info(f"Downloaded {file_path} ({size} bytes)")
            return {
                'content': content,
                'size': size
            }
            
        except GitHubServiceError as e:
            raise GitHubDocSyncServiceError(
                f"Failed to download {file_path}",
                details=f"{e.message}: {e.details}"
            )
        except Exception as e:
            raise GitHubDocSyncServiceError(
                f"Unexpected error downloading {file_path}",
                details=str(e)
            )
    
    def upload_to_sharepoint(
        self,
        item,
        filename: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Upload file to SharePoint in Item's folder
        
        Args:
            item: Item model instance
            filename: Name of the file
            content: File content as string
            
        Returns:
            Dict with 'file_id', 'web_url', and 'size'
        """
        try:
            graph_service = self._get_graph_service()
            
            # Normalize item title for folder name
            folder_name = self.normalize_folder_name(item.title)
            folder_path = f"{self.IDEAGRAPH_FOLDER}/{folder_name}"
            
            logger.info(f"Uploading {filename} to SharePoint: {folder_path}")
            
            # Convert content to bytes
            content_bytes = content.encode('utf-8')
            
            # Upload file
            result = graph_service.upload_file_to_sharepoint(
                file_content=content_bytes,
                filename=filename,
                folder_path=folder_path
            )
            
            if not result.get('success'):
                raise GitHubDocSyncServiceError(
                    f"Failed to upload {filename} to SharePoint",
                    details=result.get('error', 'Unknown error')
                )
            
            logger.info(f"Successfully uploaded {filename} to SharePoint")
            return {
                'file_id': result.get('file_id', ''),
                'web_url': result.get('web_url', ''),
                'size': len(content_bytes)
            }
            
        except GraphServiceError as e:
            raise GitHubDocSyncServiceError(
                f"SharePoint upload error for {filename}",
                details=f"{e.message}: {e.details}"
            )
        except Exception as e:
            raise GitHubDocSyncServiceError(
                f"Unexpected error uploading {filename} to SharePoint",
                details=str(e)
            )
    
    def register_in_database(
        self,
        item,
        filename: str,
        file_size: int,
        sharepoint_file_id: str,
        sharepoint_url: str,
        uploaded_by=None
    ) -> Any:
        """
        Create ItemFile record in database
        
        Args:
            item: Item model instance
            filename: Name of the file
            file_size: File size in bytes
            sharepoint_file_id: SharePoint file ID
            sharepoint_url: SharePoint file URL
            uploaded_by: User who triggered the sync (optional)
            
        Returns:
            ItemFile instance
        """
        from main.models import ItemFile
        
        try:
            # Check if file already exists
            existing_file = ItemFile.objects.filter(
                item=item,
                filename=filename
            ).first()
            
            if existing_file:
                # Update existing file
                logger.info(f"Updating existing ItemFile: {filename}")
                existing_file.file_size = file_size
                existing_file.sharepoint_file_id = sharepoint_file_id
                existing_file.sharepoint_url = sharepoint_url
                existing_file.content_type = 'text/markdown'
                existing_file.weaviate_synced = False  # Will be synced next
                existing_file.save()
                return existing_file
            else:
                # Create new file record
                logger.info(f"Creating new ItemFile: {filename}")
                item_file = ItemFile.objects.create(
                    item=item,
                    filename=filename,
                    file_size=file_size,
                    sharepoint_file_id=sharepoint_file_id,
                    sharepoint_url=sharepoint_url,
                    content_type='text/markdown',
                    weaviate_synced=False,
                    uploaded_by=uploaded_by
                )
                return item_file
                
        except Exception as e:
            raise GitHubDocSyncServiceError(
                f"Failed to register {filename} in database",
                details=str(e)
            )
    
    def sync_to_weaviate(
        self,
        item,
        filename: str,
        content: str,
        file_url: str,
        github_file_path: str,
        repo_owner: str,
        repo_name: str
    ) -> Dict[str, Any]:
        """
        Sync markdown file to Weaviate as KnowledgeObject
        
        Args:
            item: Item model instance
            filename: Name of the file
            content: File content
            file_url: SharePoint file URL
            github_file_path: Path in GitHub repository
            repo_owner: Repository owner
            repo_name: Repository name
            
        Returns:
            Dict with sync result
        """
        try:
            weaviate_service = self._get_weaviate_service()
            
            # Prepare KnowledgeObject properties
            github_url = f"https://github.com/{repo_owner}/{repo_name}/blob/main/{github_file_path}"
            
            # Extract title from filename or first heading in content
            title = filename.replace('.md', '').replace('_', ' ').replace('-', ' ').title()
            
            # Try to extract first heading from markdown
            first_heading_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if first_heading_match:
                title = first_heading_match.group(1).strip()
            
            # Prepare description (first 500 chars of content, excluding headings)
            description_text = re.sub(r'^#+\s+.*$', '', content, flags=re.MULTILINE)
            description_text = description_text.strip()[:500]
            
            properties = {
                'type': 'documentation',
                'title': title,
                'description': description_text,
                'source': 'GitHub',
                'file_url': file_url,
                'related_item': str(item.id),
                'tags': ['docs', 'documentation', 'github'],
                'last_synced': datetime.utcnow().isoformat() + 'Z',
                'github_url': github_url,
                'github_path': github_file_path,
                'github_repo': f"{repo_owner}/{repo_name}"
            }
            
            logger.info(f"Syncing {filename} to Weaviate as KnowledgeObject")
            
            # Get Weaviate client and collection
            collection = weaviate_service._client.collections.get(weaviate_service.COLLECTION_NAME)
            
            # Generate a unique UUID for this documentation object
            import uuid
            doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{repo_owner}/{repo_name}/{github_file_path}"))
            
            # Check if already exists
            try:
                existing_obj = collection.query.fetch_object_by_id(doc_uuid)
                if existing_obj:
                    # Update existing
                    logger.info(f"Updating existing KnowledgeObject: {doc_uuid}")
                    collection.data.update(
                        uuid=doc_uuid,
                        properties=properties
                    )
                else:
                    # Create new
                    logger.info(f"Creating new KnowledgeObject: {doc_uuid}")
                    collection.data.insert(
                        properties=properties,
                        uuid=doc_uuid
                    )
            except:
                # Object doesn't exist, create it
                logger.info(f"Creating new KnowledgeObject: {doc_uuid}")
                collection.data.insert(
                    properties=properties,
                    uuid=doc_uuid
                )
            
            logger.info(f"Successfully synced {filename} to Weaviate")
            return {
                'success': True,
                'uuid': doc_uuid
            }
            
        except Exception as e:
            logger.error(f"Failed to sync {filename} to Weaviate: {str(e)}")
            raise GitHubDocSyncServiceError(
                f"Failed to sync {filename} to Weaviate",
                details=str(e)
            )
    
    def sync_item(
        self,
        item_id: str,
        uploaded_by=None
    ) -> Dict[str, Any]:
        """
        Synchronize all markdown files from GitHub repository for a specific item
        
        Args:
            item_id: UUID of the item
            uploaded_by: User who triggered the sync (optional)
            
        Returns:
            Dict with sync results:
                - success: bool
                - item_title: str
                - files_processed: int
                - files_synced: int
                - errors: List[str]
        """
        from main.models import Item
        
        try:
            # Get item
            item = Item.objects.get(id=item_id)
            
            logger.info(f"Starting GitHub docs sync for item: {item.title} ({item.id})")
            
            # Check if item has github_repo
            if not item.github_repo:
                return {
                    'success': False,
                    'item_title': item.title,
                    'error': 'Item has no GitHub repository configured',
                    'files_processed': 0,
                    'files_synced': 0,
                    'errors': []
                }
            
            # Parse repository URL
            repo_info = self.parse_github_repo_url(item.github_repo)
            owner = repo_info['owner']
            repo = repo_info['repo']
            
            logger.info(f"Repository: {owner}/{repo}")
            
            # Scan repository for markdown files
            markdown_files = self.scan_repository(owner=owner, repo=repo)
            
            if not markdown_files:
                logger.info(f"No markdown files found in {owner}/{repo}")
                return {
                    'success': True,
                    'item_title': item.title,
                    'files_processed': 0,
                    'files_synced': 0,
                    'errors': []
                }
            
            logger.info(f"Found {len(markdown_files)} markdown files")
            
            # Process each file
            synced_count = 0
            errors = []
            
            for md_file in markdown_files:
                try:
                    logger.info(f"Processing: {md_file['path']}")
                    
                    # Download file content
                    download_result = self.download_markdown_file(
                        download_url=md_file['download_url'],
                        file_path=md_file['path']
                    )
                    content = download_result['content']
                    size = download_result['size']
                    
                    # Upload to SharePoint
                    sharepoint_result = self.upload_to_sharepoint(
                        item=item,
                        filename=md_file['name'],
                        content=content
                    )
                    
                    # Register in database
                    item_file = self.register_in_database(
                        item=item,
                        filename=md_file['name'],
                        file_size=size,
                        sharepoint_file_id=sharepoint_result['file_id'],
                        sharepoint_url=sharepoint_result['web_url'],
                        uploaded_by=uploaded_by
                    )
                    
                    # Sync to Weaviate
                    weaviate_result = self.sync_to_weaviate(
                        item=item,
                        filename=md_file['name'],
                        content=content,
                        file_url=sharepoint_result['web_url'],
                        github_file_path=md_file['path'],
                        repo_owner=owner,
                        repo_name=repo
                    )
                    
                    # Update ItemFile to mark as synced
                    item_file.weaviate_synced = True
                    item_file.save()
                    
                    synced_count += 1
                    logger.info(f"Successfully synced: {md_file['name']}")
                    
                except Exception as e:
                    error_msg = f"Error processing {md_file['path']}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            logger.info(f"Sync completed. Synced {synced_count}/{len(markdown_files)} files")
            
            return {
                'success': True,
                'item_title': item.title,
                'files_processed': len(markdown_files),
                'files_synced': synced_count,
                'errors': errors
            }
            
        except Item.DoesNotExist:
            raise GitHubDocSyncServiceError(f"Item not found: {item_id}")
        except Exception as e:
            logger.error(f"Error syncing item {item_id}: {str(e)}")
            raise GitHubDocSyncServiceError(
                f"Failed to sync item {item_id}",
                details=str(e)
            )
    
    def sync_all_items(
        self,
        uploaded_by=None
    ) -> Dict[str, Any]:
        """
        Synchronize all items that have GitHub repositories configured
        
        Args:
            uploaded_by: User who triggered the sync (optional)
            
        Returns:
            Dict with sync results:
                - success: bool
                - items_processed: int
                - items_synced: int
                - total_files_synced: int
                - errors: List[str]
        """
        from main.models import Item
        
        try:
            # Get all items with github_repo
            items = Item.objects.exclude(github_repo='').exclude(github_repo__isnull=True)
            
            logger.info(f"Found {items.count()} items with GitHub repositories")
            
            if items.count() == 0:
                return {
                    'success': True,
                    'items_processed': 0,
                    'items_synced': 0,
                    'total_files_synced': 0,
                    'errors': []
                }
            
            items_synced = 0
            total_files_synced = 0
            errors = []
            
            for item in items:
                try:
                    logger.info(f"Syncing item: {item.title} ({item.id})")
                    result = self.sync_item(item_id=str(item.id), uploaded_by=uploaded_by)
                    
                    if result.get('success'):
                        items_synced += 1
                        total_files_synced += result.get('files_synced', 0)
                        
                        if result.get('errors'):
                            errors.extend(result['errors'])
                    else:
                        error_msg = f"Item {item.title}: {result.get('error', 'Unknown error')}"
                        errors.append(error_msg)
                        
                except Exception as e:
                    error_msg = f"Error syncing item {item.title} ({item.id}): {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            logger.info(f"All items sync completed. Synced {items_synced}/{items.count()} items, {total_files_synced} total files")
            
            return {
                'success': True,
                'items_processed': items.count(),
                'items_synced': items_synced,
                'total_files_synced': total_files_synced,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error syncing all items: {str(e)}")
            raise GitHubDocSyncServiceError(
                "Failed to sync all items",
                details=str(e)
            )
