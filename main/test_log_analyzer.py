"""
Tests for AI Log Analyzer & Auto-Task Creator
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from main.models import LogEntry, ErrorAnalysis, Task, Tag, User


class LogEntryModelTest(TestCase):
    """Test LogEntry model"""
    
    def test_create_log_entry(self):
        """Test creating a log entry"""
        log_entry = LogEntry.objects.create(
            source='local',
            level='ERROR',
            logger_name='test_logger',
            message='Test error message',
            timestamp=timezone.now(),
            exception_type='ValueError',
            exception_value='Invalid value',
            stack_trace='Traceback...',
        )
        
        self.assertEqual(log_entry.source, 'local')
        self.assertEqual(log_entry.level, 'ERROR')
        self.assertFalse(log_entry.analyzed)
        self.assertIn('ERROR', str(log_entry))
    
    def test_log_entry_sentry_unique(self):
        """Test that sentry_event_id is unique"""
        LogEntry.objects.create(
            source='sentry',
            level='ERROR',
            logger_name='test',
            message='Test',
            timestamp=timezone.now(),
            sentry_event_id='event123',
        )
        
        # Creating another with same sentry_event_id should fail
        with self.assertRaises(Exception):
            LogEntry.objects.create(
                source='sentry',
                level='ERROR',
                logger_name='test',
                message='Test',
                timestamp=timezone.now(),
                sentry_event_id='event123',
            )


class ErrorAnalysisModelTest(TestCase):
    """Test ErrorAnalysis model"""
    
    def setUp(self):
        """Set up test data"""
        self.log_entry = LogEntry.objects.create(
            source='local',
            level='ERROR',
            logger_name='test_logger',
            message='Test error',
            timestamp=timezone.now(),
        )
    
    def test_create_error_analysis(self):
        """Test creating an error analysis"""
        analysis = ErrorAnalysis.objects.create(
            log_entry=self.log_entry,
            severity='high',
            is_actionable=True,
            summary='Critical database error',
            root_cause='Connection timeout',
            recommended_action='Implement connection pooling',
            ai_model='gpt-4',
            ai_confidence=0.95,
        )
        
        self.assertEqual(analysis.severity, 'high')
        self.assertTrue(analysis.is_actionable)
        self.assertEqual(analysis.status, 'pending')
        self.assertIn('Critical database', str(analysis))
    
    def test_approve_and_create_task(self):
        """Test approving an analysis"""
        user = User.objects.create(
            username='testuser',
            email='test@example.com',
        )
        
        analysis = ErrorAnalysis.objects.create(
            log_entry=self.log_entry,
            severity='high',
            is_actionable=True,
            summary='Test error',
            ai_confidence=0.8,
        )
        
        analysis.approve_and_create_task(user)
        
        self.assertEqual(analysis.status, 'approved')
        self.assertEqual(analysis.reviewed_by, user)
        self.assertIsNotNone(analysis.reviewed_at)


class LogAnalyzerServiceTest(TestCase):
    """Test LogAnalyzerService"""
    
    def test_log_pattern(self):
        """Test log line pattern matching"""
        from core.services.log_analyzer_service import LogAnalyzerService
        
        analyzer = LogAnalyzerService()
        
        # Valid log line
        line = "2025-10-19 11:34:34 [ERROR] [test_module] - Test error message"
        parsed = analyzer.parse_log_line(line)
        
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['level'], 'ERROR')
        self.assertEqual(parsed['logger_name'], 'test_module')
        self.assertEqual(parsed['message'], 'Test error message')
    
    def test_log_pattern_invalid(self):
        """Test invalid log line"""
        from core.services.log_analyzer_service import LogAnalyzerService
        
        analyzer = LogAnalyzerService()
        
        # Invalid log line
        line = "This is not a valid log line"
        parsed = analyzer.parse_log_line(line)
        
        self.assertIsNone(parsed)


class AutoTaskCreatorServiceTest(TestCase):
    """Test AutoTaskCreatorService"""
    
    def setUp(self):
        """Set up test data"""
        # Create Settings required for GitHubService
        from main.models import Settings
        Settings.objects.create(
            github_api_enabled=False,  # Disable GitHub for tests
            kigate_api_enabled=False,
            openai_api_enabled=False,
        )
        
        self.log_entry = LogEntry.objects.create(
            source='local',
            level='ERROR',
            logger_name='test_logger',
            message='Test error message',
            timestamp=timezone.now(),
            exception_type='ValueError',
        )
        
        self.analysis = ErrorAnalysis.objects.create(
            log_entry=self.log_entry,
            severity='high',
            is_actionable=True,
            summary='Critical database error',
            root_cause='Connection timeout',
            recommended_action='Implement retry logic',
            ai_model='gpt-4',
            ai_confidence=0.9,
        )
    
    def test_generate_task_title(self):
        """Test task title generation"""
        from core.services.auto_task_creator_service import AutoTaskCreatorService
        
        creator = AutoTaskCreatorService()
        title = creator._generate_task_title(self.analysis)
        
        self.assertIn('🐛', title)
        self.assertIn('Critical database', title)
    
    def test_generate_task_description(self):
        """Test task description generation"""
        from core.services.auto_task_creator_service import AutoTaskCreatorService
        
        creator = AutoTaskCreatorService()
        description = creator._generate_task_description(self.analysis)
        
        self.assertIn('Fehlerbehebung', description)
        self.assertIn('Critical database error', description)
        self.assertIn('Connection timeout', description)
        self.assertIn('Implement retry logic', description)
    
    def test_add_tags_to_task(self):
        """Test adding tags to task"""
        from core.services.auto_task_creator_service import AutoTaskCreatorService
        
        task = Task.objects.create(
            title='Test Task',
            description='Test',
        )
        
        creator = AutoTaskCreatorService()
        creator._add_tags_to_task(task, self.analysis)
        
        tag_names = [tag.name for tag in task.tags.all()]
        self.assertIn('bug', tag_names)
        self.assertIn('auto-generated', tag_names)
        self.assertIn('urgent', tag_names)  # high severity


class IntegrationTest(TestCase):
    """Integration tests for the complete workflow"""
    
    def test_complete_workflow_without_ai(self):
        """Test the complete workflow without AI analysis"""
        from core.services.log_analyzer_service import LogAnalyzerService
        
        # Create log analyzer
        analyzer = LogAnalyzerService()
        
        # Parse some log lines
        log_lines = [
            "2025-10-19 11:34:34 [WARNING] [test] - Warning message",
            "2025-10-19 11:34:35 [ERROR] [test] - Error message",
            "2025-10-19 11:34:36 [CRITICAL] [test] - Critical error",
        ]
        
        entries = []
        for line in log_lines:
            parsed = analyzer.parse_log_line(line)
            if parsed:
                entries.append(parsed)
        
        # Save to database
        saved_count = analyzer.save_to_database(entries)
        
        self.assertGreater(saved_count, 0)
        self.assertEqual(LogEntry.objects.count(), saved_count)
        
        # Verify entries
        error_entry = LogEntry.objects.filter(level='ERROR').first()
        self.assertIsNotNone(error_entry)
        self.assertEqual(error_entry.message, 'Error message')
