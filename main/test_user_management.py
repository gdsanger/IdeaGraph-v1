"""
Test suite for user management with first_name and last_name fields.
"""
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Client as ClientModel


class UserModelFieldsTest(TestCase):
    """Test User model with first_name and last_name fields"""
    
    def test_user_creation_with_names(self):
        """Test user is created with first and last names"""
        user = User.objects.create(
            username='johndoe',
            email='john.doe@example.com',
            first_name='John',
            last_name='Doe',
            role='user',
            is_active=True
        )
        user.set_password('Test@1234')
        user.save()
        
        self.assertEqual(user.username, 'johndoe')
        self.assertEqual(user.email, 'john.doe@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.role, 'user')
        self.assertTrue(user.is_active)
    
    def test_user_creation_without_names(self):
        """Test user can be created without first and last names"""
        user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
    
    def test_user_names_optional(self):
        """Test that first_name and last_name are optional fields"""
        user = User.objects.create(
            username='simpleuser',
            email='simple@example.com',
            first_name='',
            last_name='',
            role='user'
        )
        user.set_password('Test@1234')
        user.save()
        
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')


class UserListViewTest(TestCase):
    """Test user list view with first_name and last_name"""
    
    def setUp(self):
        self.client = Client()
        
        # Create admin user for authentication
        self.admin_user = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('Admin@1234')
        self.admin_user.save()
        
        # Create test users with names
        User.objects.create(
            username='johndoe',
            email='john@example.com',
            first_name='John',
            last_name='Doe',
            role='user',
            is_active=True
        )
        
        User.objects.create(
            username='janedoe',
            email='jane@example.com',
            first_name='Jane',
            last_name='Doe',
            role='user',
            is_active=True
        )
        
        User.objects.create(
            username='bobsmith',
            email='bob@example.com',
            first_name='Bob',
            last_name='Smith',
            role='user',
            is_active=True
        )
        
        # Login as admin
        self.client.post(reverse('main:login'), {
            'username': 'admin',
            'password': 'Admin@1234'
        })
    
    def test_user_list_displays_names(self):
        """Test user list view displays first and last names"""
        response = self.client.get(reverse('main:user_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John')
        self.assertContains(response, 'Doe')
        self.assertContains(response, 'Jane')
        self.assertContains(response, 'Bob')
        self.assertContains(response, 'Smith')
    
    def test_search_by_first_name(self):
        """Test searching users by first name"""
        response = self.client.get(reverse('main:user_list'), {'search': 'John'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'johndoe')
        self.assertNotContains(response, 'janedoe')
        self.assertNotContains(response, 'bobsmith')
    
    def test_search_by_last_name(self):
        """Test searching users by last name"""
        response = self.client.get(reverse('main:user_list'), {'search': 'Smith'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bobsmith')
        self.assertNotContains(response, 'johndoe')
        self.assertNotContains(response, 'janedoe')
    
    def test_search_by_username(self):
        """Test searching users by username still works"""
        response = self.client.get(reverse('main:user_list'), {'search': 'janedoe'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'janedoe')
        self.assertNotContains(response, 'johndoe')
        self.assertNotContains(response, 'bobsmith')
    
    def test_search_by_email(self):
        """Test searching users by email still works"""
        response = self.client.get(reverse('main:user_list'), {'search': 'bob@example.com'})
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'bobsmith')
        self.assertNotContains(response, 'johndoe')


class UserCreateViewTest(TestCase):
    """Test user creation view with first_name and last_name"""
    
    def setUp(self):
        self.client = Client()
        
        # Create admin user for authentication
        self.admin_user = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('Admin@1234')
        self.admin_user.save()
        
        # Login as admin
        self.client.post(reverse('main:login'), {
            'username': 'admin',
            'password': 'Admin@1234'
        })
    
    def test_create_user_with_names(self):
        """Test creating a user with first and last names"""
        response = self.client.post(reverse('main:user_create'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'Test@1234',
            'password_confirm': 'Test@1234',
            'role': 'user',
            'is_active': 'on'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verify user was created with names
        user = User.objects.get(username='newuser')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.email, 'newuser@example.com')
    
    def test_create_user_without_names(self):
        """Test creating a user without first and last names"""
        response = self.client.post(reverse('main:user_create'), {
            'username': 'simpleuser',
            'email': 'simple@example.com',
            'password': 'Test@1234',
            'password_confirm': 'Test@1234',
            'role': 'user',
            'is_active': 'on'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify user was created without names
        user = User.objects.get(username='simpleuser')
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
    
    def test_create_user_form_displays_name_fields(self):
        """Test that create user form displays first and last name fields"""
        response = self.client.get(reverse('main:user_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'first_name')
        self.assertContains(response, 'last_name')
        self.assertContains(response, 'First Name (Vorname)')
        self.assertContains(response, 'Last Name (Nachname)')


class UserEditViewTest(TestCase):
    """Test user edit view with first_name and last_name"""
    
    def setUp(self):
        self.client = Client()
        
        # Create admin user for authentication
        self.admin_user = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('Admin@1234')
        self.admin_user.save()
        
        # Create a test user to edit
        self.test_user = User.objects.create(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            role='user',
            is_active=True
        )
        self.test_user.set_password('Test@1234')
        self.test_user.save()
        
        # Login as admin
        self.client.post(reverse('main:login'), {
            'username': 'admin',
            'password': 'Admin@1234'
        })
    
    def test_edit_user_names(self):
        """Test editing user's first and last names"""
        response = self.client.post(reverse('main:user_edit', args=[self.test_user.id]), {
            'email': 'test@example.com',
            'first_name': 'Updated',
            'last_name': 'Name',
            'role': 'user',
            'is_active': 'on'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify names were updated
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.first_name, 'Updated')
        self.assertEqual(self.test_user.last_name, 'Name')
    
    def test_clear_user_names(self):
        """Test clearing user's first and last names"""
        response = self.client.post(reverse('main:user_edit', args=[self.test_user.id]), {
            'email': 'test@example.com',
            'first_name': '',
            'last_name': '',
            'role': 'user',
            'is_active': 'on'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify names were cleared
        self.test_user.refresh_from_db()
        self.assertEqual(self.test_user.first_name, '')
        self.assertEqual(self.test_user.last_name, '')
    
    def test_edit_user_form_displays_names(self):
        """Test that edit user form displays current names"""
        response = self.client.get(reverse('main:user_edit', args=[self.test_user.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test')
        self.assertContains(response, 'User')
        self.assertContains(response, 'First Name (Vorname)')
        self.assertContains(response, 'Last Name (Nachname)')


class UserDetailViewTest(TestCase):
    """Test user detail view with first_name and last_name"""
    
    def setUp(self):
        self.client = Client()
        
        # Create admin user for authentication
        self.admin_user = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('Admin@1234')
        self.admin_user.save()
        
        # Create a test user
        self.test_user = User.objects.create(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            role='user',
            is_active=True
        )
        
        # Login as admin
        self.client.post(reverse('main:login'), {
            'username': 'admin',
            'password': 'Admin@1234'
        })
    
    def test_user_detail_displays_names(self):
        """Test that user detail view displays first and last names"""
        response = self.client.get(reverse('main:user_detail', args=[self.test_user.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test')
        self.assertContains(response, 'User')
        self.assertContains(response, 'First Name (Vorname)')
        self.assertContains(response, 'Last Name (Nachname)')
    
    def test_user_detail_displays_dash_for_empty_names(self):
        """Test that user detail displays '-' for empty names"""
        user_without_names = User.objects.create(
            username='nonames',
            email='nonames@example.com',
            role='user'
        )
        
        response = self.client.get(reverse('main:user_detail', args=[user_without_names.id]))
        
        self.assertEqual(response.status_code, 200)
        # The template uses |default:"-" filter for empty values
        self.assertContains(response, '-')
