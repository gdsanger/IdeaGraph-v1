"""
Template tags and filters for comment rendering.
"""
import re
import bleach
from bleach.linkifier import Linker
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# Allowed HTML tags and attributes for comments
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 
    'li', 'ol', 'strong', 'ul', 'br', 'p', 'pre', 'span', 'div',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'thead', 'tbody',
    'tr', 'th', 'td', 'hr', 'img'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'abbr': ['title'],
    'acronym': ['title'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    '*': ['class', 'id']
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

# Enhanced URL pattern that includes IP addresses
# This pattern matches:
# - Standard URLs (http://example.com)
# - IP-based URLs (http://192.168.1.1:8080/path)
# - URLs with ports
# - URLs with paths, query strings, and fragments
URL_PATTERN = re.compile(
    r'(?:(?:https?):\/\/)'  # Protocol (required)
    r'(?:'
    r'(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}|'  # Domain name
    r'(?:\d{1,3}\.){3}\d{1,3}'  # OR IP address
    r')'
    r'(?::\d+)?'  # Optional port
    r'(?:\/[^\s]*)?',  # Optional path
    re.IGNORECASE
)


def find_urls(text):
    """
    Custom URL finder that includes IP addresses.
    """
    for match in URL_PATTERN.finditer(text):
        yield match.start(), match.end(), match.group()


@register.filter(name='render_comment')
def render_comment(text):
    """
    Safely render comment text with HTML and auto-linkify URLs.
    
    This filter:
    1. Sanitizes HTML to prevent XSS attacks
    2. Automatically converts URLs to clickable links (including IP-based URLs)
    3. Preserves safe HTML tags and attributes
    
    Args:
        text (str): The comment text to render
        
    Returns:
        SafeString: The sanitized and linkified HTML
    """
    if not text:
        return ''
    
    # First, sanitize HTML to prevent XSS
    cleaned = bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=False  # Don't strip disallowed tags, convert them to text
    )
    
    # Then linkify URLs using custom linker that supports IP addresses
    linker = Linker(
        callbacks=[],
        skip_tags=['pre', 'code'],  # Don't linkify inside code blocks
        parse_email=False,  # Don't try to parse emails (causes issues with IP addresses)
        url_re=URL_PATTERN  # Use our custom URL pattern
    )
    linkified = linker.linkify(cleaned)
    
    # Mark as safe since we've sanitized it
    return mark_safe(linkified)
