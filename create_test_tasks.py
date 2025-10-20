#!/usr/bin/env python
"""
Create test data for cleanup_tasks.py script testing

This script creates various test tasks to validate the cleanup script.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ideagraph.settings')
import django
django.setup()

from main.models import User, Item, Task, Tag, Section


def create_test_data():
    """Create test data for cleanup script"""
    print("Creating test data...")
    
    # Create test users
    user1, _ = User.objects.get_or_create(
        username='testuser1',
        defaults={
            'email': 'test1@example.com',
            'role': 'developer',
            'is_active': True
        }
    )
    if _:
        user1.set_password('testpass123')
        user1.save()
        print(f"Created user: {user1.username}")
    
    user2, _ = User.objects.get_or_create(
        username='testuser2',
        defaults={
            'email': 'test2@example.com',
            'role': 'developer',
            'is_active': True
        }
    )
    if _:
        user2.set_password('testpass123')
        user2.save()
        print(f"Created user: {user2.username}")
    
    # Create test section
    section, _ = Section.objects.get_or_create(name='Test Section')
    if _:
        print(f"Created section: {section.name}")
    
    # Create test tag
    tag, _ = Tag.objects.get_or_create(
        name='test-tag',
        defaults={'color': '#3b82f6'}
    )
    if _:
        print(f"Created tag: {tag.name}")
    
    # Create test items
    item1, _ = Item.objects.get_or_create(
        title='Test Item 1',
        defaults={
            'description': 'Test item 1 description',
            'status': 'new',
            'section': section,
            'created_by': user1
        }
    )
    if _:
        print(f"Created item: {item1.title}")
    
    item2, _ = Item.objects.get_or_create(
        title='Test Item 2',
        defaults={
            'description': 'Test item 2 description',
            'status': 'new',
            'section': section,
            'created_by': user2
        }
    )
    if _:
        print(f"Created item: {item2.title}")
    
    print("\nCreating test tasks...")
    
    # Create valid task (has both owner and item) - should NOT be deleted
    task1, created = Task.objects.get_or_create(
        title='Valid Task - Has Owner and Item',
        defaults={
            'description': 'This task has both owner and item',
            'status': 'new',
            'item': item1,
            'created_by': user1,
            'assigned_to': user1
        }
    )
    if created:
        task1.tags.add(tag)
        print(f"✅ Created valid task: {task1.title}")
    
    # Create task without owner - SHOULD be deleted
    task2, created = Task.objects.get_or_create(
        title='Invalid Task - No Owner',
        defaults={
            'description': 'This task has no owner (assigned_to)',
            'status': 'new',
            'item': item1,
            'created_by': user1,
            'assigned_to': None
        }
    )
    if created:
        print(f"❌ Created invalid task (no owner): {task2.title}")
    
    # Create task without item - SHOULD be deleted
    task3, created = Task.objects.get_or_create(
        title='Invalid Task - No Item',
        defaults={
            'description': 'This task has no item',
            'status': 'new',
            'item': None,
            'created_by': user1,
            'assigned_to': user1
        }
    )
    if created:
        print(f"❌ Created invalid task (no item): {task3.title}")
    
    # Create task without owner and item - SHOULD be deleted
    task4, created = Task.objects.get_or_create(
        title='Invalid Task - No Owner and No Item',
        defaults={
            'description': 'This task has neither owner nor item',
            'status': 'new',
            'item': None,
            'created_by': user1,
            'assigned_to': None
        }
    )
    if created:
        print(f"❌ Created invalid task (no owner, no item): {task4.title}")
    
    # Create another valid task
    task5, created = Task.objects.get_or_create(
        title='Valid Task 2 - Has Owner and Item',
        defaults={
            'description': 'Another valid task',
            'status': 'working',
            'item': item2,
            'created_by': user2,
            'assigned_to': user2
        }
    )
    if created:
        print(f"✅ Created valid task: {task5.title}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Data Summary")
    print("=" * 60)
    
    total_tasks = Task.objects.count()
    valid_tasks = Task.objects.filter(
        assigned_to__isnull=False,
        item__isnull=False
    ).count()
    
    tasks_no_owner = Task.objects.filter(assigned_to__isnull=True).count()
    tasks_no_item = Task.objects.filter(item__isnull=True).count()
    tasks_to_cleanup = (Task.objects.filter(assigned_to__isnull=True) | 
                       Task.objects.filter(item__isnull=True)).count()
    
    print(f"Total tasks created: {total_tasks}")
    print(f"Valid tasks (has owner and item): {valid_tasks}")
    print(f"Tasks without owner: {tasks_no_owner}")
    print(f"Tasks without item: {tasks_no_item}")
    print(f"Tasks to be cleaned up: {tasks_to_cleanup}")
    print("=" * 60)
    
    print("\nTest data created successfully!")
    print("\nNext steps:")
    print("  1. Run dry-run: python cleanup_tasks.py --dry-run")
    print("  2. Run cleanup: python cleanup_tasks.py")


if __name__ == '__main__':
    create_test_data()
