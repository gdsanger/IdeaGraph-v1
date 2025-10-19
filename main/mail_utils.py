"""
Mail utilities for sending emails via Microsoft Graph API.
"""
import logging
from django.template.loader import render_to_string
from core.services.graph_service import GraphService, GraphServiceError
from main.models import Item


logger = logging.getLogger('mail_utils')


def send_password_email(user, password):
    """
    Send a password email to a user.
    
    Args:
        user: User model instance
        password: Plain text password to send
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Render the email template
        html_content = render_to_string('main/mailtemplates/send_password.html', {
            'user': user,
            'password': password
        })
        
        # Initialize Graph service
        graph_service = GraphService()
        
        # Send email with sender as idea@angermeier.net
        result = graph_service.send_mail(
            to=[user.email],
            subject='Your New Password - IdeaGraph',
            body=html_content,
            from_address='idea@angermeier.net'
        )
        
        if result.get('success'):
            logger.info(f"Password email sent successfully to {user.email}")
            return True, "Password email sent successfully"
        else:
            logger.error(f"Failed to send password email to {user.email}")
            return False, "Failed to send email"
            
    except GraphServiceError as e:
        logger.error(f"Graph service error sending password email: {e.message}")
        return False, f"Email service error: {e.message}"
    except Exception as e:
        logger.error(f"Unexpected error sending password email: {str(e)}")
        return False, f"Unexpected error: {str(e)}"


def send_item_email(item_id, recipient_email):
    """
    Send an item with its details and tasks via email.
    
    Args:
        item_id: UUID of the item to send
        recipient_email: Email address of the recipient
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Get the item with related data
        item = Item.objects.select_related('section', 'created_by').prefetch_related('tags', 'tasks').get(id=item_id)
        
        # Get open tasks (all tasks that are not done)
        open_tasks = item.tasks.exclude(status='done').select_related('assigned_to')
        
        # Prepare context for the template
        context = {
            'item': item,
            'tags': item.tags.all(),
            'open_tasks': open_tasks,
            'open_tasks_count': open_tasks.count()
        }
        
        # Render the email template
        html_content = render_to_string('main/mailtemplates/send_item.html', context)
        
        # Initialize Graph service
        graph_service = GraphService()
        
        # Send email with item title as subject
        result = graph_service.send_mail(
            to=[recipient_email],
            subject=item.title,
            body=html_content
        )
        
        if result.get('success'):
            logger.info(f"Item email sent successfully to {recipient_email} for item {item.title}")
            return True, "Item email sent successfully"
        else:
            logger.error(f"Failed to send item email to {recipient_email}")
            return False, "Failed to send email"
            
    except Item.DoesNotExist:
        logger.error(f"Item with id {item_id} not found")
        return False, "Item not found"
    except GraphServiceError as e:
        logger.error(f"Graph service error sending item email: {e.message}")
        return False, f"Email service error: {e.message}"
    except Exception as e:
        logger.error(f"Unexpected error sending item email: {str(e)}")
        return False, f"Unexpected error: {str(e)}"
