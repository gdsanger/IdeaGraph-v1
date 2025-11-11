"""
Tests for Sentry Integration
"""
from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
from main.models import User, Item, Task, Settings
from core.services.sentry_task_sync_service import SentryTaskSyncService


class SentryIntegrationTest(TestCase):
    """Test Sentry integration for Items"""
    
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
        
        # Create test item with Sentry configured
        self.item = Item.objects.create(
            title='Test Item with Sentry',
            description='Test description',
            status='new',
            sentry_dsn='https://key@org123.ingest.sentry.io/12345',
            sentry_project_slug='test-project',
            sentry_auth_token='test_sentry_token_123',
            enable_sentry_fetch=True,
            created_by=self.user
        )
        
        # Create test item without Sentry
        self.item_no_sentry = Item.objects.create(
            title='Test Item without Sentry',
            description='Test description',
            status='new',
            created_by=self.user
        )
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in the test user"""
        self.client.post('/login/', {
            'username': self.user.username,
            'password': 'Test@123'
        })
    
    def test_item_model_has_sentry_fields(self):
        """Test that Item model has new Sentry fields"""
        self.assertTrue(hasattr(self.item, 'sentry_dsn'))
        self.assertTrue(hasattr(self.item, 'sentry_project_slug'))
        self.assertTrue(hasattr(self.item, 'enable_sentry_fetch'))
    
    def test_item_sentry_fields_values(self):
        """Test that Sentry fields can be set and retrieved"""
        self.assertEqual(self.item.sentry_dsn, 'https://key@org123.ingest.sentry.io/12345')
        self.assertEqual(self.item.sentry_project_slug, 'test-project')
        self.assertTrue(self.item.enable_sentry_fetch)
    
    def test_item_form_includes_sentry_fields(self):
        """Test that item form includes Sentry fields"""
        self.login_user()
        response = self.client.get(f'/items/{self.item.id}/edit/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sentry_dsn')
        self.assertContains(response, 'sentry_project_slug')
        self.assertContains(response, 'sentry_auth_token')
        self.assertContains(response, 'enable_sentry_fetch')
    
    def test_item_create_with_sentry_fields(self):
        """Test creating an item with Sentry fields"""
        self.login_user()
        response = self.client.post('/items/create/', {
            'title': 'New Item with Sentry',
            'description': 'Test',
            'status': 'new',
            'sentry_dsn': 'https://key@test.ingest.sentry.io/99999',
            'sentry_project_slug': 'new-project',
            'sentry_auth_token': 'test_token_123',
            'enable_sentry_fetch': 'on'
        })
        
        # Should redirect to item detail on success
        self.assertEqual(response.status_code, 302)
        
        # Check item was created with Sentry fields
        item = Item.objects.get(title='New Item with Sentry')
        self.assertEqual(item.sentry_dsn, 'https://key@test.ingest.sentry.io/99999')
        self.assertEqual(item.sentry_project_slug, 'new-project')
        self.assertEqual(item.sentry_auth_token, 'test_token_123')
        self.assertTrue(item.enable_sentry_fetch)
    
    def test_item_update_sentry_fields(self):
        """Test updating an item's Sentry fields"""
        self.login_user()
        response = self.client.post(f'/items/{self.item_no_sentry.id}/edit/', {
            'title': 'Updated Item',
            'description': 'Test',
            'status': 'new',
            'sentry_dsn': 'https://key@updated.ingest.sentry.io/88888',
            'sentry_project_slug': 'updated-project',
            'sentry_auth_token': 'updated_token',
            'enable_sentry_fetch': 'on'
        })
        
        # Should redirect to item detail on success
        self.assertEqual(response.status_code, 302)
        
        # Check item was updated
        item = Item.objects.get(id=self.item_no_sentry.id)
        self.assertEqual(item.sentry_dsn, 'https://key@updated.ingest.sentry.io/88888')
        self.assertEqual(item.sentry_project_slug, 'updated-project')
        self.assertEqual(item.sentry_auth_token, 'updated_token')
        self.assertTrue(item.enable_sentry_fetch)
    
    def test_item_model_has_sentry_auth_token(self):
        """Test that Item model has Sentry auth token field"""
        self.assertTrue(hasattr(self.item, 'sentry_auth_token'))
        self.assertEqual(self.item.sentry_auth_token, 'test_sentry_token_123')


