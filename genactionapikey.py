#!/usr/bin/env python
"""
Generate API Key Script

This script generates a new API key for the Actions API authentication.

Usage:
    python genactionapikey.py
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideagraph.settings')
import django
django.setup()

from main.models import User, ApiKey

user = User.objects.get(username='admin')
api_key = ApiKey.generate_key(
    user=user,
    name='My API Key',
    expires_at=None  # Optional expiration
)

# Save the key value - it won't be shown again
print(f"API Key: {api_key.key}")
