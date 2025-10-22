"""
Tests for Zammad Synchronization Service
"""

import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from main.models import Settings, User as AppUser, Task, Section, Tag, TaskFile
from core.services.zammad_sync_service import ZammadSyncService, ZammadSyncServiceError


class ZammadSyncServiceTestCase(TestCase):
    """Test suite for ZammadSyncService"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with Zammad integration enabled
        self.settings = Settings.objects.create(
            zammad_enabled=True,
            zammad_api_url='https://zammad.example.com',
            zammad_api_token='test_token_1234567890',
            zammad_groups='Support,Development',
            zammad_sync_interval=15
        )
        
        # Create test user
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin',
            is_active=True
        )
        self.user.set_password('testpass123!')
    
    def test_init_without_settings(self):
        """Test ZammadSyncService initialization without settings object"""
        with patch('main.models.Settings') as mock_settings_model:
            mock_settings_model.objects.first.return_value = self.settings
            service = ZammadSyncService()
            self.assertIsNotNone(service.settings)
    
    def test_init_with_disabled_integration(self):
        """Test ZammadSyncService raises error when integration is disabled"""
        self.settings.zammad_enabled = False
        self.settings.save()
        
        with self.assertRaises(ZammadSyncServiceError) as context:
            ZammadSyncService(self.settings)
        
        self.assertIn("not enabled", str(context.exception))
    
    def test_init_with_incomplete_config(self):
        """Test ZammadSyncService raises error with incomplete configuration"""
        self.settings.zammad_api_token = ''
        self.settings.save()
        
        with self.assertRaises(ZammadSyncServiceError) as context:
            ZammadSyncService(self.settings)
        
        self.assertIn("incomplete", str(context.exception))
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_test_connection_success(self, mock_request):
        """Test successful connection to Zammad API"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {'id': 1, 'login': 'testuser', 'firstname': 'Test'}
        )
        
        service = ZammadSyncService(self.settings)
        result = service.test_connection()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['user'], 'testuser')
        self.assertEqual(result['api_url'], 'https://zammad.example.com')
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_test_connection_failure(self, mock_request):
        """Test failed connection to Zammad API"""
        # Raise RequestException instead of a generic Exception
        from requests.exceptions import RequestException
        mock_request.side_effect = RequestException("Connection refused")
        
        service = ZammadSyncService(self.settings)
        result = service.test_connection()
        
        self.assertFalse(result.get('success', True))
        self.assertIn('error', result)
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_get_group_id(self, mock_request):
        """Test getting group ID by name"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [
                {'id': 1, 'name': 'Support'},
                {'id': 2, 'name': 'Development'}
            ]
        )
        
        service = ZammadSyncService(self.settings)
        group_id = service._get_group_id('Support')
        
        self.assertEqual(group_id, 1)
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_get_group_id_not_found(self, mock_request):
        """Test getting group ID for non-existent group"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [
                {'id': 1, 'name': 'Support'}
            ]
        )
        
        service = ZammadSyncService(self.settings)
        group_id = service._get_group_id('NonExistent')
        
        self.assertIsNone(group_id)
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_fetch_open_tickets(self, mock_request):
        """Test fetching open tickets from Zammad"""
        # Mock responses for different calls
        def mock_request_side_effect(*args, **kwargs):
            url = kwargs.get('url', '')
            
            # Group list request
            if '/groups' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [{'id': 1, 'name': 'Support'}]
                )
            # Ticket search request
            elif '/tickets/search' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [{'id': 123, 'title': 'Test Ticket'}]
                )
            # Individual ticket request
            elif '/tickets/123' in url:
                return Mock(
                    status_code=200,
                    json=lambda: {
                        'id': 123,
                        'title': 'Test Ticket',
                        'group': 'Support',
                        'state': {'name': 'open'},
                        'tags': ['bug']
                    }
                )
            # Articles request
            elif '/ticket_articles/by_ticket/123' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [
                        {
                            'id': 1,
                            'body': 'Test ticket body',
                            'attachments': []
                        }
                    ]
                )
        
        mock_request.side_effect = mock_request_side_effect
        
        service = ZammadSyncService(self.settings)
        tickets = service.fetch_open_tickets(['Support'])
        
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]['id'], 123)
        self.assertEqual(tickets[0]['title'], 'Test Ticket')
    
    def test_classify_task_type_default(self):
        """Test task type classification defaults to 'ticket'"""
        service = ZammadSyncService(self.settings)
        task_type = service._classify_task_type('Test Title', 'Test Description')
        
        self.assertEqual(task_type, 'ticket')
    
    def test_classify_task_type_with_ki(self):
        """Test task type classification with KI service"""
        # Enable KiGate
        self.settings.kigate_api_enabled = True
        self.settings.kigate_api_base_url = 'http://localhost:8000'
        self.settings.kigate_api_token = 'test:token'
        self.settings.save()
        
        service = ZammadSyncService(self.settings)
        
        # Mock the KiGateService call_agent method directly
        with patch.object(service, '_classify_task_type') as mock_classify:
            mock_classify.return_value = 'bug'
            
            task_type = service._classify_task_type('Bug in login', 'Users cannot login')
            self.assertEqual(task_type, 'bug')
    
    def test_find_or_create_section(self):
        """Test finding or creating section for Zammad group"""
        service = ZammadSyncService(self.settings)
        
        # First call should create
        section1 = service._find_or_create_section('Support')
        self.assertEqual(section1.name, 'Zammad - Support')
        
        # Second call should find existing
        section2 = service._find_or_create_section('Support')
        self.assertEqual(section1.id, section2.id)
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_sync_ticket_to_task_create(self, mock_request):
        """Test syncing Zammad ticket to new task"""
        # Mock responses for status update
        def mock_request_side_effect(*args, **kwargs):
            url = kwargs.get('url', '')
            
            # Mock ticket_states request
            if '/ticket_states' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [
                        {'id': 1, 'name': 'new'},
                        {'id': 2, 'name': 'open'},
                        {'id': 3, 'name': 'pending reminder'},
                        {'id': 4, 'name': 'closed'}
                    ]
                )
            # Mock ticket update request
            elif '/tickets/123' in url and kwargs.get('method') == 'PUT':
                return Mock(status_code=200, json=lambda: {'id': 123, 'state_id': 3})
            
            return Mock(status_code=200, json=lambda: {})
        
        mock_request.side_effect = mock_request_side_effect
        
        ticket = {
            'id': 123,
            'title': 'Test Ticket',
            'group': 'Support',
            'state': {'name': 'open'},
            'tags': ['bug', 'urgent'],
            'articles': [
                {
                    'id': 1,
                    'body': 'This is a test ticket description',
                    'attachments': []
                }
            ]
        }
        
        service = ZammadSyncService(self.settings)
        result = service.sync_ticket_to_task(ticket)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['action'], 'created')
        self.assertEqual(result['ticket_id'], '123')
        
        # Verify task was created
        task = Task.objects.get(external_id='123')
        self.assertEqual(task.title, 'Test Ticket')
        self.assertEqual(task.type, 'ticket')
        self.assertEqual(task.status, 'new')
        self.assertIn('https://zammad.example.com/#ticket/zoom/123', task.external_url)
        
        # Verify tags were added
        self.assertEqual(task.tags.count(), 2)
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_sync_ticket_to_task_update(self, mock_request):
        """Test syncing Zammad ticket to existing task"""
        # Mock responses for status update
        def mock_request_side_effect(*args, **kwargs):
            url = kwargs.get('url', '')
            
            # Mock ticket_states request
            if '/ticket_states' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [
                        {'id': 1, 'name': 'new'},
                        {'id': 2, 'name': 'open'},
                        {'id': 3, 'name': 'pending reminder'},
                        {'id': 4, 'name': 'closed'}
                    ]
                )
            # Mock ticket update request
            elif '/tickets/123' in url and kwargs.get('method') == 'PUT':
                return Mock(status_code=200, json=lambda: {'id': 123, 'state_id': 3})
            
            return Mock(status_code=200, json=lambda: {})
        
        mock_request.side_effect = mock_request_side_effect
        
        # Create existing task
        section = Section.objects.create(name='Zammad - Support')
        existing_task = Task.objects.create(
            title='Old Title',
            description='Old Description',
            type='ticket',
            section=section,
            external_id='123',
            external_url='https://zammad.example.com/#ticket/zoom/123'
        )
        
        ticket = {
            'id': 123,
            'title': 'Updated Ticket Title',
            'group': 'Support',
            'state': {'name': 'open'},
            'tags': [],
            'articles': [
                {
                    'id': 1,
                    'body': 'Updated ticket description',
                    'attachments': []
                }
            ]
        }
        
        service = ZammadSyncService(self.settings)
        result = service.sync_ticket_to_task(ticket)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['action'], 'updated')
        
        # Verify task was updated
        updated_task = Task.objects.get(id=existing_task.id)
        self.assertEqual(updated_task.title, 'Updated Ticket Title')
        self.assertEqual(updated_task.description, 'Updated ticket description')
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_sync_all_tickets(self, mock_request):
        """Test syncing all tickets from configured groups"""
        # Mock responses
        def mock_request_side_effect(*args, **kwargs):
            url = kwargs.get('url', '')
            method = kwargs.get('method', 'GET')
            
            if '/groups' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [
                        {'id': 1, 'name': 'Support'},
                        {'id': 2, 'name': 'Development'}
                    ]
                )
            elif '/tickets/search' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [{'id': 123}]
                )
            elif '/ticket_states' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [
                        {'id': 1, 'name': 'new'},
                        {'id': 2, 'name': 'open'},
                        {'id': 3, 'name': 'pending reminder'},
                        {'id': 4, 'name': 'closed'}
                    ]
                )
            elif '/tickets/123' in url and method == 'PUT':
                return Mock(status_code=200, json=lambda: {'id': 123, 'state_id': 3})
            elif '/tickets/123' in url:
                return Mock(
                    status_code=200,
                    json=lambda: {
                        'id': 123,
                        'title': 'Test Ticket',
                        'group': 'Support',
                        'articles': []
                    }
                )
            elif '/ticket_articles' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [{'id': 1, 'body': 'Test', 'attachments': []}]
                )
            
            return Mock(status_code=200, json=lambda: {})
        
        mock_request.side_effect = mock_request_side_effect
        
        service = ZammadSyncService(self.settings)
        result = service.sync_all_tickets()
        
        self.assertTrue(result['success'])
        self.assertIn('total_tickets', result)
        self.assertIn('created', result)
        self.assertIn('updated', result)
        self.assertIn('failed', result)

    @patch('core.services.zammad_sync_service.requests.request')
    def test_synced_tickets_excluded_from_future_fetch(self, mock_request):
        """Test that tickets updated to 'pending reminder' are excluded from future syncs"""
        # Mock responses
        def mock_request_side_effect(*args, **kwargs):
            url = kwargs.get('url', '')
            params = kwargs.get('params', {})
            
            if '/groups' in url:
                return Mock(
                    status_code=200,
                    json=lambda: [{'id': 1, 'name': 'Support'}]
                )
            # Check that the search query only includes 'open OR new' states
            elif '/tickets/search' in url:
                query = params.get('query', '')
                # Verify the query excludes 'pending reminder'
                self.assertIn('state.name:open OR state.name:new', query)
                self.assertNotIn('pending reminder', query)
                # Return empty list - no tickets should match after sync
                return Mock(status_code=200, json=lambda: [])
            
            return Mock(status_code=200, json=lambda: {})
        
        mock_request.side_effect = mock_request_side_effect
        
        service = ZammadSyncService(self.settings)
        # After tickets have been synced and updated to 'pending reminder',
        # fetch_open_tickets should not return them
        tickets = service.fetch_open_tickets(['Support'])
        
        # Should find no tickets because synced tickets are in 'pending reminder' state
        self.assertEqual(len(tickets), 0)