class SentryTaskSyncServiceTest(TestCase):
    """Test Sentry Task Sync Service"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        
        # Create test item with Sentry configured
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            sentry_dsn='https://key@org123.ingest.sentry.io/12345',
            sentry_project_slug='test-project',
            sentry_auth_token='test_sentry_token_123',
            enable_sentry_fetch=True,
            created_by=self.user
        )
        
        self.service = SentryTaskSyncService()
    
    def test_parse_sentry_dsn_info(self):
        """Test parsing Sentry DSN information"""
        dsn = 'https://key123@org456.ingest.sentry.io/78901'
        org, project_id = self.service._parse_sentry_dsn_info(dsn)
        
        self.assertEqual(org, 'org456')
        self.assertEqual(project_id, '78901')
    
    def test_parse_invalid_dsn(self):
        """Test parsing invalid Sentry DSN"""
        dsn = 'invalid-dsn-format'
        org, project_id = self.service._parse_sentry_dsn_info(dsn)
        
        self.assertIsNone(org)
        self.assertIsNone(project_id)
    
    def test_generate_task_title(self):
        """Test generating task title from Sentry issue"""
        issue = {
            'title': 'Test Error Message',
            'id': 'issue123'
        }
        
        title = self.service._generate_task_title(issue)
        self.assertEqual(title, 'Test Error Message')
    
    def test_generate_task_title_from_metadata(self):
        """Test generating task title from metadata when title is missing"""
        issue = {
            'id': 'issue123',
            'metadata': {
                'value': 'Error from metadata'
            }
        }
        
        title = self.service._generate_task_title(issue)
        self.assertEqual(title, 'Error from metadata')
    
    def test_generate_task_title_truncates_long_titles(self):
        """Test that long titles are truncated"""
        long_title = 'A' * 300
        issue = {
            'title': long_title,
            'id': 'issue123'
        }
        
        title = self.service._generate_task_title(issue)
        self.assertTrue(len(title) <= 253)  # 250 + '...'
        self.assertTrue(title.endswith('...'))
    
    def test_generate_task_description(self):
        """Test generating task description from Sentry issue"""
        issue = {
            'id': 'issue123',
            'title': 'Test Error',
            'permalink': 'https://sentry.io/issues/123',
            'level': 'error',
            'count': 5,
            'userCount': 3,
            'metadata': {
                'type': 'ValueError',
                'value': 'Invalid value provided'
            },
            'firstSeen': '2024-01-01T12:00:00Z',
            'lastSeen': '2024-01-02T12:00:00Z',
            'culprit': 'app.views.some_function'
        }
        
        description = self.service._generate_task_description(issue)
        
        # Check that description contains key information
        self.assertIn('Test Error', description)
        self.assertIn('issue123', description)
        self.assertIn('https://sentry.io/issues/123', description)
        self.assertIn('ERROR', description)
        self.assertIn('5', description)  # count
        self.assertIn('3', description)  # userCount
        self.assertIn('ValueError', description)
        self.assertIn('Invalid value provided', description)
        self.assertIn('app.views.some_function', description)
    
    @patch('core.services.sentry_task_sync_service.SentryService')
    def test_fetch_and_create_tasks_no_dsn(self, mock_sentry_service):
        """Test fetch when item has no DSN configured"""
        item_no_dsn = Item.objects.create(
            title='Item without DSN',
            enable_sentry_fetch=True,
            created_by=self.user
        )
        
        result = self.service.fetch_and_create_tasks(item_no_dsn)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'No Sentry DSN configured')
    
    @patch('core.services.sentry_task_sync_service.SentryService')
    def test_fetch_and_create_tasks_disabled(self, mock_sentry_service):
        """Test fetch when Sentry fetch is disabled"""
        item_disabled = Item.objects.create(
            title='Item with disabled fetch',
            sentry_dsn='https://key@org.ingest.sentry.io/123',
            enable_sentry_fetch=False,
            created_by=self.user
        )
        
        result = self.service.fetch_and_create_tasks(item_disabled)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Sentry fetch is disabled')
    
    def test_is_duplicate_task_by_external_id(self):
        """Test duplicate detection by external ID"""
        # Create a task with Sentry external ID
        Task.objects.create(
            title='Existing Task',
            item=self.item,
            type='bug',
            external_id='sentry-issue123',
            created_by=self.user
        )
        
        # Check if duplicate is detected
        issue = {'id': 'issue123', 'title': 'Some Error'}
        is_duplicate = self.service._is_duplicate_task(self.item, issue)
        
        self.assertTrue(is_duplicate)
    
    def test_is_duplicate_task_by_title(self):
        """Test duplicate detection by title"""
        # Create a task with matching title
        Task.objects.create(
            title='Test Error Message',
            item=self.item,
            type='bug',
            created_by=self.user
        )
        
        # Check if duplicate is detected
        issue = {'id': 'issue456', 'title': 'Test Error Message'}
        is_duplicate = self.service._is_duplicate_task(self.item, issue)
        
        self.assertTrue(is_duplicate)
    
    def test_is_not_duplicate_task(self):
        """Test that unique tasks are not detected as duplicates"""
        # Create a task with different title and ID
        Task.objects.create(
            title='Different Error',
            item=self.item,
            type='bug',
            external_id='sentry-issue999',
            created_by=self.user
        )
        
        # Check that new issue is not considered duplicate
        issue = {'id': 'issue123', 'title': 'New Unique Error'}
        is_duplicate = self.service._is_duplicate_task(self.item, issue)
        
        self.assertFalse(is_duplicate)
    
    def test_create_task_from_issue(self):
        """Test creating a task from Sentry issue"""
        issue = {
            'id': 'issue789',
            'title': 'New Sentry Error',
            'permalink': 'https://sentry.io/issues/789',
            'level': 'error',
            'count': 10,
            'metadata': {
                'type': 'TypeError',
                'value': 'Cannot read property of undefined'
            }
        }
        
        task = self.service._create_task_from_issue(self.item, issue)
        
        self.assertIsNotNone(task)
        self.assertEqual(task.title, 'New Sentry Error')
        self.assertEqual(task.type, 'bug')
        self.assertEqual(task.status, 'new')
        self.assertEqual(task.item, self.item)
        self.assertEqual(task.external_id, 'sentry-issue789')
        self.assertEqual(task.external_url, 'https://sentry.io/issues/789')
        self.assertTrue(task.ai_generated)
        self.assertIn('TypeError', task.description)
        self.assertIn('Cannot read property of undefined', task.description)


class SentryAPIEndpointTest(TestCase):
    """Test Sentry API endpoint"""
    
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
        
        # Create test item with Sentry configured
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            sentry_dsn='https://key@org123.ingest.sentry.io/12345',
            sentry_project_slug='test-project',
            sentry_auth_token='test_sentry_token_123',
            enable_sentry_fetch=True,
            created_by=self.user
        )
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in the test user"""
        self.client.post('/login/', {
            'username': self.user.username,
            'password': 'Test@123'
        })
    
    def test_api_fetch_sentry_errors_requires_auth(self):
        """Test that API endpoint requires authentication"""
        response = self.client.post(f'/api/items/{self.item.id}/fetch-sentry-errors')
        self.assertEqual(response.status_code, 401)
    
    def test_api_fetch_sentry_errors_invalid_item(self):
        """Test API endpoint with invalid item ID"""
        self.login_user()
        response = self.client.post('/api/items/00000000-0000-0000-0000-000000000000/fetch-sentry-errors')
        self.assertEqual(response.status_code, 404)
    
    @patch('core.services.sentry_task_sync_service.SentryTaskSyncService')
    def test_api_fetch_sentry_errors_success(self, mock_service_class):
        """Test successful API call to fetch Sentry errors"""
        self.login_user()
        
        # Mock the service
        mock_service = MagicMock()
        mock_service.fetch_and_create_tasks.return_value = {
            'success': True,
            'issues_fetched': 3,
            'tasks_created': 2,
            'duplicates_skipped': 1
        }
        mock_service_class.return_value = mock_service
        
        response = self.client.post(
            f'/api/items/{self.item.id}/fetch-sentry-errors',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['issues_fetched'], 3)
        self.assertEqual(data['tasks_created'], 2)
        self.assertEqual(data['duplicates_skipped'], 1)


