"""
AI Error Analyzer Service for IdeaGraph

This service uses AI (via KIGate or OpenAI) to analyze log entries and errors,
determine their severity, and recommend actions.
"""

from typing import Dict, List, Optional
from core.logger_config import get_logger
from core.services.kigate_service import KiGateService

logger = get_logger('ai_error_analyzer_service')


class AIErrorAnalyzerService:
    """Service to analyze errors using AI"""
    
    ANALYSIS_PROMPT_TEMPLATE = """Du bist ein erfahrener Software-Entwickler und Fehleranalyst.

Analysiere den folgenden Fehler aus einem Log und bewerte ihn:

**Log-Level:** {level}
**Logger:** {logger_name}
**Timestamp:** {timestamp}
**Nachricht:** {message}

{exception_info}

Bitte analysiere diesen Fehler und liefere folgende Informationen im JSON-Format:

{{
    "severity": "<low|medium|high|critical>",
    "is_actionable": <true|false>,
    "summary": "<Kurze Zusammenfassung des Fehlers in 1-2 Sätzen>",
    "root_cause": "<Wahrscheinliche Ursache des Fehlers>",
    "recommended_action": "<Konkrete Handlungsempfehlung zur Behebung>",
    "confidence": <0.0-1.0>
}}

**Bewertungskriterien:**

- **severity**: 
  - critical: Systemausfall, Datenverlust, Sicherheitslücke
  - high: Funktionsverlust, häufige Fehler, Performance-Probleme
  - medium: Teilfunktionsverlust, seltene Fehler
  - low: Warnungen, deprecations, Info-Meldungen

- **is_actionable**: 
  - true: Fehler kann durch Code-Änderung, Konfiguration oder Bugfix behoben werden
  - false: Nur Info, externe Ursache, oder bereits bekannt/erwartet

- **confidence**: 
  - Deine Sicherheit in der Analyse (0.0 = unsicher, 1.0 = sehr sicher)

Antworte NUR mit dem JSON-Objekt, keine zusätzlichen Erklärungen."""
    
    def __init__(self, use_kigate: bool = True):
        """
        Initialize the AI error analyzer service
        
        Args:
            use_kigate: Whether to use KIGate (True) or OpenAI directly (False)
        """
        self.use_kigate = use_kigate
        
        if use_kigate:
            self.kigate_service = KiGateService()
            logger.info("AI Error Analyzer initialized with KIGate")
        else:
            from core.services.openai_service import OpenAIService
            self.openai_service = OpenAIService()
            logger.info("AI Error Analyzer initialized with OpenAI")
    
    def _format_exception_info(self, log_entry) -> str:
        """Format exception information for the prompt"""
        parts = []
        
        if log_entry.exception_type:
            parts.append(f"**Exception Type:** {log_entry.exception_type}")
        
        if log_entry.exception_value:
            parts.append(f"**Exception Value:** {log_entry.exception_value}")
        
        if log_entry.stack_trace:
            # Limit stack trace to first 1000 characters to avoid token limits
            stack_trace = log_entry.stack_trace[:1000]
            if len(log_entry.stack_trace) > 1000:
                stack_trace += "\n... (truncated)"
            parts.append(f"**Stack Trace:**\n```\n{stack_trace}\n```")
        
        return '\n\n'.join(parts) if parts else ""
    
    def analyze_log_entry(self, log_entry) -> Optional[Dict]:
        """
        Analyze a single log entry using AI
        
        Args:
            log_entry: LogEntry model instance
            
        Returns:
            Dictionary with analysis results or None on error
        """
        try:
            # Build the prompt
            exception_info = self._format_exception_info(log_entry)
            prompt = self.ANALYSIS_PROMPT_TEMPLATE.format(
                level=log_entry.level,
                logger_name=log_entry.logger_name,
                timestamp=log_entry.timestamp.isoformat(),
                message=log_entry.message[:500],  # Limit message length
                exception_info=exception_info
            )
            
            logger.info(f"Analyzing log entry {log_entry.id}")
            
            # Call AI service
            if self.use_kigate:
                result = self._analyze_with_kigate(prompt)
            else:
                result = self._analyze_with_openai(prompt)
            
            if result:
                logger.info(f"Analysis completed for log entry {log_entry.id}")
                return result
            else:
                logger.error(f"Analysis failed for log entry {log_entry.id}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing log entry: {e}", exc_info=True)
            return None
    
    def _analyze_with_kigate(self, prompt: str) -> Optional[Dict]:
        """
        Analyze using KIGate
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            Parsed analysis result or None
        """
        try:
            # Use KiGate's agent execution API
            response = self.kigate_service.execute_agent(
                agent_name="error_analyzer",
                provider="openai",
                model="gpt-4",
                message=prompt,
                user_id="system",
                parameters={
                    "max_tokens": 500,
                    "temperature": 0.3,
                }
            )
            
            if not response or not response.get('success'):
                logger.error("Invalid response from KiGate")
                return None
            
            # Parse JSON response from result
            import json
            result_content = response.get('result', '')
            
            # Try to extract JSON from markdown code blocks
            if '```json' in result_content:
                result_content = result_content.split('```json')[1].split('```')[0]
            elif '```' in result_content:
                result_content = result_content.split('```')[1].split('```')[0]
            
            result = json.loads(result_content.strip())
            
            # Add model info
            result['ai_model'] = response.get('model', 'unknown')
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Response content: {result_content}")
            return None
        except Exception as e:
            logger.error(f"Error calling KiGate: {e}", exc_info=True)
            # If KiGate is not available, fall back to OpenAI
            logger.info("Falling back to OpenAI direct API")
            return self._analyze_with_openai(prompt)
    
    def _analyze_with_openai(self, prompt: str) -> Optional[Dict]:
        """
        Analyze using OpenAI directly
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            Parsed analysis result or None
        """
        try:
            response = self.openai_service.chat_completion(
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für Software-Fehleranalyse."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3,
            )
            
            if not response:
                logger.error("Invalid response from OpenAI")
                return None
            
            # Parse JSON response
            import json
            content = response.get('content', '')
            
            # Try to extract JSON from markdown code blocks
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            result = json.loads(content.strip())
            
            # Add model info
            result['ai_model'] = response.get('model', 'gpt-4')
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}", exc_info=True)
            return None
    
    def analyze_and_save(self, log_entry) -> Optional['ErrorAnalysis']:
        """
        Analyze a log entry and save the analysis to database
        
        Args:
            log_entry: LogEntry model instance
            
        Returns:
            Created ErrorAnalysis instance or None
        """
        from main.models import ErrorAnalysis
        
        # Check if already analyzed
        existing = ErrorAnalysis.objects.filter(log_entry=log_entry).first()
        if existing:
            logger.info(f"Log entry {log_entry.id} already analyzed")
            return existing
        
        # Perform analysis
        analysis_result = self.analyze_log_entry(log_entry)
        
        if not analysis_result:
            logger.error(f"Failed to analyze log entry {log_entry.id}")
            return None
        
        try:
            # Create error analysis record
            error_analysis = ErrorAnalysis.objects.create(
                log_entry=log_entry,
                severity=analysis_result.get('severity', 'medium'),
                is_actionable=analysis_result.get('is_actionable', False),
                summary=analysis_result.get('summary', ''),
                root_cause=analysis_result.get('root_cause', ''),
                recommended_action=analysis_result.get('recommended_action', ''),
                ai_model=analysis_result.get('ai_model', ''),
                ai_confidence=analysis_result.get('confidence', 0.0),
            )
            
            # Mark log entry as analyzed
            log_entry.analyzed = True
            log_entry.save()
            
            logger.info(f"Created error analysis {error_analysis.id} for log entry {log_entry.id}")
            return error_analysis
            
        except Exception as e:
            logger.error(f"Error saving analysis: {e}", exc_info=True)
            return None
    
    def batch_analyze(
        self,
        min_level: str = 'WARNING',
        limit: int = 50
    ) -> List['ErrorAnalysis']:
        """
        Analyze multiple unanalyzed log entries
        
        Args:
            min_level: Minimum log level to analyze
            limit: Maximum number of entries to analyze
            
        Returns:
            List of created ErrorAnalysis instances
        """
        from main.models import LogEntry
        
        level_priority = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4,
        }
        
        # Get unanalyzed log entries
        log_entries = LogEntry.objects.filter(
            analyzed=False
        ).order_by('-timestamp')[:limit]
        
        # Filter by level
        min_priority = level_priority.get(min_level, 2)
        log_entries = [
            entry for entry in log_entries
            if level_priority.get(entry.level, 0) >= min_priority
        ]
        
        logger.info(f"Batch analyzing {len(log_entries)} log entries")
        
        analyses = []
        for log_entry in log_entries:
            analysis = self.analyze_and_save(log_entry)
            if analysis:
                analyses.append(analysis)
        
        logger.info(f"Completed batch analysis: {len(analyses)} successful")
        return analyses
