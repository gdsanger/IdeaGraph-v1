"""
Tests for Toast Notification functionality
"""
from django.test import TestCase, Client
from django.contrib.messages import get_messages
from main.models import User


class ToastNotificationTest(TestCase):
    """Test Toast Notifications are properly displayed"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in a user"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session['user_role'] = self.user.role
        session.save()
    
    def test_toast_container_in_base_template(self):
        """Test that toast-container is present in pages"""
        self.login_user()
        response = self.client.get('/items/')
        
        # Check that the toast container is in the response
        self.assertContains(response, 'toast-container')
        self.assertContains(response, 'position-fixed top-0 end-0')
        
    def test_toast_initialization_script_present(self):
        """Test that toast initialization JavaScript is present"""
        self.login_user()
        response = self.client.get('/items/')
        
        # Check that the toast initialization script is present
        self.assertContains(response, 'Toast Initialization Script')
        self.assertContains(response, 'bootstrap.Toast')
        self.assertContains(response, 'delay: 15000')
        
    def test_success_message_creates_toast(self):
        """Test that success messages create toast notifications"""
        self.login_user()
        
        # Create an item which should generate a success message
        response = self.client.post('/items/create/', {
            'title': 'Test Item for Toast',
            'description': 'Test description',
            'status': 'new'
        }, follow=True)
        
        # Check that success message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('created successfully', str(messages[0]))
        
        # Check that toast is rendered
        self.assertContains(response, 'class="toast')
        self.assertContains(response, 'text-bg-success')
        
    def test_error_message_creates_toast(self):
        """Test that error messages create toast notifications"""
        self.login_user()
        
        # Try to create an item without title to trigger error
        response = self.client.post('/items/create/', {
            'description': 'Test description',
            'status': 'new'
        })
        
        # Check that error message was added
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('required', str(messages[0]))
        
        # Check that toast is rendered with error styling
        self.assertContains(response, 'class="toast')
        self.assertContains(response, 'text-bg-error')
    
    def test_toast_has_close_button(self):
        """Test that toasts have a close button"""
        self.login_user()
        
        # Trigger an error message
        response = self.client.post('/items/create/', {
            'status': 'new'
        })
        
        # Check that close button is present
        self.assertContains(response, 'btn-close')
        self.assertContains(response, 'data-bs-dismiss="toast"')
