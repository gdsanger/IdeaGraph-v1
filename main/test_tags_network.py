"""
Tests for Tags Network Graph functionality
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Tag, Item, Task, Section


class TagsNetworkAPITestCase(TestCase):
    """Test cases for the Tags Network Graph API"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create a second test user for filtering tests
        self.user2 = User.objects.create(
            username='testuser2',
            email='test2@example.com',
            role='user'
        )
        self.user2.set_password('testpass123')
        self.user2.save()
        
        # Log in
        self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Create test tags
        self.tag1 = Tag.objects.create(name='Python', color='#3b82f6')
        self.tag2 = Tag.objects.create(name='Django', color='#10b981')
        self.tag3 = Tag.objects.create(name='Unused Tag', color='#ef4444')
        
        # Create test section
        self.section = Section.objects.create(name='Software')
        
        # Create test item for user 1
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        self.item.tags.add(self.tag1, self.tag2)
        
        # Create test task for user 1
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            created_by=self.user
        )
        self.task.tags.add(self.tag1)
        
        # Create test item for user 2 (should not be visible to user 1)
        self.item2 = Item.objects.create(
            title='User 2 Item',
            description='User 2 description',
            status='new',
            section=self.section,
            created_by=self.user2
        )
        self.item2.tags.add(self.tag2)
        
        # Create test task for user 2 (should not be visible to user 1)
        self.task2 = Task.objects.create(
            title='User 2 Task',
            description='User 2 task description',
            status='new',
            item=self.item2,
            created_by=self.user2
        )
        self.task2.tags.add(self.tag2)
    
    def test_tags_network_view_loads(self):
        """Test that the Tags network view loads successfully"""
        response = self.client.get(reverse('main:tags_network'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tags Network Graph')
    
    def test_api_tags_network_data(self):
        """Test that the API endpoint returns correct data structure"""
        response = self.client.get(reverse('main:api_tags_network_data'))
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('nodes', data)
        self.assertIn('edges', data)
        
        # Check that nodes are present
        nodes = data['nodes']
        self.assertGreater(len(nodes), 0)
        
        # Check that edges are present
        edges = data['edges']
        self.assertGreater(len(edges), 0)
    
    def test_api_returns_tag_nodes(self):
        """Test that the API returns tag nodes only for linked tags"""
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        nodes = data['nodes']
        tag_nodes = [n for n in nodes if n['group'] == 'tag']
        
        # Should only show tags that are linked to items/tasks owned by current user
        # tag1 and tag2 are linked to user's item/task, tag3 is not used
        self.assertEqual(len(tag_nodes), 2)
        
        # Check that tag3 (unused) is not present
        tag_node_labels = [n['title'] for n in tag_nodes]
        self.assertIn('Python', tag_node_labels)
        self.assertIn('Django', tag_node_labels)
        self.assertNotIn('Unused Tag', tag_node_labels)
        
        # Check tag node structure
        tag_node = tag_nodes[0]
        self.assertIn('id', tag_node)
        self.assertIn('label', tag_node)
        self.assertIn('color', tag_node)
        self.assertEqual(tag_node['shape'], 'dot')
    
    def test_api_returns_item_nodes(self):
        """Test that the API returns item nodes"""
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        nodes = data['nodes']
        item_nodes = [n for n in nodes if n['group'] == 'item']
        self.assertEqual(len(item_nodes), 1)
        
        # Check item node structure
        item_node = item_nodes[0]
        self.assertIn('id', item_node)
        self.assertIn('label', item_node)
        self.assertIn('color', item_node)
        self.assertIn('url', item_node)
        self.assertEqual(item_node['shape'], 'box')
    
    def test_api_returns_task_nodes(self):
        """Test that the API returns task nodes"""
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        nodes = data['nodes']
        task_nodes = [n for n in nodes if n['group'] == 'task']
        self.assertEqual(len(task_nodes), 1)
        
        # Check task node structure
        task_node = task_nodes[0]
        self.assertIn('id', task_node)
        self.assertIn('label', task_node)
        self.assertIn('color', task_node)
        self.assertIn('url', task_node)
        self.assertEqual(task_node['shape'], 'diamond')
    
    def test_api_returns_edges(self):
        """Test that the API returns edges connecting nodes"""
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        edges = data['edges']
        self.assertGreater(len(edges), 0)
        
        # Check edge structure
        edge = edges[0]
        self.assertIn('from', edge)
        self.assertIn('to', edge)
        self.assertIn('color', edge)
        self.assertIn('width', edge)
    
    def test_long_labels_are_truncated(self):
        """Test that long labels are truncated with ellipsis"""
        # Create an item with a long title
        long_item = Item.objects.create(
            title='This is a very long title that should be truncated in the graph',
            description='Test',
            status='new',
            created_by=self.user
        )
        
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        nodes = data['nodes']
        long_item_nodes = [n for n in nodes if 'very long title' in n.get('title', '')]
        self.assertEqual(len(long_item_nodes), 1)
        
        # Check that label is truncated
        node = long_item_nodes[0]
        self.assertLess(len(node['label']), len(long_item.title))
        self.assertIn('...', node['label'])
    
    def test_filters_items_by_owner(self):
        """Test that only items owned by current user are returned"""
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        nodes = data['nodes']
        item_nodes = [n for n in nodes if n['group'] == 'item']
        
        # Should only have 1 item (user's item, not user2's item)
        self.assertEqual(len(item_nodes), 1)
        
        # Verify it's the correct item
        item_node = item_nodes[0]
        self.assertEqual(item_node['id'], f'item-{self.item.id}')
        self.assertIn('Test Item', item_node['title'])
    
    def test_filters_tasks_by_owner(self):
        """Test that only tasks owned by current user are returned"""
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        nodes = data['nodes']
        task_nodes = [n for n in nodes if n['group'] == 'task']
        
        # Should only have 1 task (user's task, not user2's task)
        self.assertEqual(len(task_nodes), 1)
        
        # Verify it's the correct task
        task_node = task_nodes[0]
        self.assertEqual(task_node['id'], f'task-{self.task.id}')
        self.assertIn('Test Task', task_node['title'])
    
    def test_unused_tags_not_shown(self):
        """Test that tags not linked to any items or tasks are not shown"""
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        nodes = data['nodes']
        tag_nodes = [n for n in nodes if n['group'] == 'tag']
        
        # Should not include tag3 (Unused Tag)
        tag_ids = [n['id'] for n in tag_nodes]
        self.assertNotIn(f'tag-{self.tag3.id}', tag_ids)
    
    def test_different_user_sees_different_data(self):
        """Test that a different user sees only their own items and tasks"""
        # Log out and log in as user2
        self.client.post(reverse('main:logout'))
        self.client.post(reverse('main:login'), {
            'username': 'testuser2',
            'password': 'testpass123'
        })
        
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        nodes = data['nodes']
        item_nodes = [n for n in nodes if n['group'] == 'item']
        task_nodes = [n for n in nodes if n['group'] == 'task']
        
        # User2 should only see their own item and task
        self.assertEqual(len(item_nodes), 1)
        self.assertEqual(len(task_nodes), 1)
        
        # Verify it's user2's data
        self.assertEqual(item_nodes[0]['id'], f'item-{self.item2.id}')
        self.assertEqual(task_nodes[0]['id'], f'task-{self.task2.id}')
