"""
Tests for file upload functionality in IdeaGraph
"""

import uuid
from django.test import TestCase
from main.models import User, Item, Section, ItemFile, Settings
from core.services.file_extraction_service import FileExtractionService
from core.services.item_file_service import ItemFileService


class FileExtractionServiceTest(TestCase):
    """Test file extraction service"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = FileExtractionService()
    
    def test_can_extract_text_txt(self):
        """Test text extraction support for .txt files"""
        self.assertTrue(self.service.can_extract_text('test.txt'))
        self.assertTrue(self.service.can_extract_text('test.TXT'))
    
    def test_can_extract_text_python(self):
        """Test text extraction support for Python files"""
        self.assertTrue(self.service.can_extract_text('script.py'))
    
    def test_can_extract_text_csharp(self):
        """Test text extraction support for C# files"""
        self.assertTrue(self.service.can_extract_text('Program.cs'))
    
    def test_can_extract_text_pdf(self):
        """Test text extraction support for PDF files"""
        self.assertTrue(self.service.can_extract_text('document.pdf'))
    
    def test_can_extract_text_docx(self):
        """Test text extraction support for DOCX files"""
        self.assertTrue(self.service.can_extract_text('document.docx'))
    
    def test_cannot_extract_text_binary(self):
        """Test that binary files are not supported"""
        self.assertFalse(self.service.can_extract_text('image.jpg'))
        self.assertFalse(self.service.can_extract_text('video.mp4'))
        self.assertFalse(self.service.can_extract_text('archive.zip'))
    
    def test_extract_text_from_text_file(self):
        """Test text extraction from plain text file"""
        content = b"Hello, World!\nThis is a test file."
        result = self.service.extract_text(content, 'test.txt')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['text'], "Hello, World!\nThis is a test file.")
        self.assertEqual(len(result['chunks']), 1)
        self.assertEqual(result['chunks'][0], "Hello, World!\nThis is a test file.")
    
    def test_extract_text_with_encoding(self):
        """Test text extraction with different encodings"""
        content = "Ümlauts and special chars: äöü".encode('utf-8')
        result = self.service.extract_text(content, 'test.txt')
        
        self.assertTrue(result['success'])
        self.assertIn('Ümlauts', result['text'])
    
    def test_extract_text_too_large(self):
        """Test that files exceeding max size are rejected"""
        # Create a file larger than 25MB
        large_content = b'x' * (26 * 1024 * 1024)
        result = self.service.extract_text(large_content, 'large.txt')
        
        self.assertFalse(result['success'])
        self.assertIn('exceeds maximum', result['error'])
    
    def test_extract_text_unsupported_format(self):
        """Test extraction from unsupported file format"""
        content = b'binary content'
        result = self.service.extract_text(content, 'file.exe')
        
        self.assertFalse(result['success'])
        self.assertIn('Unsupported', result['error'])
    
    def test_split_into_chunks(self):
        """Test text chunking for large files"""
        # Create text that needs to be chunked
        large_text = "Paragraph.\n\n" * 10000  # About 140k chars
        result = self.service._split_into_chunks(large_text)
        
        # Should be split into multiple chunks
        self.assertGreater(len(result), 1)
        
        # Each chunk should be under the limit
        for chunk in result:
            self.assertLessEqual(len(chunk), self.service.MAX_CHUNK_SIZE)
    
    def test_clean_text(self):
        """Test text cleaning"""
        dirty_text = "Line 1\n\n\n\nLine 2    with    spaces"
        clean = self.service._clean_text(dirty_text)
        
        # Should remove excessive newlines and spaces
        self.assertNotIn('\n\n\n', clean)
        self.assertNotIn('    ', clean)


class ItemFileServiceTest(TestCase):
    """Test item file service"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create settings (required for services)
        self.settings = Settings.objects.create(
            graph_api_enabled=False,  # Disable for tests
            weaviate_cloud_enabled=False
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item with Special Chars!@#',
            description='Test description',
            section=self.section,
            created_by=self.user
        )
    
    def test_normalize_folder_name(self):
        """Test folder name normalization"""
        service = ItemFileService(self.settings)
        
        # Test special character removal
        self.assertEqual(
            service.normalize_folder_name('Test:Folder/Name'),
            'Test_Folder_Name'
        )
        
        # Test leading/trailing dots and spaces
        self.assertEqual(
            service.normalize_folder_name('  .test.  '),
            'test'
        )
        
        # Test multiple underscores
        self.assertEqual(
            service.normalize_folder_name('test___folder'),
            'test_folder'
        )
        
        # Test empty result
        self.assertEqual(
            service.normalize_folder_name(':::'),
            'Untitled'
        )
        
        # Test length limit
        long_name = 'a' * 300
        result = service.normalize_folder_name(long_name)
        self.assertEqual(len(result), 255)
    
    def test_upload_file_validation(self):
        """Test file upload validation"""
        service = ItemFileService(self.settings)
        
        # Test file too large (should raise error)
        large_file = b'x' * (26 * 1024 * 1024)
        
        with self.assertRaises(Exception) as context:
            service.upload_file(
                item=self.item,
                file_content=large_file,
                filename='large.txt',
                content_type='text/plain',
                user=self.user
            )
        
        self.assertIn('exceeds maximum', str(context.exception))


class ItemFileModelTest(TestCase):
    """Test ItemFile model"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            created_by=self.user
        )
    
    def test_create_item_file(self):
        """Test creating an ItemFile record"""
        item_file = ItemFile.objects.create(
            item=self.item,
            filename='test.txt',
            file_size=1024,
            sharepoint_file_id='file123',
            sharepoint_url='https://sharepoint.com/file',
            content_type='text/plain',
            uploaded_by=self.user
        )
        
        self.assertEqual(item_file.filename, 'test.txt')
        self.assertEqual(item_file.file_size, 1024)
        self.assertFalse(item_file.weaviate_synced)
        self.assertEqual(item_file.uploaded_by, self.user)
    
    def test_item_file_relationship(self):
        """Test ItemFile relationship with Item"""
        item_file = ItemFile.objects.create(
            item=self.item,
            filename='test.txt',
            file_size=1024,
            uploaded_by=self.user
        )
        
        # Test reverse relationship
        self.assertIn(item_file, self.item.files.all())
        self.assertEqual(self.item.files.count(), 1)
    
    def test_item_file_cascade_delete(self):
        """Test that ItemFile is deleted when Item is deleted"""
        item_file = ItemFile.objects.create(
            item=self.item,
            filename='test.txt',
            file_size=1024,
            uploaded_by=self.user
        )
        
        file_id = item_file.id
        
        # Delete item
        self.item.delete()
        
        # File should be deleted too
        self.assertFalse(ItemFile.objects.filter(id=file_id).exists())
