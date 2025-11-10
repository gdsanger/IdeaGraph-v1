"""
Support Precheck Service

This service performs prechecks before submitting a support request:
1. Generates an auto-answer using the existing Q&A pipeline
2. Finds duplicate tasks within the same item
3. Provides recommendation on whether to proceed with submission
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('support_precheck_service')


class SupportPrecheckService:
    """
    Service to precheck support submissions
    
    Combines auto-answer generation and duplicate detection to help
    users find existing solutions before creating new tasks.
    """
    
    def __init__(self, settings=None):
        """
        Initialize SupportPrecheckService
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise Exception(f"Failed to load settings: {str(e)}")
        
        self.settings = settings
        if not self.settings:
            raise Exception("No settings found in database")
    
    def precheck(
        self,
        item_id: str,
        title: str,
        description: str,
        task_type: str = 'support'
    ) -> Dict[str, Any]:
        """
        Perform precheck on a support submission
        
        Args:
            item_id: UUID of the item
            title: Title of the support request
            description: Description of the support request
            task_type: Type of task (support, bug, feature, etc.)
        
        Returns:
            Dictionary with:
            {
                'auto_answer': {
                    'summary': str,
                    'confidence': float (0.0-1.0),
                    'sources': list
                },
                'duplicates': [
                    {
                        'task_id': str,
                        'title': str,
                        'similarity': float,
                        'status': str
                    }
                ],
                'recommendation': 'resolve' | 'submit' | 'ask_user'
            }
        """
        from core.services.item_question_answering_service import (
            ItemQuestionAnsweringService,
            ItemQuestionAnsweringServiceError
        )
        from core.services.support_duplicate_finder_service import SupportDuplicateFinderService
        
        result = {
            'auto_answer': {
                'summary': '',
                'confidence': 0.0,
                'sources': []
            },
            'duplicates': [],
            'recommendation': 'submit'
        }
        
        # Step 1: Generate auto-answer using existing Q&A service
        try:
            qa_service = ItemQuestionAnsweringService(settings=self.settings)
            
            # Create question from title and description
            question = f"{title}\n\n{description}" if description else title
            
            # Get answer from Q&A service
            answer_result = qa_service.answer_question(
                item_id=item_id,
                question=question,
                conversation_history=[]
            )
            
            if answer_result.get('success'):
                # Extract summary (first 500 chars of answer)
                full_answer = answer_result.get('answer', '')
                summary = full_answer[:500] + '...' if len(full_answer) > 500 else full_answer
                
                result['auto_answer'] = {
                    'summary': summary,
                    'confidence': answer_result.get('relevance_score', 0.0),
                    'sources': answer_result.get('sources', [])[:3]  # Limit to top 3 sources
                }
                
                logger.info(f"Generated auto-answer for item {item_id} with confidence {result['auto_answer']['confidence']}")
            else:
                logger.warning(f"Failed to generate auto-answer: {answer_result.get('error', 'Unknown error')}")
        
        except ItemQuestionAnsweringServiceError as e:
            logger.warning(f"Q&A service error during precheck: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error generating auto-answer: {str(e)}", exc_info=True)
        
        # Step 2: Find duplicate tasks
        try:
            duplicate_finder = SupportDuplicateFinderService(settings=self.settings)
            
            duplicates = duplicate_finder.find_similar_tasks(
                item_id=item_id,
                title=title,
                description=description,
                limit=5,
                source_filter=None  # Search all tasks, not just support
            )
            
            result['duplicates'] = duplicates
            logger.info(f"Found {len(duplicates)} potential duplicates for item {item_id}")
        
        except Exception as e:
            logger.error(f"Error finding duplicates: {str(e)}", exc_info=True)
        
        # Step 3: Determine recommendation
        result['recommendation'] = self._determine_recommendation(
            result['auto_answer']['confidence'],
            result['duplicates']
        )
        
        logger.info(f"Precheck complete for item {item_id}: recommendation={result['recommendation']}")
        return result
    
    def _determine_recommendation(
        self,
        confidence: float,
        duplicates: list
    ) -> str:
        """
        Determine recommendation based on auto-answer confidence and duplicates
        
        Args:
            confidence: Confidence score of auto-answer (0.0-1.0)
            duplicates: List of duplicate tasks with similarity scores
        
        Returns:
            'resolve' - high confidence answer or high similarity duplicate found
            'submit' - low confidence and no duplicates
            'ask_user' - medium confidence or medium similarity duplicates
        """
        # Check for high similarity duplicates
        if duplicates:
            highest_similarity = max([d.get('similarity', 0.0) for d in duplicates])
            
            if highest_similarity >= 0.90:
                # Very likely duplicate
                return 'resolve'
            elif highest_similarity >= 0.80:
                # Possible duplicate, ask user
                return 'ask_user'
        
        # Check auto-answer confidence
        if confidence >= 0.8:
            # High confidence answer
            return 'resolve'
        elif confidence >= 0.5:
            # Medium confidence, ask user
            return 'ask_user'
        
        # Low confidence and no duplicates
        return 'submit'
