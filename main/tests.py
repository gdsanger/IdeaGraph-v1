from django.test import TestCase, Client
from django.urls import reverse
from .models import Tag
import uuid


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
