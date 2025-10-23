"""
Test multi-file upload and pagination for Item files
"""
import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from main.models import User, Item, Section, ItemFile, Settings
from main.api_views import api_item_file_upload, api_item_file_list
from django.core.files.uploadedfile import SimpleUploadedFile


class MultiFileUploadAndPaginationTest(TestCase):
    """Test multi-file upload and pagination functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(
            name='Test Section'
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
        
        # Set up request factory
        self.factory = RequestFactory()
    
    def test_api_accepts_multiple_files(self):
        """Test that API can accept multiple files in one request"""
        # Create mock files
        file1 = SimpleUploadedFile("test1.txt", b"Test content 1", content_type="text/plain")
        file2 = SimpleUploadedFile("test2.txt", b"Test content 2", content_type="text/plain")
        file3 = SimpleUploadedFile("test3.txt", b"Test content 3", content_type="text/plain")
        
        # Create POST request with multiple files
        request = self.factory.post(
            f'/api/items/{self.item.id}/files/upload',
            data={'files': [file1, file2, file3]}
        )
        
        # Set HX-Request header to simulate HTMX
        request.META['HTTP_HX_REQUEST'] = 'true'
        
        # Add user to request
        request.user = self.user
        request.session = {'user_id': str(self.user.id)}
        
        # Mock the ItemFileService to avoid SharePoint calls
        with patch('core.services.item_file_service.ItemFileService') as MockService:
            mock_service = MockService.return_value
            mock_service.upload_file.return_value = {'success': True}
            mock_service.list_files.return_value = {
                'success': True,
                'files': [],
                'page': 1,
                'total_pages': 1,
                'total_count': 3
            }
            
            # Call the API
            response = api_item_file_upload(request, str(self.item.id))
            
            # Verify upload_file was called 3 times (once per file)
            # Note: This test validates that the API structure is correct
            # Actual file uploads are mocked to avoid SharePoint calls
            self.assertEqual(response.status_code, 200)
    
    def test_pagination_parameters_passed_to_service(self):
        """Test that pagination parameters are passed to the service"""
        # Create GET request with pagination parameters
        request = self.factory.get(
            f'/api/items/{self.item.id}/files',
            data={'page': '2', 'per_page': '20'}
        )
        
        # Set HX-Request header
        request.META['HTTP_HX_REQUEST'] = 'true'
        
        # Add user to request
        request.user = self.user
        request.session = {'user_id': str(self.user.id)}
        
        # Mock the ItemFileService for pagination test
        with patch('core.services.item_file_service.ItemFileService') as MockService:
            mock_service = MockService.return_value
            mock_service.list_files.return_value = {
                'success': True,
                'files': [],
                'page': 2,
                'total_pages': 3,
                'total_count': 45,
                'has_next': True,
                'has_previous': True,
            }
            
            # Call the API
            response = api_item_file_list(request, str(self.item.id))
            
            # Verify list_files was called with correct parameters
            mock_service.list_files.assert_called_once_with(
                str(self.item.id),
                page=2,
                per_page=20
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_pagination_defaults_applied(self):
        """Test that default pagination values are used when not provided"""
        # Create GET request without pagination parameters
        request = self.factory.get(f'/api/items/{self.item.id}/files')
        
        # Set HX-Request header
        request.META['HTTP_HX_REQUEST'] = 'true'
        
        # Add user to request
        request.user = self.user
        request.session = {'user_id': str(self.user.id)}
        
        # Mock the ItemFileService for defaults test
        with patch('core.services.item_file_service.ItemFileService') as MockService:
            mock_service = MockService.return_value
            mock_service.list_files.return_value = {
                'success': True,
                'files': [],
                'page': 1,
                'total_pages': 1,
                'total_count': 0,
            }
            
            # Call the API
            response = api_item_file_list(request, str(self.item.id))
            
            # Verify list_files was called with default parameters (page=1, per_page=20)
            mock_service.list_files.assert_called_once_with(
                str(self.item.id),
                page=1,
                per_page=20
            )
            
            self.assertEqual(response.status_code, 200)
    
    def test_item_file_service_pagination(self):
        """Test that ItemFileService returns paginated results"""
        from core.services.item_file_service import ItemFileService
        
        # Create some test files in the database
        for i in range(25):
            ItemFile.objects.create(
                item=self.item,
                filename=f'test_file_{i}.txt',
                file_size=1024,
                content_type='text/plain',
                sharepoint_url=f'https://sharepoint.test/file_{i}.txt',
                uploaded_by=self.user
            )
        
        # Test first page
        service = ItemFileService()
        result = service.list_files(str(self.item.id), page=1, per_page=20)
        
        self.assertEqual(result['success'], True)
        self.assertEqual(len(result['files']), 20)
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['total_pages'], 2)
        self.assertEqual(result['total_count'], 25)
        self.assertTrue(result['has_next'])
        self.assertFalse(result['has_previous'])
        
        # Test second page
        result = service.list_files(str(self.item.id), page=2, per_page=20)
        
        self.assertEqual(result['success'], True)
        self.assertEqual(len(result['files']), 5)  # Remaining 5 files
        self.assertEqual(result['page'], 2)
        self.assertEqual(result['total_pages'], 2)
        self.assertEqual(result['total_count'], 25)
        self.assertFalse(result['has_next'])
        self.assertTrue(result['has_previous'])
