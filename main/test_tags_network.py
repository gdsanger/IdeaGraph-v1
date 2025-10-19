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
        
        # Log in
        self.client.post(reverse('main:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Create test tags
        self.tag1 = Tag.objects.create(name='Python', color='#3b82f6')
        self.tag2 = Tag.objects.create(name='Django', color='#10b981')
        
        # Create test section
        self.section = Section.objects.create(name='Software')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        self.item.tags.add(self.tag1, self.tag2)
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            created_by=self.user
        )
        self.task.tags.add(self.tag1)
    
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
        """Test that the API returns tag nodes"""
        response = self.client.get(reverse('main:api_tags_network_data'))
        data = json.loads(response.content)
        
        nodes = data['nodes']
        tag_nodes = [n for n in nodes if n['group'] == 'tag']
        self.assertEqual(len(tag_nodes), 2)
        
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
