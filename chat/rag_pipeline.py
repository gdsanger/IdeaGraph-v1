"""
RAG Pipeline for Chat in IdeaGraph

This module implements a comprehensive RAG (Retrieval-Augmented Generation) pipeline for chat:
1. Question optimization via question-optimization-agent (KiGate)
2. Parallel retrieval: Semantic/Hybrid search + Keyword/Tag search
3. Result fusion and reranking
4. Context assembly with A/B/C layers
5. Answer generation via question-answering-agent (KiGate)
"""

import logging
import json
import time
from typing import Dict, Any, List, Optional, Tuple
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery, Filter, HybridFusion

logger = logging.getLogger('rag_pipeline')


class RAGPipelineError(Exception):
    """Base exception for RAG Pipeline errors"""
    
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


class RAGPipeline:
    """
    RAG Pipeline for Chat
    
    Implements a complete RAG workflow:
    - Question optimization with synonyms, phrases, and tags
    - Dual retrieval strategy (semantic + keyword)
    - Intelligent fusion and reranking
    - Structured context assembly (A/B/C layers)
    - AI-powered answer generation
    """
    
    COLLECTION_NAME = 'KnowledgeObject'
    
    # Retrieval configuration
    SEMANTIC_ALPHA = 0.6  # Balance between vector (0) and BM25 (1)
    KEYWORD_ALPHA = 0.7   # More BM25-focused for keyword search
    SEMANTIC_LIMIT = 24   # Number of results from semantic search
    KEYWORD_LIMIT = 20    # Number of results from keyword search
    FINAL_TOP_N = 6       # Top N results for final context
    
    # Query expansion configuration
    MAX_SYNONYMS = 3      # Maximum synonyms to include
    MAX_PHRASES = 2       # Maximum phrases to include
    MAX_TAGS = 2          # Maximum tags to include
    
    # Reranking weights
    WEIGHT_SEM_SCORE = 0.6
    WEIGHT_BM25_SCORE = 0.2
    WEIGHT_TAG_MATCH = 0.15
    WEIGHT_SAME_ITEM = 0.05
    
    # Context assembly configuration
    TIER_A_MAX = 3  # Thread/Task-near snippets
    TIER_B_MAX = 3  # Item context snippets
    TIER_C_MAX = 2  # Global background snippets
    
    # Fallback messages by language
    FALLBACK_MESSAGES = {
        'de': '[#FAQ] Keine spezifischen Informationen gefunden. Bitte formulieren Sie Ihre Frage präziser oder kontaktieren Sie den Support.',
        'en': '[#FAQ] No specific information found. Please rephrase your question more precisely or contact support.',
    }
    DEFAULT_FALLBACK_LANGUAGE = 'de'
    
    def __init__(self, settings=None):
        """
        Initialize RAG Pipeline with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise RAGPipelineError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise RAGPipelineError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_weaviate()
        
        # Initialize KiGate service
        from core.services.kigate_service import KiGateService, KiGateServiceError
        try:
            self.kigate = KiGateService(settings=self.settings)
        except KiGateServiceError as e:
            logger.warning(f"KiGate service not available: {str(e)}")
            self.kigate = None
    
    def _initialize_weaviate(self):
        """Initialize Weaviate client"""
        try:
            if self.settings.weaviate_cloud_enabled:
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise RAGPipelineError(
                        "Weaviate Cloud enabled but URL or API key not configured"
                    )
                
                logger.info(f"Initializing Weaviate client for cloud: {self.settings.weaviate_url}")
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
                )
            else:
                logger.info("Initializing Weaviate client at localhost:8081")
                self._client = weaviate.connect_to_local(
                    host="localhost",
                    port=8081
                )
            
            logger.info("Weaviate client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {str(e)}")
            raise RAGPipelineError("Failed to initialize Weaviate client", details=str(e))
    
    def optimize_question(self, question: str) -> Dict[str, Any]:
        """
        Optimize question using question-optimization-agent (KiGate)
        
        The agent analyzes the question and returns:
        - language: Detected language
        - core: Core/simplified question
        - synonyms: List of synonyms
        - phrases: List of related phrases
        - entities: Extracted entities
        - tags: Relevant tags/keywords
        - ban: Terms to exclude
        - followup_questions: Suggested follow-up questions
        
        Args:
            question: Original user question
            
        Returns:
            Dictionary with optimization results
        """
        logger.info(f"Optimizing question: {question[:100]}...")
        
        if not self.kigate:
            logger.warning("KiGate not available, using fallback optimization")
            return self._fallback_optimization(question)
        
        try:
            # Call question-optimization-agent
            response = self.kigate.execute_agent(
                agent_name="question-optimization-agent",
                parameters={
                    "question": question
                }
            )
            
            if not response.get('success'):
                logger.error(f"Question optimization failed: {response.get('error')}")
                return self._fallback_optimization(question)
            
            # Parse JSON response
            result_text = response.get('result', '{}')
            try:
                optimized = json.loads(result_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse optimization JSON: {str(e)}")
                return self._fallback_optimization(question)
            
            # Validate required fields
            if 'core' not in optimized:
                logger.warning("Optimization missing 'core' field, using fallback")
                return self._fallback_optimization(question)
            
            # Ensure all expected fields exist with defaults
            optimized.setdefault('language', 'de')
            optimized.setdefault('synonyms', [])
            optimized.setdefault('phrases', [])
            optimized.setdefault('entities', {})
            optimized.setdefault('tags', [])
            optimized.setdefault('ban', [])
            optimized.setdefault('followup_questions', [])
            
            logger.info(f"Question optimized successfully: core='{optimized['core']}'")
            return optimized
            
        except Exception as e:
            logger.error(f"Error optimizing question: {str(e)}")
            return self._fallback_optimization(question)
    
    def _fallback_optimization(self, question: str) -> Dict[str, Any]:
        """
        Fallback optimization when KiGate is unavailable
        
        Args:
            question: Original question
            
        Returns:
            Basic optimization dictionary
        """
        return {
            'language': 'de',
            'core': question,
            'synonyms': [],
            'phrases': [],
            'entities': {},
            'tags': [],
            'ban': [],
            'followup_questions': []
        }
    
    def _build_search_query(
        self, 
        expanded: Dict[str, Any], 
        max_synonyms: int = None,
        max_phrases: int = None,
        max_tags: int = None
    ) -> str:
        """
        Build search query from expanded question data
        
        Args:
            expanded: Expanded question dictionary
            max_synonyms: Maximum synonyms to include
            max_phrases: Maximum phrases to include
            max_tags: Maximum tags to include
            
        Returns:
            Combined search query string
        """
        if max_synonyms is None:
            max_synonyms = self.MAX_SYNONYMS
        if max_phrases is None:
            max_phrases = self.MAX_PHRASES
        if max_tags is None:
            max_tags = self.MAX_TAGS
        
        parts = [expanded['core']]
        
        # Add top synonyms
        synonyms = expanded.get('synonyms', [])[:max_synonyms]
        parts.extend(synonyms)
        
        # Add top phrases
        phrases = expanded.get('phrases', [])[:max_phrases]
        parts.extend(phrases)
        
        # Add top tags
        tags = expanded.get('tags', [])[:max_tags]
        parts.extend(tags)
        
        query = ' '.join(parts)
        logger.debug(f"Built search query: {query}")
        return query
    
    def retrieve_semantic(
        self, 
        expanded: Dict[str, Any], 
        item_id: Optional[str] = None,
        tenant: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve results using semantic/hybrid search
        
        Uses Weaviate hybrid query with alpha≈0.6 (balanced semantic + BM25)
        
        Args:
            expanded: Expanded question dictionary
            item_id: Optional item ID to filter results
            tenant: Optional tenant ID to filter results
            
        Returns:
            List of search results with scores
        """
        logger.info("Performing semantic/hybrid search")
        
        try:
            # Build query
            query = self._build_search_query(
                expanded,
                max_synonyms=self.MAX_SYNONYMS,
                max_phrases=self.MAX_PHRASES,
                max_tags=self.MAX_TAGS
            )
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Build filter if needed
            filters = None
            if item_id:
                filters = Filter.by_property("itemId").equal(item_id)
            
            # Execute hybrid search
            response = collection.query.hybrid(
                query=query,
                alpha=self.SEMANTIC_ALPHA,
                limit=self.SEMANTIC_LIMIT,
                return_metadata=MetadataQuery(score=True, certainty=True),
                filters=filters,
                fusion_type=HybridFusion.RELATIVE_SCORE
            )
            
            results = []
            for obj in response.objects:
                result = {
                    'id': str(obj.uuid),
                    'type': obj.properties.get('objectType', 'unknown'),
                    'item_id': obj.properties.get('itemId'),
                    'title': obj.properties.get('title', ''),
                    'excerpt': obj.properties.get('excerpt', '')[:500],
                    'tags': obj.properties.get('tags', []),
                    'score_semantic': obj.metadata.score if obj.metadata.score else 0.0,
                    'score_bm25': 0.0,  # Will be populated if available
                    'certainty': obj.metadata.certainty if obj.metadata.certainty else 0.0,
                }
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} results from semantic search")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []
    
    def retrieve_keywords(
        self, 
        expanded: Dict[str, Any], 
        item_id: Optional[str] = None,
        tenant: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve results using keyword/tag search
        
        Uses BM25-focused search (alpha≈0.7) with tags and core query
        
        Args:
            expanded: Expanded question dictionary
            item_id: Optional item ID to filter results
            tenant: Optional tenant ID to filter results
            
        Returns:
            List of search results with scores
        """
        logger.info("Performing keyword/tag search")
        
        try:
            # Build query focusing on tags and core
            parts = [expanded['core']]
            parts.extend(expanded.get('tags', []))
            query = ' '.join(parts)
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Build filter if needed
            filters = None
            if item_id:
                filters = Filter.by_property("itemId").equal(item_id)
            
            # Execute hybrid search with higher alpha (BM25-focused)
            response = collection.query.hybrid(
                query=query,
                alpha=self.KEYWORD_ALPHA,
                limit=self.KEYWORD_LIMIT,
                return_metadata=MetadataQuery(score=True, certainty=True),
                filters=filters,
                fusion_type=HybridFusion.RELATIVE_SCORE
            )
            
            results = []
            for obj in response.objects:
                result = {
                    'id': str(obj.uuid),
                    'type': obj.properties.get('objectType', 'unknown'),
                    'item_id': obj.properties.get('itemId'),
                    'title': obj.properties.get('title', ''),
                    'excerpt': obj.properties.get('excerpt', '')[:500],
                    'tags': obj.properties.get('tags', []),
                    'score_semantic': 0.0,
                    'score_bm25': obj.metadata.score if obj.metadata.score else 0.0,
                    'certainty': obj.metadata.certainty if obj.metadata.certainty else 0.0,
                }
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} results from keyword search")
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}")
            return []
    
    def fuse_and_rerank(
        self, 
        results_sem: List[Dict[str, Any]], 
        results_kw: List[Dict[str, Any]],
        expanded: Dict[str, Any],
        item_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fuse and rerank results from both searches
        
        Scoring formula:
        final_score = 0.6*score_sem + 0.2*score_bm25 + 0.15*tag_match + 0.05*same_item
        
        Args:
            results_sem: Results from semantic search
            results_kw: Results from keyword search
            expanded: Expanded question dictionary
            item_id: Current item ID for same-item boost
            
        Returns:
            Deduplicated and reranked results
        """
        logger.info("Fusing and reranking results")
        start_time = time.time()
        
        # Deduplicate by ID
        seen_ids = set()
        all_results = []
        
        # Add semantic results
        for result in results_sem:
            if result['id'] not in seen_ids:
                seen_ids.add(result['id'])
                all_results.append(result)
        
        # Add keyword results, merge if already exists
        for result in results_kw:
            if result['id'] in seen_ids:
                # Find and update existing result
                for existing in all_results:
                    if existing['id'] == result['id']:
                        # Merge BM25 score
                        existing['score_bm25'] = max(existing['score_bm25'], result['score_bm25'])
                        break
            else:
                seen_ids.add(result['id'])
                all_results.append(result)
        
        # Rerank with combined scoring
        query_tags = set(expanded.get('tags', []))
        
        for result in all_results:
            # Calculate tag match score (only if both query and result have tags)
            result_tags = set(result.get('tags', []))
            if query_tags and result_tags:
                # Safe division: both sets are non-empty
                tag_match = len(query_tags & result_tags) / len(query_tags)
            else:
                tag_match = 0.0
            
            # Calculate same-item bonus
            same_item = 1.0 if item_id and result.get('item_id') == item_id else 0.0
            
            # Calculate final score
            final_score = (
                self.WEIGHT_SEM_SCORE * result['score_semantic'] +
                self.WEIGHT_BM25_SCORE * result['score_bm25'] +
                self.WEIGHT_TAG_MATCH * tag_match +
                self.WEIGHT_SAME_ITEM * same_item
            )
            
            result['final_score'] = final_score
            result['tag_match'] = tag_match
            result['same_item_boost'] = same_item
        
        # Sort by final score
        all_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Take top N
        top_results = all_results[:self.FINAL_TOP_N]
        
        fusion_time = time.time() - start_time
        logger.info(f"Fusion completed in {fusion_time:.2f}s, kept top {len(top_results)} results")
        
        return top_results
    
    def assemble_context(
        self, 
        results: List[Dict[str, Any]], 
        item_id: Optional[str] = None,
        language: str = None
    ) -> str:
        """
        Assemble context with A/B/C layer structure
        
        Layers:
        - A: Thread/Task-near context (2-3 snippets)
        - B: Item context (2-3 snippets)
        - C: Global background (1-2 snippets)
        
        Args:
            results: Reranked search results
            item_id: Current item ID for layer classification
            language: Language for fallback message (default: 'de')
            
        Returns:
            Formatted context string with layer markers
        """
        logger.info("Assembling context with A/B/C layers")
        
        if not results:
            logger.warning("No results to assemble, using fallback context")
            if language is None:
                language = self.DEFAULT_FALLBACK_LANGUAGE
            fallback = self.FALLBACK_MESSAGES.get(
                language, 
                self.FALLBACK_MESSAGES[self.DEFAULT_FALLBACK_LANGUAGE]
            )
            return fallback
        
        # Classify results into layers
        tier_a = []  # Same item, high relevance
        tier_b = []  # Same item, medium relevance
        tier_c = []  # Different item, global context
        
        for result in results:
            is_same_item = item_id and result.get('item_id') == item_id
            score = result.get('final_score', 0.0)
            
            if is_same_item and score > 0.5:
                tier_a.append(result)
            elif is_same_item:
                tier_b.append(result)
            else:
                tier_c.append(result)
        
        # Limit each tier
        tier_a = tier_a[:self.TIER_A_MAX]
        tier_b = tier_b[:self.TIER_B_MAX]
        tier_c = tier_c[:self.TIER_C_MAX]
        
        # Format context
        lines = ["CONTEXT:"]
        
        # Add Tier A
        for idx, result in enumerate(tier_a, 1):
            marker = f"#A{idx}"
            title = result.get('title', 'Untitled')
            excerpt = result.get('excerpt', '')
            lines.append(f"[{marker}] {title}")
            lines.append(excerpt)
            lines.append("")
        
        # Add Tier B
        for idx, result in enumerate(tier_b, 1):
            marker = f"#B{idx}"
            title = result.get('title', 'Untitled')
            excerpt = result.get('excerpt', '')
            lines.append(f"[{marker}] {title}")
            lines.append(excerpt)
            lines.append("")
        
        # Add Tier C
        for idx, result in enumerate(tier_c, 1):
            marker = f"#C{idx}"
            title = result.get('title', 'Untitled')
            excerpt = result.get('excerpt', '')
            lines.append(f"[{marker}] {title}")
            lines.append(excerpt)
            lines.append("")
        
        context = '\n'.join(lines)
        
        # Calculate token estimate
        token_estimate = len(context.split())
        logger.info(f"Context assembled: {len(tier_a)} A, {len(tier_b)} B, {len(tier_c)} C layers, ~{token_estimate} tokens")
        
        return context
    
    def send_to_answering_agent(
        self, 
        original_question: str, 
        context: str
    ) -> str:
        """
        Send question and context to question-answering-agent (KiGate)
        
        Args:
            original_question: Original user question
            context: Assembled context string
            
        Returns:
            AI-generated answer
        """
        logger.info("Sending to question-answering-agent")
        
        if not self.kigate:
            logger.error("KiGate not available")
            return "Entschuldigung, der KI-Service ist momentan nicht verfügbar."
        
        try:
            # Build prompt
            prompt = f"""USER QUESTION: {original_question}

{context}

INSTRUCTION: Antworte ausschließlich auf Basis des CONTEXT. Referenziere die Quellen mit ihren Markern (z.B. [#A1], [#B2]). 
Wenn der Context keine passende Information enthält, sage es ehrlich."""
            
            # Call question-answering-agent
            response = self.kigate.execute_agent(
                agent_name="question-answering-agent",
                parameters={
                    "prompt": prompt
                }
            )
            
            if not response.get('success'):
                logger.error(f"Answer generation failed: {response.get('error')}")
                return "Entschuldigung, bei der Antwortgenerierung ist ein Fehler aufgetreten."
            
            answer = response.get('result', '')
            logger.info(f"Answer generated successfully, length: {len(answer)}")
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return "Entschuldigung, bei der Antwortgenerierung ist ein Fehler aufgetreten."
    
    def process_question(
        self,
        question: str,
        item_id: Optional[str] = None,
        tenant: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a chat question through the complete RAG pipeline
        
        Args:
            question: User question
            item_id: Optional item ID for context
            tenant: Optional tenant ID for filtering
            
        Returns:
            Dictionary with answer and metadata
        """
        logger.info(f"Processing question: {question[:100]}...")
        start_time = time.time()
        
        try:
            # Step 1: Optimize question
            expanded = self.optimize_question(question)
            
            # Step 2: Parallel retrieval
            results_sem = self.retrieve_semantic(expanded, item_id, tenant)
            results_kw = self.retrieve_keywords(expanded, item_id, tenant)
            
            # Step 3: Fuse and rerank
            final_results = self.fuse_and_rerank(results_sem, results_kw, expanded, item_id)
            
            # Step 4: Assemble context
            context = self.assemble_context(final_results, item_id)
            
            # Step 5: Generate answer
            answer = self.send_to_answering_agent(question, context)
            
            # Calculate metrics
            total_time = time.time() - start_time
            
            result = {
                'success': True,
                'answer': answer,
                'question': question,
                'expanded': expanded,
                'hits_sem': len(results_sem),
                'hits_kw': len(results_kw),
                'hits_final': len(final_results),
                'sources': final_results,
                'context': context,
                'total_time': total_time,
                'token_estimate': len(context.split()),
            }
            
            logger.info(f"Question processed successfully in {total_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'answer': "Entschuldigung, bei der Verarbeitung Ihrer Frage ist ein Fehler aufgetreten.",
                'question': question,
            }
    
    def __del__(self):
        """Cleanup Weaviate client on deletion"""
        if self._client:
            try:
                self._client.close()
            except:
                pass
