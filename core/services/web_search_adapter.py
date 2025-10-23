"""
Web Search Adapter for IdeaGraph

This module provides web search functionality using:
- Google Custom Search API (Google PSE)
- Brave Search API (fallback)
"""

import json
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
        
        # Log configuration status (without exposing secrets)
        logger.debug(f"Google API Key configured: {bool(self.google_api_key)} (length: {len(self.google_api_key) if self.google_api_key else 0})")
        logger.debug(f"Google CX configured: {bool(self.google_cx)} (length: {len(self.google_cx) if self.google_cx else 0})")
        logger.debug(f"Brave API Key configured: {bool(self.brave_api_key)}")
    
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
            logger.error("Google Search API credentials not configured")
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
            logger.debug(f"Google Search request URL: {url}")
            logger.debug(f"Google Search params: cx={self.google_cx[:10]}..., num={params['num']}")
            
            response = requests.get(url, params=params, timeout=10)
            
            logger.debug(f"Google Search response status: {response.status_code}")
            
            if response.status_code != 200:
                error_details = response.text
                logger.error(f"Google Search API error (status {response.status_code}): {error_details}")
                
                # Try to parse error details from JSON response
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = error_data['error'].get('message', error_details)
                        error_reason = error_data['error'].get('errors', [{}])[0].get('reason', 'unknown')
                        logger.error(f"Google API Error: {error_msg} (reason: {error_reason})")
                        error_details = f"{error_msg} (reason: {error_reason})"
                except:
                    pass
                
                raise WebSearchAdapterError(
                    f"Google Search API returned status {response.status_code}",
                    details=error_details
                )
            
            data = response.json()
            
            # Log if no items found
            if 'items' not in data:
                logger.warning(f"Google Search returned no items. Response keys: {list(data.keys())}")
                if 'error' in data:
                    logger.error(f"Google Search error in response: {data['error']}")
            
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
            
        except WebSearchAdapterError:
            # Re-raise WebSearchAdapterError as-is
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Google Search API timeout: {str(e)}")
            raise WebSearchAdapterError("Google Search API timeout", details=str(e))
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Search API request failed: {str(e)}")
            raise WebSearchAdapterError(
                "Google Search API request failed",
                details=str(e)
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Google Search response as JSON: {str(e)}")
            raise WebSearchAdapterError(
                "Invalid JSON response from Google Search API",
                details=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in Google Search: {type(e).__name__}: {str(e)}")
            logger.exception("Full traceback:")
            raise WebSearchAdapterError(
                f"Google Search failed: {type(e).__name__}",
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
            logger.error("Brave Search API credentials not configured")
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
            logger.debug(f"Brave Search request URL: {url}")
            logger.debug(f"Brave Search params: count={params['count']}")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            logger.debug(f"Brave Search response status: {response.status_code}")
            
            if response.status_code != 200:
                error_details = response.text
                logger.error(f"Brave Search API error (status {response.status_code}): {error_details}")
                
                # Try to parse error details from JSON response
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_details = error_data['message']
                        logger.error(f"Brave API Error: {error_details}")
                except:
                    pass
                
                raise WebSearchAdapterError(
                    f"Brave Search API returned status {response.status_code}",
                    details=error_details
                )
            
            data = response.json()
            
            # Log if no results found
            if 'web' not in data or 'results' not in data.get('web', {}):
                logger.warning(f"Brave Search returned no web results. Response keys: {list(data.keys())}")
            
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
            
        except WebSearchAdapterError:
            # Re-raise WebSearchAdapterError as-is
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Brave Search API timeout: {str(e)}")
            raise WebSearchAdapterError("Brave Search API timeout", details=str(e))
        except requests.exceptions.RequestException as e:
            logger.error(f"Brave Search API request failed: {str(e)}")
            raise WebSearchAdapterError(
                "Brave Search API request failed",
                details=str(e)
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Brave Search response as JSON: {str(e)}")
            raise WebSearchAdapterError(
                "Invalid JSON response from Brave Search API",
                details=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error in Brave Search: {type(e).__name__}: {str(e)}")
            logger.exception("Full traceback:")
            raise WebSearchAdapterError(
                f"Brave Search failed: {type(e).__name__}",
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
                error_msg = f"{e.message}"
                if e.details:
                    error_msg += f" - Details: {e.details}"
                logger.warning(f"Google search failed: {error_msg}")
                errors.append(f"Google: {e.message}")
        else:
            logger.info("Google Search not configured, skipping")
        
        # Fallback to Brave
        if self.brave_api_key:
            try:
                return self.search_brave(query, max_results)
            except WebSearchAdapterError as e:
                error_msg = f"{e.message}"
                if e.details:
                    error_msg += f" - Details: {e.details}"
                logger.warning(f"Brave search failed: {error_msg}")
                errors.append(f"Brave: {e.message}")
        else:
            logger.info("Brave Search not configured, skipping")
        
        # If both failed, raise error
        error_details = "; ".join(errors) if errors else "No search provider configured"
        logger.error(f"All search providers failed: {error_details}")
        raise WebSearchAdapterError(
            "All search providers failed or not configured",
            details=error_details
        )
