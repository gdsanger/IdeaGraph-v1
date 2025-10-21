"""
OpenAI API Service for IdeaGraph

This module provides integration with OpenAI API for AI-powered text and code processing.
Includes automatic fallback to KiGate agents when available.
"""

import logging
from typing import Optional, Dict, Any

import requests


logger = logging.getLogger('openai_service')


class OpenAIServiceError(Exception):
    """Base exception for OpenAI Service errors"""
    
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


class OpenAIService:
    """
    OpenAI API Service
    
    Provides methods for:
    - Direct OpenAI API queries
    - Automatic routing to KiGate agents when available
    - Model information retrieval
    """
    
    def __init__(self, settings=None):
        """
        Initialize OpenAIService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise OpenAIServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise OpenAIServiceError("No settings found in database")
        
        if not self.settings.openai_api_enabled:
            raise OpenAIServiceError("OpenAI API is not enabled in settings")
        
        # Validate required configuration
        if not self.settings.openai_api_key:
            raise OpenAIServiceError(
                "OpenAI API configuration incomplete",
                details="openai_api_key is required"
            )
        
        self.api_key = self.settings.openai_api_key
        self.org_id = self.settings.openai_org_id
        self.base_url = self.settings.openai_api_base_url or 'https://api.openai.com/v1'
        self.default_model = self.settings.openai_default_model or 'gpt-4'
        self.timeout = self.settings.openai_api_timeout or 30
        
        # Remove trailing slash from base_url if present
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with authentication
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Add organization header if org_id is set
        if self.org_id:
            headers['OpenAI-Organization'] = self.org_id
        
        return headers
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to OpenAI API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data (for POST, PUT)
            params: Query parameters (for GET)
        
        Returns:
            Response data as dictionary
        
        Raises:
            OpenAIServiceError: If request fails
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
                error_msg = f"OpenAI API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    details = error_data.get('error', {}).get('message', response.text)
                except:
                    details = response.text
                
                logger.error(f"{error_msg}: {details}")
                raise OpenAIServiceError(
                    error_msg,
                    status_code=response.status_code,
                    details=details
                )
            
            # Parse response
            return response.json()
            
        except requests.exceptions.Timeout:
            error_msg = f"Request to OpenAI API timed out after {self.timeout} seconds"
            logger.error(error_msg)
            raise OpenAIServiceError(error_msg, status_code=408)
        
        except requests.exceptions.ConnectionError as e:
            error_msg = "Failed to connect to OpenAI API"
            logger.error(f"{error_msg}: {str(e)}")
            raise OpenAIServiceError(error_msg, details=str(e), status_code=503)
        
        except requests.exceptions.RequestException as e:
            error_msg = "OpenAI API request failed"
            logger.error(f"{error_msg}: {str(e)}")
            raise OpenAIServiceError(error_msg, details=str(e))
    
    def _check_kigate_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Check if a specific KiGate agent exists
        
        Args:
            agent_name: Name of the agent to check
        
        Returns:
            Agent details if found, None otherwise
        """
        # Check if KiGate is enabled
        if not self.settings.kigate_api_enabled:
            return None
        
        try:
            from core.services.kigate_service import KiGateService, KiGateServiceError
            
            kigate = KiGateService(self.settings)
            result = kigate.get_agent_details(agent_name)
            
            if result.get('success'):
                logger.info(f"Found KiGate agent: {agent_name}")
                return result.get('agent')
            
            return None
            
        except KiGateServiceError as e:
            # Agent not found or other KiGate error - continue with direct OpenAI
            logger.info(f"KiGate agent '{agent_name}' not available: {e.message}")
            return None
        except Exception as e:
            # Any other error - log and continue with direct OpenAI
            logger.warning(f"Error checking KiGate agent: {str(e)}")
            return None
    
    def query(
        self, 
        prompt: str, 
        model: Optional[str] = None, 
        user_id: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a query to OpenAI API
        
        Args:
            prompt: The prompt/question to send to the AI
            model: Model to use (defaults to settings default_model)
            user_id: User identifier for logging/tracking
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
        
        Returns:
            Dictionary containing:
                - success: bool
                - result: str (AI response text)
                - tokens_used: int
                - model: str
                - source: str ("openai")
        
        Raises:
            OpenAIServiceError: If request fails
        """
        if not prompt:
            raise OpenAIServiceError("prompt is required", status_code=400)
        
        model_name = model or self.default_model
        
        # Prepare request data
        data = {
            'model': model_name,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': temperature
        }
        
        if max_tokens:
            data['max_tokens'] = max_tokens
        
        try:
            logger.info(f"Querying OpenAI with model: {model_name}, user: {user_id or 'unknown'}")
            response = self._make_request('POST', '/chat/completions', data=data)
            
            # Extract result
            result_text = response['choices'][0]['message']['content']
            tokens_used = response['usage']['total_tokens']
            
            logger.info(f"Query successful. Tokens used: {tokens_used}")
            
            return {
                'success': True,
                'result': result_text,
                'tokens_used': tokens_used,
                'model': model_name,
                'source': 'openai'
            }
            
        except OpenAIServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in query: {str(e)}")
            raise OpenAIServiceError("Failed to execute query", details=str(e))
    
    def query_with_agent(
        self,
        prompt: str,
        agent_name: str,
        user_id: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute query with automatic KiGate agent routing if available
        
        First checks if the specified KiGate agent exists. If it does, routes
        the query through KiGate. Otherwise, falls back to direct OpenAI API.
        
        Args:
            prompt: The prompt/question to send to the AI
            agent_name: Name of the KiGate agent to use
            user_id: User identifier for logging/tracking
            model: Model to use for fallback (defaults to settings default_model)
        
        Returns:
            Dictionary containing:
                - success: bool
                - result: str (AI response text)
                - tokens_used: int (if available)
                - model: str
                - source: str ("kigate" or "openai")
        
        Raises:
            OpenAIServiceError: If request fails
        """
        if not prompt:
            raise OpenAIServiceError("prompt is required", status_code=400)
        if not agent_name:
            raise OpenAIServiceError("agent_name is required", status_code=400)
        
        # Check if KiGate agent exists
        agent_details = self._check_kigate_agent(agent_name)
        
        if agent_details:
            # Route through KiGate
            try:
                from core.services.kigate_service import KiGateService, KiGateServiceError
                
                kigate = KiGateService(self.settings)
                
                # Use agent's configured provider and model
                provider = agent_details.get('provider', 'openai')
                agent_model = agent_details.get('model', model or self.default_model)
                
                logger.info(f"Routing to KiGate agent: {agent_name}")
                result = kigate.execute_agent(
                    agent_name=agent_name,
                    provider=provider,
                    model=agent_model,
                    message=prompt,
                    user_id=user_id or 'unknown'
                )
                
                return {
                    'success': True,
                    'result': result.get('result', ''),
                    'tokens_used': result.get('tokens_used', 0),
                    'model': agent_model,
                    'source': 'kigate',
                    'agent': agent_name
                }
                
            except KiGateServiceError as e:
                # KiGate execution failed, fall back to direct OpenAI
                logger.warning(f"KiGate execution failed, falling back to OpenAI: {e.message}")
        
        # Fallback to direct OpenAI query
        logger.info(f"Using direct OpenAI API (agent '{agent_name}' not available)")
        result = self.query(prompt=prompt, model=model, user_id=user_id)
        result['agent_requested'] = agent_name
        return result
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a chat completion request to OpenAI API
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model to use (defaults to settings default_model)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
        
        Returns:
            Dictionary containing:
                - success: bool
                - content: str (AI response text)
                - tokens_used: int
                - model: str
        
        Raises:
            OpenAIServiceError: If request fails
        """
        if not messages:
            raise OpenAIServiceError("messages list is required", status_code=400)
        
        model_name = model or self.default_model
        
        # Prepare request data
        data = {
            'model': model_name,
            'messages': messages,
            'temperature': temperature
        }
        
        if max_tokens:
            data['max_tokens'] = max_tokens
        
        try:
            logger.info(f"Chat completion with model: {model_name}")
            response = self._make_request('POST', '/chat/completions', data=data)
            
            # Extract result
            content = response['choices'][0]['message']['content']
            tokens_used = response['usage']['total_tokens']
            
            logger.info(f"Chat completion successful. Tokens used: {tokens_used}")
            
            return {
                'success': True,
                'content': content,
                'tokens_used': tokens_used,
                'model': model_name
            }
            
        except OpenAIServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in chat_completion: {str(e)}")
            raise OpenAIServiceError("Failed to execute chat completion", details=str(e))
    
    def get_models(self) -> Dict[str, Any]:
        """
        Get list of available OpenAI models
        
        Returns:
            Dictionary containing:
                - success: bool
                - models: list of model objects
        
        Raises:
            OpenAIServiceError: If request fails
        """
        try:
            logger.info("Fetching available models from OpenAI")
            response = self._make_request('GET', '/models')
            
            # Filter to only chat models (gpt-* models)
            all_models = response.get('data', [])
            chat_models = [
                m for m in all_models 
                if m.get('id', '').startswith('gpt-')
            ]
            
            logger.info(f"Retrieved {len(chat_models)} chat models")
            
            return {
                'success': True,
                'models': chat_models
            }
            
        except OpenAIServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_models: {str(e)}")
            raise OpenAIServiceError("Failed to retrieve models", details=str(e))