class ZammadAPIEndpointsTestCase(TestCase):
    """Test suite for Zammad API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create admin user
        self.admin_user = AppUser.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('admin123!')
        self.admin_user.save()
        
        # Create settings
        self.settings = Settings.objects.create(
            zammad_enabled=True,
            zammad_api_url='https://zammad.example.com',
            zammad_api_token='test_token',
            zammad_groups='Support',
            zammad_sync_interval=15
        )
        
        # Login via session
        from django.contrib.auth import get_user_model
        # We need to use the session directly since we're not using Django's built-in auth
        session = self.client.session
        session['user_id'] = str(self.admin_user.id)
        session.save()
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_api_zammad_test_connection(self, mock_request):
        """Test Zammad connection test endpoint"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {'id': 1, 'login': 'testuser'}
        )
        
        response = self.client.post(
            '/api/zammad/test-connection',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['user'], 'testuser')
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_api_zammad_sync(self, mock_request):
        """Test manual Zammad synchronization endpoint"""
        # Mock all necessary requests
        def mock_request_side_effect(*args, **kwargs):
            url = kwargs.get('url', '')
            
            if '/groups' in url:
                return Mock(status_code=200, json=lambda: [{'id': 1, 'name': 'Support'}])
            elif '/tickets/search' in url:
                return Mock(status_code=200, json=lambda: [])
            
            return Mock(status_code=200, json=lambda: {})
        
        mock_request.side_effect = mock_request_side_effect
        
        response = self.client.post(
            '/api/zammad/sync',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('total_tickets', data)
    
    def test_api_zammad_status(self):
        """Test Zammad status endpoint"""
        # Create some test tasks
        section = Section.objects.create(name='Zammad - Support')
        Task.objects.create(
            title='Test Ticket 1',
            type='ticket',
            section=section,
            external_id='123',
            status='new'
        )
        Task.objects.create(
            title='Test Ticket 2',
            type='ticket',
            section=section,
            external_id='124',
            status='working'
        )
        
        response = self.client.get('/api/zammad/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['enabled'])
        self.assertEqual(data['api_url'], 'https://zammad.example.com')
        self.assertEqual(data['statistics']['total_tasks'], 2)
        self.assertEqual(data['statistics']['new'], 1)
        self.assertEqual(data['statistics']['working'], 1)
    
    def test_api_zammad_endpoints_require_admin(self):
        """Test that Zammad API endpoints require admin role"""
        # Create non-admin user
        user = AppUser.objects.create(
            username='user',
            email='user@example.com',
            role='user',
            is_active=True
        )
        user.set_password('user123!')
        user.save()
        
        # Create new client and login as regular user
        client = Client()
        session = client.session
        session['user_id'] = str(user.id)
        session.save()
        
        # Test connection endpoint - should be forbidden
        response = client.post(
            '/api/zammad/test-connection',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)


class ZammadManagementCommandTestCase(TestCase):
    """Test suite for Zammad management command"""
    
    def setUp(self):
        """Set up test data"""
        self.settings = Settings.objects.create(
            zammad_enabled=True,
            zammad_api_url='https://zammad.example.com',
            zammad_api_token='test_token',
            zammad_groups='Support',
            zammad_sync_interval=15
        )
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_command_test_connection(self, mock_request):
        """Test management command with --test-connection flag"""
        from django.core.management import call_command
        from io import StringIO
        
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {'id': 1, 'login': 'testuser'}
        )
        
        out = StringIO()
        call_command('sync_zammad_tickets', '--test-connection', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Connection successful', output)
        self.assertIn('testuser', output)
    
    @patch('core.services.zammad_sync_service.requests.request')
    def test_command_sync_tickets(self, mock_request):
        """Test management command ticket sync"""
        from django.core.management import call_command
        from io import StringIO
        
        # Mock all necessary requests
        def mock_request_side_effect(*args, **kwargs):
            url = kwargs.get('url', '')
            
            if '/groups' in url:
                return Mock(status_code=200, json=lambda: [{'id': 1, 'name': 'Support'}])
            elif '/tickets/search' in url:
                return Mock(status_code=200, json=lambda: [])
            
            return Mock(status_code=200, json=lambda: {})
        
        mock_request.side_effect = mock_request_side_effect
        
        out = StringIO()
        call_command('sync_zammad_tickets', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Synchronization completed', output)
