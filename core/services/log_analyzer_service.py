"""
Log Analyzer Service for IdeaGraph

This service analyzes local log files and extracts error information.
It parses log entries from rotating log files and stores them in the database.
"""

import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from core.logger_config import get_logger

logger = get_logger('log_analyzer_service')


class LogAnalyzerService:
    """Service to analyze and parse local log files"""
    
    # Log line pattern: YYYY-MM-DD HH:MM:SS [LEVEL] [module_name] - message
    LOG_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] \[([^\]]+)\] - (.+)$'
    )
    
    def __init__(self, log_dir: str = None):
        """
        Initialize the log analyzer service
        
        Args:
            log_dir: Directory containing log files (defaults to settings LOG_DIR)
        """
        if log_dir is None:
            from django.conf import settings
            log_dir = settings.BASE_DIR / os.getenv('LOG_DIR', 'logs')
        
        self.log_dir = Path(log_dir)
        logger.info(f"Log Analyzer initialized with directory: {self.log_dir}")
    
    def get_log_files(self) -> List[Path]:
        """
        Get all log files in the log directory
        
        Returns:
            List of Path objects for log files
        """
        if not self.log_dir.exists():
            logger.warning(f"Log directory does not exist: {self.log_dir}")
            return []
        
        log_files = sorted(
            self.log_dir.glob('*.log*'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        logger.info(f"Found {len(log_files)} log files")
        return log_files
    
    def parse_log_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single log line
        
        Args:
            line: Log line string
            
        Returns:
            Dictionary with parsed data or None if line doesn't match pattern
        """
        match = self.LOG_PATTERN.match(line.strip())
        if not match:
            return None
        
        timestamp_str, level, logger_name, message = match.groups()
        
        try:
            from django.utils import timezone as tz
            import pytz
            
            # Parse timestamp as naive datetime
            naive_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            
            # Make it timezone-aware (assume local timezone or UTC)
            timestamp = tz.make_aware(naive_dt, pytz.UTC)
        except ValueError:
            logger.debug(f"Could not parse timestamp: {timestamp_str}")
            return None
        
        return {
            'timestamp': timestamp,
            'level': level,
            'logger_name': logger_name,
            'message': message,
        }
    
    def extract_exception_info(self, lines: List[str], start_idx: int) -> Dict:
        """
        Extract exception information from subsequent lines
        
        Args:
            lines: List of all log lines
            start_idx: Index of the error log line
            
        Returns:
            Dictionary with exception details
        """
        exception_info = {
            'exception_type': '',
            'exception_value': '',
            'stack_trace': '',
        }
        
        # Look for exception details in the following lines
        idx = start_idx + 1
        stack_trace_lines = []
        
        while idx < len(lines):
            line = lines[idx].strip()
            
            # Stop if we hit another log entry
            if self.LOG_PATTERN.match(line):
                break
            
            # Collect stack trace
            if line:
                stack_trace_lines.append(line)
            
            idx += 1
        
        if stack_trace_lines:
            exception_info['stack_trace'] = '\n'.join(stack_trace_lines)
            
            # Try to extract exception type and value
            for line in stack_trace_lines:
                if ':' in line and not line.startswith('File'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        exception_info['exception_type'] = parts[0].strip()
                        exception_info['exception_value'] = parts[1].strip()
                        break
        
        return exception_info
    
    def parse_log_file(
        self,
        file_path: Path,
        min_level: str = 'WARNING',
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Parse a log file and extract relevant entries
        
        Args:
            file_path: Path to the log file
            min_level: Minimum log level to extract (WARNING, ERROR, CRITICAL)
            since: Only extract entries after this timestamp
            
        Returns:
            List of parsed log entries
        """
        level_priority = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4,
        }
        
        min_priority = level_priority.get(min_level, 2)
        entries = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            logger.info(f"Parsing {len(lines)} lines from {file_path.name}")
            
            for idx, line in enumerate(lines):
                parsed = self.parse_log_line(line)
                if not parsed:
                    continue
                
                # Check level priority
                if level_priority.get(parsed['level'], 0) < min_priority:
                    continue
                
                # Check timestamp
                if since and parsed['timestamp'] < since:
                    continue
                
                # Extract exception info for ERROR and CRITICAL
                if parsed['level'] in ['ERROR', 'CRITICAL']:
                    exception_info = self.extract_exception_info(lines, idx)
                    parsed.update(exception_info)
                
                entries.append(parsed)
            
            logger.info(f"Extracted {len(entries)} relevant entries from {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error parsing log file {file_path}: {e}", exc_info=True)
        
        return entries
    
    def analyze_logs(
        self,
        hours_back: int = 24,
        min_level: str = 'WARNING'
    ) -> List[Dict]:
        """
        Analyze all log files and extract relevant entries
        
        Args:
            hours_back: Number of hours to look back
            min_level: Minimum log level to extract
            
        Returns:
            List of all relevant log entries
        """
        from django.utils import timezone as tz
        
        since = tz.now() - timedelta(hours=hours_back)
        all_entries = []
        
        logger.info(f"Analyzing logs from the last {hours_back} hours, min level: {min_level}")
        
        for log_file in self.get_log_files():
            entries = self.parse_log_file(log_file, min_level=min_level, since=since)
            all_entries.extend(entries)
        
        logger.info(f"Total entries extracted: {len(all_entries)}")
        return all_entries
    
    def save_to_database(self, entries: List[Dict]) -> int:
        """
        Save log entries to the database
        
        Args:
            entries: List of parsed log entries
            
        Returns:
            Number of entries saved
        """
        from main.models import LogEntry
        
        saved_count = 0
        
        for entry in entries:
            try:
                # Check if entry already exists (avoid duplicates)
                existing = LogEntry.objects.filter(
                    timestamp=entry['timestamp'],
                    logger_name=entry['logger_name'],
                    message=entry['message']
                ).first()
                
                if existing:
                    logger.debug(f"Entry already exists, skipping")
                    continue
                
                # Create new log entry
                log_entry = LogEntry.objects.create(
                    source='local',
                    level=entry['level'],
                    logger_name=entry['logger_name'],
                    message=entry['message'],
                    timestamp=entry['timestamp'],
                    exception_type=entry.get('exception_type', ''),
                    exception_value=entry.get('exception_value', ''),
                    stack_trace=entry.get('stack_trace', ''),
                    sentry_event_id=None,  # Local logs don't have Sentry IDs
                )
                
                saved_count += 1
                logger.debug(f"Saved log entry: {log_entry}")
                
            except Exception as e:
                logger.error(f"Error saving log entry: {e}", exc_info=True)
        
        logger.info(f"Saved {saved_count} new log entries to database")
        return saved_count
