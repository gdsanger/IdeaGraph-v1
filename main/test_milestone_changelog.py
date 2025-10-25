"""
Tests for Milestone ChangeLog Feature
"""
from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from main.models import User, Item, Section, Milestone, Task, MilestoneFile


class MilestoneChangeLogModelTest(TestCase):
    """Test the Milestone changelog field and MilestoneFile model"""
    
    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create a test section
        self.section = Section.objects.create(
            name='Test Section'
        )
        
        # Create a test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user,
            status='new'
        )
        
        # Create a test milestone
        self.milestone = Milestone.objects.create(
            name='Test Milestone',
            description='Test milestone description',
            due_date=date.today() + timedelta(days=30),
            status='planned',
            item=self.item
        )
    
    def test_milestone_has_changelog_field(self):
        """Test that milestone has a changelog field"""
        self.assertTrue(hasattr(self.milestone, 'changelog'))
        self.assertEqual(self.milestone.changelog, '')
    
    def test_milestone_changelog_can_be_set(self):
        """Test that changelog can be set and saved"""
        changelog_content = """# ChangeLog

## Version 1.0.0

### Added
- New feature A
- New feature B

### Fixed
- Bug fix 1
- Bug fix 2
"""
        self.milestone.changelog = changelog_content
        self.milestone.save()
        
        # Retrieve from database
        milestone_from_db = Milestone.objects.get(id=self.milestone.id)
        self.assertEqual(milestone_from_db.changelog, changelog_content)
    
    def test_milestone_file_model_exists(self):
        """Test that MilestoneFile model exists and can be created"""
        milestone_file = MilestoneFile.objects.create(
            milestone=self.milestone,
            filename='CHANGELOG_Test_Milestone_20241025.md',
            file_size=1024,
            content_type='text/markdown',
            uploaded_by=self.user
        )
        
        self.assertIsNotNone(milestone_file.id)
        self.assertEqual(milestone_file.milestone, self.milestone)
        self.assertEqual(milestone_file.filename, 'CHANGELOG_Test_Milestone_20241025.md')
        self.assertEqual(milestone_file.file_size, 1024)
        self.assertEqual(milestone_file.content_type, 'text/markdown')
        self.assertEqual(milestone_file.uploaded_by, self.user)
        self.assertFalse(milestone_file.weaviate_synced)
    
    def test_milestone_file_relationship(self):
        """Test relationship between Milestone and MilestoneFile"""
        # Create multiple files
        file1 = MilestoneFile.objects.create(
            milestone=self.milestone,
            filename='changelog1.md',
            file_size=100,
            content_type='text/markdown',
            uploaded_by=self.user
        )
        
        file2 = MilestoneFile.objects.create(
            milestone=self.milestone,
            filename='changelog2.md',
            file_size=200,
            content_type='text/markdown',
            uploaded_by=self.user
        )
        
        # Test reverse relationship
        files = self.milestone.files.all()
        self.assertEqual(files.count(), 2)
        self.assertIn(file1, files)
        self.assertIn(file2, files)
    
    def test_milestone_file_cascade_delete(self):
        """Test that MilestoneFile is deleted when Milestone is deleted"""
        milestone_file = MilestoneFile.objects.create(
            milestone=self.milestone,
            filename='changelog.md',
            file_size=512,
            content_type='text/markdown',
            uploaded_by=self.user
        )
        
        file_id = milestone_file.id
        
        # Delete milestone
        self.milestone.delete()
        
        # Check that file is also deleted
        with self.assertRaises(MilestoneFile.DoesNotExist):
            MilestoneFile.objects.get(id=file_id)
    
    def test_milestone_file_string_representation(self):
        """Test the string representation of MilestoneFile"""
        milestone_file = MilestoneFile.objects.create(
            milestone=self.milestone,
            filename='test_changelog.md',
            file_size=256,
            content_type='text/markdown',
            uploaded_by=self.user
        )
        
        expected_str = f"test_changelog.md ({self.milestone.name})"
        self.assertEqual(str(milestone_file), expected_str)
    
    def test_milestone_with_completed_tasks(self):
        """Test milestone with completed tasks for changelog generation"""
        # Create some tasks
        task1 = Task.objects.create(
            title='Task 1',
            description='Description 1',
            status='done',
            item=self.item,
            milestone=self.milestone,
            created_by=self.user,
            completed_at=timezone.now()
        )
        
        task2 = Task.objects.create(
            title='Task 2',
            description='Description 2',
            status='done',
            item=self.item,
            milestone=self.milestone,
            created_by=self.user,
            completed_at=timezone.now()
        )
        
        task3 = Task.objects.create(
            title='Task 3',
            description='Description 3',
            status='working',
            item=self.item,
            milestone=self.milestone,
            created_by=self.user
        )
        
        # Get completed tasks
        completed_tasks = self.milestone.tasks.filter(status='done')
        self.assertEqual(completed_tasks.count(), 2)
        
        # Verify tasks
        self.assertIn(task1, completed_tasks)
        self.assertIn(task2, completed_tasks)
        self.assertNotIn(task3, completed_tasks)


class MilestoneChangeLogViewTest(TestCase):
    """Test the Milestone changelog in views"""
    
    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = User.objects.create(
            username='viewtestuser',
            email='viewtest@example.com',
            role='admin'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create a test section
        self.section = Section.objects.create(
            name='View Test Section'
        )
        
        # Create a test item
        self.item = Item.objects.create(
            title='View Test Item',
            description='View test description',
            section=self.section,
            created_by=self.user,
            status='new'
        )
        
        # Create a test milestone
        self.milestone = Milestone.objects.create(
            name='View Test Milestone',
            description='View test milestone description',
            due_date=date.today() + timedelta(days=30),
            status='planned',
            item=self.item,
            changelog='# Test ChangeLog\n\nThis is a test changelog.'
        )
    
    def test_milestone_edit_with_changelog(self):
        """Test that milestone changelog field can be updated"""
        # Update milestone with new changelog
        self.milestone.name = 'Updated Milestone'
        self.milestone.description = 'Updated description'
        self.milestone.changelog = '# Updated ChangeLog\n\nUpdated content.'
        self.milestone.save()
        
        # Verify changelog was updated
        milestone_from_db = Milestone.objects.get(id=self.milestone.id)
        self.assertIn('Updated ChangeLog', milestone_from_db.changelog)
        self.assertEqual(milestone_from_db.name, 'Updated Milestone')
