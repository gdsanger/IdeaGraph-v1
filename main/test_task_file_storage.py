"""
Test Task File Storage functionality
"""
import os
import uuid
from django.conf import settings
from django.test import TestCase
from main.models import User, Item, Task, Section, TaskFile, Settings
from core.services.task_file_service import TaskFileService, TaskFileServiceError


class TaskFileStorageTest(TestCase):
    """Test task file storage to local filesystem"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create settings (disable external services for tests)
        self.settings = Settings.objects.create(
            graph_api_enabled=False,
            weaviate_cloud_enabled=False
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
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
        
        # Create test task with item
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            created_by=self.user
        )
        
        # Create standalone task (without item)
        self.standalone_task = Task.objects.create(
            title='Standalone Task',
            description='Task without item',
            status='new',
            created_by=self.user
        )
    
    def tearDown(self):
        """Clean up test files"""
        # Clean up any test files created
        task_files_dir = os.path.join(settings.BASE_DIR, 'media', 'task_files')
        
        # Remove test files
        if os.path.exists(task_files_dir):
            for root, dirs, files in os.walk(task_files_dir, topdown=False):
                for name in files:
                    try:
                        os.remove(os.path.join(root, name))
                    except:
                        pass
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except:
                        pass
    
    def test_save_file_locally_with_item(self):
        """Test that files are saved locally in item/task folder structure"""
        service = TaskFileService(self.settings)
        
        # Test file content
        file_content = b"Test file content for task"
        filename = "test_file.txt"
        
        # Save file locally
        file_path = service._save_file_locally(self.task, file_content, filename)
        
        # Verify file path structure
        self.assertIn('media/task_files', file_path)
        self.assertIn('Test Item with Special Chars', file_path)  # Normalized item name (! @ # removed)
        self.assertIn(str(self.task.id), file_path)  # Task UUID
        self.assertIn(filename, file_path)
        
        # Verify file was actually created
        full_path = os.path.join(settings.BASE_DIR, file_path)
        self.assertTrue(os.path.exists(full_path))
        
        # Verify file content
        with open(full_path, 'rb') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, file_content)
    
    def test_save_file_locally_standalone_task(self):
        """Test that files for standalone tasks are saved in Tasks folder"""
        service = TaskFileService(self.settings)
        
        # Test file content
        file_content = b"Test file content for standalone task"
        filename = "standalone_test.txt"
        
        # Save file locally
        file_path = service._save_file_locally(self.standalone_task, file_content, filename)
        
        # Verify file path structure for standalone task
        self.assertIn('media/task_files/Tasks', file_path)
        self.assertIn(str(self.standalone_task.id), file_path)
        self.assertIn(filename, file_path)
        
        # Verify file was actually created
        full_path = os.path.join(settings.BASE_DIR, file_path)
        self.assertTrue(os.path.exists(full_path))
    
    def test_upload_file_saves_locally(self):
        """Test that upload_file saves file locally and updates file_path"""
        service = TaskFileService(self.settings)
        
        # Test file content
        file_content = b"Test upload content"
        filename = "upload_test.txt"
        content_type = "text/plain"
        
        # Upload file (SharePoint will fail but local save should work)
        result = service.upload_file(
            task=self.task,
            file_content=file_content,
            filename=filename,
            content_type=content_type,
            user=self.user
        )
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['filename'], filename)
        self.assertIn('file_path', result)
        
        # Verify TaskFile record was created with file_path
        task_file = TaskFile.objects.get(id=result['file_id'])
        self.assertIsNotNone(task_file.file_path)
        self.assertIn('media/task_files', task_file.file_path)
        self.assertIn(str(self.task.id), task_file.file_path)
        
        # Verify file exists on filesystem
        full_path = os.path.join(settings.BASE_DIR, task_file.file_path)
        self.assertTrue(os.path.exists(full_path))
    
    def test_upload_file_size_validation(self):
        """Test that files exceeding max size are rejected"""
        service = TaskFileService(self.settings)
        
        # Create file larger than 25MB
        large_content = b'x' * (26 * 1024 * 1024)
        
        with self.assertRaises(TaskFileServiceError) as context:
            service.upload_file(
                task=self.task,
                file_content=large_content,
                filename='large.txt',
                content_type='text/plain',
                user=self.user
            )
        
        self.assertIn('exceeds maximum', str(context.exception))
    
    def test_folder_name_normalization(self):
        """Test that folder names are properly normalized"""
        service = TaskFileService(self.settings)
        
        # Test various special characters
        test_cases = [
            ('Test:Folder/Name', 'Test_Folder_Name'),
            ('Test<>File?', 'Test_File'),
            ('  .test.  ', 'test'),
            ('test___folder', 'test_folder'),
            (':::', 'Untitled'),
        ]
        
        for input_name, expected in test_cases:
            result = service.normalize_folder_name(input_name)
            self.assertEqual(result, expected, f"Failed for input: {input_name}")
    
    def test_delete_file_removes_local_file(self):
        """Test that deleting a TaskFile also removes the local file"""
        service = TaskFileService(self.settings)
        
        # Upload a file first
        file_content = b"Test file to delete"
        filename = "delete_test.txt"
        
        result = service.upload_file(
            task=self.task,
            file_content=file_content,
            filename=filename,
            content_type='text/plain',
            user=self.user
        )
        
        file_id = result['file_id']
        
        # Get the file path before deletion
        task_file = TaskFile.objects.get(id=file_id)
        full_path = os.path.join(settings.BASE_DIR, task_file.file_path)
        
        # Verify file exists
        self.assertTrue(os.path.exists(full_path))
        
        # Delete the file
        delete_result = service.delete_file(file_id, self.user)
        self.assertTrue(delete_result['success'])
        
        # Verify file was removed from filesystem
        self.assertFalse(os.path.exists(full_path))
        
        # Verify database record was deleted
        self.assertFalse(TaskFile.objects.filter(id=file_id).exists())
    
    def test_folder_structure_with_uuid(self):
        """Test that task folder is created with UUID"""
        service = TaskFileService(self.settings)
        
        file_content = b"UUID folder test"
        filename = "uuid_test.txt"
        
        result = service.upload_file(
            task=self.task,
            file_content=file_content,
            filename=filename,
            content_type='text/plain',
            user=self.user
        )
        
        task_file = TaskFile.objects.get(id=result['file_id'])
        
        # Verify the UUID is in the path
        self.assertIn(str(self.task.id), task_file.file_path)
        
        # Verify the folder structure matches expected pattern
        # Should be: media/task_files/{normalized_item_name}/{task_uuid}/filename
        path_parts = task_file.file_path.split(os.sep)
        self.assertEqual(path_parts[0], 'media')
        self.assertEqual(path_parts[1], 'task_files')
        # Third part should be normalized item name
        self.assertEqual(path_parts[2], 'Test Item with Special Chars')  # ! @ # removed by normalization
        # Fourth part should be the task UUID
        self.assertEqual(path_parts[3], str(self.task.id))
        # Fifth part should be the filename
        self.assertEqual(path_parts[4], filename)
    
    def test_filename_sanitization(self):
        """Test that malicious filenames are sanitized"""
        service = TaskFileService(self.settings)
        
        # Test path traversal attack
        malicious_filename = "../../../etc/passwd"
        result = service.upload_file(
            task=self.task,
            file_content=b"test content",
            filename=malicious_filename,
            content_type='text/plain',
            user=self.user
        )
        
        task_file = TaskFile.objects.get(id=result['file_id'])
        
        # Verify the file path doesn't contain parent directory references
        self.assertNotIn('..', task_file.file_path)
        self.assertIn('media/task_files', task_file.file_path)
        self.assertIn(str(self.task.id), task_file.file_path)
        
        # Verify file was saved safely
        full_path = os.path.join(settings.BASE_DIR, task_file.file_path)
        self.assertTrue(os.path.exists(full_path))
        self.assertIn('task_files', full_path)  # Must be in task_files directory
