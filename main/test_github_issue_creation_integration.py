"""
Integration test for GitHub issue creation with assignment and comment
"""
import json
from unittest.mock import Mock, patch
from django.test import TestCase, Client
from django.urls import reverse

from main.models import Settings, User as AppUser, Item, Task, Tag, Section


class GitHubIssueCreationIntegrationTestCase(TestCase):
    """Test suite for GitHub issue creation with assignment and comments"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with GitHub API enabled
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='ghp_test_token_1234567890',
            github_api_base_url='https://api.github.com',
            github_default_owner='test-owner',
            github_default_repo='test-repo',
            github_copilot_username='copilot'
        )
        
        # Create test user
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create section, item and task
        self.section = Section.objects.create(name='Test Section')
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description',
            section=self.section,
            created_by=self.user,
            github_repo='test-owner/test-repo'
        )
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            item=self.item,
            status='ready'
        )
        
        # Create a tag
        self.tag = Tag.objects.create(name='test-tag')
        self.task.tags.add(self.tag)
        
        self.client = Client()
    
    @patch('core.services.github_service.requests.request')
    def test_create_github_issue_with_assignment_and_comment(self, mock_request):
        """Test that creating a GitHub issue assigns it to copilot and adds a comment"""
        
        # Mock responses for both issue creation and comment creation
        def request_side_effect(method, url, *args, **kwargs):
            if '/issues/' in url and '/comments' in url:
                # Comment creation
                return Mock(
                    status_code=201,
                    json=lambda: {
                        'id': 12345,
                        'body': kwargs.get('json', {}).get('body', ''),
                        'html_url': 'https://github.com/test-owner/test-repo/issues/42#issuecomment-12345'
                    },
                    content=b'...'
                )
            else:
                # Issue creation
                return Mock(
                    status_code=201,
                    json=lambda: {
                        'number': 42,
                        'title': 'Test Task',
                        'html_url': 'https://github.com/test-owner/test-repo/issues/42',
                        'state': 'open'
                    },
                    content=b'...'
                )
        
        mock_request.side_effect = request_side_effect
        
        # Set up session authentication
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        # Make the API request
        url = reverse('main:api_task_create_github_issue', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            content_type='application/json',
            HTTP_X_CSRFTOKEN='test-token'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('issue_number'), 42)
        
        # Verify task was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.github_issue_id, 42)
        self.assertIsNotNone(self.task.github_synced_at)
        
        # Verify task is assigned to GitHub Copilot user
        self.assertIsNotNone(self.task.assigned_to)
        self.assertEqual(self.task.assigned_to.username, 'GitHub Copilot')
        self.assertEqual(self.task.assigned_to.first_name, 'GitHub')
        self.assertEqual(self.task.assigned_to.last_name, 'Copilot')
        self.assertEqual(self.task.assigned_to.role, 'developer')
        
        # Verify that both issue creation and comment creation were called
        self.assertEqual(mock_request.call_count, 2)
        
        # Check issue creation call
        issue_call = mock_request.call_args_list[0]
        issue_json = issue_call[1]['json']
        self.assertEqual(issue_json['title'], 'Test Task')
        self.assertEqual(issue_json['assignees'], ['copilot'])
        self.assertEqual(issue_json['labels'], ['test-tag'])
        
        # Check comment creation call
        comment_call = mock_request.call_args_list[1]
        comment_json = comment_call[1]['json']
        self.assertIn('Created with IdeaGraph v1.0', comment_json['body'])
        self.assertIn(str(self.task.id), comment_json['body'])
        self.assertIn('/tasks/', comment_json['body'])
    
    @patch('core.services.github_service.requests.request')
    def test_create_github_issue_without_copilot_username(self, mock_request):
        """Test that creating a GitHub issue works even without copilot username configured"""
        
        # Remove copilot username
        self.settings.github_copilot_username = ''
        self.settings.save()
        
        # Mock responses for both issue creation and comment creation
        def request_side_effect(method, url, *args, **kwargs):
            if '/issues/' in url and '/comments' in url:
                # Comment creation
                return Mock(
                    status_code=201,
                    json=lambda: {
                        'id': 12345,
                        'body': kwargs.get('json', {}).get('body', ''),
                        'html_url': 'https://github.com/test-owner/test-repo/issues/43#issuecomment-12345'
                    },
                    content=b'...'
                )
            else:
                # Issue creation
                return Mock(
                    status_code=201,
                    json=lambda: {
                        'number': 43,
                        'title': 'Test Task',
                        'html_url': 'https://github.com/test-owner/test-repo/issues/43',
                        'state': 'open'
                    },
                    content=b'...'
                )
        
        mock_request.side_effect = request_side_effect
        
        # Set up session authentication
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        # Make the API request
        url = reverse('main:api_task_create_github_issue', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            content_type='application/json',
            HTTP_X_CSRFTOKEN='test-token'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success'))
        
        # Verify task is still assigned to GitHub Copilot user even without copilot_username setting
        self.task.refresh_from_db()
        self.assertIsNotNone(self.task.assigned_to)
        self.assertEqual(self.task.assigned_to.username, 'GitHub Copilot')
        
        # Check that issue was created without assignees
        issue_call = mock_request.call_args_list[0]
        issue_json = issue_call[1]['json']
        # When assignees is empty, it should not be in the request
        self.assertNotIn('assignees', issue_json)
    
    @patch('core.services.github_service.requests.request')
    def test_create_github_copilot_user_with_default_mail_sender(self, mock_request):
        """Test that GitHub Copilot user is created with email from Settings.default_mail_sender"""
        
        # Remove any existing GitHub Copilot user to test creation
        AppUser.objects.filter(username='GitHub Copilot').delete()
        
        # Set default mail sender in settings
        self.settings.default_mail_sender = 'noreply@ideagraph.example.com'
        self.settings.save()
        
        # Mock responses for both issue creation and comment creation
        def request_side_effect(method, url, *args, **kwargs):
            if '/issues/' in url and '/comments' in url:
                return Mock(
                    status_code=201,
                    json=lambda: {
                        'id': 12345,
                        'body': kwargs.get('json', {}).get('body', ''),
                        'html_url': 'https://github.com/test-owner/test-repo/issues/44#issuecomment-12345'
                    },
                    content=b'...'
                )
            else:
                return Mock(
                    status_code=201,
                    json=lambda: {
                        'number': 44,
                        'title': 'Test Task',
                        'html_url': 'https://github.com/test-owner/test-repo/issues/44',
                        'state': 'open'
                    },
                    content=b'...'
                )
        
        mock_request.side_effect = request_side_effect
        
        # Set up session authentication
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        # Make the API request
        url = reverse('main:api_task_create_github_issue', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            content_type='application/json',
            HTTP_X_CSRFTOKEN='test-token'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success'))
        
        # Verify GitHub Copilot user was created with correct email
        copilot_user = AppUser.objects.get(username='GitHub Copilot')
        self.assertEqual(copilot_user.email, 'noreply@ideagraph.example.com')
        self.assertEqual(copilot_user.first_name, 'GitHub')
        self.assertEqual(copilot_user.last_name, 'Copilot')
        self.assertEqual(copilot_user.role, 'developer')
        self.assertTrue(copilot_user.is_active)
        self.assertEqual(copilot_user.auth_type, 'local')
        # Verify password is set (user has a password_hash)
        self.assertNotEqual(copilot_user.password_hash, '')
        
        # Verify task is assigned to this user
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to.id, copilot_user.id)
    
    @patch('core.services.github_service.requests.request')
    def test_preserve_requester_when_creating_github_issue(self, mock_request):
        """Test that task requester is preserved when creating GitHub issue"""
        
        # Create a requester user
        requester = AppUser.objects.create(
            username='requester',
            email='requester@example.com',
            role='user'
        )
        
        # Set requester on task
        self.task.requester = requester
        self.task.save()
        
        # Mock responses
        def request_side_effect(method, url, *args, **kwargs):
            if '/issues/' in url and '/comments' in url:
                return Mock(
                    status_code=201,
                    json=lambda: {
                        'id': 12345,
                        'body': kwargs.get('json', {}).get('body', ''),
                        'html_url': 'https://github.com/test-owner/test-repo/issues/45#issuecomment-12345'
                    },
                    content=b'...'
                )
            else:
                return Mock(
                    status_code=201,
                    json=lambda: {
                        'number': 45,
                        'title': 'Test Task',
                        'html_url': 'https://github.com/test-owner/test-repo/issues/45',
                        'state': 'open'
                    },
                    content=b'...'
                )
        
        mock_request.side_effect = request_side_effect
        
        # Set up session authentication
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        # Make the API request
        url = reverse('main:api_task_create_github_issue', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            content_type='application/json',
            HTTP_X_CSRFTOKEN='test-token'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success'))
        
        # Verify requester is unchanged and assigned_to is set to GitHub Copilot
        self.task.refresh_from_db()
        self.assertEqual(self.task.requester.id, requester.id)
        self.assertIsNotNone(self.task.assigned_to)
        self.assertEqual(self.task.assigned_to.username, 'GitHub Copilot')
        self.assertNotEqual(self.task.requester.id, self.task.assigned_to.id)
