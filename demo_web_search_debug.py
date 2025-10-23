#!/usr/bin/env python
"""
Demo script to show improved web_search_adapter debug logging

This script demonstrates the enhanced error messages and logging
that have been added to the web_search_adapter.
"""

import os
import sys
import django
import logging

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideagraph.settings')
django.setup()

# Configure logging to show all levels
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from main.models import Settings
from core.services.web_search_adapter import WebSearchAdapter, WebSearchAdapterError


def demo_missing_credentials():
    """Demo: Missing API credentials"""
    print("\n" + "="*80)
    print("DEMO 1: Missing API Credentials")
    print("="*80)
    
    # Create settings with empty credentials
    settings = Settings.objects.create(
        google_search_api_key='',
        google_search_cx=''
    )
    
    adapter = WebSearchAdapter(settings=settings)
    
    try:
        adapter.search_google("test query")
    except WebSearchAdapterError as e:
        print(f"\nCaught expected error:")
        print(f"  Message: {e.message}")
        print(f"  Details: {e.details}")
    finally:
        settings.delete()


def demo_invalid_credentials():
    """Demo: Invalid API credentials (will fail in real API call)"""
    print("\n" + "="*80)
    print("DEMO 2: Invalid API Credentials (simulated)")
    print("="*80)
    
    # Create settings with fake credentials
    settings = Settings.objects.create(
        google_search_api_key='invalid_api_key_123',
        google_search_cx='invalid_cx_456'
    )
    
    adapter = WebSearchAdapter(settings=settings)
    
    print("\nNote: This would trigger a real API call which would fail.")
    print("Logs would show:")
    print("  [INFO] Searching Google for: test query")
    print("  [DEBUG] Google Search request URL: https://www.googleapis.com/customsearch/v1")
    print("  [DEBUG] Google Search params: cx=invalid_cx..., num=5")
    print("  [DEBUG] Google Search response status: 403")
    print("  [ERROR] Google Search API error (status 403): ...")
    print("  [ERROR] Google API Error: API key not valid (reason: forbidden)")
    
    settings.delete()


def demo_configuration_logging():
    """Demo: Configuration logging on initialization"""
    print("\n" + "="*80)
    print("DEMO 3: Configuration Logging")
    print("="*80)
    
    # Create settings with Google credentials
    settings = Settings.objects.create(
        google_search_api_key='test_key_with_39_characters_length_xx',
        google_search_cx='test_cx_21_chars_xxx'
    )
    
    print("\nInitializing WebSearchAdapter...")
    adapter = WebSearchAdapter(settings=settings)
    
    print("\nNote: Check the DEBUG logs above for configuration details.")
    print("You should see:")
    print("  - Google API Key configured: True (length: 39)")
    print("  - Google CX configured: True (length: 21)")
    print("  - Brave API Key configured: False")
    
    settings.delete()


def demo_error_dict():
    """Demo: WebSearchAdapterError.to_dict() method"""
    print("\n" + "="*80)
    print("DEMO 4: Error Dictionary Serialization")
    print("="*80)
    
    error = WebSearchAdapterError(
        "Google Search API returned status 403",
        details="API key not valid. Please pass a valid API key. (reason: forbidden)"
    )
    
    error_dict = error.to_dict()
    
    print("\nError as dictionary (for API responses):")
    import json
    print(json.dumps(error_dict, indent=2))


def main():
    """Run all demos"""
    print("\n" + "#"*80)
    print("# Web Search Adapter Debug Logging Demo")
    print("#"*80)
    
    demo_configuration_logging()
    demo_missing_credentials()
    demo_invalid_credentials()
    demo_error_dict()
    
    print("\n" + "="*80)
    print("Demo completed!")
    print("="*80)
    print("\nKey improvements:")
    print("  1. Configuration is logged on initialization (with key lengths)")
    print("  2. Request/response details are logged at DEBUG level")
    print("  3. Errors include specific details (status codes, reasons, etc.)")
    print("  4. Full tracebacks are logged for unexpected errors")
    print("  5. Warnings are shown when no results are found")
    print("\nFor more information, see:")
    print("  - WEB_SEARCH_DEBUGGING_GUIDE.md")
    print("  - WEB_SEARCH_DEBUG_SUMMARY.md")
    print()


if __name__ == '__main__':
    main()
