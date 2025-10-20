"""
Tests for the unused tag cleanup CLI script
"""
import io
import sys
from unittest.mock import patch, MagicMock
from django.test import TestCase
from main.models import Tag, Item, Task, Section, User
from cleanup_unused_tags import (
    identify_unused_tags,
    verify_tag_usage,
    delete_tags,
)


class UnusedTagCleanupTest(TestCase):
    """Test unused tag cleanup functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        
        # Create a test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create a test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user
        )
        
        # Create a test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            created_by=self.user
        )
    
    def test_identify_unused_tags_empty(self):
        """Test identifying unused tags when there are none"""
        # Create some used tags
        tag1 = Tag.objects.create(name='Used Tag 1', usage_count=1)
        tag2 = Tag.objects.create(name='Used Tag 2', usage_count=5)
        
        unused_tags = identify_unused_tags()
        
        self.assertEqual(unused_tags.count(), 0)
    
    def test_identify_unused_tags_with_unused(self):
        """Test identifying unused tags when they exist"""
        # Create unused tags
        unused_tag1 = Tag.objects.create(name='Unused Tag 1', usage_count=0)
        unused_tag2 = Tag.objects.create(name='Unused Tag 2', usage_count=0)
        
        # Create used tags
        used_tag = Tag.objects.create(name='Used Tag', usage_count=3)
        
        unused_tags = identify_unused_tags()
        
        self.assertEqual(unused_tags.count(), 2)
        self.assertIn(unused_tag1, unused_tags)
        self.assertIn(unused_tag2, unused_tags)
        self.assertNotIn(used_tag, unused_tags)
    
    def test_verify_tag_usage_truly_unused(self):
        """Test verifying a tag that is truly unused"""
        unused_tag = Tag.objects.create(name='Unused Tag', usage_count=0)
        
        result = verify_tag_usage(unused_tag)
        
        self.assertTrue(result)
    
    def test_verify_tag_usage_actually_used_by_item(self):
        """Test verifying a tag that claims to be unused but is used by an item"""
        # Create a tag with incorrect usage_count
        tag = Tag.objects.create(name='Test Tag', usage_count=0)
        
        # Assign tag to item
        self.item.tags.add(tag)
        
        result = verify_tag_usage(tag)
        
        self.assertFalse(result)
    
    def test_verify_tag_usage_actually_used_by_task(self):
        """Test verifying a tag that claims to be unused but is used by a task"""
        # Create a tag with incorrect usage_count
        tag = Tag.objects.create(name='Test Tag', usage_count=0)
        
        # Assign tag to task
        self.task.tags.add(tag)
        
        result = verify_tag_usage(tag)
        
        self.assertFalse(result)
    
    def test_verify_tag_usage_used_by_both(self):
        """Test verifying a tag that is used by both items and tasks"""
        # Create a tag with incorrect usage_count
        tag = Tag.objects.create(name='Test Tag', usage_count=0)
        
        # Assign tag to both item and task
        self.item.tags.add(tag)
        self.task.tags.add(tag)
        
        result = verify_tag_usage(tag)
        
        self.assertFalse(result)
    
    def test_delete_tags_dry_run(self):
        """Test deleting tags in dry-run mode"""
        # Create unused tags
        unused_tag1 = Tag.objects.create(name='Unused Tag 1', usage_count=0)
        unused_tag2 = Tag.objects.create(name='Unused Tag 2', usage_count=0)
        
        unused_tags = Tag.objects.filter(usage_count=0)
        initial_count = Tag.objects.count()
        
        deleted_count, skipped_count, errors = delete_tags(
            unused_tags, dry_run=True
        )
        
        # Verify nothing was deleted in dry-run
        self.assertEqual(deleted_count, 2)
        self.assertEqual(skipped_count, 0)
        self.assertEqual(len(errors), 0)
        self.assertEqual(Tag.objects.count(), initial_count)
    
    def test_delete_tags_actually_deletes(self):
        """Test that tags are actually deleted when not in dry-run mode"""
        # Create unused tags
        unused_tag1 = Tag.objects.create(name='Unused Tag 1', usage_count=0)
        unused_tag2 = Tag.objects.create(name='Unused Tag 2', usage_count=0)
        
        # Create a used tag that should not be deleted
        used_tag = Tag.objects.create(name='Used Tag', usage_count=5)
        
        unused_tags = Tag.objects.filter(usage_count=0)
        initial_count = Tag.objects.count()
        
        deleted_count, skipped_count, errors = delete_tags(
            unused_tags, dry_run=False
        )
        
        # Verify tags were deleted
        self.assertEqual(deleted_count, 2)
        self.assertEqual(skipped_count, 0)
        self.assertEqual(len(errors), 0)
        self.assertEqual(Tag.objects.count(), 1)
        
        # Verify the used tag still exists
        self.assertTrue(Tag.objects.filter(id=used_tag.id).exists())
        
        # Verify unused tags were deleted
        self.assertFalse(Tag.objects.filter(id=unused_tag1.id).exists())
        self.assertFalse(Tag.objects.filter(id=unused_tag2.id).exists())
    
    def test_delete_tags_skips_actually_used(self):
        """Test that tags with incorrect usage_count are skipped"""
        # Create a tag with incorrect usage_count
        tag = Tag.objects.create(name='Test Tag', usage_count=0)
        
        # Assign tag to item (making usage_count incorrect)
        self.item.tags.add(tag)
        
        unused_tags = Tag.objects.filter(usage_count=0)
        
        deleted_count, skipped_count, errors = delete_tags(
            unused_tags, dry_run=False
        )
        
        # Verify tag was skipped, not deleted
        self.assertEqual(deleted_count, 0)
        self.assertEqual(skipped_count, 1)
        self.assertEqual(len(errors), 0)
        
        # Verify tag still exists
        self.assertTrue(Tag.objects.filter(id=tag.id).exists())
    
    def test_delete_tags_mixed_scenario(self):
        """Test deleting with a mix of truly unused and falsely unused tags"""
        # Create truly unused tags
        truly_unused1 = Tag.objects.create(name='Truly Unused 1', usage_count=0)
        truly_unused2 = Tag.objects.create(name='Truly Unused 2', usage_count=0)
        
        # Create falsely unused tag (usage_count is wrong)
        falsely_unused = Tag.objects.create(name='Falsely Unused', usage_count=0)
        self.item.tags.add(falsely_unused)
        
        # Create a properly used tag
        properly_used = Tag.objects.create(name='Properly Used', usage_count=1)
        
        unused_tags = Tag.objects.filter(usage_count=0)
        
        deleted_count, skipped_count, errors = delete_tags(
            unused_tags, dry_run=False
        )
        
        # Verify results
        self.assertEqual(deleted_count, 2)  # Only truly unused tags
        self.assertEqual(skipped_count, 1)  # Falsely unused tag skipped
        self.assertEqual(len(errors), 0)
        
        # Verify correct tags remain
        self.assertFalse(Tag.objects.filter(id=truly_unused1.id).exists())
        self.assertFalse(Tag.objects.filter(id=truly_unused2.id).exists())
        self.assertTrue(Tag.objects.filter(id=falsely_unused.id).exists())
        self.assertTrue(Tag.objects.filter(id=properly_used.id).exists())
    
    def test_delete_tags_empty_queryset(self):
        """Test deleting when there are no unused tags"""
        unused_tags = Tag.objects.filter(usage_count=0)
        
        deleted_count, skipped_count, errors = delete_tags(
            unused_tags, dry_run=False
        )
        
        self.assertEqual(deleted_count, 0)
        self.assertEqual(skipped_count, 0)
        self.assertEqual(len(errors), 0)


class TagUsageCountIntegrityTest(TestCase):
    """Test tag usage_count field integrity"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        self.section = Section.objects.create(name='Test Section')
    
    def test_new_tag_has_zero_usage_count(self):
        """Test that newly created tags have usage_count of 0"""
        tag = Tag.objects.create(name='New Tag')
        
        self.assertEqual(tag.usage_count, 0)
    
    def test_calculate_usage_count_no_usage(self):
        """Test calculate_usage_count with no usage"""
        tag = Tag.objects.create(name='Test Tag')
        
        count = tag.calculate_usage_count()
        
        self.assertEqual(count, 0)
        self.assertEqual(tag.usage_count, 0)
    
    def test_calculate_usage_count_with_items(self):
        """Test calculate_usage_count with items"""
        tag = Tag.objects.create(name='Test Tag')
        
        # Create items with this tag
        item1 = Item.objects.create(
            title='Item 1',
            section=self.section,
            created_by=self.user
        )
        item1.tags.add(tag)
        
        item2 = Item.objects.create(
            title='Item 2',
            section=self.section,
            created_by=self.user
        )
        item2.tags.add(tag)
        
        count = tag.calculate_usage_count()
        
        self.assertEqual(count, 2)
        self.assertEqual(tag.usage_count, 2)
    
    def test_calculate_usage_count_with_tasks(self):
        """Test calculate_usage_count with tasks"""
        tag = Tag.objects.create(name='Test Tag')
        
        # Create tasks with this tag
        task1 = Task.objects.create(
            title='Task 1',
            created_by=self.user
        )
        task1.tags.add(tag)
        
        task2 = Task.objects.create(
            title='Task 2',
            created_by=self.user
        )
        task2.tags.add(tag)
        
        count = tag.calculate_usage_count()
        
        self.assertEqual(count, 2)
        self.assertEqual(tag.usage_count, 2)
    
    def test_calculate_usage_count_with_both(self):
        """Test calculate_usage_count with both items and tasks"""
        tag = Tag.objects.create(name='Test Tag')
        
        # Create item with this tag
        item = Item.objects.create(
            title='Item',
            section=self.section,
            created_by=self.user
        )
        item.tags.add(tag)
        
        # Create task with this tag
        task = Task.objects.create(
            title='Task',
            created_by=self.user
        )
        task.tags.add(tag)
        
        count = tag.calculate_usage_count()
        
        self.assertEqual(count, 2)
        self.assertEqual(tag.usage_count, 2)
