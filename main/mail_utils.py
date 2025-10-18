"""
Mail utilities for sending emails via Microsoft Graph API.
"""
import logging
from django.template.loader import render_to_string
from core.services.graph_service import GraphService, GraphServiceError


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
