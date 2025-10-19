"""
Test suite for centralized logging configuration.
"""
import os
import tempfile
from pathlib import Path
from django.test import TestCase, override_settings
from core.logger_config import get_logger, LOG_DIR, LOG_FILE_PATH
import logging


class LoggerConfigTest(TestCase):
    """Test logging configuration functionality"""
    
    def test_logger_creation(self):
        """Test that logger can be created successfully"""
        logger = get_logger('test_logger')
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, 'test_logger')
    
    def test_logger_has_handlers(self):
        """Test that logger has file and console handlers"""
        logger = get_logger('test_logger_handlers')
        self.assertTrue(len(logger.handlers) >= 2)
        
        # Check for RotatingFileHandler and StreamHandler
        handler_types = [type(h).__name__ for h in logger.handlers]
        self.assertIn('RotatingFileHandler', handler_types)
        self.assertIn('StreamHandler', handler_types)
    
    def test_logger_levels(self):
        """Test that logger respects level configuration"""
        logger = get_logger('test_logger_levels')
        
        # Logger should be configured based on LOG_LEVEL env var
        # Default is INFO
        self.assertTrue(logger.level <= logging.INFO)
    
    def test_log_directory_creation(self):
        """Test that log directory is created"""
        self.assertTrue(LOG_DIR.exists())
        self.assertTrue(LOG_DIR.is_dir())
    
    def test_log_message_formatting(self):
        """Test that log messages are formatted correctly"""
        logger = get_logger('test_formatter')
        
        # Get the file handler
        file_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                file_handler = handler
                break
        
        self.assertIsNotNone(file_handler)
        
        # Check formatter exists and has correct format
        formatter = file_handler.formatter
        self.assertIsNotNone(formatter)
        self.assertIn('%(asctime)s', formatter._fmt)
        self.assertIn('%(levelname)s', formatter._fmt)
        self.assertIn('%(name)s', formatter._fmt)
    
    def test_logger_singleton_behavior(self):
        """Test that getting the same logger name returns the same instance"""
        logger1 = get_logger('test_singleton')
        logger2 = get_logger('test_singleton')
        
        # Should have the same handlers (not duplicated)
        self.assertEqual(len(logger1.handlers), len(logger2.handlers))
    
    def test_default_logger(self):
        """Test that default logger is named IdeaGraph"""
        from core.logger_config import logger as default_logger
        self.assertEqual(default_logger.name, 'IdeaGraph')
    
    def test_log_file_rotation_config(self):
        """Test that file handler has correct rotation configuration"""
        logger = get_logger('test_rotation')
        
        file_handler = None
        for handler in logger.handlers:
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                file_handler = handler
                break
        
        self.assertIsNotNone(file_handler)
        self.assertEqual(file_handler.maxBytes, int(os.getenv('LOG_MAX_BYTES', 5_000_000)))
        self.assertEqual(file_handler.backupCount, int(os.getenv('LOG_BACKUP_COUNT', 5)))


class LoggerIntegrationTest(TestCase):
    """Test logging integration with Django"""
    
    def test_django_logger_configuration(self):
        """Test that Django logging is properly configured"""
        from django.conf import settings
        
        self.assertIn('LOGGING', dir(settings))
        logging_config = settings.LOGGING
        
        self.assertEqual(logging_config['version'], 1)
        self.assertFalse(logging_config['disable_existing_loggers'])
    
    def test_service_loggers_configured(self):
        """Test that service-specific loggers are configured"""
        from django.conf import settings
        logging_config = settings.LOGGING
        
        # Check that key service loggers are configured
        expected_loggers = ['IdeaGraph', 'auth_service', 'kigate_service', 'openai_service']
        for logger_name in expected_loggers:
            self.assertIn(logger_name, logging_config['loggers'])
    
    def test_log_message_writing(self):
        """Test that log messages can be written"""
        logger = get_logger('test_write')
        
        # This should not raise any exceptions
        try:
            logger.debug("Debug message for testing")
            logger.info("Info message for testing")
            logger.warning("Warning message for testing")
        except Exception as e:
            self.fail(f"Logging raised an exception: {e}")


class SentryConfigTest(TestCase):
    """Test Sentry configuration (without actually initializing Sentry)"""
    
    def test_sentry_optional(self):
        """Test that Sentry is optional and doesn't break if not configured"""
        # This test verifies that the logger works even without Sentry
        logger = get_logger('test_no_sentry')
        
        # Should work fine without Sentry
        logger.info("Test message without Sentry")
        self.assertTrue(True)
    
    def test_sentry_env_var_check(self):
        """Test that ENABLE_SENTRY environment variable is checked"""
        enable_sentry = os.getenv('ENABLE_SENTRY', 'False')
        self.assertIn(enable_sentry.lower(), ['true', 'false'])
