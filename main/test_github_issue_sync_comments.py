"""
Tests for GitHub Issue Sync Comment Integration

This module tests that the GitHub issue synchronization service properly
creates task comments when issues are closed or completed.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from main.models import User, Item, Task, TaskComment, Settings
from core.services.weaviate_github_issue_sync_service import WeaviateGitHubIssueSyncService


class GitHubIssueSyncCommentTestCase(TestCase):
    """Test that sync service creates comments correctly"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='test_token',
            weaviate_cloud_enabled=False
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        
        # Create test item with GitHub repo
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            created_by=self.user,
            github_repo='testowner/testrepo'
        )
        
        # Create test task with GitHub issue
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            item=self.item,
            created_by=self.user,
            status='working',
            github_issue_id=123,
            github_issue_url='https://github.com/testowner/testrepo/issues/123'
        )
    
    @patch('core.services.weaviate_github_issue_sync_service.WeaviateGitHubIssueSyncService._initialize_client')
    @patch('core.services.github_service.GitHubService.get_issue')
    @patch('core.services.weaviate_github_issue_sync_service.WeaviateGitHubIssueSyncService.sync_issue_to_weaviate')
    def test_sync_creates_comment_when_issue_closed(self, mock_sync_weaviate, mock_get_issue, mock_init_client):
        """Test that syncing a closed issue creates a completion comment"""
        # Mock Weaviate client initialization
        mock_init_client.return_value = None
        
        # Mock GitHub API to return closed issue
        mock_get_issue.return_value = {
            'success': True,
            'issue': {
                'number': 123,
                'state': 'closed',
                'title': 'Test Issue',
                'body': 'Test issue description',
                'html_url': 'https://github.com/testowner/testrepo/issues/123',
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-02T00:00:00Z'
            }
        }
        
        # Mock Weaviate sync
        mock_sync_weaviate.return_value = None
        
        # Verify no comments exist initially
        initial_comments = TaskComment.objects.filter(task=self.task, source='agent').count()
        self.assertEqual(initial_comments, 0)
        
        # Run sync
        sync_service = WeaviateGitHubIssueSyncService(self.settings)
        result = sync_service.sync_tasks_with_github_issues(
            repo='testrepo',
            owner='testowner'
        )
        
        # Verify sync was successful
        self.assertTrue(result['success'])
        self.assertEqual(result['results']['tasks_checked'], 1)
        self.assertEqual(result['results']['tasks_updated'], 1)
        
        # Verify task was marked as done
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'done')
        
        # Verify comment was created
        comments = TaskComment.objects.filter(task=self.task, source='agent')
        self.assertEqual(comments.count(), 1)
        
        comment = comments.first()
        self.assertIn('123', comment.text)
        self.assertIn('GitHub Issue Completed', comment.text)
        self.assertIn('closed', comment.text.lower())
    
    @patch('core.services.weaviate_github_issue_sync_service.WeaviateGitHubIssueSyncService._initialize_client')
    @patch('core.services.github_service.GitHubService.get_issue')
    @patch('core.services.weaviate_github_issue_sync_service.WeaviateGitHubIssueSyncService.sync_issue_to_weaviate')
    def test_sync_no_comment_when_issue_open(self, mock_sync_weaviate, mock_get_issue, mock_init_client):
        """Test that syncing an open issue does not create a comment"""
        # Mock Weaviate client initialization
        mock_init_client.return_value = None
        
        # Mock GitHub API to return open issue
        mock_get_issue.return_value = {
            'success': True,
            'issue': {
                'number': 123,
                'state': 'open',
                'title': 'Test Issue',
                'body': 'Test issue description',
                'html_url': 'https://github.com/testowner/testrepo/issues/123',
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-02T00:00:00Z'
            }
        }
        
        # Mock Weaviate sync
        mock_sync_weaviate.return_value = None
        
        # Verify no comments exist initially
        initial_comments = TaskComment.objects.filter(task=self.task, source='agent').count()
        self.assertEqual(initial_comments, 0)
        
        # Run sync
        sync_service = WeaviateGitHubIssueSyncService(self.settings)
        result = sync_service.sync_tasks_with_github_issues(
            repo='testrepo',
            owner='testowner'
        )
        
        # Verify sync was successful
        self.assertTrue(result['success'])
        self.assertEqual(result['results']['tasks_checked'], 1)
        self.assertEqual(result['results']['tasks_updated'], 0)  # Task not updated since issue is still open
        
        # Verify task status unchanged
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'working')
        
        # Verify no comment was created
        comments = TaskComment.objects.filter(task=self.task, source='agent')
        self.assertEqual(comments.count(), 0)
