"""
Support Advisor Service for IdeaGraph

This module provides AI-powered support analysis for tasks:
- Internal analysis using Weaviate knowledge base (RAG)
- External analysis using web search (Google PSE or Brave API)
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger('support_advisor_service')


class SupportAdvisorServiceError(Exception):
    """Base exception for Support Advisor Service errors"""
    
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


class SupportAdvisorService:
    """
    Support Advisor Service
    
    Provides AI-powered support analysis for tasks:
    - Internal mode: Analyzes task using Weaviate knowledge base
    - External mode: Analyzes task using web search and external sources
    """
    
    def __init__(self, settings=None):
        """
        Initialize SupportAdvisorService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise SupportAdvisorServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise SupportAdvisorServiceError("No settings found in database")
    
    def analyze_internal(
        self,
        task_description: str,
        task_title: str = "",
        user_id: str = "",
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Perform internal support analysis using Weaviate knowledge base
        
        Args:
            task_description: Task description to analyze
            task_title: Optional task title
            user_id: User identifier
            max_results: Maximum number of similar objects to retrieve
        
        Returns:
            Dictionary containing analysis result with recommendations
            
        Example response:
            {
                "success": True,
                "analysis": "### 🧩 Interne Analyse\n...",
                "similar_objects": [
                    {"type": "task", "id": "123", "title": "...", "similarity": 0.95},
                    ...
                ]
            }
        
        Raises:
            SupportAdvisorServiceError: If analysis fails
        """
        try:
            # Step 1: Query Weaviate for similar objects
            from core.services.weaviate_sync_service import WeaviateItemSyncService
            from core.services.weaviate_task_sync_service import WeaviateTaskSyncService
            
            similar_objects = []
            
            # Search for similar tasks
            try:
                task_sync = WeaviateTaskSyncService(self.settings)
                search_query = f"{task_title}\n{task_description}" if task_title else task_description
                task_results = task_sync.search_similar(search_query, n_results=max_results)
                
                if task_results.get('success') and task_results.get('results'):
                    for result in task_results['results']:
                        metadata = result.get('metadata', {})
                        similar_objects.append({
                            'type': 'task',
                            'id': metadata.get('task_id', ''),
                            'title': metadata.get('title', 'N/A'),
                            'description': result.get('document', '')[:200],
                            'similarity': result.get('distance', 0)
                        })
                    logger.info(f"Found {len(task_results['results'])} similar tasks")
            except Exception as e:
                logger.warning(f"Could not search Weaviate tasks: {str(e)}")
            
            # Search for similar items
            try:
                item_sync = WeaviateItemSyncService(self.settings)
                item_results = item_sync.search_similar(search_query, n_results=max_results)
                
                if item_results.get('success') and item_results.get('results'):
                    for result in item_results['results']:
                        metadata = result.get('metadata', {})
                        similar_objects.append({
                            'type': 'item',
                            'id': metadata.get('item_id', ''),
                            'title': metadata.get('title', 'N/A'),
                            'description': result.get('document', '')[:200],
                            'similarity': result.get('distance', 0)
                        })
                    logger.info(f"Found {len(item_results['results'])} similar items")
            except Exception as e:
                logger.warning(f"Could not search Weaviate items: {str(e)}")
            
            # Step 2: Build context from similar objects
            context_text = ""
            if similar_objects:
                context_items = []
                for idx, obj in enumerate(similar_objects[:5], 1):
                    obj_type = obj['type'].capitalize()
                    context_items.append(
                        f"{obj_type} {idx}:\nTitle: {obj['title']}\n"
                        f"Description: {obj['description']}..."
                    )
                context_text = "\n\n".join(context_items)
            
            # Step 3: Use KiGate to analyze with context
            from core.services.kigate_service import KiGateService
            
            kigate = KiGateService(self.settings)
            
            analysis_message = (
                f"Analysiere den folgenden Tasktext im Kontext der vorhandenen "
                f"Datenbankobjekte und liefere Handlungsempfehlungen.\n\n"
                f"Task-Titel: {task_title}\n\n"
                f"Task-Beschreibung:\n{task_description}\n\n"
            )
            
            if context_text:
                analysis_message += (
                    f"--- Kontext aus ähnlichen Objekten ---\n"
                    f"{context_text}\n"
                    f"--- Ende des Kontexts ---\n\n"
                )
            
            analysis_message += (
                f"Erstelle eine strukturierte Analyse mit:\n"
                f"- Mögliche Ursachen\n"
                f"- Ähnliche Tasks oder Issues (falls gefunden)\n"
                f"- Handlungsempfehlungen\n\n"
                f"Formatiere die Antwort in Markdown mit dem Header '### 🧩 Interne Analyse'."
            )
            
            result = kigate.execute_agent(
                agent_name='support-advisor-internal-agent',
                provider='openai',
                model='gpt-4',
                message=analysis_message,
                user_id=user_id or 'system'
            )
            
            if not result.get('success'):
                raise SupportAdvisorServiceError(
                    "Failed to generate internal analysis",
                    details=result.get('error', 'Unknown error')
                )
            
            analysis_text = result.get('result', result.get('response', ''))
            
            return {
                'success': True,
                'analysis': analysis_text,
                'similar_objects': similar_objects[:5],
                'mode': 'internal'
            }
            
        except SupportAdvisorServiceError:
            raise
        except Exception as e:
            logger.error(f"Internal analysis error: {str(e)}")
            raise SupportAdvisorServiceError(
                "Failed to perform internal analysis",
                details=str(e)
            )
    
    def analyze_external(
        self,
        task_description: str,
        task_title: str = "",
        user_id: str = "",
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Perform external support analysis using web search
        
        Args:
            task_description: Task description to analyze
            task_title: Optional task title
            user_id: User identifier
            max_results: Maximum number of search results to retrieve
        
        Returns:
            Dictionary containing analysis result with recommendations
            
        Example response:
            {
                "success": True,
                "analysis": "### 🌍 Externe Analyse\n...",
                "sources": [
                    {"title": "...", "url": "...", "snippet": "..."},
                    ...
                ]
            }
        
        Raises:
            SupportAdvisorServiceError: If analysis fails
        """
        try:
            # Step 1: Perform web search
            from core.services.web_search_adapter import WebSearchAdapter
            
            search_adapter = WebSearchAdapter(self.settings)
            search_query = f"{task_title} {task_description}"[:200]  # Limit query length
            
            search_results = search_adapter.search(search_query, max_results=max_results)
            
            if not search_results.get('success'):
                raise SupportAdvisorServiceError(
                    "Web search failed",
                    details=search_results.get('error', 'Unknown error')
                )
            
            sources = search_results.get('results', [])
            
            # Step 2: Build context from search results
            context_text = ""
            if sources:
                context_items = []
                for idx, source in enumerate(sources[:5], 1):
                    context_items.append(
                        f"Quelle {idx}:\n"
                        f"Titel: {source.get('title', 'N/A')}\n"
                        f"URL: {source.get('url', 'N/A')}\n"
                        f"Snippet: {source.get('snippet', 'N/A')}"
                    )
                context_text = "\n\n".join(context_items)
            
            # Step 3: Use KiGate to analyze with search results
            from core.services.kigate_service import KiGateService
            
            kigate = KiGateService(self.settings)
            
            analysis_message = (
                f"Analysiere den folgenden Text, nutze die bereitgestellten "
                f"Websuche-Ergebnisse und liefere eine zusammengefasste Antwort "
                f"mit Handlungsempfehlung und Quellen.\n\n"
                f"Task-Titel: {task_title}\n\n"
                f"Task-Beschreibung:\n{task_description}\n\n"
            )
            
            if context_text:
                analysis_message += (
                    f"--- Websuche-Ergebnisse ---\n"
                    f"{context_text}\n"
                    f"--- Ende der Websuche-Ergebnisse ---\n\n"
                )
            
            analysis_message += (
                f"Erstelle eine strukturierte Analyse mit:\n"
                f"- Lösungsvorschläge basierend auf den Quellen\n"
                f"- Relevante Quellen mit Links\n"
                f"- Handlungsempfehlungen\n\n"
                f"Formatiere die Antwort in Markdown mit dem Header '### 🌍 Externe Analyse'."
            )
            
            result = kigate.execute_agent(
                agent_name='support-advisor-external-agent',
                provider='openai',
                model='gpt-4',
                message=analysis_message,
                user_id=user_id or 'system'
            )
            
            if not result.get('success'):
                raise SupportAdvisorServiceError(
                    "Failed to generate external analysis",
                    details=result.get('error', 'Unknown error')
                )
            
            analysis_text = result.get('result', result.get('response', ''))
            
            return {
                'success': True,
                'analysis': analysis_text,
                'sources': sources[:5],
                'mode': 'external'
            }
            
        except SupportAdvisorServiceError:
            raise
        except Exception as e:
            logger.error(f"External analysis error: {str(e)}")
            raise SupportAdvisorServiceError(
                "Failed to perform external analysis",
                details=str(e)
            )
