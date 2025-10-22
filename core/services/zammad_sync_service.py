"""
Zammad Synchronization Service for IdeaGraph

This module provides integration with Zammad API for ticket synchronization.
It automatically fetches open tickets from configured groups and creates/updates
tasks in IdeaGraph. Attachments are uploaded to SharePoint via TaskFileService.
"""

import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger('zammad_service')


class ZammadSyncServiceError(Exception):
    """Base exception for Zammad Sync Service errors"""
    
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


class ZammadSyncService:
    """
    Zammad Synchronization Service
    
    Provides methods for:
    - Fetching open tickets from Zammad
    - Creating/updating tasks from tickets
    - Downloading and uploading attachments to SharePoint
    - Updating ticket status in Zammad
    - AI-based task type classification (optional)
    """
    
    REQUEST_TIMEOUT = 30  # seconds
    
    def __init__(self, settings=None):
        """
        Initialize ZammadSyncService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise ZammadSyncServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise ZammadSyncServiceError("No settings found in database")
        
        if not self.settings.zammad_enabled:
            raise ZammadSyncServiceError("Zammad integration is not enabled in settings")
        
        # Validate required configuration
        if not self.settings.zammad_api_url or not self.settings.zammad_api_token:
            raise ZammadSyncServiceError(
                "Zammad configuration incomplete",
                details="zammad_api_url and zammad_api_token are required"
            )
        
        self.api_url = self.settings.zammad_api_url.rstrip('/')
        self.api_token = self.settings.zammad_api_token
        self.groups = [g.strip() for g in self.settings.zammad_groups.split(',') if g.strip()]
        
        logger.info(f"ZammadSyncService initialized with URL: {self.api_url}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> requests.Response:
        """
        Make authenticated request to Zammad API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base URL)
            json_data: JSON data for request body
            params: Query parameters
            
        Returns:
            Response object
            
        Raises:
            ZammadSyncServiceError: If request fails
        """
        url = f"{self.api_url}/api/v1/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Token token={self.api_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            logger.debug(f"Making {method} request to {url}")
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            raise ZammadSyncServiceError(
                "Request timeout",
                details=f"Request to {url} timed out after {self.REQUEST_TIMEOUT}s"
            )
        except requests.exceptions.RequestException as e:
            status_code = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            error_detail = getattr(e.response, 'text', str(e)) if hasattr(e, 'response') else str(e)
            raise ZammadSyncServiceError(
                f"Request failed with status {status_code}" if status_code else "Request failed",
                details=error_detail
            )
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Zammad API
        
        Returns:
            Dict with success status and connection info
        """
        try:
            response = self._make_request('GET', '/users/me')
            user_data = response.json()
            
            return {
                'success': True,
                'message': 'Connection successful',
                'user': user_data.get('login', 'Unknown'),
                'api_url': self.api_url
            }
        except ZammadSyncServiceError as e:
            logger.error(f"Connection test failed: {e.message}")
            return e.to_dict()
    
    def _get_group_id(self, group_name: str) -> Optional[int]:
        """
        Get group ID by name
        
        Args:
            group_name: Name of the group
            
        Returns:
            Group ID or None if not found
        """
        try:
            response = self._make_request('GET', '/groups')
            groups = response.json()
            
            for group in groups:
                if group.get('name') == group_name:
                    return group.get('id')
            
            logger.warning(f"Group '{group_name}' not found")
            return None
        except ZammadSyncServiceError as e:
            logger.error(f"Failed to fetch groups: {e.message}")
            return None
    
    def fetch_open_tickets(self, group_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch open tickets from specified groups
        
        Args:
            group_names: List of group names to fetch tickets from. If None, uses configured groups.
            
        Returns:
            List of ticket dictionaries
        """
        if group_names is None:
            group_names = self.groups
        
        if not group_names:
            logger.warning("No groups configured for ticket fetching")
            return []
        
        all_tickets = []
        
        for group_name in group_names:
            group_id = self._get_group_id(group_name)
            if not group_id:
                continue
            
            try:
                # Search for open tickets in this group
                params = {
                    'query': f'group.name:{group_name} AND state.name:open OR state.name:new',
                    'limit': 100
                }
                response = self._make_request('GET', '/tickets/search', params=params)
                tickets = response.json()
                
                logger.info(f"Found {len(tickets)} open tickets in group '{group_name}'")
                
                # Fetch full ticket details including articles
                for ticket in tickets:
                    ticket_id = ticket.get('id')
                    try:
                        # Get full ticket details
                        ticket_response = self._make_request('GET', f'/tickets/{ticket_id}')
                        full_ticket = ticket_response.json()
                        
                        # Get ticket articles (comments, emails)
                        articles_response = self._make_request('GET', f'/ticket_articles/by_ticket/{ticket_id}')
                        articles = articles_response.json()
                        full_ticket['articles'] = articles
                        
                        all_tickets.append(full_ticket)
                    except ZammadSyncServiceError as e:
                        logger.error(f"Failed to fetch details for ticket {ticket_id}: {e.message}")
                        continue
                
            except ZammadSyncServiceError as e:
                logger.error(f"Failed to fetch tickets from group '{group_name}': {e.message}")
                continue
        
        return all_tickets
    
    def _download_attachment(self, article_id: int, attachment_id: int, filename: str) -> Optional[bytes]:
        """
        Download attachment from Zammad
        
        Args:
            article_id: Article ID
            attachment_id: Attachment ID
            filename: Filename to save as
            
        Returns:
            File content as bytes or None if download failed
        """
        try:
            endpoint = f'/ticket_attachment/{article_id}/{attachment_id}/{filename}'
            response = self._make_request('GET', endpoint)
            
            logger.info(f"Downloaded attachment: {filename} ({len(response.content)} bytes)")
            return response.content
        except Exception as e:
            logger.error(f"Failed to download attachment {filename}: {str(e)}")
            return None
    
    def _classify_task_type(self, title: str, description: str) -> str:
        """
        Classify task type using KI (optional)
        
        Args:
            title: Task title
            description: Task description
            
        Returns:
            Task type (task, feature, bug, ticket, maintenance)
        """
        # Try to use KI classification if enabled
        if self.settings.kigate_api_enabled:
            try:
                from core.services.kigate_service import KiGateService
                kigate = KiGateService(self.settings)
                
                # Use task-type-classifier agent
                result = kigate.call_agent(
                    agent_name='task-type-classifier',
                    payload={
                        'title': title,
                        'description': description
                    }
                )
                
                if result.get('success'):
                    task_type = result.get('data', {}).get('type', 'ticket').lower()
                    logger.info(f"KI classified task as: {task_type}")
                    return task_type
            except Exception as e:
                logger.warning(f"KI classification failed: {str(e)}, defaulting to 'ticket'")
        
        # Default to 'ticket' type
        return 'ticket'
    
    def _find_or_create_section(self, group_name: str):
        """
        Find or create a section for the Zammad group
        
        Args:
            group_name: Zammad group name
            
        Returns:
            Section object
        """
        from main.models import Section
        
        section_name = f"Zammad - {group_name}"
        section, created = Section.objects.get_or_create(name=section_name)
        
        if created:
            logger.info(f"Created new section: {section_name}")
        
        return section
    
    @transaction.atomic
    def sync_ticket_to_task(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronize a Zammad ticket to an IdeaGraph task
        
        Args:
            ticket: Zammad ticket dictionary
            
        Returns:
            Result dictionary with success status and task info
        """
        from main.models import Task, Tag
        
        ticket_id = str(ticket.get('id'))
        title = ticket.get('title', 'Untitled Ticket')
        
        # Get first article body as description
        articles = ticket.get('articles', [])
        description = ""
        if articles:
            # Sort by created_at to get the first article
            sorted_articles = sorted(articles, key=lambda x: x.get('created_at', ''))
            first_article = sorted_articles[0] if sorted_articles else {}
            description = first_article.get('body', '')
        
        # Get group name
        group_name = ticket.get('group', 'Unknown')
        if isinstance(group_name, dict):
            group_name = group_name.get('name', 'Unknown')
        
        # Find or create section
        section = self._find_or_create_section(group_name)
        
        # Build ticket URL
        ticket_url = f"{self.api_url}/#ticket/zoom/{ticket_id}"
        
        try:
            # Check if task already exists
            task = Task.objects.filter(external_id=ticket_id).first()
            
            if task:
                # Update existing task
                task.title = title
                task.description = description
                task.external_url = ticket_url
                task.updated_at = timezone.now()
                task.save()
                logger.info(f"Updated existing task {task.id} for ticket {ticket_id}")
                action = 'updated'
            else:
                # Classify task type
                task_type = self._classify_task_type(title, description)
                
                # Create new task
                task = Task.objects.create(
                    title=title,
                    description=description,
                    type=task_type,
                    section=section,
                    external_id=ticket_id,
                    external_url=ticket_url,
                    status='new'
                )
                logger.info(f"Created new task {task.id} for ticket {ticket_id}")
                action = 'created'
            
            # Process tags
            ticket_tags = ticket.get('tags', [])
            if ticket_tags:
                for tag_name in ticket_tags:
                    tag, _ = Tag.objects.get_or_create(name=tag_name)
                    task.tags.add(tag)
            
            # Process attachments
            attachment_count = 0
            for article in articles:
                attachments = article.get('attachments', [])
                article_id = article.get('id')
                
                for attachment in attachments:
                    attachment_id = attachment.get('id')
                    filename = attachment.get('filename', 'attachment')
                    size = attachment.get('size', 0)
                    content_type = attachment.get('preferences', {}).get('Content-Type', 'application/octet-stream')
                    
                    # Download attachment content
                    file_content = self._download_attachment(article_id, attachment_id, filename)
                    
                    if file_content:
                        try:
                            # Upload to SharePoint via TaskFileService
                            from core.services.task_file_service import TaskFileService, TaskFileServiceError
                            
                            task_file_service = TaskFileService(self.settings)
                            upload_result = task_file_service.upload_file(
                                task=task,
                                file_content=file_content,
                                filename=filename,
                                content_type=content_type,
                                user=None  # System upload, no specific user
                            )
                            
                            if upload_result['success']:
                                attachment_count += 1
                                logger.info(f"Uploaded attachment {filename} to SharePoint")
                            else:
                                logger.error(f"Failed to upload attachment {filename}: {upload_result.get('error')}")
                        
                        except TaskFileServiceError as e:
                            logger.error(f"TaskFileService error for {filename}: {e.message}")
                        except Exception as e:
                            logger.error(f"Unexpected error uploading {filename}: {str(e)}")
            
            logger.info(f"Processed {attachment_count} attachments for task {task.id}")
            
            # Update ticket status in Zammad to "pending reminder" to exclude it from future syncs
            try:
                self._update_ticket_status(ticket_id, 'pending reminder')
            except Exception as e:
                logger.warning(f"Failed to update ticket status in Zammad: {str(e)}")
            
            return {
                'success': True,
                'action': action,
                'task_id': str(task.id),
                'ticket_id': ticket_id,
                'title': title,
                'attachments': attachment_count
            }
            
        except Exception as e:
            logger.error(f"Failed to sync ticket {ticket_id}: {str(e)}")
            return {
                'success': False,
                'ticket_id': ticket_id,
                'error': str(e)
            }
    
    def _update_ticket_status(self, ticket_id: str, status: str):
        """
        Update ticket status in Zammad
        
        Args:
            ticket_id: Ticket ID
            status: New status (e.g., 'open', 'closed')
        """
        try:
            # Get state ID for the status
            response = self._make_request('GET', '/ticket_states')
            states = response.json()
            
            state_id = None
            for state in states:
                if state.get('name', '').lower() == status.lower():
                    state_id = state.get('id')
                    break
            
            if not state_id:
                logger.warning(f"Could not find state ID for status '{status}'")
                return
            
            # Update ticket
            self._make_request(
                'PUT',
                f'/tickets/{ticket_id}',
                json_data={'state_id': state_id}
            )
            logger.info(f"Updated ticket {ticket_id} status to '{status}'")
        except ZammadSyncServiceError as e:
            logger.error(f"Failed to update ticket status: {e.message}")
            raise
    
    def sync_all_tickets(self) -> Dict[str, Any]:
        """
        Sync all open tickets from configured groups
        
        Returns:
            Result dictionary with sync statistics
        """
        logger.info("Starting Zammad ticket synchronization")
        start_time = timezone.now()
        
        # Fetch tickets
        tickets = self.fetch_open_tickets()
        
        results = {
            'success': True,
            'started_at': start_time.isoformat(),
            'total_tickets': len(tickets),
            'created': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }
        
        # Process each ticket
        for ticket in tickets:
            result = self.sync_ticket_to_task(ticket)
            
            if result.get('success'):
                if result.get('action') == 'created':
                    results['created'] += 1
                elif result.get('action') == 'updated':
                    results['updated'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'ticket_id': result.get('ticket_id'),
                    'error': result.get('error')
                })
        
        # Calculate duration
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        results['completed_at'] = end_time.isoformat()
        results['duration_seconds'] = duration
        
        logger.info(
            f"Sync completed: {results['created']} created, "
            f"{results['updated']} updated, {results['failed']} failed "
            f"in {duration:.2f}s"
        )
        
        return results
