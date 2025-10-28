"""
Item Question Answering Service for IdeaGraph

This module provides context-based Q&A functionality for items using
Weaviate semantic search and KIGate AI agents.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery, Filter, HybridFusion

logger = logging.getLogger('item_question_answering_service')


class ItemQuestionAnsweringServiceError(Exception):
    """Base exception for ItemQuestionAnsweringService errors"""
    
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


class ItemQuestionAnsweringService:
    """
    Item Question Answering Service
    
    Provides context-based Q&A functionality:
    - Searches for relevant KnowledgeObjects related to a specific item
    - Uses KIGate to generate comprehensive answers
    - Tracks Q&A history
    - Optionally saves answers as KnowledgeObjects
    """
    
    COLLECTION_NAME = 'KnowledgeObject'
    DEFAULT_SEARCH_LIMIT = 10
    MIN_RELEVANCE_CERTAINTY = 0.7
    
    def __init__(self, settings=None):
        """
        Initialize ItemQuestionAnsweringService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise ItemQuestionAnsweringServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise ItemQuestionAnsweringServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            ItemQuestionAnsweringServiceError: If initialization fails
        """
        try:
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise ItemQuestionAnsweringServiceError(
                        "Weaviate Cloud enabled but URL or API key not configured"
                    )
                
                logger.info(f"Initializing Weaviate client for cloud: {self.settings.weaviate_url}")
                
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
                )
            else:
                # Use local Weaviate instance at localhost:8081 with no authentication
                logger.info("Initializing Weaviate client at localhost:8081")
                
                self._client = weaviate.connect_to_local(
                    host="localhost",
                    port=8081
                )

            logger.info(f"Weaviate client initialized for Q&A service")

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {str(e)}")
            raise ItemQuestionAnsweringServiceError(
                "Failed to initialize Weaviate client",
                details=str(e)
            )
    
    def search_related_knowledge(
        self,
        item_id: str,
        question: str,
        limit: int = DEFAULT_SEARCH_LIMIT
    ) -> Dict[str, Any]:
        """
        Search for KnowledgeObjects related to a specific item using semantic search
        
        Args:
            item_id: UUID of the item (as string)
            question: User's question text
            limit: Maximum number of results to return
        
        Returns:
            Dictionary containing:
                - success: bool
                - results: list of relevant KnowledgeObjects with scores
                - total: number of results found
        
        Raises:
            ItemQuestionAnsweringServiceError: If search fails
        """
        try:
            logger.info(f"Searching related knowledge for item {item_id} with question: {question[:100]}")
            
            if not question or not question.strip():
                return {
                    'success': True,
                    'results': [],
                    'total': 0
                }
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Build query with related_item filter
            # Note: related_item filter searches for objects that have this item as their parent
            # We also want to include the item itself
            item_uuid_str = str(item_id)
            
            # Create filter for related_item OR the item itself
            # First, try to find objects where related_item equals our item_id
            related_filter = Filter.by_property("itemId").equal(item_uuid_str)
            
            # Also include objects where the uuid is the item itself
            item_filter = Filter.by_id().equal(item_uuid_str)
            
            # Combine with OR
            combined_filter = related_filter | item_filter
            
            # Perform hybrid search
            response = collection.query.hybrid(
                query=question,
                limit=limit,
                filters=combined_filter,
                return_metadata=MetadataQuery(distance=True, certainty=True, score=True),
                fusion_type=HybridFusion.RANKED
            )
            
            # Format results
            search_results = []
            for obj in response.objects:
                # Calculate relevance score
                distance = obj.metadata.distance if obj.metadata and obj.metadata.distance is not None else 2.0
                certainty = obj.metadata.certainty if obj.metadata and obj.metadata.certainty is not None else 0.0
                
                # Use certainty if available (0-1, higher is better)
                if certainty > 0:
                    relevance = certainty
                else:
                    relevance = max(0.0, 1.0 - (distance / 2.0))
                
                # Skip results with low relevance
                if relevance < self.MIN_RELEVANCE_CERTAINTY:
                    continue
                
                # Extract properties
                props = obj.properties
                obj_type = props.get('type', 'Unknown')
                title = props.get('title', 'Untitled')
                description = props.get('description', '')
                url = props.get('url', '')
                
                # Ensure created_at is always a string (convert datetime if necessary)
                created_at = props.get('createdAt', '')
                if isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                
                result = {
                    'uuid': str(obj.uuid),
                    'type': obj_type,
                    'title': title,
                    'description': description,
                    'url': url,
                    'relevance': round(relevance, 2),
                    'source': props.get('source', ''),
                    'created_at': created_at
                }
                
                search_results.append(result)
            
            logger.info(f"Found {len(search_results)} relevant results for item {item_id}")
            
            return {
                'success': True,
                'results': search_results,
                'total': len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Failed to search related knowledge: {str(e)}")
            raise ItemQuestionAnsweringServiceError(
                "Failed to search related knowledge",
                details=str(e)
            )
    
    def generate_answer_with_kigate(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        item_title: str,
        user_id: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate an answer using KIGate's question-answering-agent
        
        Args:
            question: User's question
            search_results: List of relevant KnowledgeObjects from search
            item_title: Title of the item for context
            user_id: User ID for KIGate request
            conversation_history: Optional list of previous messages (max last 5)
        
        Returns:
            Dictionary containing:
                - success: bool
                - answer: Generated answer in markdown format
                - sources_used: List of sources referenced
        
        Raises:
            ItemQuestionAnsweringServiceError: If answer generation fails
        """
        try:
            from core.services.kigate_service import KiGateService, KiGateServiceError
            
            logger.info(f"Generating answer using KIGate for question: {question[:100]}")
            
            # Check if we have any search results
            if not search_results:
                return {
                    'success': True,
                    'answer': "**Keine relevanten Informationen gefunden**\n\nZu dieser Frage wurden keine passenden Informationen im Projektkontext gefunden. Bitte versuche eine andere Formulierung oder füge relevante Dokumentationen, Tasks oder Dateien zum Item hinzu.",
                    'sources_used': []
                }
            
            # Prepare context from search results
            context_parts = []
            for i, result in enumerate(search_results, 1):
                context_parts.append(f"""
**Quelle {i}: {result['type']} - {result['title']}**
Relevanz: {result['relevance']}
URL: {result['url']}
Inhalt: {result['description'][:500]}...
""")
            
            context_text = "\n\n".join(context_parts)
            
            # Prepare conversation history context if provided
            history_text = ""
            if conversation_history and len(conversation_history) > 0:
                # Take only the last 5 messages
                recent_history = conversation_history[-5:]
                history_parts = []
                for msg in recent_history:
                    role = msg.get('type', 'user')
                    content = msg.get('content', '')
                    if role == 'user':
                        history_parts.append(f"**Nutzer:** {content}")
                    elif role == 'bot':
                        history_parts.append(f"**Assistant:** {content}")
                
                if history_parts:
                    history_text = "\n\n**Bisheriger Gesprächsverlauf:**\n\n" + "\n\n".join(history_parts) + "\n\n"
            
            # Build the prompt for KIGate agent
            prompt = f"""Du bist der IdeaGraph Assistant. Beantworte die folgende Frage basierend auf den bereitgestellten Informationen aus dem Projektkontext.

**Item:** {item_title}
{history_text}
**Frage:** {question}

**Verfügbare Informationen aus dem Projektkontext:**

{context_text}

**Anweisungen:**
- Formuliere eine klare, präzise Antwort in Markdown-Format
- Nutze die bereitgestellten Informationen als Basis
- Berücksichtige den bisherigen Gesprächsverlauf für Kontext und Zusammenhang
- Erstelle eine Liste der genutzten Quellen mit Titel und Link am Ende
- Erfinde keine neuen Fakten - bleibe bei den bereitgestellten Informationen
- Wenn die Informationen nicht ausreichen, sage das deutlich

**Format der Antwort:**
## Antwort auf deine Frage:
[Deine Antwort hier]

## Quellen:
1. [Typ] [Titel] - [Link]
2. ...
"""
            
            # Initialize KiGate service
            kigate_service = KiGateService(self.settings)
            
            # Execute question-answering-agent
            # Note: These parameters should be configurable via settings
            response = kigate_service.execute_agent(
                agent_name='question-answering-agent',
                provider='openai',
                model='gpt-4',
                message=prompt,
                user_id=user_id
            )
            
            if not response.get('success'):
                raise ItemQuestionAnsweringServiceError(
                    "KiGate agent execution failed",
                    details=response.get('error', 'Unknown error')
                )
            
            answer = response.get('result', '')
            
            logger.info(f"Successfully generated answer using KIGate")
            
            return {
                'success': True,
                'answer': answer,
                'sources_used': search_results
            }
            
        except KiGateServiceError as e:
            logger.error(f"KiGate service error: {str(e)}")
            raise ItemQuestionAnsweringServiceError(
                "Failed to generate answer with KIGate",
                details=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to generate answer: {str(e)}")
            raise ItemQuestionAnsweringServiceError(
                "Failed to generate answer",
                details=str(e)
            )
    
    def save_as_knowledge_object(
        self,
        item_id: str,
        question: str,
        answer: str,
        qa_id: str
    ) -> Dict[str, Any]:
        """
        Save a Q&A pair as a KnowledgeObject in Weaviate
        
        Args:
            item_id: UUID of the item
            question: The question text
            answer: The answer text
            qa_id: UUID of the ItemQuestionAnswer record
        
        Returns:
            Dictionary containing:
                - success: bool
                - weaviate_uuid: UUID in Weaviate
        
        Raises:
            ItemQuestionAnsweringServiceError: If save fails
        """
        try:
            logger.info(f"Saving Q&A as KnowledgeObject: {qa_id}")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Prepare properties
            properties = {
                'type': 'qa-response',
                'title': f"Q: {question[:100]}",
                'description': f"**Frage:**\n{question}\n\n**Antwort:**\n{answer}",
                'related_item': str(item_id),
                'source': 'IdeaGraph Q&A',
                'url': f'/items/{item_id}/#qa-{qa_id}',
                'createdAt': datetime.now(timezone.utc).isoformat(),
            }
            
            # Add to collection
            uuid = collection.data.insert(
                properties=properties
            )
            
            logger.info(f"Saved Q&A as KnowledgeObject with UUID: {uuid}")
            
            return {
                'success': True,
                'weaviate_uuid': str(uuid)
            }
            
        except Exception as e:
            logger.error(f"Failed to save Q&A as KnowledgeObject: {str(e)}")
            raise ItemQuestionAnsweringServiceError(
                "Failed to save as KnowledgeObject",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate Q&A client connection closed")
