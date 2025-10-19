"""
Tests for Item views
"""
from django.test import TestCase, Client
from main.models import User, Item, Section, Tag


class ItemViewsTest(TestCase):
    """Test Item views"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create admin user
        self.admin = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        self.admin.set_password('Admin@123')
        self.admin.save()
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create tag
        self.tag = Tag.objects.create(name='Test Tag', color='#3b82f6')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        self.item.tags.add(self.tag)
        
        self.client = Client()
    
    def login_user(self, user):
        """Helper to log in a user"""
        self.client.post('/login/', {
            'username': user.username,
            'password': 'Test@123' if user == self.user else 'Admin@123'
        })
    
    def test_item_list_requires_login(self):
        """Test that item list requires login"""
        response = self.client.get('/items/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_item_list_view(self):
        """Test item list view"""
        self.login_user(self.user)
        response = self.client.get('/items/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Items - List View')
        self.assertContains(response, 'Test Item')
    
    def test_item_kanban_view(self):
        """Test item kanban view"""
        self.login_user(self.user)
        response = self.client.get('/items/kanban/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Items - Kanban View')
        self.assertContains(response, 'Test Item')
    
    def test_item_detail_view(self):
        """Test item detail view"""
        self.login_user(self.user)
        response = self.client.get(f'/items/{self.item.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Item')
        self.assertContains(response, 'Item Details')
    
    def test_item_create_view_get(self):
        """Test item create view GET"""
        self.login_user(self.user)
        response = self.client.get('/items/create/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Item')
    
    def test_item_create_view_post(self):
        """Test item create view POST"""
        self.login_user(self.user)
        response = self.client.post('/items/create/', {
            'title': 'New Test Item',
            'description': 'New description',
            'status': 'new',
            'section': self.section.id,
            'tags': [self.tag.id]
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Item.objects.filter(title='New Test Item').exists())
    
    def test_item_edit_view_post(self):
        """Test item edit view POST"""
        self.login_user(self.user)
        response = self.client.post(f'/items/{self.item.id}/edit/', {
            'title': 'Updated Title',
            'description': 'Updated description',
            'status': 'working',
            'section': self.section.id,
            'tags': [self.tag.id]
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'Updated Title')
        self.assertEqual(self.item.status, 'working')
    
    def test_item_delete_view(self):
        """Test item delete view"""
        self.login_user(self.user)
        item_id = self.item.id
        response = self.client.post(f'/items/{item_id}/delete/')
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertFalse(Item.objects.filter(id=item_id).exists())
    
    def test_user_can_only_see_own_items(self):
        """Test that users can only see their own items"""
        # Create another user and item
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='user'
        )
        other_user.set_password('Test@123')
        other_user.save()
        
        other_item = Item.objects.create(
            title='Other User Item',
            description='Other description',
            status='new',
            created_by=other_user
        )
        
        # Login as first user
        self.login_user(self.user)
        response = self.client.get('/items/')
        
        # Should see own item but not other user's item
        self.assertContains(response, 'Test Item')
        self.assertNotContains(response, 'Other User Item')
    
    def test_admin_can_see_all_items(self):
        """Test that admin can see all items"""
        # Create another user and item
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='user'
        )
        other_item = Item.objects.create(
            title='Other User Item',
            description='Other description',
            status='new',
            created_by=other_user
        )
        
        # Login as admin
        self.login_user(self.admin)
        response = self.client.get('/items/')
        
        # Should see all items
        self.assertContains(response, 'Test Item')
        self.assertContains(response, 'Other User Item')
    
    def test_item_status_choices(self):
        """Test that all status choices are available"""
        self.login_user(self.user)
        response = self.client.get('/items/create/')
        
        # Check all status options are present
        self.assertContains(response, 'Neu')
        self.assertContains(response, 'Spezifikation Review')
        self.assertContains(response, 'Working')
        self.assertContains(response, 'Ready')
        self.assertContains(response, 'Erledigt')
        self.assertContains(response, 'Verworfen')
    
    def test_item_detail_view_post_saves_changes(self):
        """Test that item detail view handles POST requests and saves changes"""
        self.login_user(self.user)
        
        # Update item through detail view
        response = self.client.post(f'/items/{self.item.id}/', {
            'title': 'Updated via Detail View',
            'description': 'Updated description via detail',
            'status': 'ready',
            'section': self.section.id,
            'tags': [self.tag.id]
        })
        
        # Should return 200 (stay on same page)
        self.assertEqual(response.status_code, 200)
        
        # Verify changes were saved
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'Updated via Detail View')
        self.assertEqual(self.item.description, 'Updated description via detail')
        self.assertEqual(self.item.status, 'ready')
        
        # Check success message
        messages_list = list(response.context['messages'])
        self.assertTrue(any('updated successfully' in str(m) for m in messages_list))


class ItemBuildTasksAPITest(TestCase):
    """Test Item Build Tasks API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        from unittest.mock import patch
        from main.models import Settings
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create settings with KiGate enabled
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_token='test_token',
            kigate_api_base_url='http://localhost:8000',
            kigate_api_timeout=30
        )
        
        # Create test item with description
        self.item = Item.objects.create(
            title='Test Item',
            description='This is a test item that needs tasks to be built.',
            status='ready',
            created_by=self.user
        )
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in the test user"""
        self.client.post('/login/', {
            'username': self.user.username,
            'password': 'Test@123'
        })
    
    def test_build_tasks_requires_auth(self):
        """Test that build tasks endpoint requires authentication"""
        from django.test import Client
        response = self.client.post(f'/api/items/{self.item.id}/build-tasks')
        self.assertEqual(response.status_code, 401)
    
    def test_build_tasks_requires_item_ownership(self):
        """Test that users can only build tasks for their own items"""
        # Create another user
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='user'
        )
        other_user.set_password('Test@123')
        other_user.save()
        
        # Create item for other user
        other_item = Item.objects.create(
            title='Other Item',
            description='Another item',
            status='ready',
            created_by=other_user
        )
        
        # Login as first user and try to build tasks for other user's item
        self.login_user()
        response = self.client.post(f'/api/items/{other_item.id}/build-tasks')
        self.assertEqual(response.status_code, 403)
    
    def test_build_tasks_requires_description(self):
        """Test that build tasks requires item description"""
        # Create item without description
        empty_item = Item.objects.create(
            title='Empty Item',
            description='',
            status='ready',
            created_by=self.user
        )
        
        self.login_user()
        response = self.client.post(f'/api/items/{empty_item.id}/build-tasks')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('description is required', data['error'])
    
    def test_build_tasks_success(self):
        """Test successful task building"""
        from unittest.mock import patch, Mock
        
        # Mock KiGate service responses
        with patch('main.api_views.KiGateService') as mock_kigate:
            mock_service = Mock()
            mock_kigate.return_value = mock_service
            
            # Mock role identification
            mock_service.execute_agent.side_effect = [
                {
                    'success': True,
                    'result': 'Ich bin Software Developer'
                },
                # Mock task extraction
                {
                    'success': True,
                    'result': '[{"Titel": "Task 1", "Beschreibung": "Description for task 1\\nWith line breaks"}, {"Titel": "Task 2", "Beschreibung": "Description 2"}]'
                }
            ]
            
            self.login_user()
            response = self.client.post(f'/api/items/{self.item.id}/build-tasks')
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
            self.assertEqual(data['tasks_created'], 2)
            self.assertEqual(len(data['tasks']), 2)
            
            # Verify tasks were created in database
            from main.models import Task
            tasks = Task.objects.filter(item=self.item)
            self.assertEqual(tasks.count(), 2)
            
            # Verify first task
            task1 = tasks.get(title='Task 1')
            self.assertEqual(task1.status, 'review')
            self.assertTrue(task1.ai_generated)
            self.assertEqual(task1.created_by, self.user)
            # Check that \n was converted to actual line breaks
            self.assertIn('\n', task1.description)
            self.assertNotIn('\\n', task1.description)
    
    def test_build_tasks_kigate_error(self):
        """Test handling KiGate service errors"""
        from unittest.mock import patch
        from core.services.kigate_service import KiGateServiceError
        
        with patch('main.api_views.KiGateService') as mock_kigate:
            mock_kigate.side_effect = KiGateServiceError('KiGate not configured')
            
            self.login_user()
            response = self.client.post(f'/api/items/{self.item.id}/build-tasks')
            
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertFalse(data['success'])
    
    def test_build_tasks_invalid_json_response(self):
        """Test handling invalid JSON from task extraction agent"""
        from unittest.mock import patch, Mock
        
        with patch('main.api_views.KiGateService') as mock_kigate:
            mock_service = Mock()
            mock_kigate.return_value = mock_service
            
            # Mock role identification
            mock_service.execute_agent.side_effect = [
                {
                    'success': True,
                    'result': 'Ich bin Developer'
                },
                # Return invalid JSON
                {
                    'success': True,
                    'result': 'This is not valid JSON'
                }
            ]
            
            self.login_user()
            response = self.client.post(f'/api/items/{self.item.id}/build-tasks')
            
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertIn('parse', data['error'].lower())

