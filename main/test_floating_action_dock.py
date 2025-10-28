"""
Tests for Floating Action Dock v2 context-based visibility
"""

from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, Section, Settings


class FloatingActionDockTest(TestCase):
    """Test floating action dock context visibility"""
    
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
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test Task Description',
            item=self.item,
            created_by=self.user
        )
        
        # Create settings
        self.settings = Settings.objects.create()
        
        # Set up client and login
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Store session
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_floating_dock_in_item_detail(self):
        """Test that floating action dock appears in item detail view"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'floating-action-dock')
        self.assertContains(response, 'data-context="item"')
    
    def test_floating_dock_in_task_detail(self):
        """Test that floating action dock appears in task detail view"""
        url = reverse('main:task_detail', args=[self.task.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'floating-action-dock')
        self.assertContains(response, 'data-context="task"')
    
    def test_chat_button_in_item_view(self):
        """Test that chat button appears in item view"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'qaChatModal')
        self.assertContains(response, 'floating-action-btn-chat')
    
    def test_graph_button_in_both_views(self):
        """Test that graph button appears in both item and task views"""
        # Item view
        item_url = reverse('main:item_detail', args=[self.item.id])
        item_response = self.client.get(item_url)
        self.assertEqual(item_response.status_code, 200)
        self.assertContains(item_response, 'graphModal')
        self.assertContains(item_response, 'floating-action-btn-graph')
        
        # Task view
        task_url = reverse('main:task_detail', args=[self.task.id])
        task_response = self.client.get(task_url)
        self.assertEqual(task_response.status_code, 200)
        self.assertContains(task_response, 'graphModal')
        self.assertContains(task_response, 'floating-action-btn-graph')
    
    def test_files_button_in_both_views(self):
        """Test that files button appears in both item and task views"""
        # Item view
        item_url = reverse('main:item_detail', args=[self.item.id])
        item_response = self.client.get(item_url)
        self.assertEqual(item_response.status_code, 200)
        self.assertContains(item_response, 'filesModal')
        self.assertContains(item_response, 'floating-action-btn-files')
        
        # Task view
        task_url = reverse('main:task_detail', args=[self.task.id])
        task_response = self.client.get(task_url)
        self.assertEqual(task_response.status_code, 200)
        self.assertContains(task_response, 'filesModal')
        self.assertContains(task_response, 'floating-action-btn-files')
    
    def test_global_search_button_present(self):
        """Test that global search button appears in views"""
        # Item view
        item_url = reverse('main:item_detail', args=[self.item.id])
        item_response = self.client.get(item_url)
        self.assertEqual(item_response.status_code, 200)
        self.assertContains(item_response, 'globalSearchModal')
        self.assertContains(item_response, 'floating-action-btn-search')
        
        # Task view
        task_url = reverse('main:task_detail', args=[self.task.id])
        task_response = self.client.get(task_url)
        self.assertEqual(task_response.status_code, 200)
        self.assertContains(task_response, 'globalSearchModal')
        self.assertContains(task_response, 'floating-action-btn-search')
    
    def test_semantic_network_removed_from_task_view(self):
        """Test that embedded semantic network container is removed from task detail"""
        url = reverse('main:task_detail', args=[self.task.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Should not contain the old inline semantic network container
        self.assertNotContains(response, 'id="semanticNetworkContainer"')
        # But should contain the modal version
        self.assertContains(response, 'semanticNetworkModalContainer')
    
    def test_modals_have_lazy_loading_structure(self):
        """Test that modals have proper structure for lazy loading"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for modal IDs
        self.assertContains(response, 'id="filesModal"')
        self.assertContains(response, 'id="globalSearchModal"')
        self.assertContains(response, 'id="graphModal"')
        self.assertContains(response, 'id="qaChatModal"')
        
        # Check for content containers
        self.assertContains(response, 'id="filesModalContent"')
        self.assertContains(response, 'id="globalSearchResults"')
        self.assertContains(response, 'id="semanticNetworkModalContainer"')
