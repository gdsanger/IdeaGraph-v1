"""
Context processors for making data available in all templates.
"""
from django.db import DatabaseError
from .models import Item, Task


def mail_inbox_badge(request):
    """
    Context processor to add mail inbox badge count to all templates.
    
    Returns the count of new tasks in the "Mail-Eingang" item and the item ID.
    """
    try:
        # Find the "Mail-Eingang" item
        mail_inbox_item = Item.objects.filter(title="Mail-Eingang").first()
        
        if mail_inbox_item:
            # Count tasks with status 'new' in this item
            new_task_count = Task.objects.filter(
                item=mail_inbox_item,
                status='new'
            ).count()
            
            return {
                'mail_inbox_id': mail_inbox_item.id,
                'mail_inbox_new_tasks': new_task_count,
            }
        else:
            # Item doesn't exist yet
            return {
                'mail_inbox_id': None,
                'mail_inbox_new_tasks': 0,
            }
    except (DatabaseError, ValueError, TypeError) as e:
        # In case of database errors or data issues, return safe defaults
        # Log the error for debugging but don't break the page render
        return {
            'mail_inbox_id': None,
            'mail_inbox_new_tasks': 0,
        }
