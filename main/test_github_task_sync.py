"""
Tests for GitHub Task Synchronization Service
"""

import uuid
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.utils import timezone

from main.models import User, Item, Task, Settings, Section, Tag
from core.services.github_task_sync_service import GitHubTaskSyncService, GitHubTaskSyncServiceError


class GitHubTaskSyncServiceTest(TestCase):
    """Test cases for GitHubTaskSyncService"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        
        # Create test settings
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='test_token',
            github_default_owner='testowner',
            github_default_repo='testrepo'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            github_repo='testowner/testrepo',
            created_by=self.user
        )
    
    def test_service_initialization(self):
        """Test service initialization with settings"""
        service = GitHubTaskSyncService(self.settings)
        self.assertIsNotNone(service)
        self.assertEqual(service.settings, self.settings)
    
    def test_service_initialization_without_settings(self):
        """Test service initialization fetches settings from database"""
        service = GitHubTaskSyncService()
        self.assertIsNotNone(service)
        self.assertEqual(service.settings.id, self.settings.id)
    
    def test_service_initialization_github_disabled(self):
        """Test service initialization fails when GitHub is disabled"""
        self.settings.github_api_enabled = False
        self.settings.save()
        
        with self.assertRaises(GitHubTaskSyncServiceError) as context:
            GitHubTaskSyncService(self.settings)
        
        self.assertIn('GitHub API is not enabled', str(context.exception))
    
    def test_title_similarity_calculation(self):
        """Test title similarity calculation"""
        service = GitHubTaskSyncService(self.settings)
        
        # Identical titles
        similarity = service._calculate_title_similarity('Test Title', 'Test Title')
        self.assertEqual(similarity, 1.0)
        
        # Very similar titles
        similarity = service._calculate_title_similarity('Fix bug in login', 'Fix bug in Login')
        self.assertGreater(similarity, 0.85)
        
        # Different titles
        similarity = service._calculate_title_similarity('Fix login bug', 'Add new feature')
        self.assertLess(similarity, 0.5)
    
    def test_check_duplicate_by_issue_id(self):
        """Test duplicate detection by GitHub issue ID"""
        service = GitHubTaskSyncService(self.settings)
        
        # Create task with GitHub issue ID
        Task.objects.create(
            title='Test Task',
            item=self.item,
            github_issue_id=123,
            created_by=self.user
        )
        
        # Check for duplicate
        is_duplicate = service._check_duplicate_by_issue_id(self.item, 123)
        self.assertTrue(is_duplicate)
        
        # Check for non-duplicate
        is_duplicate = service._check_duplicate_by_issue_id(self.item, 456)
        self.assertFalse(is_duplicate)
    
    def test_check_duplicate_by_title(self):
        """Test duplicate detection by title similarity"""
        service = GitHubTaskSyncService(self.settings)
        
        # Create task with similar title
        Task.objects.create(
            title='Fix authentication bug',
            item=self.item,
            created_by=self.user
        )
        
        # Check for duplicate with similar title
        is_duplicate, matching_title = service._check_duplicate_by_title(
            self.item, 
            'Fix Authentication Bug'
        )
        self.assertTrue(is_duplicate)
        self.assertEqual(matching_title, 'Fix authentication bug')
        
        # Check for non-duplicate with different title
        is_duplicate, matching_title = service._check_duplicate_by_title(
            self.item, 
            'Add new feature for payments'
        )
        self.assertFalse(is_duplicate)
        self.assertIsNone(matching_title)
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_github_issues_to_tasks_no_repo(self, mock_github_service):
        """Test sync fails when no repository is specified"""
        service = GitHubTaskSyncService(self.settings)
        
        # Create item without github_repo
        item_without_repo = Item.objects.create(
            title='Item Without Repo',
            created_by=self.user
        )
        
        result = service.sync_github_issues_to_tasks(
            item=item_without_repo,
            created_by=self.user
        )
        
        self.assertFalse(result['success'])
        self.assertIn('No GitHub repository', result['error'])
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_github_issues_to_tasks_success(self, mock_github_service):
        """Test successful synchronization of GitHub issues to tasks"""
        service = GitHubTaskSyncService(self.settings)
        
        # Mock GitHub API response
        mock_issues = [
            {
                'number': 1,
                'title': 'Fix login bug',
                'body': 'Users cannot login',
                'state': 'open',
                'html_url': 'https://github.com/test/repo/issues/1'
            },
            {
                'number': 2,
                'title': 'Add feature X',
                'body': 'Add new feature X',
                'state': 'closed',
                'html_url': 'https://github.com/test/repo/issues/2'
            }
        ]
        
        mock_service_instance = Mock()
        mock_service_instance.list_issues.return_value = {
            'success': True,
            'issues': mock_issues
        }
        mock_github_service.return_value = mock_service_instance
        
        # Run sync
        result = service.sync_github_issues_to_tasks(
            item=self.item,
            created_by=self.user
        )
        
        # Verify results
        self.assertTrue(result['success'])
        self.assertEqual(result['issues_checked'], 2)
        self.assertEqual(result['tasks_created'], 2)
        self.assertEqual(result['duplicates_by_id'], 0)
        self.assertEqual(result['duplicates_by_title'], 0)
        
        # Verify tasks were created
        tasks = Task.objects.filter(item=self.item)
        self.assertEqual(tasks.count(), 2)
        
        # Verify task details
        task1 = tasks.get(github_issue_id=1)
        self.assertEqual(task1.title, 'Fix login bug')
        self.assertEqual(task1.status, 'new')  # open issue
        
        task2 = tasks.get(github_issue_id=2)
        self.assertEqual(task2.title, 'Add feature X')
        self.assertEqual(task2.status, 'done')  # closed issue
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_github_issues_with_duplicate_by_id(self, mock_github_service):
        """Test sync marks duplicate when GitHub issue ID exists"""
        service = GitHubTaskSyncService(self.settings)
        
        # Create existing task with GitHub issue ID
        Task.objects.create(
            title='Existing Task',
            item=self.item,
            github_issue_id=1,
            created_by=self.user
        )
        
        # Mock GitHub API response with duplicate issue
        mock_issues = [
            {
                'number': 1,
                'title': 'Fix login bug',
                'body': 'Users cannot login',
                'state': 'open',
                'html_url': 'https://github.com/test/repo/issues/1'
            }
        ]
        
        mock_service_instance = Mock()
        mock_service_instance.list_issues.return_value = {
            'success': True,
            'issues': mock_issues
        }
        mock_github_service.return_value = mock_service_instance
        
        # Run sync
        result = service.sync_github_issues_to_tasks(
            item=self.item,
            created_by=self.user
        )
        
        # Verify duplicate was detected
        self.assertTrue(result['success'])
        self.assertEqual(result['duplicates_by_id'], 1)
        
        # Verify duplicate task was created with prefix
        duplicate_tasks = Task.objects.filter(
            item=self.item,
            github_issue_id=1,
            title__startswith='*** Duplikat? ***'
        )
        self.assertEqual(duplicate_tasks.count(), 1)
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_github_issues_with_duplicate_by_title(self, mock_github_service):
        """Test sync marks duplicate when similar title exists"""
        service = GitHubTaskSyncService(self.settings)
        
        # Create existing task with similar title
        Task.objects.create(
            title='Fix authentication bug',
            item=self.item,
            created_by=self.user
        )
        
        # Mock GitHub API response with similar title
        mock_issues = [
            {
                'number': 10,
                'title': 'Fix Authentication Bug',
                'body': 'Authentication not working',
                'state': 'open',
                'html_url': 'https://github.com/test/repo/issues/10'
            }
        ]
        
        mock_service_instance = Mock()
        mock_service_instance.list_issues.return_value = {
            'success': True,
            'issues': mock_issues
        }
        mock_github_service.return_value = mock_service_instance
        
        # Run sync
        result = service.sync_github_issues_to_tasks(
            item=self.item,
            created_by=self.user
        )
        
        # Verify duplicate was detected
        self.assertTrue(result['success'])
        self.assertEqual(result['duplicates_by_title'], 1)
        
        # Verify duplicate task was created with prefix
        duplicate_tasks = Task.objects.filter(
            item=self.item,
            title__startswith='*** Duplikat? ***'
        )
        self.assertEqual(duplicate_tasks.count(), 1)
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_github_issues_skip_pull_requests(self, mock_github_service):
        """Test sync skips pull requests"""
        service = GitHubTaskSyncService(self.settings)
        
        # Mock GitHub API response with a PR (has pull_request key)
        mock_issues = [
            {
                'number': 1,
                'title': 'Fix login bug',
                'body': 'Users cannot login',
                'state': 'open',
                'html_url': 'https://github.com/test/repo/issues/1'
            },
            {
                'number': 2,
                'title': 'Add feature PR',
                'body': 'PR for new feature',
                'state': 'open',
                'html_url': 'https://github.com/test/repo/pull/2',
                'pull_request': {
                    'url': 'https://api.github.com/repos/test/repo/pulls/2'
                }
            }
        ]
        
        mock_service_instance = Mock()
        mock_service_instance.list_issues.return_value = {
            'success': True,
            'issues': mock_issues
        }
        mock_github_service.return_value = mock_service_instance
        
        # Run sync
        result = service.sync_github_issues_to_tasks(
            item=self.item,
            created_by=self.user
        )
        
        # Verify only issue was processed (PR skipped)
        self.assertTrue(result['success'])
        self.assertEqual(result['issues_checked'], 2)  # Both checked
        self.assertEqual(result['tasks_created'], 1)   # Only issue created
        
        # Verify only issue task exists
        tasks = Task.objects.filter(item=self.item)
        self.assertEqual(tasks.count(), 1)
        self.assertEqual(tasks.first().github_issue_id, 1)
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_github_issues_pagination(self, mock_github_service):
        """Test sync handles pagination correctly"""
        service = GitHubTaskSyncService(self.settings)
        
        # Mock GitHub API response with pagination
        # First page: 100 issues
        first_page_issues = [
            {
                'number': i,
                'title': f'Issue {i}',
                'body': f'Body {i}',
                'state': 'open',
                'html_url': f'https://github.com/test/repo/issues/{i}'
            }
            for i in range(1, 101)
        ]
        
        # Second page: 50 issues
        second_page_issues = [
            {
                'number': i,
                'title': f'Issue {i}',
                'body': f'Body {i}',
                'state': 'open',
                'html_url': f'https://github.com/test/repo/issues/{i}'
            }
            for i in range(101, 151)
        ]
        
        mock_service_instance = Mock()
        mock_service_instance.list_issues.side_effect = [
            {'success': True, 'issues': first_page_issues},
            {'success': True, 'issues': second_page_issues}
        ]
        mock_github_service.return_value = mock_service_instance
        
        # Run sync
        result = service.sync_github_issues_to_tasks(
            item=self.item,
            created_by=self.user
        )
        
        # Verify all issues were processed
        self.assertTrue(result['success'])
        self.assertEqual(result['issues_checked'], 150)
        self.assertEqual(result['tasks_created'], 150)
        
        # Verify list_issues was called twice (pagination)
        self.assertEqual(mock_service_instance.list_issues.call_count, 2)
