"""
Test script to generate sample log entries for testing the log analyzer
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideagraph.settings')
import django
django.setup()

from core.logger_config import get_logger

# Get different loggers
logger = get_logger('test_module')
error_logger = get_logger('error_prone_service')
api_logger = get_logger('api_service')

print("Generating test log entries...")

# Generate some normal logs
logger.info("Application started successfully")
logger.debug("Debug information: variable x = 42")
api_logger.info("API request received: GET /api/items")

# Generate warnings
logger.warning("API rate limit approaching: 85% used")
error_logger.warning("Database connection pool running low: 2 connections available")

# Generate errors
try:
    # Simulate a database error
    raise ValueError("Invalid configuration: DATABASE_URL not set")
except Exception as e:
    error_logger.error(f"Configuration error: {e}", exc_info=True)

try:
    # Simulate a file not found error
    raise FileNotFoundError("Log file not found: /var/logs/missing.log")
except Exception as e:
    logger.error(f"File operation failed: {e}", exc_info=True)

try:
    # Simulate an API error
    raise ConnectionError("Failed to connect to external API: timeout after 30s")
except Exception as e:
    api_logger.error(f"External API failure: {e}", exc_info=True)

# Critical error
try:
    # Simulate a critical system error
    raise RuntimeError("Database connection lost - cannot establish connection to primary database")
except Exception as e:
    error_logger.critical(f"CRITICAL: System failure: {e}", exc_info=True)

logger.info("Test log generation completed")

print("\n✅ Test logs generated successfully!")
print(f"Check the logs directory at: {project_root / 'logs'}")
