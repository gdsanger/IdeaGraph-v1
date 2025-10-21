"""
Test suite for authentication system.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, Mock
from main.models import User, PasswordResetToken, Settings
from main.auth_utils import validate_password
from main.auth_views import send_password_reset_email
import time


class UserModelTest(TestCase):
    """Test User model functionality"""
    
    def setUp(self):
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('Test@1234')
        self.user.save()
    
    def test_user_creation(self):
        """Test user is created successfully"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.role, 'user')
        self.assertTrue(self.user.is_active)
    
    def test_password_hashing(self):
        """Test password is hashed correctly"""
        self.assertNotEqual(self.user.password_hash, 'Test@1234')
        self.assertTrue(self.user.check_password('Test@1234'))
        self.assertFalse(self.user.check_password('wrongpassword'))
    
    def test_update_last_login(self):
        """Test last login timestamp is updated"""
        self.assertIsNone(self.user.last_login)
        self.user.update_last_login()
        self.assertIsNotNone(self.user.last_login)


class PasswordValidationTest(TestCase):
    """Test password validation"""
    
    def test_valid_password(self):
        """Test valid password passes validation"""
        is_valid, msg = validate_password('Test@1234')
        self.assertTrue(is_valid)
        self.assertEqual(msg, '')
    
    def test_password_too_short(self):
        """Test password that is too short fails"""
        is_valid, msg = validate_password('Test@1')
        self.assertFalse(is_valid)
        self.assertIn('at least 8 characters', msg)
    
    def test_password_no_number(self):
        """Test password without number fails"""
        is_valid, msg = validate_password('TestTest@')
        self.assertFalse(is_valid)
        self.assertIn('at least one number', msg)
    
    def test_password_no_special(self):
        """Test password without special character fails"""
        is_valid, msg = validate_password('Test1234')
        self.assertFalse(is_valid)
        self.assertIn('special character', msg)


