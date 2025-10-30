"""
Mail utilities for sending emails via Microsoft Graph API.
"""
import logging
from django.template.loader import render_to_string
from core.services.graph_service import GraphService, GraphServiceError
from core.services.email_conversation_service import EmailConversationService
from core.services.kigate_service import KiGateService, KiGateServiceError
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


def _convert_markdown_to_html(markdown_content: str) -> str:
    """
    Convert Markdown content to HTML using KiGate agent with fallback.
    
    Args:
        markdown_content: Markdown string to convert
        
    Returns:
        HTML string
    """
    if not markdown_content:
        return ""
    
    # Try to use KiGate service for conversion
    try:
        from main.models import Settings
        settings = Settings.objects.first()
        
        if settings and settings.kigate_api_enabled:
            kigate_service = KiGateService(settings)
            
            result = kigate_service.execute_agent(
                agent_name='markdown-to-html-converter',
                provider='openai',
                model='gpt-4',
                message=markdown_content,
                user_id='system'
            )
            
            if result.get('success'):
                html = result.get('result', '')
                # Verify that we actually got HTML back
                if html and ('<' in html and '>' in html):
                    logger.info("Successfully converted Markdown to HTML using KiGate")
                    return html
                else:
                    logger.warning("Markdown to HTML conversion returned non-HTML content, using fallback")
            else:
                logger.warning("Markdown to HTML conversion failed, using fallback")
    except KiGateServiceError as e:
        logger.warning(f"KiGate service error: {e.message}, using fallback conversion")
    except Exception as e:
        logger.warning(f"Error during markdown to HTML conversion: {str(e)}, using fallback")
    
    # Fallback: basic markdown to HTML conversion
    return _basic_markdown_to_html(markdown_content)


def _basic_markdown_to_html(markdown_content: str) -> str:
    """
    Basic fallback method to convert common markdown patterns to HTML.
    
    Args:
        markdown_content: Markdown string to convert
        
    Returns:
        HTML string with basic formatting
    """
    import re
    
    html = markdown_content
    
    # Convert headers (must be done before other conversions)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Convert bold (must be done before italic to avoid conflicts)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html)
    
    # Convert italic (avoid matching already converted bold tags)
    # Use negative lookahead/lookbehind to avoid matching asterisks in bold patterns
    html = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', html)
    html = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<em>\1</em>', html)
    
    # Convert links
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)
    
    # Helper function to process lists
    def process_lists(text: str, list_pattern: str, list_tag: str) -> str:
        lines = text.split('\n')
        in_list = False
        result_lines = []
        for line in lines:
            if re.match(list_pattern, line):
                if not in_list:
                    result_lines.append(f'<{list_tag}>')
                    in_list = True
                # Remove the list marker and wrap in <li>
                list_item = re.sub(list_pattern, '', line)
                result_lines.append(f'<li>{list_item}</li>')
            else:
                if in_list:
                    result_lines.append(f'</{list_tag}>')
                    in_list = False
                result_lines.append(line)
        if in_list:
            result_lines.append(f'</{list_tag}>')
        return '\n'.join(result_lines)
    
    # Convert unordered lists
    html = process_lists(html, r'^\s*[-*+]\s+', 'ul')
    
    # Convert ordered lists
    html = process_lists(html, r'^\s*\d+\.\s+', 'ol')
    
    # Convert code blocks
    html = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
    
    # Convert inline code
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    
    # Convert line breaks (two spaces at end of line or double newline)
    html = re.sub(r'  \n', '<br>\n', html)
    html = re.sub(r'\n\n', '<br><br>\n', html)
    
    return html


def send_task_moved_notification(task_id, source_item_title, target_item_title):
    """
    Send a notification email to the task requester when a task is moved to another item.
    
    Args:
        task_id: UUID of the task that was moved
        source_item_title: Title of the source item (where the task was before)
        target_item_title: Title of the target item (where the task was moved to)
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Get the task with requester information
        task = Task.objects.select_related('requester').get(id=task_id)
        
        # Check if task has a requester
        if not task.requester:
            logger.info(f"Task {task_id} has no requester, skipping notification email")
            return True, "No requester to notify"
        
        # Check if requester has an email
        if not task.requester.email:
            logger.warning(f"Task requester {task.requester.username} has no email address")
            return False, "Requester has no email address"
        
        # Convert task description from Markdown to HTML
        task_description_html = _convert_markdown_to_html(task.description) if task.description else ""
        
        # Prepare context for the email template
        context = {
            'requester_name': task.requester.username,
            'task_title': task.title,
            'task_description': task_description_html,
            'source_item_title': source_item_title,
            'target_item_title': target_item_title
        }
        
        # Render the email template
        html_content = render_to_string('main/mailtemplates/task_moved.html', context)
        
        # Initialize Graph service
        graph_service = GraphService()
        
        # Send email
        result = graph_service.send_mail(
            to=[task.requester.email],
            subject=f'Task verschoben: {task.title}',
            body=html_content
        )
        
        if result.get('success'):
            logger.info(f"Task moved notification sent successfully to {task.requester.email} for task {task.title}")
            return True, "Notification email sent successfully"
        else:
            logger.error(f"Failed to send task moved notification to {task.requester.email}")
            return False, "Failed to send notification email"
            
    except Task.DoesNotExist:
        logger.error(f"Task with id {task_id} not found")
        return False, "Task not found"
    except GraphServiceError as e:
        logger.error(f"Graph service error sending task moved notification: {e.message}")
        return False, f"Email service error: {e.message}"
    except Exception as e:
        logger.error(f"Unexpected error sending task moved notification: {str(e)}")
        return False, f"Unexpected error: {str(e)}"
