"""
GitHub API Service for IdeaGraph

This module provides integration with GitHub REST API v3 for repository and issue management.
"""

import logging
from typing import Optional, Dict, Any, List

import requests


logger = logging.getLogger('github_service')


class GitHubServiceError(Exception):
    """Base exception for GitHub Service errors"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to structured dictionary"""
        return {
            'success': False,
            'error': self.message,
            'details': self.details or ''
        }


class GitHubService:
    """
    GitHub API Service
    
    Provides methods for:
    - Repository operations (list repositories)
    - Issue operations (create, get, list issues)
    - Bearer token authentication
    """
    
    REQUEST_TIMEOUT = 10  # seconds
    
    def __init__(self, settings=None):
        """
        Initialize GitHubService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise GitHubServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise GitHubServiceError("No settings found in database")
        
        if not self.settings.github_api_enabled:
            raise GitHubServiceError("GitHub API is not enabled in settings")
        
        # Validate required configuration
        if not self.settings.github_token:
            raise GitHubServiceError(
                "GitHub API configuration incomplete",
                details="github_token is required"
            )
        
        self.token = self.settings.github_token
        self.base_url = self.settings.github_api_base_url or 'https://api.github.com'
        self.default_owner = self.settings.github_default_owner
        self.default_repo = self.settings.github_default_repo
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> requests.Response:
        """
        Make authenticated request to GitHub API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base_url)
            json_data: JSON data for request body
            params: Query parameters
            
        Returns:
            Response object
            
        Raises:
            GitHubServiceError: On request failure
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        
        try:
            logger.info(f"{method} {url}")
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=self.REQUEST_TIMEOUT
            )
            
            logger.info(f"Response: {response.status_code}")
            return response
            
        except requests.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise GitHubServiceError("Network error during API request", details=str(e))
    
    def _handle_response(
        self,
        response: requests.Response,
        success_codes: List[int] = [200]
    ) -> Dict[str, Any]:
        """
        Handle API response and convert to standard format
        
        Args:
            response: Response object from GitHub API
            success_codes: List of HTTP status codes considered successful
            
        Returns:
            Dict with parsed response data
            
        Raises:
            GitHubServiceError: On error response
        """
        if response.status_code in success_codes:
            return response.json() if response.content else {}
        
        # Handle error responses
        error_message = "GitHub API request failed"
        details = response.text
        
        try:
            error_data = response.json()
            error_message = error_data.get('message', error_message)
        except:
            pass
        
        logger.error(f"GitHub API error {response.status_code}: {error_message}")
        raise GitHubServiceError(
            error_message,
            status_code=response.status_code,
            details=details
        )
    
    # Repository Methods
    
    def get_repositories(self, owner: Optional[str] = None, per_page: int = 30, page: int = 1) -> Dict[str, Any]:
        """
        Get list of repositories accessible with the configured token
        
        Args:
            owner: Optional owner filter (username or organization)
            per_page: Number of results per page (max 100)
            page: Page number for pagination
            
        Returns:
            Dict with success status and list of repositories
        """
        per_page = min(per_page, 100)  # GitHub API max
        
        if owner:
            # Get repositories for specific user/org
            endpoint = f"users/{owner}/repos"
        else:
            # Get repositories accessible to authenticated user
            endpoint = "user/repos"
        
        params = {
            'per_page': per_page,
            'page': page,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            repos = self._handle_response(response)
            
            return {
                'success': True,
                'repositories': repos,
                'count': len(repos)
            }
            
        except GitHubServiceError:
            raise
        except Exception as e:
            logger.error(f"Error listing repositories: {str(e)}")
            raise GitHubServiceError("Error listing repositories", details=str(e))
    
    # Issue Methods
    
    def create_issue(
        self,
        title: str,
        body: str,
        repo: Optional[str] = None,
        owner: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        milestone: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new issue in a GitHub repository
        
        Args:
            title: Issue title
            body: Issue body/description
            repo: Repository name (uses default if not provided)
            owner: Repository owner (uses default if not provided)
            labels: List of label names
            assignees: List of assignee usernames
            milestone: Milestone number (GitHub milestone number, not ID)
            
        Returns:
            Dict with success status and created issue data
        """
        owner = owner or self.default_owner
        repo = repo or self.default_repo
        
        if not owner or not repo:
            raise GitHubServiceError(
                "Repository information required",
                details="owner and repo must be provided or configured as defaults"
            )
        
        endpoint = f"repos/{owner}/{repo}/issues"
        
        issue_data = {
            'title': title,
            'body': body
        }
        
        if labels:
            issue_data['labels'] = labels
        
        if assignees:
            issue_data['assignees'] = assignees
        
        if milestone:
            issue_data['milestone'] = milestone
        
        try:
            response = self._make_request('POST', endpoint, json_data=issue_data)
            issue = self._handle_response(response, success_codes=[201])
            
            logger.info(f"Created issue #{issue.get('number')} in {owner}/{repo}")
            return {
                'success': True,
                'issue': issue,
                'issue_number': issue.get('number'),
                'url': issue.get('html_url')
            }
            
        except GitHubServiceError:
            raise
        except Exception as e:
            logger.error(f"Error creating issue: {str(e)}")
            raise GitHubServiceError("Error creating issue", details=str(e))
    
    def get_issue(
        self,
        issue_number: int,
        repo: Optional[str] = None,
        owner: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get details of a specific issue
        
        Args:
            issue_number: Issue number
            repo: Repository name (uses default if not provided)
            owner: Repository owner (uses default if not provided)
            
        Returns:
            Dict with success status and issue data
        """
        owner = owner or self.default_owner
        repo = repo or self.default_repo
        
        if not owner or not repo:
            raise GitHubServiceError(
                "Repository information required",
                details="owner and repo must be provided or configured as defaults"
            )
        
        endpoint = f"repos/{owner}/{repo}/issues/{issue_number}"
        
        try:
            response = self._make_request('GET', endpoint)
            issue = self._handle_response(response)
            
            return {
                'success': True,
                'issue': issue
            }
            
        except GitHubServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting issue: {str(e)}")
            raise GitHubServiceError("Error getting issue", details=str(e))
    
    def list_issues(
        self,
        repo: Optional[str] = None,
        owner: Optional[str] = None,
        state: str = 'open',
        labels: Optional[List[str]] = None,
        per_page: int = 30,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        List issues in a repository
        
        Args:
            repo: Repository name (uses default if not provided)
            owner: Repository owner (uses default if not provided)
            state: Issue state filter ('open', 'closed', 'all')
            labels: Filter by labels
            per_page: Number of results per page (max 100)
            page: Page number for pagination
            
        Returns:
            Dict with success status and list of issues
        """
        owner = owner or self.default_owner
        repo = repo or self.default_repo
        
        if not owner or not repo:
            raise GitHubServiceError(
                "Repository information required",
                details="owner and repo must be provided or configured as defaults"
            )
        
        per_page = min(per_page, 100)  # GitHub API max
        
        endpoint = f"repos/{owner}/{repo}/issues"
        
        params = {
            'state': state,
            'per_page': per_page,
            'page': page,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        if labels:
            params['labels'] = ','.join(labels)
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            issues = self._handle_response(response)
            
            return {
                'success': True,
                'issues': issues,
                'count': len(issues)
            }
            
        except GitHubServiceError:
            raise
        except Exception as e:
            logger.error(f"Error listing issues: {str(e)}")
            raise GitHubServiceError("Error listing issues", details=str(e))
    
    # Pull Request Methods
    
    def get_pull_request(
        self,
        pr_number: int,
        repo: Optional[str] = None,
        owner: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get details of a specific pull request
        
        Args:
            pr_number: Pull request number
            repo: Repository name (uses default if not provided)
            owner: Repository owner (uses default if not provided)
            
        Returns:
            Dict with success status and pull request data
        """
        owner = owner or self.default_owner
        repo = repo or self.default_repo
        
        if not owner or not repo:
            raise GitHubServiceError(
                "Repository information required",
                details="owner and repo must be provided or configured as defaults"
            )
        
        endpoint = f"repos/{owner}/{repo}/pulls/{pr_number}"
        
        try:
            response = self._make_request('GET', endpoint)
            pull_request = self._handle_response(response)
            
            return {
                'success': True,
                'pull_request': pull_request
            }
            
        except GitHubServiceError:
            raise
        except Exception as e:
            logger.error(f"Error getting pull request: {str(e)}")
            raise GitHubServiceError("Error getting pull request", details=str(e))
    
    def list_pull_requests(
        self,
        repo: Optional[str] = None,
        owner: Optional[str] = None,
        state: str = 'open',
        per_page: int = 30,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        List pull requests in a repository
        
        Args:
            repo: Repository name (uses default if not provided)
            owner: Repository owner (uses default if not provided)
            state: Pull request state filter ('open', 'closed', 'all')
            per_page: Number of results per page (max 100)
            page: Page number for pagination
            
        Returns:
            Dict with success status and list of pull requests
        """
        owner = owner or self.default_owner
        repo = repo or self.default_repo
        
        if not owner or not repo:
            raise GitHubServiceError(
                "Repository information required",
                details="owner and repo must be provided or configured as defaults"
            )
        
        per_page = min(per_page, 100)  # GitHub API max
        
        endpoint = f"repos/{owner}/{repo}/pulls"
        
        params = {
            'state': state,
            'per_page': per_page,
            'page': page,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            pull_requests = self._handle_response(response)
            
            return {
                'success': True,
                'pull_requests': pull_requests,
                'count': len(pull_requests)
            }
            
        except GitHubServiceError:
            raise
        except Exception as e:
            logger.error(f"Error listing pull requests: {str(e)}")
            raise GitHubServiceError("Error listing pull requests", details=str(e))