class LoginViewTest(TestCase):
    """Test login functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('Test@1234')
        self.user.save()
    
    def test_login_page_loads(self):
        """Test login page loads successfully"""
        response = self.client.get(reverse('main:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/auth/login.html')
    
    def test_successful_login(self):
        """Test successful login"""
        response = self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'Test@1234'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
        self.assertIn('user_id', self.client.session)
        self.assertEqual(self.client.session['username'], 'testuser')
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('user_id', self.client.session)
    
    def test_login_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        
        response = self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'Test@1234'
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('user_id', self.client.session)


class LogoutViewTest(TestCase):
    """Test logout functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('Test@1234')
        self.user.save()
        
        # Login first
        self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'Test@1234'
        })
    
    def test_logout(self):
        """Test logout clears session"""
        self.assertIn('user_id', self.client.session)
        
        response = self.client.get(reverse('main:logout'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Session should be cleared
        self.assertNotIn('user_id', self.client.session)


class RegistrationViewTest(TestCase):
    """Test registration functionality"""
    
    def setUp(self):
        self.client = Client()
    
    def test_registration_page_loads(self):
        """Test registration page loads successfully"""
        response = self.client.get(reverse('main:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/auth/register.html')
    
    def test_successful_registration(self):
        """Test successful user registration"""
        response = self.client.post(reverse('main:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'Test@1234',
            'password_confirm': 'Test@1234'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Check user was created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'new@example.com')
        self.assertTrue(user.check_password('Test@1234'))
    
    def test_registration_password_mismatch(self):
        """Test registration with mismatched passwords"""
        response = self.client.post(reverse('main:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'Test@1234',
            'password_confirm': 'Different@1234'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_registration_duplicate_username(self):
        """Test registration with existing username"""
        User.objects.create(
            username='existinguser',
            email='existing@example.com',
            role='user'
        )
        
        response = self.client.post(reverse('main:register'), {
            'username': 'existinguser',
            'email': 'new@example.com',
            'password': 'Test@1234',
            'password_confirm': 'Test@1234'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='existinguser').count(), 1)


class PasswordResetTest(TestCase):
    """Test password reset functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('Test@1234')
        self.user.save()
    
    def test_password_reset_token_generation(self):
        """Test password reset token is generated correctly"""
        token = PasswordResetToken.generate_token(self.user)
        
        self.assertIsNotNone(token)
        self.assertEqual(token.user, self.user)
        self.assertFalse(token.used)
        self.assertTrue(token.is_valid())
    
    def test_password_reset_token_expiration(self):
        """Test password reset token expires"""
        token = PasswordResetToken.generate_token(self.user)
        
        # Manually expire the token
        token.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        token.save()
        
        self.assertFalse(token.is_valid())
    
    def test_password_reset_token_used(self):
        """Test used token is not valid"""
        token = PasswordResetToken.generate_token(self.user)
        token.mark_as_used()
        
        self.assertFalse(token.is_valid())
    
    def test_password_reset_invalidates_old_tokens(self):
        """Test generating new token invalidates old ones"""
        token1 = PasswordResetToken.generate_token(self.user)
        token2 = PasswordResetToken.generate_token(self.user)
        
        # Refresh token1 from database
        token1.refresh_from_db()
        
        self.assertTrue(token1.used)
        self.assertFalse(token2.used)


class ChangePasswordTest(TestCase):
    """Test password change functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('Test@1234')
        self.user.save()
        
        # Login
        self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'Test@1234'
        })
    
    def test_change_password_page_loads(self):
        """Test change password page loads for logged-in user"""
        response = self.client.get(reverse('main:change_password'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/auth/change_password.html')
    
    def test_successful_password_change(self):
        """Test successful password change"""
        response = self.client.post(reverse('main:change_password'), {
            'current_password': 'Test@1234',
            'new_password': 'NewPass@1234',
            'confirm_password': 'NewPass@1234'
        })
        self.assertEqual(response.status_code, 302)  # Redirect to home
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass@1234'))
        self.assertFalse(self.user.check_password('Test@1234'))
    
    def test_password_change_wrong_current(self):
        """Test password change with wrong current password"""
        response = self.client.post(reverse('main:change_password'), {
            'current_password': 'WrongPass@1234',
            'new_password': 'NewPass@1234',
            'confirm_password': 'NewPass@1234'
        })
        self.assertEqual(response.status_code, 200)
        
        # Verify password was not changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Test@1234'))


class AdminAccessTest(TestCase):
    """Test admin access control"""
    
    def setUp(self):
        self.client = Client()
        
        # Create regular user
        self.user = User.objects.create(
            username='regularuser',
            email='user@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('Test@1234')
        self.user.save()
        
        # Create admin user
        self.admin = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin.set_password('Admin@1234')
        self.admin.save()
    
    def test_admin_can_access_user_list(self):
        """Test admin can access user list"""
        # Login as admin
        self.client.post(reverse('main:login'), {
            'username': 'admin',
            'password': 'Admin@1234'
        })
        
        response = self.client.get(reverse('main:user_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_regular_user_cannot_access_admin_pages(self):
        """Test regular user cannot access admin pages"""
        # Login as regular user
        self.client.post(reverse('main:login'), {
            'username': 'regularuser',
            'password': 'Test@1234'
        })
        
        response = self.client.get(reverse('main:user_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to home


class DefaultAdminTest(TestCase):
    """Test default admin creation"""
    
    def test_default_admin_credentials(self):
        """Test default admin can login"""
        # Create default admin
        admin = User.objects.create(
            username='admin',
            email='admin@local',
            role='admin',
            is_active=True
        )
        admin.set_password('admin1234')
        admin.save()
        
        # Test login
        client = Client()
        response = client.post(reverse('main:login'), {
            'username': 'admin',
            'password': 'admin1234'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
        self.assertIn('user_id', client.session)
        self.assertEqual(client.session['user_role'], 'admin')


class PasswordGenerationTest(TestCase):
    """Test password generation functionality"""
    
    def test_generate_secure_password(self):
        """Test that generated password is secure and valid"""
        from main.auth_utils import generate_secure_password, validate_password
        
        # Generate password
        password = generate_secure_password(12)
        
        # Check length
        self.assertEqual(len(password), 12)
        
        # Validate password meets requirements
        is_valid, msg = validate_password(password)
        self.assertTrue(is_valid, f"Generated password should be valid: {msg}")
        
    def test_generate_secure_password_minimum_length(self):
        """Test that minimum password length is enforced"""
        from main.auth_utils import generate_secure_password
        
        # Try to generate a short password (should default to 8)
        password = generate_secure_password(4)
        self.assertGreaterEqual(len(password), 8)
        
    def test_password_uniqueness(self):
        """Test that generated passwords are unique"""
        from main.auth_utils import generate_secure_password
        
        # Generate multiple passwords
        passwords = [generate_secure_password(12) for _ in range(10)]
        
        # Check all are unique
        self.assertEqual(len(passwords), len(set(passwords)))


class PasswordResetEmailTest(TestCase):
    """Test password reset email functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('Test@1234')
        self.user.save()
        
        # Create settings with Graph API configuration
        self.settings = Settings.objects.create(
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret',
            default_mail_sender='noreply@ideagraph.test'
        )
    
    @patch('main.auth_views.GraphService')
    def test_send_password_reset_email_uses_correct_parameters(self, mock_graph_service_class):
        """Test that password reset email uses correct send_mail parameters"""
        # Mock the GraphService instance and its send_mail method
        mock_service = Mock()
        mock_service.send_mail.return_value = {'success': True, 'message': 'Email sent'}
        mock_graph_service_class.return_value = mock_service
        
        # Call the function
        reset_url = 'https://example.com/reset/abc123'
        result = send_password_reset_email(self.user, reset_url)
        
        # Verify the function returned True
        self.assertTrue(result)
        
        # Verify send_mail was called with correct parameters
        mock_service.send_mail.assert_called_once()
        call_args = mock_service.send_mail.call_args
        
        # Check positional and keyword arguments
        kwargs = call_args.kwargs if call_args.kwargs else {}
        
        # Verify 'to' parameter is a list containing the user's email
        self.assertIn('to', kwargs)
        self.assertEqual(kwargs['to'], [self.user.email])
        
        # Verify subject is present
        self.assertIn('subject', kwargs)
        self.assertEqual(kwargs['subject'], 'Password Reset Request - IdeaGraph')
        
        # Verify body is present and contains the reset URL
        self.assertIn('body', kwargs)
        self.assertIn(reset_url, kwargs['body'])
        
        # Verify that no incorrect parameters are passed
        self.assertNotIn('to_email', kwargs)
        self.assertNotIn('content_type', kwargs)
    
    @patch('main.auth_views.GraphService')
    def test_send_password_reset_email_uses_default_sender(self, mock_graph_service_class):
        """Test that password reset email uses default sender from settings"""
        # Mock the GraphService instance
        mock_service = Mock()
        mock_service.send_mail.return_value = {'success': True, 'message': 'Email sent'}
        mock_graph_service_class.return_value = mock_service
        
        # Call the function
        reset_url = 'https://example.com/reset/abc123'
        send_password_reset_email(self.user, reset_url)
        
        # Verify send_mail was called without from_address parameter
        # This means it will use the default_mail_sender from settings
        call_args = mock_service.send_mail.call_args
        kwargs = call_args.kwargs if call_args.kwargs else {}
        
        # Verify that from_address is not explicitly set (will use default)
        self.assertNotIn('from_address', kwargs)
    
    @patch('main.auth_views.GraphService')
    def test_send_password_reset_email_handles_graph_error(self, mock_graph_service_class):
        """Test that password reset email handles GraphService errors"""
        from core.services.graph_service import GraphServiceError
        
        # Mock the GraphService to raise an error
        mock_service = Mock()
        mock_service.send_mail.side_effect = GraphServiceError('Service unavailable')
        mock_graph_service_class.return_value = mock_service
        
        # Call the function and expect it to raise an exception
        reset_url = 'https://example.com/reset/abc123'
        with self.assertRaises(GraphServiceError):
            send_password_reset_email(self.user, reset_url)

