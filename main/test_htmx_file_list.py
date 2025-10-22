"""
Tests for htmx-based file list updates in IdeaGraph
"""

import uuid
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Section, ItemFile, Settings


class HtmxFileListTest(TestCase):
    """Test htmx file list functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test section
        self.section = Section.objects.create(
            name='Test Section',
            description='Test Description'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            section=self.section,
            created_by=self.user
        )
        
        # Create settings
        self.settings = Settings.objects.create()
        
        # Set up client and login
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Store session
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_file_list_returns_html_for_htmx_request(self):
        """Test that file list endpoint returns HTML for htmx requests"""
        response = self.client.get(
            f'/api/items/{self.item.id}/files',
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'text/html', response['Content-Type'].encode())
        # Should contain the partial template content
        self.assertIn(b'No files uploaded yet', response.content)
    
    def test_file_list_returns_json_for_regular_request(self):
        """Test that file list endpoint returns JSON for regular requests"""
        response = self.client.get(
            f'/api/items/{self.item.id}/files'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])
        
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('files', data)
    
    def test_file_upload_returns_html_for_htmx_request(self):
        """Test that file upload returns HTML partial for htmx requests"""
        # Create a simple test file
        from io import BytesIO
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        test_file = SimpleUploadedFile(
            "test.txt",
            b"Test file content",
            content_type="text/plain"
        )
        
        response = self.client.post(
            f'/api/items/{self.item.id}/files/upload',
            {'file': test_file},
            HTTP_HX_REQUEST='true'
        )
        
        # Should return HTML partial
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'text/html', response['Content-Type'].encode())
    
    def test_file_delete_returns_html_for_htmx_request(self):
        """Test that file delete returns HTML partial for htmx requests"""
        # First create a file
        file_obj = ItemFile.objects.create(
            item=self.item,
            filename='test.txt',
            file_size=100,
            uploaded_by=self.user
        )
        
        response = self.client.delete(
            f'/api/files/{file_obj.id}/delete',
            HTTP_HX_REQUEST='true'
        )
        
        # Should return HTML partial with updated file list
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'text/html', response['Content-Type'].encode())
    
    def test_htmx_attributes_in_partial_template(self):
        """Test that partial template contains necessary htmx attributes"""
        # Create a test file
        file_obj = ItemFile.objects.create(
            item=self.item,
            filename='test.txt',
            file_size=100,
            sharepoint_url='https://example.com',
            uploaded_by=self.user
        )
        
        response = self.client.get(
            f'/api/items/{self.item.id}/files',
            HTTP_HX_REQUEST='true'
        )
        
        content = response.content.decode('utf-8')
        
        # Should contain htmx attributes for delete button
        self.assertIn('hx-delete', content)
        self.assertIn('hx-target', content)
        self.assertIn('hx-swap', content)
        self.assertIn('hx-confirm', content)
    
    def test_empty_state_displayed_when_no_files(self):
        """Test that empty state is shown when there are no files"""
        response = self.client.get(
            f'/api/items/{self.item.id}/files',
            HTTP_HX_REQUEST='true'
        )
        
        content = response.content.decode('utf-8')
        
        # Should show empty state message
        self.assertIn('No files uploaded yet', content)
        self.assertIn('bi-file-earmark', content)  # Icon class
    
    def test_file_list_displays_files(self):
        """Test that file list displays uploaded files"""
        # Create test files
        ItemFile.objects.create(
            item=self.item,
            filename='test1.txt',
            file_size=1024,
            sharepoint_url='https://example.com/file1',
            uploaded_by=self.user
        )
        ItemFile.objects.create(
            item=self.item,
            filename='test2.pdf',
            file_size=2048,
            sharepoint_url='https://example.com/file2',
            uploaded_by=self.user
        )
        
        response = self.client.get(
            f'/api/items/{self.item.id}/files',
            HTTP_HX_REQUEST='true'
        )
        
        content = response.content.decode('utf-8')
        
        # Should display both files
        self.assertIn('test1.txt', content)
        self.assertIn('test2.pdf', content)
        # Should display table structure
        self.assertIn('<table', content)
        self.assertIn('<thead>', content)
        self.assertIn('<tbody>', content)
    
    def test_unauthorized_access_to_files(self):
        """Test that unauthorized users cannot access files"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Create item owned by other user
        other_item = Item.objects.create(
            title='Other Item',
            description='Other Description',
            section=self.section,
            created_by=other_user
        )
        
        # Try to access files for other user's item
        response = self.client.get(
            f'/api/items/{other_item.id}/files',
            HTTP_HX_REQUEST='true'
        )
        
        # Should be denied access (403 for API, but htmx returns error in HTML)
        self.assertIn(response.status_code, [403, 200])
        if response.status_code == 200:
            # Should show error message in HTML
            content = response.content.decode('utf-8')
            self.assertIn('Permission denied', content)
    
    def test_weaviate_sync_badge_displayed(self):
        """Test that Weaviate sync status badge is displayed"""
        # Create file with Weaviate sync
        ItemFile.objects.create(
            item=self.item,
            filename='synced.txt',
            file_size=1024,
            sharepoint_url='https://example.com/file',
            uploaded_by=self.user,
            weaviate_synced=True
        )
        
        # Create file without Weaviate sync
        ItemFile.objects.create(
            item=self.item,
            filename='notsynced.txt',
            file_size=1024,
            sharepoint_url='https://example.com/file2',
            uploaded_by=self.user,
            weaviate_synced=False
        )
        
        response = self.client.get(
            f'/api/items/{self.item.id}/files',
            HTTP_HX_REQUEST='true'
        )
        
        content = response.content.decode('utf-8')
        
        # Should show both sync statuses
        self.assertIn('Synced', content)
        self.assertIn('Not synced', content)
        self.assertIn('badge bg-success', content)
        self.assertIn('badge bg-secondary', content)


class HtmxFileListIntegrationTest(TestCase):
    """Integration tests for htmx file list functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.section = Section.objects.create(
            name='Test Section',
            description='Test Description'
        )
        
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            section=self.section,
            created_by=self.user
        )
        
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_upload_then_list_workflow(self):
        """Test complete workflow: upload file, then list files"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Upload a file (simulated - would need mock for SharePoint)
        test_file = SimpleUploadedFile(
            "workflow.txt",
            b"Test workflow content",
            content_type="text/plain"
        )
        
        # Note: Actual upload would fail without SharePoint mock
        # But we can test the htmx response format
        response = self.client.post(
            f'/api/items/{self.item.id}/files/upload',
            {'file': test_file},
            HTTP_HX_REQUEST='true'
        )
        
        # Response should be HTML partial (or error message in HTML)
        self.assertEqual(response.status_code, 200)
    
    def test_delete_then_list_workflow(self):
        """Test complete workflow: delete file, then list remaining files"""
        # Create two files
        file1 = ItemFile.objects.create(
            item=self.item,
            filename='file1.txt',
            file_size=1024,
            uploaded_by=self.user
        )
        file2 = ItemFile.objects.create(
            item=self.item,
            filename='file2.txt',
            file_size=2048,
            uploaded_by=self.user
        )
        
        # Delete first file via htmx
        response = self.client.delete(
            f'/api/files/{file1.id}/delete',
            HTTP_HX_REQUEST='true'
        )
        
        # Should return HTML partial with updated list
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        
        # Should show second file but not first
        self.assertIn('file2.txt', content)
        self.assertNotIn('file1.txt', content)
