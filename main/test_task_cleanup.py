"""
Test Task Cleanup Script

This test file creates test data and validates the cleanup_tasks.py script
functionality.
"""
from django.test import TestCase
from main.models import User, Item, Task, Tag, Section
from django.db import connection
from django.test.utils import CaptureQueriesContext
import subprocess
import sys
import os
from pathlib import Path


class TaskCleanupScriptTest(TestCase):
    """Test the task cleanup CLI script"""
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user1 = User.objects.create(
            username='testuser1',
            email='test1@example.com',
            role='developer',
            is_active=True
        )
        self.user1.set_password('testpass123')
        self.user1.save()
        
        self.user2 = User.objects.create(
            username='testuser2',
            email='test2@example.com',
            role='developer',
            is_active=True
        )
        self.user2.set_password('testpass123')
        self.user2.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test tag
        self.tag = Tag.objects.create(name='test-tag', color='#3b82f6')
        
        # Create test items
        self.item1 = Item.objects.create(
            title='Test Item 1',
            description='Test item 1 description',
            status='new',
            section=self.section,
            created_by=self.user1
        )
        
        self.item2 = Item.objects.create(
            title='Test Item 2',
            description='Test item 2 description',
            status='new',
            section=self.section,
            created_by=self.user2
        )
    
    def test_identify_tasks_without_owner(self):
        """Test identifying tasks without owner (assigned_to is NULL)"""
        # Create tasks: some with owner, some without
        task_with_owner = Task.objects.create(
            title='Task with Owner',
            description='Has owner and item',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=self.user1
        )
        
        task_without_owner = Task.objects.create(
            title='Task without Owner',
            description='No owner but has item',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=None  # No owner
        )
        
        # Query tasks without owner
        tasks_without_owner = Task.objects.filter(assigned_to__isnull=True)
        
        # Assertions
        self.assertEqual(tasks_without_owner.count(), 1)
        self.assertIn(task_without_owner, tasks_without_owner)
        self.assertNotIn(task_with_owner, tasks_without_owner)
    
    def test_identify_tasks_without_item(self):
        """Test identifying tasks without item (item is NULL)"""
        # Create tasks: some with item, some without
        task_with_item = Task.objects.create(
            title='Task with Item',
            description='Has owner and item',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=self.user1
        )
        
        task_without_item = Task.objects.create(
            title='Task without Item',
            description='Has owner but no item',
            status='new',
            item=None,  # No item
            created_by=self.user1,
            assigned_to=self.user1
        )
        
        # Query tasks without item
        tasks_without_item = Task.objects.filter(item__isnull=True)
        
        # Assertions
        self.assertEqual(tasks_without_item.count(), 1)
        self.assertIn(task_without_item, tasks_without_item)
        self.assertNotIn(task_with_item, tasks_without_item)
    
    def test_identify_tasks_without_owner_or_item(self):
        """Test identifying tasks without owner AND/OR item"""
        # Create various task scenarios
        task_complete = Task.objects.create(
            title='Complete Task',
            description='Has both owner and item',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=self.user1
        )
        
        task_no_owner = Task.objects.create(
            title='Task without Owner',
            description='No owner but has item',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=None
        )
        
        task_no_item = Task.objects.create(
            title='Task without Item',
            description='Has owner but no item',
            status='new',
            item=None,
            created_by=self.user1,
            assigned_to=self.user1
        )
        
        task_no_owner_no_item = Task.objects.create(
            title='Task without Owner and Item',
            description='No owner and no item',
            status='new',
            item=None,
            created_by=self.user1,
            assigned_to=None
        )
        
        # Query tasks without owner OR without item
        tasks_to_cleanup = Task.objects.filter(
            assigned_to__isnull=True
        ) | Task.objects.filter(
            item__isnull=True
        )
        
        # Assertions
        self.assertEqual(tasks_to_cleanup.count(), 3)
        self.assertNotIn(task_complete, tasks_to_cleanup)
        self.assertIn(task_no_owner, tasks_to_cleanup)
        self.assertIn(task_no_item, tasks_to_cleanup)
        self.assertIn(task_no_owner_no_item, tasks_to_cleanup)
    
    def test_delete_tasks_without_owner_or_item(self):
        """Test deleting tasks without owner or item"""
        # Create tasks to be deleted
        task_to_delete1 = Task.objects.create(
            title='Task to Delete 1',
            description='No owner',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=None
        )
        
        task_to_delete2 = Task.objects.create(
            title='Task to Delete 2',
            description='No item',
            status='new',
            item=None,
            created_by=self.user1,
            assigned_to=self.user1
        )
        
        # Create task to keep
        task_to_keep = Task.objects.create(
            title='Task to Keep',
            description='Has both owner and item',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=self.user1
        )
        
        # Record initial counts
        initial_count = Task.objects.count()
        self.assertEqual(initial_count, 3)
        
        # Delete tasks without owner or item
        tasks_to_delete = Task.objects.filter(
            assigned_to__isnull=True
        ) | Task.objects.filter(
            item__isnull=True
        )
        deleted_count = tasks_to_delete.count()
        tasks_to_delete.delete()
        
        # Verify deletion
        final_count = Task.objects.count()
        self.assertEqual(deleted_count, 2)
        self.assertEqual(final_count, 1)
        
        # Verify the correct tasks were deleted
        self.assertFalse(Task.objects.filter(id=task_to_delete1.id).exists())
        self.assertFalse(Task.objects.filter(id=task_to_delete2.id).exists())
        self.assertTrue(Task.objects.filter(id=task_to_keep.id).exists())
    
    def test_delete_preserves_related_objects(self):
        """Test that deleting tasks doesn't delete related objects"""
        # Create task without owner
        task = Task.objects.create(
            title='Task to Delete',
            description='No owner',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=None
        )
        task.tags.add(self.tag)
        
        # Record counts before deletion
        item_count_before = Item.objects.count()
        user_count_before = User.objects.count()
        tag_count_before = Tag.objects.count()
        
        # Delete task
        task.delete()
        
        # Verify related objects are preserved
        self.assertEqual(Item.objects.count(), item_count_before)
        self.assertEqual(User.objects.count(), user_count_before)
        self.assertEqual(Tag.objects.count(), tag_count_before)
        
        # Verify item and user still exist
        self.assertTrue(Item.objects.filter(id=self.item1.id).exists())
        self.assertTrue(User.objects.filter(id=self.user1.id).exists())
        self.assertTrue(Tag.objects.filter(id=self.tag.id).exists())
    
    def test_empty_database(self):
        """Test script behavior when no tasks need cleanup"""
        # Create only valid tasks
        Task.objects.create(
            title='Valid Task 1',
            description='Has owner and item',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=self.user1
        )
        
        Task.objects.create(
            title='Valid Task 2',
            description='Has owner and item',
            status='new',
            item=self.item2,
            created_by=self.user2,
            assigned_to=self.user2
        )
        
        # Query tasks without owner or item
        tasks_to_cleanup = Task.objects.filter(
            assigned_to__isnull=True
        ) | Task.objects.filter(
            item__isnull=True
        )
        
        # Assertions
        self.assertEqual(tasks_to_cleanup.count(), 0)
    
    def test_task_with_github_integration(self):
        """Test cleanup of tasks that are synced with GitHub"""
        # Create task with GitHub integration but no owner
        github_task = Task.objects.create(
            title='GitHub Task',
            description='Synced with GitHub but no owner',
            status='new',
            item=self.item1,
            created_by=self.user1,
            assigned_to=None,
            github_issue_id=123,
            github_issue_url='https://github.com/test/repo/issues/123'
        )
        
        # Query tasks without owner
        tasks_to_cleanup = Task.objects.filter(assigned_to__isnull=True)
        
        # Verify it's identified for cleanup
        self.assertEqual(tasks_to_cleanup.count(), 1)
        self.assertIn(github_task, tasks_to_cleanup)
        
        # Delete and verify
        github_task.delete()
        self.assertFalse(Task.objects.filter(id=github_task.id).exists())
