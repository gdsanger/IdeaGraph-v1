"""
Tests for Hierarchical Item Relationships

This module tests the hierarchical parent-child functionality for Items.
"""
from django.test import TestCase
from main.models import User, Item, Section, Tag


class HierarchicalItemTest(TestCase):
    """Test cases for hierarchical item relationships"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create a section
        self.section = Section.objects.create(name='Test Section')
        
        # Create some tags
        self.tag1 = Tag.objects.create(name='Parent Tag', color='#3b82f6')
        self.tag2 = Tag.objects.create(name='Child Tag', color='#f59e0b')
    
    def test_parent_field_exists(self):
        """Test that parent field exists on Item model"""
        parent_item = Item.objects.create(
            title='Parent Item',
            description='This is a parent item',
            created_by=self.user
        )
        
        child_item = Item.objects.create(
            title='Child Item',
            description='This is a child item',
            parent=parent_item,
            created_by=self.user
        )
        
        self.assertEqual(child_item.parent, parent_item)
        self.assertIn(child_item, parent_item.children.all())
    
    def test_is_template_field(self):
        """Test that is_template field works correctly"""
        template_item = Item.objects.create(
            title='Template Item',
            description='This is a template',
            is_template=True,
            created_by=self.user
        )
        
        self.assertTrue(template_item.is_template)
    
    def test_inherit_context_field(self):
        """Test that inherit_context field works correctly"""
        parent_item = Item.objects.create(
            title='Parent Item',
            description='Parent description',
            created_by=self.user
        )
        
        child_item = Item.objects.create(
            title='Child Item',
            description='Child description',
            parent=parent_item,
            inherit_context=True,
            created_by=self.user
        )
        
        self.assertTrue(child_item.inherit_context)
    
    def test_get_all_children(self):
        """Test get_all_children method"""
        parent = Item.objects.create(
            title='Parent',
            created_by=self.user
        )
        
        child1 = Item.objects.create(
            title='Child 1',
            parent=parent,
            created_by=self.user
        )
        
        child2 = Item.objects.create(
            title='Child 2',
            parent=parent,
            created_by=self.user
        )
        
        grandchild = Item.objects.create(
            title='Grandchild',
            parent=child1,
            created_by=self.user
        )
        
        all_children = parent.get_all_children()
        
        # Should include both direct children and grandchildren
        self.assertEqual(len(all_children), 3)
        self.assertIn(child1, all_children)
        self.assertIn(child2, all_children)
        self.assertIn(grandchild, all_children)
    
    def test_get_all_parents(self):
        """Test get_all_parents method"""
        grandparent = Item.objects.create(
            title='Grandparent',
            created_by=self.user
        )
        
        parent = Item.objects.create(
            title='Parent',
            parent=grandparent,
            created_by=self.user
        )
        
        child = Item.objects.create(
            title='Child',
            parent=parent,
            created_by=self.user
        )
        
        all_parents = child.get_all_parents()
        
        # Should include both parent and grandparent
        self.assertEqual(len(all_parents), 2)
        self.assertEqual(all_parents[0], parent)
        self.assertEqual(all_parents[1], grandparent)
    
    def test_get_inherited_context_without_parent(self):
        """Test get_inherited_context when there's no parent"""
        item = Item.objects.create(
            title='Standalone Item',
            description='Test description',
            created_by=self.user
        )
        item.tags.add(self.tag1)
        
        context = item.get_inherited_context()
        
        self.assertEqual(context['description'], 'Test description')
        self.assertFalse(context['has_parent'])
        self.assertEqual(len(context['tags']), 1)
        self.assertIn(self.tag1, context['tags'])
    
    def test_get_inherited_context_with_parent_no_inheritance(self):
        """Test get_inherited_context when inheritance is disabled"""
        parent = Item.objects.create(
            title='Parent',
            description='Parent description',
            created_by=self.user
        )
        parent.tags.add(self.tag1)
        
        child = Item.objects.create(
            title='Child',
            description='Child description',
            parent=parent,
            inherit_context=False,  # Inheritance disabled
            created_by=self.user
        )
        child.tags.add(self.tag2)
        
        context = child.get_inherited_context()
        
        # Should only get child's own context
        self.assertEqual(context['description'], 'Child description')
        self.assertFalse(context['has_parent'])
        self.assertEqual(len(context['tags']), 1)
        self.assertIn(self.tag2, context['tags'])
    
    def test_get_inherited_context_with_inheritance_enabled(self):
        """Test get_inherited_context when inheritance is enabled"""
        parent = Item.objects.create(
            title='Parent',
            description='Parent description',
            created_by=self.user
        )
        parent.tags.add(self.tag1)
        
        child = Item.objects.create(
            title='Child',
            description='Child description',
            parent=parent,
            inherit_context=True,  # Inheritance enabled
            created_by=self.user
        )
        child.tags.add(self.tag2)
        
        context = child.get_inherited_context()
        
        # Should combine parent and child context
        self.assertIn('Parent description', context['description'])
        self.assertIn('Child description', context['description'])
        self.assertTrue(context['has_parent'])
        self.assertEqual(context['parent_id'], str(parent.id))
        self.assertEqual(context['parent_title'], 'Parent')
        
        # Should have both tags (deduplicated)
        self.assertEqual(len(context['tags']), 2)
        tag_list = list(context['tags'])
        self.assertIn(self.tag1, tag_list)
        self.assertIn(self.tag2, tag_list)
    
    def test_inherited_context_with_empty_descriptions(self):
        """Test inherited context when descriptions are empty"""
        parent = Item.objects.create(
            title='Parent',
            description='',
            created_by=self.user
        )
        
        child = Item.objects.create(
            title='Child',
            description='',
            parent=parent,
            inherit_context=True,
            created_by=self.user
        )
        
        context = child.get_inherited_context()
        
        # Should return empty string, not None
        self.assertEqual(context['description'], '')
        self.assertTrue(context['has_parent'])
