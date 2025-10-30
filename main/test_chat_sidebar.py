"""
Tests for Chat Sidebar Integration
"""

from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, Section


class ChatSidebarTest(TestCase):
    """Test chat sidebar integration and visibility"""
    
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
            title='Test Item for Chat',
            description='Test Description for Chat Sidebar',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task for Chat',
            description='Test Task Description for Chat Sidebar',
            item=self.item,
            created_by=self.user
        )
        
        # Set up client and login
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_chat_sidebar_in_item_detail(self):
        """Test that chat sidebar is included in item detail view"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for chat sidebar element
        self.assertContains(response, 'id="chatSidebar"')
        self.assertContains(response, 'chat-sidebar')
        # Check for floating chat button
        self.assertContains(response, 'id="chatFloatingBtn"')
        self.assertContains(response, 'chat-floating-btn-breadcrumb')
        # Check for chat widget container
        self.assertContains(response, 'id="ideagraph-chat-widget-sidebar"')
    
    def test_chat_sidebar_in_task_detail(self):
        """Test that chat sidebar is included in task detail view"""
        url = reverse('main:task_detail', args=[self.task.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for chat sidebar element
        self.assertContains(response, 'id="chatSidebar"')
        self.assertContains(response, 'chat-sidebar')
        # Check for floating chat button
        self.assertContains(response, 'id="chatFloatingBtn"')
        self.assertContains(response, 'chat-floating-btn-breadcrumb')
        # Check for chat widget container
        self.assertContains(response, 'id="ideagraph-chat-widget-sidebar"')
    
    def test_chat_sidebar_has_correct_data_attributes_item(self):
        """Test that chat sidebar has correct data attributes for item"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check data attributes
        self.assertContains(response, f'data-object-id="{self.item.id}"')
        self.assertContains(response, 'data-object-type="item"')
    
    def test_chat_sidebar_has_correct_data_attributes_task(self):
        """Test that chat sidebar has correct data attributes for task"""
        url = reverse('main:task_detail', args=[self.task.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check data attributes
        self.assertContains(response, f'data-object-id="{self.task.id}"')
        self.assertContains(response, 'data-object-type="task"')
    
    def test_activity_sidebar_removed_from_base(self):
        """Test that activity sidebar is not present in item detail"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that activity sidebar is NOT present
        self.assertNotContains(response, 'activity-sidebar')
        self.assertNotContains(response, 'Letzte Aktivitäten')
    
    def test_chat_button_not_in_floating_dock(self):
        """Test that chat button is removed from floating action dock"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check that chat button is NOT in floating dock
        self.assertNotContains(response, 'floating-action-btn-chat')
        # But other buttons should still be there
        self.assertContains(response, 'floating-action-btn-graph')
        self.assertContains(response, 'floating-action-btn-files')
    
    def test_chat_sidebar_styling(self):
        """Test that chat sidebar includes necessary styling"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for thinking animation styles
        self.assertContains(response, 'thinking-animation')
        self.assertContains(response, 'thinkingPulse')
        # Check for source font size styles
        self.assertContains(response, '.message-sources')
        self.assertContains(response, 'font-size: 0.8rem')
    
    def test_breadcrumb_chat_button_styling(self):
        """Test that breadcrumb has chat button with correct styling"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for breadcrumb chat button styles
        self.assertContains(response, 'chat-floating-btn-breadcrumb')
        self.assertContains(response, 'onclick="toggleChatSidebar()"')
    
    def test_chat_sidebar_javascript_functions(self):
        """Test that required JavaScript functions are present"""
        url = reverse('main:item_detail', args=[self.item.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        # Check for JavaScript toggle function
        self.assertContains(response, 'function toggleChatSidebar()')
        self.assertContains(response, 'chatWidgetInstance')
