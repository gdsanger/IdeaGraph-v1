"""
Integration tests for GitHub Issue Synchronization Service
"""
from django.test import TestCase
from unittest.mock import patch, Mock, MagicMock
from main.models import User, Item, Task, Tag, Settings
import uuid


class GitHubIssueSyncServiceTest(TestCase):
    """Test GitHub Issue Sync Service"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings
        self.settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='test-key-123',
            openai_api_base_url='https://api.openai.com/v1',
            chroma_api_key='test-cloud-key',
            chroma_database='test-db',
            chroma_tenant='test-tenant',
            github_api_enabled=True,
            github_token='test-github-token',
            github_default_owner='testowner',
            github_default_repo='testrepo'
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            status='new',
            created_by=self.user
        )
        
        # Create tag
        self.tag = Tag.objects.create(name='bug', color='#ef4444')
        
        # Create task with GitHub issue
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='working',
            item=self.item,
            created_by=self.user,
            github_issue_id=123
        )
        self.task.tags.add(self.tag)
    
    @patch('core.services.github_issue_sync_service.requests.post')
    @patch('core.services.github_issue_sync_service.chromadb.HttpClient')
    def test_service_initialization(self, mock_client, mock_post):
        """Test that service initializes correctly"""
        from core.services.github_issue_sync_service import GitHubIssueSyncService
        
        # Mock ChromaDB client
        mock_collection = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance
        
        # Initialize service
        service = GitHubIssueSyncService(self.settings)
        
        # Verify
        self.assertIsNotNone(service)
        self.assertEqual(service.settings, self.settings)
        mock_client.assert_called_once()
        mock_client_instance.get_or_create_collection.assert_called_once_with(
            name='GitHubIssues',
            metadata={'description': 'GitHub Issues and Pull Requests with embeddings'}
        )
    
    @patch('core.services.github_issue_sync_service.requests.post')
    @patch('core.services.github_issue_sync_service.chromadb.HttpClient')
    def test_sync_issue_to_chroma(self, mock_client, mock_post):
        """Test syncing a GitHub issue to ChromaDB"""
        from core.services.github_issue_sync_service import GitHubIssueSyncService
        
        # Mock ChromaDB client
        mock_collection = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance
        
        # Mock OpenAI embedding response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        # Initialize service
        service = GitHubIssueSyncService(self.settings)
        
        # Create test issue data
        issue = {
            'number': 123,
            'title': 'Test Issue',
            'body': 'Test issue body',
            'state': 'open',
            'html_url': 'https://github.com/test/test/issues/123'
        }
        
        # Sync issue
        result = service.sync_issue_to_chroma(issue, self.task)
        
        # Verify
        self.assertTrue(result['success'])
        self.assertIn('Issue #123 synced to ChromaDB', result['message'])
        
        # Verify ChromaDB upsert was called
        mock_collection.upsert.assert_called_once()
        call_args = mock_collection.upsert.call_args
        self.assertEqual(call_args[1]['ids'], ['issue_123'])
        self.assertEqual(len(call_args[1]['embeddings'][0]), 1536)
        
        # Verify metadata
        metadata = call_args[1]['metadatas'][0]
        self.assertEqual(metadata['type'], 'issue')
        self.assertEqual(metadata['github_issue_id'], 123)
        self.assertEqual(metadata['github_issue_title'], 'Test Issue')
        self.assertEqual(metadata['task_id'], str(self.task.id))
        self.assertEqual(metadata['task_title'], 'Test Task')
        self.assertEqual(metadata['item_id'], str(self.item.id))
    
    @patch('core.services.github_issue_sync_service.requests.post')
    @patch('core.services.github_issue_sync_service.chromadb.HttpClient')
    def test_sync_pull_request_to_chroma(self, mock_client, mock_post):
        """Test syncing a GitHub pull request to ChromaDB"""
        from core.services.github_issue_sync_service import GitHubIssueSyncService
        
        # Mock ChromaDB client
        mock_collection = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance
        
        # Mock OpenAI embedding response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        # Initialize service
        service = GitHubIssueSyncService(self.settings)
        
        # Create test PR data
        pr = {
            'number': 456,
            'title': 'Test PR',
            'body': 'Test PR body with breaking changes',
            'state': 'open',
            'merged': False,
            'mergeable': True,
            'html_url': 'https://github.com/test/test/pull/456'
        }
        
        # Sync PR
        result = service.sync_pull_request_to_chroma(pr, self.task)
        
        # Verify
        self.assertTrue(result['success'])
        self.assertIn('PR #456 synced to ChromaDB', result['message'])
        
        # Verify ChromaDB upsert was called
        mock_collection.upsert.assert_called_once()
        call_args = mock_collection.upsert.call_args
        self.assertEqual(call_args[1]['ids'], ['pr_456'])
        
        # Verify metadata
        metadata = call_args[1]['metadatas'][0]
        self.assertEqual(metadata['type'], 'pull_request')
        self.assertEqual(metadata['github_issue_id'], 456)
        self.assertEqual(metadata['pr_merged'], False)
        self.assertEqual(metadata['pr_mergeable'], True)
    
    @patch('core.services.github_service.GitHubService')
    @patch('core.services.github_issue_sync_service.requests.post')
    @patch('core.services.github_issue_sync_service.chromadb.HttpClient')
    def test_sync_tasks_with_closed_issue(self, mock_client, mock_post, mock_github_service):
        """Test that closed GitHub issues mark tasks as done"""
        from core.services.github_issue_sync_service import GitHubIssueSyncService
        
        # Mock ChromaDB client
        mock_collection = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance
        
        # Mock OpenAI embedding response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        # Mock GitHub service
        mock_github_instance = MagicMock()
        mock_github_service.return_value = mock_github_instance
        
        # Mock GitHub API response with closed issue
        mock_github_instance.get_issue.return_value = {
            'success': True,
            'issue': {
                'number': 123,
                'title': 'Test Issue',
                'body': 'Test issue body',
                'state': 'closed',  # Issue is closed
                'html_url': 'https://github.com/test/test/issues/123'
            }
        }
        
        # Initialize service
        service = GitHubIssueSyncService(self.settings)
        
        # Verify task is not done initially
        self.assertEqual(self.task.status, 'working')
        
        # Run synchronization
        result = service.sync_tasks_with_github_issues()
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(result['results']['tasks_checked'], 1)
        self.assertEqual(result['results']['tasks_updated'], 1)
        
        # Refresh task from database
        self.task.refresh_from_db()
        
        # Verify task is now marked as done
        self.assertEqual(self.task.status, 'done')
        self.assertIsNotNone(self.task.completed_at)
    
    @patch('core.services.github_service.GitHubService')
    @patch('core.services.github_issue_sync_service.requests.post')
    @patch('core.services.github_issue_sync_service.chromadb.HttpClient')
    def test_sync_skips_done_tasks(self, mock_client, mock_post, mock_github_service):
        """Test that tasks with status='done' are skipped during synchronization"""
        from core.services.github_issue_sync_service import GitHubIssueSyncService
        
        # Mock ChromaDB client
        mock_collection = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance
        
        # Mock OpenAI embedding response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        # Mock GitHub service
        mock_github_instance = MagicMock()
        mock_github_service.return_value = mock_github_instance
        
        # Create a task with status='done' and a GitHub issue ID
        done_task = Task.objects.create(
            title='Done Task',
            description='This task is already done',
            status='done',
            item=self.item,
            created_by=self.user,
            github_issue_id=789,
            completed_at=self.item.created_at
        )
        
        # Initialize service
        service = GitHubIssueSyncService(self.settings)
        
        # Run synchronization
        result = service.sync_tasks_with_github_issues()
        
        # Verify that only the non-done task was checked
        # (self.task has status='working', done_task has status='done')
        self.assertTrue(result['success'])
        self.assertEqual(result['results']['tasks_checked'], 1)  # Only one task checked
        
        # Verify GitHub service was not called for the done task
        # It should only be called once for self.task (status='working')
        self.assertEqual(mock_github_instance.get_issue.call_count, 1)
    
    @patch('core.services.github_issue_sync_service.requests.post')
    @patch('core.services.github_issue_sync_service.chromadb.HttpClient')
    def test_search_similar(self, mock_client, mock_post):
        """Test searching for similar issues"""
        from core.services.github_issue_sync_service import GitHubIssueSyncService
        
        # Mock ChromaDB client
        mock_collection = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_client.return_value = mock_client_instance
        
        # Mock OpenAI embedding response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'embedding': [0.1] * 1536}]
        }
        mock_post.return_value = mock_response
        
        # Mock ChromaDB query results
        mock_collection.query.return_value = {
            'ids': [['issue_123', 'issue_456']],
            'metadatas': [[
                {'type': 'issue', 'github_issue_id': 123, 'github_issue_title': 'Test Issue 1'},
                {'type': 'issue', 'github_issue_id': 456, 'github_issue_title': 'Test Issue 2'}
            ]],
            'documents': [['Issue body 1', 'Issue body 2']],
            'distances': [[0.1, 0.2]]
        }
        
        # Initialize service
        service = GitHubIssueSyncService(self.settings)
        
        # Search for similar issues
        result = service.search_similar('authentication bug', n_results=2)
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(len(result['results']), 2)
        self.assertEqual(result['results'][0]['id'], 'issue_123')
        self.assertEqual(result['results'][0]['distance'], 0.1)


class GitHubServicePullRequestTest(TestCase):
    """Test GitHub Service Pull Request methods"""
    
    def setUp(self):
        """Set up test data"""
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='test-github-token',
            github_default_owner='testowner',
            github_default_repo='testrepo'
        )
    
    @patch('core.services.github_service.requests.request')
    def test_get_pull_request(self, mock_request):
        """Test getting a pull request"""
        from core.services.github_service import GitHubService
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = {
            'number': 123,
            'title': 'Test PR',
            'body': 'Test PR body',
            'state': 'open'
        }
        mock_request.return_value = mock_response
        
        # Initialize service
        service = GitHubService(self.settings)
        
        # Get PR
        result = service.get_pull_request(123)
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(result['pull_request']['number'], 123)
        self.assertEqual(result['pull_request']['title'], 'Test PR')
    
    @patch('core.services.github_service.requests.request')
    def test_list_pull_requests(self, mock_request):
        """Test listing pull requests"""
        from core.services.github_service import GitHubService
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = True
        mock_response.json.return_value = [
            {'number': 123, 'title': 'Test PR 1', 'state': 'open'},
            {'number': 456, 'title': 'Test PR 2', 'state': 'closed'}
        ]
        mock_request.return_value = mock_response
        
        # Initialize service
        service = GitHubService(self.settings)
        
        # List PRs
        result = service.list_pull_requests(state='all')
        
        # Verify
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['pull_requests']), 2)
