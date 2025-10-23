"""
Web Search Adapter for IdeaGraph

This module provides web search functionality using:
- Google Custom Search API (Google PSE)
- Brave Search API (fallback)
"""

import logging
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger('web_search_adapter')


class WebSearchAdapterError(Exception):
    """Base exception for Web Search Adapter errors"""
    
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


class WebSearchAdapter:
    """
    Web Search Adapter
    
    Provides web search functionality using external search APIs:
    - Google Custom Search API (primary)
    - Brave Search API (fallback)
    """
    
    def __init__(self, settings=None):
        """
        Initialize WebSearchAdapter with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise WebSearchAdapterError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise WebSearchAdapterError("No settings found in database")
        
        # Get search API configuration from settings
        # Fall back to environment variables if not set in settings
        import os
        self.google_api_key = getattr(self.settings, 'google_search_api_key', '') or os.environ.get('GOOGLE_SEARCH_API_KEY', '')
        self.google_cx = getattr(self.settings, 'google_search_cx', '') or os.environ.get('GOOGLE_SEARCH_CX', '')
        self.brave_api_key = os.environ.get('BRAVE_SEARCH_API_KEY', '')
    
    def search_google(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Perform search using Google Custom Search API
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
        
        Returns:
            Dictionary containing search results
        
        Raises:
            WebSearchAdapterError: If search fails
        """
        if not self.google_api_key or not self.google_cx:
            raise WebSearchAdapterError(
                "Google Search API not configured",
                details="GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX required"
            )
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_api_key,
                'cx': self.google_cx,
                'q': query,
                'num': min(max_results, 10)  # Google API max is 10
            }
            
            logger.info(f"Searching Google for: {query}")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                raise WebSearchAdapterError(
                    f"Google Search API returned status {response.status_code}",
                    details=response.text
                )
            
            data = response.json()
            items = data.get('items', [])
            
            results = []
            for item in items:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
            
            logger.info(f"Google Search returned {len(results)} results")
            
            return {
                'success': True,
                'results': results,
                'total_results': len(results),
                'provider': 'google'
            }
            
        except requests.exceptions.Timeout:
            raise WebSearchAdapterError("Google Search API timeout")
        except requests.exceptions.RequestException as e:
            raise WebSearchAdapterError(
                "Google Search API request failed",
                details=str(e)
            )
        except Exception as e:
            raise WebSearchAdapterError(
                "Google Search failed",
                details=str(e)
            )
    
    def search_brave(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Perform search using Brave Search API
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
        
        Returns:
            Dictionary containing search results
        
        Raises:
            WebSearchAdapterError: If search fails
        """
        if not self.brave_api_key:
            raise WebSearchAdapterError(
                "Brave Search API not configured",
                details="BRAVE_SEARCH_API_KEY required"
            )
        
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                'Accept': 'application/json',
                'X-Subscription-Token': self.brave_api_key
            }
            params = {
                'q': query,
                'count': min(max_results, 20)  # Brave API max is 20
            }
            
            logger.info(f"Searching Brave for: {query}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                raise WebSearchAdapterError(
                    f"Brave Search API returned status {response.status_code}",
                    details=response.text
                )
            
            data = response.json()
            web_results = data.get('web', {}).get('results', [])
            
            results = []
            for item in web_results:
                results.append({
                    'title': item.get('title', ''),
                    'url': item.get('url', ''),
                    'snippet': item.get('description', '')
                })
            
            logger.info(f"Brave Search returned {len(results)} results")
            
            return {
                'success': True,
                'results': results,
                'total_results': len(results),
                'provider': 'brave'
            }
            
        except requests.exceptions.Timeout:
            raise WebSearchAdapterError("Brave Search API timeout")
        except requests.exceptions.RequestException as e:
            raise WebSearchAdapterError(
                "Brave Search API request failed",
                details=str(e)
            )
        except Exception as e:
            raise WebSearchAdapterError(
                "Brave Search failed",
                details=str(e)
            )
    
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Perform web search using available search provider
        
        Tries Google first, falls back to Brave if Google is unavailable
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
        
        Returns:
            Dictionary containing search results
        
        Raises:
            WebSearchAdapterError: If all search providers fail
        """
        errors = []
        
        # Try Google first
        if self.google_api_key and self.google_cx:
            try:
                return self.search_google(query, max_results)
            except WebSearchAdapterError as e:
                logger.warning(f"Google search failed: {e.message}")
                errors.append(f"Google: {e.message}")
        
        # Fallback to Brave
        if self.brave_api_key:
            try:
                return self.search_brave(query, max_results)
            except WebSearchAdapterError as e:
                logger.warning(f"Brave search failed: {e.message}")
                errors.append(f"Brave: {e.message}")
        
        # If both failed, raise error
        error_details = "; ".join(errors) if errors else "No search provider configured"
        raise WebSearchAdapterError(
            "All search providers failed or not configured",
            details=error_details
        )
