"""
Mail utilities for sending emails via Microsoft Graph API.
"""
import logging
from django.template.loader import render_to_string
from core.services.graph_service import GraphService, GraphServiceError
from core.services.email_conversation_service import EmailConversationService
from main.models import Item, Task


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


def send_task_email(task_id, recipient_email, subject, body, user=None, in_reply_to=None, cc=None):
    """
    Send an email from a task context with conversation threading.
    
    This function automatically:
    - Adds the task Short-ID to the subject line
    - Sets proper email headers for threading (Message-ID, In-Reply-To, References)
    - Creates a comment in the task to track the sent email
    
    Args:
        task_id: UUID of the task
        recipient_email: Email address of the recipient (can be comma-separated list)
        subject: Email subject (Short-ID will be appended automatically)
        body: Email body in HTML format
        user: User sending the email (optional)
        in_reply_to: Message-ID this email is replying to (optional)
        cc: CC email addresses (can be comma-separated list, optional)
        
    Returns:
        tuple: (success, message/details_dict)
    """
    try:
        # Get the task
        task = Task.objects.get(id=task_id)
        
        # Get settings
        from main.models import Settings
        settings = Settings.objects.first()
        
        if not settings:
            logger.error("No settings found in database")
            return False, "No settings configured"
        
        # Initialize email conversation service
        email_service = EmailConversationService(settings)
        
        # Parse recipient email(s)
        to_list = [email.strip() for email in recipient_email.split(',') if email.strip()]
        
        # Parse CC email(s) if provided
        cc_list = None
        if cc:
            cc_list = [email.strip() for email in cc.split(',') if email.strip()]
        
        # Get references from previous comments if replying
        references = ''
        if in_reply_to:
            # Find the comment with this Message-ID to get its references
            try:
                reply_comment = task.comments.filter(email_message_id=in_reply_to).first()
                if reply_comment and reply_comment.email_references:
                    references = reply_comment.email_references
            except Exception as e:
                logger.warning(f"Could not retrieve references from comment: {str(e)}")
        
        # Send email with threading
        result = email_service.send_task_email(
            task=task,
            to=to_list,
            subject=subject,
            body=body,
            author=user,
            in_reply_to=in_reply_to,
            references=references,
            cc=cc_list
        )
        
        if result.get('success'):
            logger.info(f"Task email sent successfully to {recipient_email} for task {task.title}")
            return True, result
        else:
            logger.error(f"Failed to send task email to {recipient_email}")
            return False, result.get('message', 'Failed to send email')
            
    except Task.DoesNotExist:
        logger.error(f"Task with id {task_id} not found")
        return False, "Task not found"
    except Exception as e:
        logger.error(f"Unexpected error sending task email: {str(e)}")
        return False, f"Unexpected error: {str(e)}"
