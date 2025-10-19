"""
IdeaGraph Django Application

This module initializes Sentry for error tracking after Django settings are loaded.
"""
import os

# Initialize Sentry after Django settings are loaded
# This must happen here (after settings are imported) rather than in logger_config.py
# to ensure Django is fully configured before Sentry initialization
if os.getenv('ENABLE_SENTRY', 'False').lower() == 'true':
    from core.logger_config import initialize_sentry
    initialize_sentry()
