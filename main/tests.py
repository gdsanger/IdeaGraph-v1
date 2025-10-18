from django.test import TestCase, Client
from django.urls import reverse
from .models import Section
import uuid


class SectionModelTest(TestCase):
    """Test cases for Section model"""
    
    def setUp(self):
        self.section = Section.objects.create(name="Software Project")
    
    def test_section_creation(self):
        """Test that a section can be created"""
        self.assertEqual(self.section.name, "Software Project")
        self.assertIsInstance(self.section.id, uuid.UUID)
    
    def test_section_str_representation(self):
        """Test the string representation of a section"""
        self.assertEqual(str(self.section), "Software Project")
    
    def test_section_unique_name(self):
        """Test that section names must be unique"""
        with self.assertRaises(Exception):
            Section.objects.create(name="Software Project")
    
    def test_section_ordering(self):
        """Test that sections are ordered by name"""
        Section.objects.create(name="DIY Item")
        Section.objects.create(name="Action Required")
        sections = Section.objects.all()
        self.assertEqual(sections[0].name, "Action Required")
        self.assertEqual(sections[1].name, "DIY Item")
        self.assertEqual(sections[2].name, "Software Project")


class SectionViewTest(TestCase):
    """Test cases for Section views"""
    
    def setUp(self):
        self.client = Client()
        self.section = Section.objects.create(name="Test Section")
    
    def test_section_list_view(self):
        """Test the section list view"""
        response = self.client.get(reverse('main:section_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Section")
        self.assertTemplateUsed(response, 'main/section_list.html')
    
    def test_section_create_view_get(self):
        """Test GET request to section create view"""
        response = self.client.get(reverse('main:section_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/section_form.html')
    
    def test_section_create_view_post(self):
        """Test POST request to create a new section"""
        response = self.client.post(
            reverse('main:section_create'),
            {'name': 'New Section'}
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Section.objects.filter(name='New Section').exists())
    
    def test_section_update_view_get(self):
        """Test GET request to section update view"""
        response = self.client.get(
            reverse('main:section_update', kwargs={'pk': self.section.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Section")
        self.assertTemplateUsed(response, 'main/section_form.html')
    
    def test_section_update_view_post(self):
        """Test POST request to update a section"""
        response = self.client.post(
            reverse('main:section_update', kwargs={'pk': self.section.pk}),
            {'name': 'Updated Section'}
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.section.refresh_from_db()
        self.assertEqual(self.section.name, 'Updated Section')
    
    def test_section_delete_view_get(self):
        """Test GET request to section delete view"""
        response = self.client.get(
            reverse('main:section_delete', kwargs={'pk': self.section.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Section")
        self.assertTemplateUsed(response, 'main/section_confirm_delete.html')
    
    def test_section_delete_view_post(self):
        """Test POST request to delete a section"""
        section_pk = self.section.pk
        response = self.client.post(
            reverse('main:section_delete', kwargs={'pk': section_pk})
        )
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertFalse(Section.objects.filter(pk=section_pk).exists())
    
    def test_section_list_view_empty(self):
        """Test section list view when no sections exist"""
        Section.objects.all().delete()
        response = self.client.get(reverse('main:section_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No sections yet")
