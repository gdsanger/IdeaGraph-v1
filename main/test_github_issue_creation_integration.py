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
        
        # Check that issue was created without assignees
        issue_call = mock_request.call_args_list[0]
        issue_json = issue_call[1]['json']
        # When assignees is empty, it should not be in the request
        self.assertNotIn('assignees', issue_json)
