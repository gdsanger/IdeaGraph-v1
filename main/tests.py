from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model as get_django_user_model
from .models import Tag, Settings, User as AppUser
import uuid
import json


DjangoUser = get_django_user_model()


class TagModelTest(TestCase):
    """Test the Tag model"""

    def test_create_tag_with_default_color(self):
        """Test creating a tag with default color assignment"""
        tag = Tag.objects.create(name="Test Tag")
        self.assertEqual(tag.name, "Test Tag")
        self.assertIsNotNone(tag.color)
        self.assertTrue(tag.color.startswith('#'))
        self.assertEqual(len(tag.color), 7)
        self.assertIn(tag.color, Tag.COLOR_PALETTE)

    def test_create_tag_with_custom_color(self):
        """Test creating a tag with custom color"""
        custom_color = "#123456"
        tag = Tag.objects.create(name="Custom Tag", color=custom_color)
        tag.refresh_from_db()
        self.assertEqual(tag.color, custom_color)

    def test_tag_str_representation(self):
        """Test tag string representation"""
        tag = Tag.objects.create(name="String Test")
        self.assertEqual(str(tag), "String Test")

    def test_tag_uuid_primary_key(self):
        """Test that tag uses UUID as primary key"""
        tag = Tag.objects.create(name="UUID Test")
        self.assertIsInstance(tag.id, uuid.UUID)

    def test_tag_unique_name(self):
        """Test that tag names must be unique"""
        Tag.objects.create(name="Unique Tag")
        with self.assertRaises(Exception):
            Tag.objects.create(name="Unique Tag")


