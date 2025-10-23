"""
Tests for GitHub API Service
"""

import json
from unittest.mock import Mock, patch
from django.test import TestCase, Client
from django.urls import reverse

from main.models import Settings, User as AppUser
from core.services.github_service import GitHubService, GitHubServiceError


class GitHubServiceTestCase(TestCase):
    """Test suite for GitHubService"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings with GitHub API enabled
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='ghp_test_token_1234567890',
            github_api_base_url='https://api.github.com',
            github_default_owner='test-owner',
            github_default_repo='test-repo'
        )
    
    def test_init_without_settings(self):
        """Test GitHubService initialization without settings object"""
        with patch('main.models.Settings') as mock_settings_model:
            mock_settings_model.objects.first.return_value = self.settings
            service = GitHubService()
            self.assertIsNotNone(service.settings)
    
    def test_init_with_disabled_api(self):
        """Test GitHubService raises error when API is disabled"""
        self.settings.github_api_enabled = False
        self.settings.save()
        
        with self.assertRaises(GitHubServiceError) as context:
            GitHubService(self.settings)
        
        self.assertIn("not enabled", str(context.exception))
    
    def test_init_with_no_token(self):
        """Test GitHubService raises error without token"""
        self.settings.github_token = ''
        self.settings.save()
        
        with self.assertRaises(GitHubServiceError) as context:
            GitHubService(self.settings)
        
        self.assertIn("incomplete", str(context.exception))
    
    @patch('core.services.github_service.requests.request')
    def test_get_repositories_authenticated_user(self, mock_request):
        """Test getting repositories for authenticated user"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [
                {'id': 1, 'name': 'repo1', 'full_name': 'user/repo1'},
                {'id': 2, 'name': 'repo2', 'full_name': 'user/repo2'}
            ],
            content=b'[...]'
        )
        
        service = GitHubService(self.settings)
        result = service.get_repositories()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['repositories']), 2)
    
    @patch('core.services.github_service.requests.request')
    def test_get_repositories_specific_owner(self, mock_request):
        """Test getting repositories for specific owner"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [
                {'id': 1, 'name': 'repo1', 'full_name': 'owner/repo1'}
            ],
            content=b'[...]'
        )
        
        service = GitHubService(self.settings)
        result = service.get_repositories(owner='owner')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 1)
        
        # Verify correct endpoint was called
        call_args = mock_request.call_args
        self.assertIn('users/owner/repos', call_args[1]['url'])
    
    @patch('core.services.github_service.requests.request')
    def test_get_repositories_with_pagination(self, mock_request):
        """Test repository listing with pagination parameters"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [],
            content=b'[]'
        )
        
        service = GitHubService(self.settings)
        result = service.get_repositories(per_page=50, page=2)
        
        # Verify pagination params were included
        call_args = mock_request.call_args
        params = call_args[1]['params']
        self.assertEqual(params['per_page'], 50)
        self.assertEqual(params['page'], 2)
    
    @patch('core.services.github_service.requests.request')
    def test_get_repositories_error(self, mock_request):
        """Test error handling when listing repositories"""
        mock_request.return_value = Mock(
            status_code=401,
            text='Unauthorized',
            json=lambda: {'message': 'Bad credentials'},
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        
        with self.assertRaises(GitHubServiceError) as context:
            service.get_repositories()
        
        self.assertEqual(context.exception.status_code, 401)
    
    @patch('core.services.github_service.requests.request')
    def test_create_issue_success(self, mock_request):
        """Test creating an issue successfully"""
        mock_request.return_value = Mock(
            status_code=201,
            json=lambda: {
                'number': 42,
                'title': 'Test Issue',
                'html_url': 'https://github.com/owner/repo/issues/42',
                'state': 'open'
            },
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        result = service.create_issue(
            title='Test Issue',
            body='Test issue body',
            owner='owner',
            repo='repo',
            labels=['bug', 'enhancement']
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['issue_number'], 42)
        self.assertIn('github.com', result['url'])
        
        # Verify request data
        call_args = mock_request.call_args
        json_data = call_args[1]['json']
        self.assertEqual(json_data['title'], 'Test Issue')
        self.assertEqual(json_data['body'], 'Test issue body')
        self.assertEqual(json_data['labels'], ['bug', 'enhancement'])
    
    @patch('core.services.github_service.requests.request')
    def test_create_issue_with_defaults(self, mock_request):
        """Test creating issue using default owner/repo from settings"""
        mock_request.return_value = Mock(
            status_code=201,
            json=lambda: {
                'number': 1,
                'title': 'Test',
                'html_url': 'https://github.com/test-owner/test-repo/issues/1'
            },
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        result = service.create_issue(title='Test', body='Body')
        
        self.assertTrue(result['success'])
        
        # Verify default owner/repo was used
        call_args = mock_request.call_args
        url = call_args[1]['url']
        self.assertIn('test-owner/test-repo', url)
    
    @patch('core.services.github_service.requests.request')
    def test_create_issue_missing_repo_info(self, mock_request):
        """Test creating issue without repo info raises error"""
        self.settings.github_default_owner = ''
        self.settings.github_default_repo = ''
        self.settings.save()
        
        service = GitHubService(self.settings)
        
        with self.assertRaises(GitHubServiceError) as context:
            service.create_issue(title='Test', body='Body')
        
        self.assertIn("Repository information required", str(context.exception))
    
    @patch('core.services.github_service.requests.request')
    def test_create_issue_error(self, mock_request):
        """Test error handling when creating issue"""
        mock_request.return_value = Mock(
            status_code=422,
            text='Validation failed',
            json=lambda: {'message': 'Validation Failed'},
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        
        with self.assertRaises(GitHubServiceError) as context:
            service.create_issue(title='', body='Body', owner='owner', repo='repo')
        
        self.assertEqual(context.exception.status_code, 422)
    
    @patch('core.services.github_service.requests.request')
    def test_get_issue_success(self, mock_request):
        """Test getting a specific issue"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'number': 42,
                'title': 'Test Issue',
                'state': 'open',
                'body': 'Issue body',
                'labels': [{'name': 'bug'}]
            },
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        result = service.get_issue(issue_number=42, owner='owner', repo='repo')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['issue']['number'], 42)
        self.assertEqual(result['issue']['state'], 'open')
    
    @patch('core.services.github_service.requests.request')
    def test_get_issue_not_found(self, mock_request):
        """Test getting non-existent issue"""
        mock_request.return_value = Mock(
            status_code=404,
            text='Not Found',
            json=lambda: {'message': 'Not Found'},
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        
        with self.assertRaises(GitHubServiceError) as context:
            service.get_issue(issue_number=999, owner='owner', repo='repo')
        
        self.assertEqual(context.exception.status_code, 404)
    
    @patch('core.services.github_service.requests.request')
    def test_list_issues_success(self, mock_request):
        """Test listing issues in a repository"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [
                {'number': 1, 'title': 'Issue 1', 'state': 'open'},
                {'number': 2, 'title': 'Issue 2', 'state': 'open'}
            ],
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        result = service.list_issues(owner='owner', repo='repo', state='open')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['issues']), 2)
    
    @patch('core.services.github_service.requests.request')
    def test_list_issues_with_filters(self, mock_request):
        """Test listing issues with label filters"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [
                {'number': 1, 'title': 'Bug Issue'}
            ],
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        result = service.list_issues(
            owner='owner',
            repo='repo',
            state='closed',
            labels=['bug', 'critical']
        )
        
        # Verify filters were applied
        call_args = mock_request.call_args
        params = call_args[1]['params']
        self.assertEqual(params['state'], 'closed')
        self.assertEqual(params['labels'], 'bug,critical')
    
    @patch('core.services.github_service.requests.request')
    def test_list_issues_pagination(self, mock_request):
        """Test issue listing with pagination"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [],
            content=b'[]'
        )
        
        service = GitHubService(self.settings)
        result = service.list_issues(
            owner='owner',
            repo='repo',
            per_page=50,
            page=3
        )
        
        call_args = mock_request.call_args
        params = call_args[1]['params']
        self.assertEqual(params['per_page'], 50)
        self.assertEqual(params['page'], 3)
    
    def test_github_service_error_to_dict(self):
        """Test GitHubServiceError to_dict method"""
        error = GitHubServiceError(
            message="Test error",
            status_code=500,
            details="Test details"
        )
        
        error_dict = error.to_dict()
        
        self.assertFalse(error_dict['success'])
        self.assertEqual(error_dict['error'], "Test error")
        self.assertEqual(error_dict['details'], "Test details")
    
    @patch('core.services.github_service.requests.request')
    def test_request_headers(self, mock_request):
        """Test that proper headers are sent with requests"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [],
            content=b'[]'
        )
        
        service = GitHubService(self.settings)
        service.get_repositories()
        
        call_args = mock_request.call_args
        headers = call_args[1]['headers']
        
        self.assertIn('Authorization', headers)
        self.assertTrue(headers['Authorization'].startswith('Bearer '))
        self.assertIn('Accept', headers)
        self.assertEqual(headers['Accept'], 'application/vnd.github.v3+json')


class GitHubAPIEndpointsTestCase(TestCase):
    """Test suite for GitHub API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create admin user
        self.admin = AppUser(username='admin', email='admin@example.com', role='admin')
        self.admin.set_password('AdminPass123!')
        self.admin.save()
        
        # Create developer user
        self.developer = AppUser(username='dev', email='dev@example.com', role='developer')
        self.developer.set_password('DevPass123!')
        self.developer.save()
        
        # Create regular user
        self.user = AppUser(username='user', email='user@example.com', role='user')
        self.user.set_password('UserPass123!')
        self.user.save()
        
        # Create settings
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='ghp_test_token',
            github_default_owner='test-owner',
            github_default_repo='test-repo'
        )
        
        # Get admin token
        response = self.client.post(
            reverse('main:api_login'),
            data=json.dumps({'username': 'admin', 'password': 'AdminPass123!'}),
            content_type='application/json'
        )
        self.admin_token = response.json()['token']
        
        # Get developer token
        response = self.client.post(
            reverse('main:api_login'),
            data=json.dumps({'username': 'dev', 'password': 'DevPass123!'}),
            content_type='application/json'
        )
        self.developer_token = response.json()['token']
        
        # Get user token
        response = self.client.post(
            reverse('main:api_login'),
            data=json.dumps({'username': 'user', 'password': 'UserPass123!'}),
            content_type='application/json'
        )
        self.user_token = response.json()['token']
    
    @patch('core.services.github_service.requests.request')
    def test_list_repos_admin(self, mock_request):
        """Test listing repositories as admin"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [
                {'id': 1, 'name': 'repo1'}
            ],
            content=b'...'
        )
        
        response = self.client.get(
            reverse('main:api_github_repos'),
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)
    
    @patch('core.services.github_service.requests.request')
    def test_list_repos_developer(self, mock_request):
        """Test listing repositories as developer"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [
                {'id': 1, 'name': 'repo1'}
            ],
            content=b'...'
        )
        
        response = self.client.get(
            reverse('main:api_github_repos'),
            HTTP_AUTHORIZATION=f'Bearer {self.developer_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_list_repos_regular_user(self):
        """Test that regular users cannot list repositories"""
        response = self.client.get(
            reverse('main:api_github_repos'),
            HTTP_AUTHORIZATION=f'Bearer {self.user_token}'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)
    
    @patch('core.services.github_service.requests.request')
    def test_create_issue_admin(self, mock_request):
        """Test creating issue as admin"""
        mock_request.return_value = Mock(
            status_code=201,
            json=lambda: {
                'number': 1,
                'title': 'Test Issue',
                'html_url': 'https://github.com/owner/repo/issues/1'
            },
            content=b'...'
        )
        
        response = self.client.post(
            reverse('main:api_github_create_issue'),
            data=json.dumps({
                'title': 'Test Issue',
                'body': 'Test body',
                'owner': 'owner',
                'repo': 'repo',
                'labels': ['bug']
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['issue_number'], 1)
    
    def test_create_issue_missing_params(self):
        """Test create issue with missing parameters"""
        response = self.client.post(
            reverse('main:api_github_create_issue'),
            data=json.dumps({
                'title': 'Test Issue'
                # Missing body
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
    
    @patch('core.services.github_service.requests.request')
    def test_get_issue_success(self, mock_request):
        """Test getting a specific issue"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                'number': 42,
                'title': 'Test Issue',
                'state': 'open'
            },
            content=b'...'
        )
        
        response = self.client.get(
            reverse('main:api_github_get_issue', kwargs={
                'owner': 'owner',
                'repo': 'repo',
                'issue_number': 42
            }),
            HTTP_AUTHORIZATION=f'Bearer {self.developer_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['issue']['number'], 42)
    
    @patch('core.services.github_service.requests.request')
    def test_list_issues_success(self, mock_request):
        """Test listing issues"""
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: [
                {'number': 1, 'title': 'Issue 1'}
            ],
            content=b'...'
        )
        
        response = self.client.get(
            reverse('main:api_github_list_issues', kwargs={
                'owner': 'owner',
                'repo': 'repo'
            }) + '?state=open',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_endpoints_require_auth(self):
        """Test that endpoints require authentication"""
        # Test GET endpoints
        get_endpoints = [
            reverse('main:api_github_repos'),
        ]
        
        for endpoint in get_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 403)
        
        # Test POST endpoints
        post_endpoints = [
            reverse('main:api_github_create_issue'),
        ]
        
        for endpoint in post_endpoints:
            response = self.client.post(
                endpoint,
                data=json.dumps({}),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 403)


class GitHubServiceCommentTestCase(TestCase):
    """Test suite for GitHubService comment methods"""
    
    def setUp(self):
        """Set up test data"""
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='ghp_test_token_1234567890',
            github_api_base_url='https://api.github.com',
            github_default_owner='test-owner',
            github_default_repo='test-repo',
            github_copilot_username='copilot'
        )
    
    @patch('core.services.github_service.requests.request')
    def test_create_issue_comment_success(self, mock_request):
        """Test creating a comment on an issue successfully"""
        mock_request.return_value = Mock(
            status_code=201,
            json=lambda: {
                'id': 12345,
                'body': 'Test comment',
                'html_url': 'https://github.com/owner/repo/issues/42#issuecomment-12345',
                'created_at': '2025-10-23T00:00:00Z'
            },
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        result = service.create_issue_comment(
            issue_number=42,
            body='Test comment',
            owner='owner',
            repo='repo'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['comment_id'], 12345)
        self.assertIn('github.com', result['url'])
        
        # Verify request data
        call_args = mock_request.call_args
        json_data = call_args[1]['json']
        self.assertEqual(json_data['body'], 'Test comment')
        self.assertIn('/issues/42/comments', call_args[1]['url'])
    
    @patch('core.services.github_service.requests.request')
    def test_create_issue_comment_with_defaults(self, mock_request):
        """Test creating comment using default owner/repo from settings"""
        mock_request.return_value = Mock(
            status_code=201,
            json=lambda: {
                'id': 1,
                'body': 'Comment',
                'html_url': 'https://github.com/test-owner/test-repo/issues/1#issuecomment-1'
            },
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        result = service.create_issue_comment(issue_number=1, body='Comment')
        
        self.assertTrue(result['success'])
        
        # Verify default owner/repo was used
        call_args = mock_request.call_args
        url = call_args[1]['url']
        self.assertIn('test-owner/test-repo', url)
    
    @patch('core.services.github_service.requests.request')
    def test_create_issue_comment_missing_repo_info(self, mock_request):
        """Test creating comment without repo info raises error"""
        self.settings.github_default_owner = ''
        self.settings.github_default_repo = ''
        self.settings.save()
        
        service = GitHubService(self.settings)
        
        with self.assertRaises(GitHubServiceError) as context:
            service.create_issue_comment(issue_number=1, body='Comment')
        
        self.assertIn("Repository information required", str(context.exception))
    
    @patch('core.services.github_service.requests.request')
    def test_create_issue_comment_error(self, mock_request):
        """Test error handling when creating comment"""
        mock_request.return_value = Mock(
            status_code=404,
            text='Not Found',
            json=lambda: {'message': 'Issue not found'},
            content=b'...'
        )
        
        service = GitHubService(self.settings)
        
        with self.assertRaises(GitHubServiceError) as context:
            service.create_issue_comment(
                issue_number=999,
                body='Comment',
                owner='owner',
                repo='repo'
            )
        
        self.assertEqual(context.exception.status_code, 404)
