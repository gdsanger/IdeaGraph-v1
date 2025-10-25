"""
KiGate API Service for IdeaGraph

This module provides integration with KiGate API for agent-based AI workflows.
"""

import logging
from typing import Optional, Dict, Any, List

import requests


logger = logging.getLogger('kigate_service')


class KiGateServiceError(Exception):
    """Base exception for KiGate Service errors"""
    
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


class KiGateService:
    """
    KiGate API Service
    
    Provides methods for:
    - Listing available agents
    - Executing agents with specified parameters
    - Getting agent details
    """
    
    def __init__(self, settings=None):
        """
        Initialize KiGateService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise KiGateServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise KiGateServiceError("No settings found in database")
        
        if not self.settings.kigate_api_enabled:
            raise KiGateServiceError("KiGate API is not enabled in settings")
        
        # Validate required configuration
        if not self.settings.kigate_api_token:
            raise KiGateServiceError(
                "KiGate API configuration incomplete",
                details="kigate_api_token is required"
            )
        
        self.token = self.settings.kigate_api_token
        self.base_url = self.settings.kigate_api_base_url or 'http://localhost:8000'
        self.timeout = self.settings.kigate_api_timeout
        
        # Remove trailing slash from base_url if present
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with authentication
        
        Returns:
            Dictionary of HTTP headers
        """
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to KiGate API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data (for POST, PUT)
            params: Query parameters (for GET)
        
        Returns:
            Response data as dictionary
        
        Raises:
            KiGateServiceError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"Making {method} request to {url}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=data,
                params=params,
                timeout=self.timeout
            )
            
            # Log response status
            logger.info(f"Response status: {response.status_code}")
            
            # Handle error responses
            if response.status_code >= 400:
                error_msg = f"KiGate API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    details = error_data.get('detail', response.text)
                except:
                    details = response.text
                
                logger.error(f"{error_msg}: {details}")
                raise KiGateServiceError(
                    error_msg,
                    status_code=response.status_code,
                    details=details
                )
            
            # Parse response
            return response.json()
            
        except requests.exceptions.Timeout:
            error_msg = f"Request to KiGate API timed out after {self.timeout} seconds"
            logger.error(error_msg)
            raise KiGateServiceError(error_msg, status_code=408)
        
        except requests.exceptions.ConnectionError as e:
            error_msg = "Failed to connect to KiGate API"
            logger.error(f"{error_msg}: {str(e)}")
            raise KiGateServiceError(error_msg, details=str(e), status_code=503)
        
        except requests.exceptions.RequestException as e:
            error_msg = "KiGate API request failed"
            logger.error(f"{error_msg}: {str(e)}")
            raise KiGateServiceError(error_msg, details=str(e))
    
    def get_agents(self) -> Dict[str, Any]:
        """
        Get list of all available agents from KiGate API
        
        Returns:
            Dictionary containing agent list and metadata
            
        Example response:
            {
                "success": True,
                "agents": [
                    {
                        "name": "translation-agent",
                        "description": "...",
                        "provider": "openai",
                        "model": "gpt-4"
                    },
                    ...
                ]
            }
        
        Raises:
            KiGateServiceError: If request fails
        """
        try:
            response = self._make_request('GET', '/api/agents')
            logger.info(f"Retrieved {len(response.get('agents', []))} agents")
            return {
                'success': True,
                'agents': response.get('agents', [])
            }
        except KiGateServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_agents: {str(e)}")
            raise KiGateServiceError("Failed to retrieve agents", details=str(e))
    
    def execute_agent(
        self,
        agent_name: str,
        provider: str,
        model: str,
        message: str,
        user_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a specific agent with given parameters
        
        Args:
            agent_name: Name of the agent to execute
            provider: AI provider (e.g., "openai", "claude")
            model: AI model (e.g., "gpt-4", "claude-3-sonnet")
            message: User message/prompt for the agent
            user_id: User identifier
            parameters: Optional additional parameters for the agent
        
        Returns:
            Dictionary containing execution result
            
        Example response:
            {
                "success": True,
                "job_id": "job-123-abc",
                "agent": "translation-agent",
                "provider": "openai",
                "model": "gpt-4",
                "status": "completed",
                "result": "..."
            }
        
        Raises:
            KiGateServiceError: If request fails
        """
        # Validate required parameters
        if not agent_name:
            raise KiGateServiceError("agent_name is required", status_code=400)
        if not provider:
            raise KiGateServiceError("provider is required", status_code=400)
        if not model:
            raise KiGateServiceError("model is required", status_code=400)
        if not message:
            raise KiGateServiceError("message is required", status_code=400)
        if not user_id:
            raise KiGateServiceError("user_id is required", status_code=400)
        
        # Prepare request data
        data = {
            'agent_name': agent_name,
            'provider': provider,
            'model': model,
            'message': message,
            'user_id': user_id
        }
        
        # Add optional parameters if provided
        if parameters:
            data['parameters'] = parameters
        
        try:
            logger.info(f"Executing agent: {agent_name} with provider: {provider}, model: {model}")
            response = self._make_request('POST', '/agent/execute', data=data)
            
            return {
                'success': True,
                'job_id': response.get('job_id'),
                'agent': response.get('agent'),
                'provider': response.get('provider'),
                'model': response.get('model'),
                'status': response.get('status'),
                'result': response.get('result')
            }
        except KiGateServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in execute_agent: {str(e)}")
            raise KiGateServiceError("Failed to execute agent", details=str(e))
    
    def get_agent_details(self, agent_name: str) -> Dict[str, Any]:
        """
        Get detailed configuration of a specific agent
        
        Args:
            agent_name: Name of the agent
        
        Returns:
            Dictionary containing agent details
            
        Example response:
            {
                "success": True,
                "agent": {
                    "name": "translation-agent",
                    "description": "...",
                    "role": "...",
                    "task": "...",
                    "provider": "openai",
                    "model": "gpt-4",
                    "parameters": [...]
                }
            }
        
        Raises:
            KiGateServiceError: If request fails
        """
        if not agent_name:
            raise KiGateServiceError("agent_name is required", status_code=400)
        
        try:
            logger.info(f"Getting details for agent: {agent_name}")
            response = self._make_request('GET', f'/api/agents/{agent_name}')
            
            return {
                'success': True,
                'agent': response
            }
        except KiGateServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_agent_details: {str(e)}")
            raise KiGateServiceError("Failed to retrieve agent details", details=str(e))
