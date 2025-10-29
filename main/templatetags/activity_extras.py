"""
Template tags and filters for activity sidebar
"""

from django import template
from django.utils import timezone
from datetime import datetime, timedelta

register = template.Library()


# Icon mapping for different activity types
ICON_MAP = {
    "Email": "bi-envelope-fill",
    "Task": "bi-check-square-fill",
    "Item": "bi-lightbulb-fill",
    "GitHubPullRequest": "bi-git",
    "GitHubIssue": "bi-github",
    "File": "bi-file-earmark-text-fill",
    "Comment": "bi-chat-left-text-fill",
}


@register.filter
def type_to_icon(activity_type):
    """
    Convert activity type to Bootstrap icon class
    
    Args:
        activity_type: Type of activity (Email, Task, Item, etc.)
    
    Returns:
        Bootstrap icon class string
    """
    return ICON_MAP.get(activity_type, "bi-file-earmark-fill")


@register.filter
def type_to_badge_color(activity_type):
    """
    Convert activity type to Bootstrap badge color class
    
    Args:
        activity_type: Type of activity
    
    Returns:
        Bootstrap badge color class
    """
    color_map = {
        "Email": "primary",
        "Task": "success",
        "Item": "warning",
        "GitHubPullRequest": "info",
        "GitHubIssue": "danger",
        "File": "secondary",
        "Comment": "light",
    }
    return color_map.get(activity_type, "secondary")


@register.simple_tag
def build_activity_link(item):
    """
    Build internal or external link for activity item
    
    Args:
        item: Activity item dictionary
    
    Returns:
        URL string
    """
    # External link (GitHub)
    if item.get("url"):
        return item["url"]
    
    activity_type = item.get("type")
    
    # Email: link to task comment
    if activity_type == "Email":
        task_id = item.get("taskId")
        item_id = item.get("id")
        if task_id:
            return f"/tasks/{task_id}/#comment-{item_id}"
        return "#"
    
    # Task: link to task detail
    if activity_type == "Task":
        slug = item.get("slug") or item.get("id")
        if slug:
            return f"/tasks/{slug}/"
        return "#"
    
    # Item: link to item detail
    if activity_type == "Item":
        slug = item.get("slug") or item.get("id")
        if slug:
            return f"/items/{slug}/"
        return "#"
    
    # Default fallback
    return "#"


@register.filter
def relative_time(timestamp):
    """
    Convert timestamp to relative time string (e.g., "2 hours ago")
    
    Args:
        timestamp: ISO timestamp string or datetime object
    
    Returns:
        Relative time string in German
    """
    if not timestamp:
        return "Unbekannt"
    
    # Parse timestamp if it's a string
    if isinstance(timestamp, str):
        try:
            # Try parsing ISO format with timezone
            if 'T' in timestamp:
                # Remove microseconds and parse
                timestamp = timestamp.split('.')[0]
                if timestamp.endswith('Z'):
                    timestamp = timestamp[:-1]
                dt = datetime.fromisoformat(timestamp)
            else:
                dt = datetime.fromisoformat(timestamp)
        except (ValueError, AttributeError):
            return "Unbekannt"
    else:
        dt = timestamp
    
    # Make timezone-aware if needed
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    
    now = timezone.now()
    diff = now - dt
    
    # Calculate relative time
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Gerade eben"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"vor {minutes} Min." if minutes > 1 else "vor 1 Min."
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"vor {hours} Std." if hours > 1 else "vor 1 Std."
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"vor {days} Tagen" if days > 1 else "vor 1 Tag"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"vor {weeks} Wochen" if weeks > 1 else "vor 1 Woche"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"vor {months} Monaten" if months > 1 else "vor 1 Monat"
    else:
        years = int(seconds / 31536000)
        return f"vor {years} Jahren" if years > 1 else "vor 1 Jahr"


@register.filter
def truncate_title(title, max_length=50):
    """
    Truncate title to max_length characters
    
    Args:
        title: Title string
        max_length: Maximum length (default: 50)
    
    Returns:
        Truncated title with ellipsis if needed
    """
    if not title:
        return "(ohne Titel)"
    
    if len(title) <= max_length:
        return title
    
    return title[:max_length-3] + "..."
