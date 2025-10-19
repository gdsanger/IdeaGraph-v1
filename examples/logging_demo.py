#!/usr/bin/env python
"""
Demo script to test centralized logging functionality

This script demonstrates:
1. Different log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
2. Multiple loggers with different names
3. Log rotation capabilities
4. Console and file output
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideagraph.settings')
import django
django.setup()

from core.logger_config import get_logger, LOG_FILE_PATH

def main():
    print("=" * 60)
    print("IdeaGraph Centralized Logging System - Demo")
    print("=" * 60)
    print()
    
    # Get loggers for different components
    main_logger = get_logger('IdeaGraph')
    kigate_logger = get_logger('kigate_service')
    openai_logger = get_logger('openai_service')
    auth_logger = get_logger('auth_service')
    
    print(f"Log file location: {LOG_FILE_PATH}")
    print(f"Log file exists: {LOG_FILE_PATH.exists()}")
    print()
    
    print("Demonstrating different log levels:")
    print("-" * 60)
    
    # Main logger examples
    print("\n1. IdeaGraph Main Logger:")
    main_logger.debug("Debug: Detailed diagnostic information")
    main_logger.info("Info: Application started successfully")
    main_logger.warning("Warning: Configuration value missing, using default")
    main_logger.error("Error: Failed to connect to external service")
    main_logger.critical("Critical: System resource exhausted!")
    
    # Service logger examples
    print("\n2. KiGate Service Logger:")
    kigate_logger.info("KiGate API initialized")
    kigate_logger.info("Making GET request to http://localhost:8000/api/agents")
    kigate_logger.info("Response status: 200")
    kigate_logger.info("Retrieved 5 agents")
    
    print("\n3. OpenAI Service Logger:")
    openai_logger.info("OpenAI API initialized with model: gpt-4")
    openai_logger.info("Making POST request to https://api.openai.com/v1/chat/completions")
    openai_logger.warning("Request took longer than expected: 5.2s")
    openai_logger.info("Response status: 200")
    
    print("\n4. Auth Service Logger:")
    auth_logger.info("User login attempt: user@example.com")
    auth_logger.info("User authenticated successfully: user@example.com")
    auth_logger.warning("Failed login attempt for: invalid@example.com")
    auth_logger.error("Account locked due to too many failed attempts: blocked@example.com")
    
    print("\n" + "-" * 60)
    print("Logging demonstration completed!")
    print(f"\nCheck the log file at: {LOG_FILE_PATH}")
    print()
    
    # Show last few lines of log file
    if LOG_FILE_PATH.exists():
        print("Last 10 lines from log file:")
        print("=" * 60)
        with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(line.rstrip())
        print("=" * 60)

if __name__ == '__main__':
    main()
