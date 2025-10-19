"""
Sentry API Integration Service for IdeaGraph

This service integrates with Sentry's REST API to fetch error events and issues.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from core.logger_config import get_logger

logger = get_logger('sentry_service')


class SentryService:
    """Service to interact with Sentry API"""
    
    def __init__(self, dsn: str = None, auth_token: str = None):
        """
        Initialize the Sentry service
        
        Args:
            dsn: Sentry DSN (will extract org/project from it)
            auth_token: Sentry API authentication token
        """
        self.dsn = dsn
        self.auth_token = auth_token
        self.base_url = "https://sentry.io/api/0"
        
        # Parse DSN to extract organization and project
        self.organization = None
        self.project_slug = None
        
        if dsn:
            self._parse_dsn(dsn)
        
        logger.info(f"Sentry Service initialized for org: {self.organization}, project: {self.project_slug}")
    
    def _parse_dsn(self, dsn: str):
        """
        Parse Sentry DSN to extract organization and project info
        
        DSN format: https://<key>@<org>.ingest.sentry.io/<project_id>
        """
        try:
            # Extract organization from the DSN
            if '@' in dsn and '.ingest.sentry.io' in dsn:
                parts = dsn.split('@')[1].split('.ingest.sentry.io')
                self.organization = parts[0]
                
                # Note: Project ID from DSN is numeric, but we need the slug
                # This will need to be configured separately or fetched from API
                logger.info(f"Extracted organization from DSN: {self.organization}")
            else:
                logger.warning("Could not parse organization from DSN")
        except Exception as e:
            logger.error(f"Error parsing DSN: {e}", exc_info=True)
    
    def configure(self, organization: str, project_slug: str, auth_token: str):
        """
        Manually configure Sentry connection
        
        Args:
            organization: Sentry organization slug
            project_slug: Sentry project slug
            auth_token: API authentication token
        """
        self.organization = organization
        self.project_slug = project_slug
        self.auth_token = auth_token
        logger.info(f"Sentry configured for {organization}/{project_slug}")
    
    def _get_headers(self) -> Dict:
        """Get HTTP headers for API requests"""
        if not self.auth_token:
            logger.error("No auth token configured for Sentry API")
            return {}
        
        return {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json',
        }
    
    def test_connection(self) -> bool:
        """
        Test the Sentry API connection
        
        Returns:
            True if connection is successful
        """
        if not self.organization or not self.auth_token:
            logger.error("Sentry not fully configured")
            return False
        
        try:
            url = f"{self.base_url}/organizations/{self.organization}/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                logger.info("Sentry API connection successful")
                return True
            else:
                logger.error(f"Sentry API returned status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error testing Sentry connection: {e}", exc_info=True)
            return False
    
    def get_projects(self) -> List[Dict]:
        """
        Get list of projects in the organization
        
        Returns:
            List of project information
        """
        if not self.organization or not self.auth_token:
            logger.error("Sentry not fully configured")
            return []
        
        try:
            url = f"{self.base_url}/organizations/{self.organization}/projects/"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                projects = response.json()
                logger.info(f"Retrieved {len(projects)} projects from Sentry")
                return projects
            else:
                logger.error(f"Failed to get projects: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching projects: {e}", exc_info=True)
            return []
    
    def get_issues(
        self,
        hours_back: int = 24,
        limit: int = 100,
        query: str = ""
    ) -> List[Dict]:
        """
        Get issues from Sentry
        
        Args:
            hours_back: Number of hours to look back
            limit: Maximum number of issues to retrieve
            query: Additional query parameters (e.g., "is:unresolved")
            
        Returns:
            List of issue data
        """
        if not self.organization or not self.project_slug or not self.auth_token:
            logger.error("Sentry not fully configured")
            return []
        
        try:
            # Build query with time range
            since = datetime.utcnow() - timedelta(hours=hours_back)
            time_query = f"timestamp:>{since.isoformat()}"
            full_query = f"{query} {time_query}".strip()
            
            url = f"{self.base_url}/projects/{self.organization}/{self.project_slug}/issues/"
            params = {
                'query': full_query,
                'limit': limit,
                'statsPeriod': f'{hours_back}h',
            }
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                issues = response.json()
                logger.info(f"Retrieved {len(issues)} issues from Sentry")
                return issues
            else:
                logger.error(f"Failed to get issues: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching issues: {e}", exc_info=True)
            return []
    
    def get_events_for_issue(self, issue_id: str, limit: int = 10) -> List[Dict]:
        """
        Get events for a specific issue
        
        Args:
            issue_id: Sentry issue ID
            limit: Maximum number of events to retrieve
            
        Returns:
            List of event data
        """
        if not self.organization or not self.project_slug or not self.auth_token:
            logger.error("Sentry not fully configured")
            return []
        
        try:
            url = f"{self.base_url}/organizations/{self.organization}/issues/{issue_id}/events/"
            params = {'limit': limit}
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                events = response.json()
                logger.info(f"Retrieved {len(events)} events for issue {issue_id}")
                return events
            else:
                logger.error(f"Failed to get events: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching events: {e}", exc_info=True)
            return []
    
    def parse_sentry_event(self, event: Dict) -> Dict:
        """
        Parse a Sentry event into our log entry format
        
        Args:
            event: Raw Sentry event data
            
        Returns:
            Dictionary with parsed log entry data
        """
        try:
            # Extract exception information
            exception_info = {}
            if 'exception' in event and event['exception'].get('values'):
                exc = event['exception']['values'][0]
                exception_info = {
                    'exception_type': exc.get('type', ''),
                    'exception_value': exc.get('value', ''),
                    'stack_trace': self._format_stacktrace(exc.get('stacktrace', {})),
                }
            
            # Extract metadata
            metadata = event.get('metadata', {})
            
            return {
                'timestamp': datetime.fromisoformat(event['dateCreated'].replace('Z', '+00:00')),
                'level': event.get('level', 'ERROR').upper(),
                'logger_name': event.get('logger', 'unknown'),
                'message': metadata.get('value') or event.get('message', ''),
                'sentry_event_id': event.get('eventID', ''),
                'sentry_issue_id': event.get('groupID', ''),
                **exception_info,
            }
            
        except Exception as e:
            logger.error(f"Error parsing Sentry event: {e}", exc_info=True)
            return {}
    
    def _format_stacktrace(self, stacktrace: Dict) -> str:
        """Format Sentry stacktrace into a readable string"""
        if not stacktrace or 'frames' not in stacktrace:
            return ''
        
        lines = []
        for frame in stacktrace['frames']:
            filename = frame.get('filename', 'unknown')
            function = frame.get('function', 'unknown')
            lineno = frame.get('lineNo', 0)
            context = frame.get('context', [])
            
            lines.append(f'  File "{filename}", line {lineno}, in {function}')
            
            if context:
                for line_info in context:
                    if isinstance(line_info, list) and len(line_info) >= 2:
                        lines.append(f'    {line_info[1]}')
        
        return '\n'.join(lines)
    
    def fetch_and_save_events(self, hours_back: int = 24) -> int:
        """
        Fetch events from Sentry and save to database
        
        Args:
            hours_back: Number of hours to look back
            
        Returns:
            Number of events saved
        """
        from main.models import LogEntry
        
        issues = self.get_issues(hours_back=hours_back)
        saved_count = 0
        
        for issue in issues:
            issue_id = issue.get('id')
            if not issue_id:
                continue
            
            events = self.get_events_for_issue(issue_id, limit=5)
            
            for event in events:
                parsed = self.parse_sentry_event(event)
                if not parsed:
                    continue
                
                try:
                    # Check if event already exists
                    sentry_event_id = parsed.get('sentry_event_id')
                    if sentry_event_id:
                        existing = LogEntry.objects.filter(sentry_event_id=sentry_event_id).first()
                        if existing:
                            logger.debug(f"Event {sentry_event_id} already exists")
                            continue
                    
                    # Create new log entry
                    log_entry = LogEntry.objects.create(
                        source='sentry',
                        level=parsed['level'],
                        logger_name=parsed['logger_name'],
                        message=parsed['message'],
                        timestamp=parsed['timestamp'],
                        exception_type=parsed.get('exception_type', ''),
                        exception_value=parsed.get('exception_value', ''),
                        stack_trace=parsed.get('stack_trace', ''),
                        sentry_event_id=sentry_event_id,
                        sentry_issue_id=parsed.get('sentry_issue_id', ''),
                    )
                    
                    saved_count += 1
                    logger.debug(f"Saved Sentry event: {log_entry}")
                    
                except Exception as e:
                    logger.error(f"Error saving Sentry event: {e}", exc_info=True)
        
        logger.info(f"Saved {saved_count} new Sentry events to database")
        return saved_count
