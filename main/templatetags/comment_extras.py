"""
Template tags and filters for comment rendering.
"""
import re
import bleach
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


@register.filter(name='render_comment')
def render_comment(text):
    """
    Safely render comment text with HTML and auto-linkify URLs.
    
    This filter:
    1. Sanitizes HTML to prevent XSS attacks
    2. Automatically converts URLs to clickable links
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
    
    # Then linkify URLs (this will only affect plain text URLs, not existing <a> tags)
    linkified = bleach.linkify(
        cleaned,
        callbacks=[],
        skip_tags=['pre', 'code']  # Don't linkify inside code blocks
    )
    
    # Mark as safe since we've sanitized it
    return mark_safe(linkified)