class TagViewTest(TestCase):
    """Test the Tag views"""

    def setUp(self):
        """Set up test client and sample data"""
        self.client = Client()
        self.tag = Tag.objects.create(name="Test Tag", color="#ef4444")

    def test_tag_list_view(self):
        """Test tag list view returns correctly"""
        response = self.client.get(reverse('main:tag_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Tag")
        self.assertContains(response, self.tag.color)

    def test_tag_create_view_get(self):
        """Test tag create view GET request"""
        response = self.client.get(reverse('main:tag_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create New Tag")

    def test_tag_create_view_post(self):
        """Test tag create view POST request"""
        data = {
            'name': 'New Tag',
            'color': '#00ff00'
        }
        response = self.client.post(reverse('main:tag_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Tag.objects.filter(name='New Tag').exists())
        
        new_tag = Tag.objects.get(name='New Tag')
        self.assertEqual(new_tag.color, '#00ff00')

    def test_tag_edit_view_get(self):
        """Test tag edit view GET request"""
        response = self.client.get(reverse('main:tag_edit', args=[self.tag.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Tag")
        self.assertContains(response, self.tag.name)

    def test_tag_edit_view_post(self):
        """Test tag edit view POST request"""
        data = {
            'name': 'Updated Tag',
            'color': '#0000ff'
        }
        response = self.client.post(reverse('main:tag_edit', args=[self.tag.id]), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, 'Updated Tag')
        self.assertEqual(self.tag.color, '#0000ff')

    def test_tag_delete_view_get(self):
        """Test tag delete view GET request"""
        response = self.client.get(reverse('main:tag_delete', args=[self.tag.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete Tag")
        self.assertContains(response, self.tag.name)

    def test_tag_delete_view_post(self):
        """Test tag delete view POST request"""
        tag_id = self.tag.id
        response = self.client.post(reverse('main:tag_delete', args=[self.tag.id]))
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertFalse(Tag.objects.filter(id=tag_id).exists())

    def test_settings_view(self):
        """Test settings page view"""
        response = self.client.get(reverse('main:settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Settings")


class SectionModelTest(TestCase):
    """Test the Section model"""

    def test_create_section(self):
        """Test creating a section"""
        section = Section.objects.create(name="Software Project")
        self.assertEqual(section.name, "Software Project")
        self.assertIsNotNone(section.id)

    def test_section_str_representation(self):
        """Test section string representation"""
        section = Section.objects.create(name="DIY Item")
        self.assertEqual(str(section), "DIY Item")

    def test_section_uuid_primary_key(self):
        """Test that section uses UUID as primary key"""
        section = Section.objects.create(name="UUID Test")
        self.assertIsInstance(section.id, uuid.UUID)

    def test_section_unique_name(self):
        """Test that section names must be unique"""
        Section.objects.create(name="Unique Section")
        with self.assertRaises(Exception):
            Section.objects.create(name="Unique Section")

    def test_section_ordering(self):
        """Test that sections are ordered by name"""
        Section.objects.create(name="Zebra")
        Section.objects.create(name="Alpha")
        Section.objects.create(name="Beta")
        sections = list(Section.objects.all())
        self.assertEqual(sections[0].name, "Alpha")
        self.assertEqual(sections[1].name, "Beta")
        self.assertEqual(sections[2].name, "Zebra")


class SectionViewTest(TestCase):
    """Test the Section views"""

    def setUp(self):
        """Set up test client and sample data"""
        self.client = Client()
        self.section = Section.objects.create(name="Test Section")

    def test_section_list_view(self):
        """Test section list view returns correctly"""
        response = self.client.get(reverse('main:section_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Section")
        self.assertContains(response, "Sections")

    def test_section_create_view_get(self):
        """Test section create view GET request"""
        response = self.client.get(reverse('main:section_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create New Section")

    def test_section_create_view_post(self):
        """Test section create view POST request"""
        data = {'name': 'New Section'}
        response = self.client.post(reverse('main:section_create'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Section.objects.filter(name='New Section').exists())

    def test_section_edit_view_get(self):
        """Test section edit view GET request"""
        response = self.client.get(reverse('main:section_edit', args=[self.section.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit Section")
        self.assertContains(response, self.section.name)

    def test_section_edit_view_post(self):
        """Test section edit view POST request"""
        data = {'name': 'Updated Section'}
        response = self.client.post(reverse('main:section_edit', args=[self.section.id]), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        self.section.refresh_from_db()
        self.assertEqual(self.section.name, 'Updated Section')

    def test_section_delete_view_get(self):
        """Test section delete view GET request"""
        response = self.client.get(reverse('main:section_delete', args=[self.section.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete Section")
        self.assertContains(response, self.section.name)

    def test_section_delete_view_post(self):
        """Test section delete view POST request"""
        section_id = self.section.id
        response = self.client.post(reverse('main:section_delete', args=[self.section.id]))
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertFalse(Section.objects.filter(id=section_id).exists())


from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Settings
import uuid

User = get_user_model()


class SettingsModelTest(TestCase):
    """Test the Settings model"""
    
    def test_create_settings(self):
        """Test creating a settings entry"""
        settings = Settings.objects.create(
            openai_api_key='test-key',
            max_tags_per_idea=10
        )
        self.assertIsInstance(settings.id, uuid.UUID)
        self.assertEqual(settings.openai_api_key, 'test-key')
        self.assertEqual(settings.max_tags_per_idea, 10)
    
    def test_settings_string_representation(self):
        """Test the string representation of settings"""
        settings = Settings.objects.create()
        self.assertTrue(str(settings).startswith('Settings - '))


class SettingsViewTest(TestCase):
    """Test the Settings views"""
    
    def setUp(self):
        """Set up test client and admin user"""
        self.client = Client()
        self.admin_user = DjangoUser.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.settings = Settings.objects.create(
            openai_api_key='test-key',
            max_tags_per_idea=5
        )
    
    def test_settings_list_requires_staff(self):
        """Test that settings list requires staff access"""
        response = self.client.get(reverse('main:settings_list'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
    
    def test_settings_list_accessible_by_staff(self):
        """Test that staff can access settings list"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('main:settings_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Settings Management')
    
    def test_settings_create_get(self):
        """Test settings create form display"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('main:settings_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Settings')
    
    def test_settings_create_post(self):
        """Test creating settings via POST"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(reverse('main:settings_create'), {
            'openai_api_key': 'new-key',
            'max_tags_per_idea': 15
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(Settings.objects.count(), 2)  # One from setUp, one new
    
    def test_settings_update_get(self):
        """Test settings update form display"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('main:settings_update', kwargs={'pk': self.settings.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Update Settings')
        self.assertContains(response, 'test-key')
    
    def test_settings_update_post(self):
        """Test updating settings via POST"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.post(
            reverse('main:settings_update', kwargs={'pk': self.settings.id}),
            {
                'openai_api_key': 'updated-key',
                'max_tags_per_idea': 20
            }
        )
        self.assertEqual(response.status_code, 302)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.openai_api_key, 'updated-key')
        self.assertEqual(self.settings.max_tags_per_idea, 20)
    
    def test_settings_delete_get(self):
        """Test settings delete confirmation display"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(
            reverse('main:settings_delete', kwargs={'pk': self.settings.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirm Deletion')
    
    def test_settings_delete_post(self):
        """Test deleting settings via POST"""
        self.client.login(username='admin', password='testpass123')
        settings_id = self.settings.id
        response = self.client.post(
            reverse('main:settings_delete', kwargs={'pk': settings_id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Settings.objects.filter(id=settings_id).exists())


class UserModelTest(TestCase):
    """Test the User model"""
    
    def test_create_user(self):
        """Test creating a user"""
        user = AppUser(username='testuser', email='test@example.com', role='user')
        user.set_password('TestPass123!')
        user.save()
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.role, 'user')
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.password_hash)
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        user = AppUser(username='testuser', email='test@example.com')
        password = 'SecurePass123!'
        user.set_password(password)
        user.save()
        
        # Password should be hashed
        self.assertNotEqual(user.password_hash, password)
        
        # check_password should verify correctly
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.check_password('wrongpassword'))
    
    def test_user_roles(self):
        """Test different user roles"""
        admin = AppUser.objects.create(username='admin', email='admin@example.com', role='admin')
        user = AppUser.objects.create(username='user', email='user@example.com', role='user')
        viewer = AppUser.objects.create(username='viewer', email='viewer@example.com', role='viewer')
        
        self.assertEqual(admin.role, 'admin')
        self.assertEqual(user.role, 'user')
        self.assertEqual(viewer.role, 'viewer')
    
    def test_update_last_login(self):
        """Test updating last login timestamp"""
        user = AppUser.objects.create(username='testuser', email='test@example.com')
        self.assertIsNone(user.last_login)
        
        user.update_last_login()
        self.assertIsNotNone(user.last_login)


class UserAPITest(TestCase):
    """Test the User API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create admin user
        self.admin = AppUser(username='admin', email='admin@example.com', role='admin')
        self.admin.set_password('AdminPass123!')
        self.admin.save()
        
        # Create regular user
        self.user = AppUser(username='user', email='user@example.com', role='user')
        self.user.set_password('UserPass123!')
        self.user.save()
        
    def test_login_success(self):
        """Test successful login"""
        response = self.client.post(
            reverse('main:api_login'),
            data=json.dumps({'username': 'admin', 'password': 'AdminPass123!'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'admin')
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post(
            reverse('main:api_login'),
            data=json.dumps({'username': 'admin', 'password': 'wrongpassword'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)
    
    def test_login_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        
        response = self.client.post(
            reverse('main:api_login'),
            data=json.dumps({'username': 'user', 'password': 'UserPass123!'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
    
    def test_logout(self):
        """Test logout endpoint"""
        response = self.client.post(reverse('main:api_logout'))
        self.assertEqual(response.status_code, 200)


class UserViewTest(TestCase):
    """Test the User management views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create Django admin user (for staff access)
        self.admin_user = DjangoUser.objects.create_superuser(
            username='djangoadmin',
            email='djangoadmin@test.com',
            password='testpass123'
        )
        
        # Create app user
        self.app_user = AppUser(username='appuser', email='appuser@example.com', role='user')
        self.app_user.set_password('UserPass123!')
        self.app_user.save()
    
    def test_user_list_requires_staff(self):
        """Test that user list requires staff access"""
        response = self.client.get(reverse('main:user_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_user_list_accessible_by_staff(self):
        """Test that staff can access user list"""
        self.client.login(username='djangoadmin', password='testpass123')
        response = self.client.get(reverse('main:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')
    
    def test_user_create_get(self):
        """Test user create form display"""
        self.client.login(username='djangoadmin', password='testpass123')
        response = self.client.get(reverse('main:user_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New User')
    
    def test_user_create_post(self):
        """Test creating a user via POST"""
        self.client.login(username='djangoadmin', password='testpass123')
        response = self.client.post(reverse('main:user_create'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!',
            'role': 'user',
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(AppUser.objects.filter(username='newuser').exists())
    
    def test_user_edit_get(self):
        """Test user edit form display"""
        self.client.login(username='djangoadmin', password='testpass123')
        response = self.client.get(reverse('main:user_edit', args=[self.app_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit User')
        self.assertContains(response, self.app_user.username)
    
    def test_user_edit_post(self):
        """Test updating a user via POST"""
        self.client.login(username='djangoadmin', password='testpass123')
        response = self.client.post(
            reverse('main:user_edit', args=[self.app_user.id]),
            {
                'email': 'updated@example.com',
                'role': 'admin',
                'is_active': 'on',
            }
        )
        self.assertEqual(response.status_code, 302)
        self.app_user.refresh_from_db()
        self.assertEqual(self.app_user.email, 'updated@example.com')
        self.assertEqual(self.app_user.role, 'admin')
    
    def test_user_detail_get(self):
        """Test user detail view"""
        self.client.login(username='djangoadmin', password='testpass123')
        response = self.client.get(reverse('main:user_detail', args=[self.app_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Details')
        self.assertContains(response, self.app_user.username)
    
    def test_user_delete_get(self):
        """Test user delete confirmation display"""
        self.client.login(username='djangoadmin', password='testpass123')
        response = self.client.get(reverse('main:user_delete', args=[self.app_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete User')
        self.assertContains(response, self.app_user.username)
    
    def test_user_delete_post(self):
        """Test deleting a user via POST"""
        self.client.login(username='djangoadmin', password='testpass123')
        user_id = self.app_user.id
        response = self.client.post(reverse('main:user_delete', args=[user_id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(AppUser.objects.filter(id=user_id).exists())
