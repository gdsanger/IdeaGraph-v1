"""
Centralized Logging Configuration for IdeaGraph

This module provides a centralized logging system with:
- Local file logging with rotation
- Console logging for development
- Sentry integration for error tracking
- Configurable log levels via environment variables
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Sentry SDK is optional - only import if enabled
sentry_sdk = None
if os.getenv('ENABLE_SENTRY', 'False').lower() == 'true':
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError:
        sentry_sdk = None

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / os.getenv('LOG_DIR', 'logs')
LOG_FILE_PATH = LOG_DIR / os.getenv('LOG_FILE_NAME', 'ideagraph.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 5_000_000))  # 5 MB default
BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))

# Create logs directory if it doesn't exist
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log format: [Datum Uhrzeit] [LEVEL] [Modul] - Nachricht
LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(name)s] - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def initialize_sentry():
    """
    Initialize Sentry SDK for error tracking
    
    Only initializes if ENABLE_SENTRY=True in environment variables
    and SENTRY_DSN is provided.
    """
    if sentry_sdk is None:
        return
    
    sentry_dsn = os.getenv('SENTRY_DSN')
    if not sentry_dsn:
        logging.warning("ENABLE_SENTRY is True but SENTRY_DSN is not set")
        return
    
    environment = os.getenv('APP_ENVIRONMENT', 'development')
    traces_sample_rate = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '1.0'))
    
    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[DjangoIntegration()],
            traces_sample_rate=traces_sample_rate,
            environment=environment,
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of sampled transactions.
            # We recommend adjusting this value in production.
            profiles_sample_rate=traces_sample_rate,
        )
        logging.info(f"Sentry initialized for environment: {environment}")
    except Exception as e:
        logging.error(f"Failed to initialize Sentry: {e}")


def get_logger(name='IdeaGraph'):
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (default: 'IdeaGraph')
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if logger doesn't have handlers yet
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
    
    return logger


# Create default logger instance
logger = get_logger('IdeaGraph')