class SentryAutoFetchProjectSlugTest(TestCase):
    """Test auto-fetch functionality for Sentry project slug"""
    
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
        
        self.service = SentryTaskSyncService()
    
    @patch('core.services.sentry_service.SentryService.get_projects')
    def test_auto_fetch_project_slug_success(self, mock_get_projects):
        """Test successful auto-fetch of project slug"""
        # Create item with DSN but no project slug
        item = Item.objects.create(
            title='Test Item',
            sentry_dsn='https://key@org123.ingest.sentry.io/12345',
            sentry_auth_token='test_sentry_token_123',
            created_by=self.user
        )
        
        # Mock the Sentry API response
        mock_get_projects.return_value = [
            {'id': 12345, 'slug': 'my-awesome-project'},
            {'id': 67890, 'slug': 'another-project'}
        ]
        
        # Call auto-fetch
        project_slug = self.service.auto_fetch_project_slug(item)
        
        # Verify result
        self.assertEqual(project_slug, 'my-awesome-project')
    
    @patch('core.services.sentry_service.SentryService.get_projects')
    def test_auto_fetch_project_slug_not_found(self, mock_get_projects):
        """Test auto-fetch when project is not found"""
        item = Item.objects.create(
            title='Test Item',
            sentry_dsn='https://key@org123.ingest.sentry.io/99999',
            sentry_auth_token='test_sentry_token_123',
            created_by=self.user
        )
        
        # Mock the Sentry API response with different project IDs
        mock_get_projects.return_value = [
            {'id': 12345, 'slug': 'my-awesome-project'},
            {'id': 67890, 'slug': 'another-project'}
        ]
        
        # Call auto-fetch
        project_slug = self.service.auto_fetch_project_slug(item)
        
        # Verify result is None
        self.assertIsNone(project_slug)
    
    def test_auto_fetch_project_slug_no_dsn(self):
        """Test auto-fetch when item has no DSN"""
        item = Item.objects.create(
            title='Test Item',
            created_by=self.user
        )
        
        # Call auto-fetch
        project_slug = self.service.auto_fetch_project_slug(item)
        
        # Verify result is None
        self.assertIsNone(project_slug)
    
    def test_auto_fetch_project_slug_no_auth_token(self):
        """Test auto-fetch when no auth token is configured"""
        # Create item without auth token
        item = Item.objects.create(
            title='Test Item',
            sentry_dsn='https://key@org123.ingest.sentry.io/12345',
            created_by=self.user
        )
        
        # Call auto-fetch
        project_slug = self.service.auto_fetch_project_slug(item)
        
        # Verify result is None
        self.assertIsNone(project_slug)
    
    @patch('core.services.sentry_service.SentryService.get_projects')
    def test_fetch_and_create_tasks_auto_fills_slug(self, mock_get_projects):
        """Test that fetch_and_create_tasks auto-fills missing project slug"""
        # Create item with DSN but no project slug
        item = Item.objects.create(
            title='Test Item',
            sentry_dsn='https://key@org123.ingest.sentry.io/12345',
            sentry_auth_token='test_sentry_token_123',
            enable_sentry_fetch=True,
            created_by=self.user
        )
        
        # Mock the Sentry API response for projects
        mock_get_projects.return_value = [
            {'id': 12345, 'slug': 'auto-filled-project'}
        ]
        
        # Mock the get_issues method to return empty list (we don't care about tasks)
        with patch('core.services.sentry_service.SentryService.get_issues', return_value=[]):
            result = self.service.fetch_and_create_tasks(item)
        
        # Verify the project slug was auto-filled and saved
        item.refresh_from_db()
        self.assertEqual(item.sentry_project_slug, 'auto-filled-project')
        self.assertTrue(result['success'])
    
    def test_get_project_slug_from_id(self):
        """Test SentryService.get_project_slug_from_id method"""
        from core.services.sentry_service import SentryService
        
        service = SentryService()
        service.organization = 'org123'
        service.auth_token = 'test_token'
        
        # Mock get_projects to return test data
        with patch.object(service, 'get_projects', return_value=[
            {'id': 12345, 'slug': 'test-project'},
            {'id': 67890, 'slug': 'another-project'}
        ]):
            # Test finding existing project
            slug = service.get_project_slug_from_id('12345')
            self.assertEqual(slug, 'test-project')
            
            # Test project not found
            slug = service.get_project_slug_from_id('99999')
            self.assertIsNone(slug)
