"""
Tests for GitHub Issue to Task Status Synchronization
Tests the automatic status flow: GitHub issue closed → Task status = "testing"
"""
from django.test import TestCase
from unittest.mock import Mock, patch
from main.models import User, Item, Task, Settings
from core.services.github_task_sync_service import GitHubTaskSyncService


class GitHubTaskStatusSyncTest(TestCase):
    """Test GitHub Task Status Synchronization"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create test item with GitHub repo
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            github_repo='owner/repo',
            created_by=self.user
        )
        
        # Create settings with GitHub API enabled
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='test_token',
            github_default_owner='owner'
        )
    
    def test_existing_task_status_updated_when_github_issue_closed(self):
        """Test that existing task status is updated to 'testing' when GitHub issue is closed"""
        # Create an existing task with status 'working'
        existing_task = Task.objects.create(
            title='Test Task',
            description='Test description',
            item=self.item,
            status='working',
            github_issue_id=123,
            created_by=self.user
        )
        
        # Mock GitHub service to return a closed issue
        mock_github_issues = [
            {
                'number': 123,
                'title': 'Test Issue',
                'body': 'Test body',
                'state': 'closed',
                'html_url': 'https://github.com/owner/repo/issues/123'
            }
        ]
        
        with patch('core.services.github_service.GitHubService') as mock_github_service:
            # Mock the list_issues method
            mock_service_instance = Mock()
            mock_service_instance.list_issues.return_value = {
                'success': True,
                'issues': mock_github_issues
            }
            mock_github_service.return_value = mock_service_instance
            
            # Run sync
            sync_service = GitHubTaskSyncService(self.settings)
            result = sync_service.sync_github_issues_to_tasks(
                item=self.item,
                owner='owner',
                repo='repo',
                state='all',
                created_by=self.user
            )
        
        # Verify sync was successful
        self.assertTrue(result['success'])
        self.assertEqual(result['duplicates_by_id'], 1)
        self.assertEqual(result['tasks_created'], 0)
        
        # Verify task status was updated to 'testing'
        existing_task.refresh_from_db()
        self.assertEqual(existing_task.status, 'testing')
    
    def test_new_task_created_with_testing_status_for_closed_issue(self):
        """Test that new task is created with 'testing' status for closed GitHub issue"""
        # Mock GitHub service to return a closed issue
        mock_github_issues = [
            {
                'number': 456,
                'title': 'New Closed Issue',
                'body': 'Test body',
                'state': 'closed',
                'html_url': 'https://github.com/owner/repo/issues/456'
            }
        ]
        
        with patch('core.services.github_service.GitHubService') as mock_github_service:
            # Mock the list_issues method
            mock_service_instance = Mock()
            mock_service_instance.list_issues.return_value = {
                'success': True,
                'issues': mock_github_issues
            }
            mock_github_service.return_value = mock_service_instance
            
            # Mock Weaviate sync to avoid actual sync
            with patch('core.services.weaviate_github_issue_sync_service.WeaviateGitHubIssueSyncService'):
                # Run sync
                sync_service = GitHubTaskSyncService(self.settings)
                result = sync_service.sync_github_issues_to_tasks(
                    item=self.item,
                    owner='owner',
                    repo='repo',
                    state='all',
                    created_by=self.user
                )
        
        # Verify sync was successful
        self.assertTrue(result['success'])
        self.assertEqual(result['tasks_created'], 1)
        
        # Verify task was created with 'testing' status
        new_task = Task.objects.get(github_issue_id=456)
        self.assertEqual(new_task.status, 'testing')
        self.assertEqual(new_task.title, 'New Closed Issue')
    
    def test_new_task_created_with_new_status_for_open_issue(self):
        """Test that new task is created with 'new' status for open GitHub issue"""
        # Mock GitHub service to return an open issue
        mock_github_issues = [
            {
                'number': 789,
                'title': 'New Open Issue',
                'body': 'Test body',
                'state': 'open',
                'html_url': 'https://github.com/owner/repo/issues/789'
            }
        ]
        
        with patch('core.services.github_service.GitHubService') as mock_github_service:
            # Mock the list_issues method
            mock_service_instance = Mock()
            mock_service_instance.list_issues.return_value = {
                'success': True,
                'issues': mock_github_issues
            }
            mock_github_service.return_value = mock_service_instance
            
            # Mock Weaviate sync to avoid actual sync
            with patch('core.services.weaviate_github_issue_sync_service.WeaviateGitHubIssueSyncService'):
                # Run sync
                sync_service = GitHubTaskSyncService(self.settings)
                result = sync_service.sync_github_issues_to_tasks(
                    item=self.item,
                    owner='owner',
                    repo='repo',
                    state='all',
                    created_by=self.user
                )
        
        # Verify sync was successful
        self.assertTrue(result['success'])
        self.assertEqual(result['tasks_created'], 1)
        
        # Verify task was created with 'new' status
        new_task = Task.objects.get(github_issue_id=789)
        self.assertEqual(new_task.status, 'new')
        self.assertEqual(new_task.title, 'New Open Issue')
    
    def test_task_status_not_updated_if_already_done(self):
        """Test that task status is not changed to 'testing' if already marked as 'done'"""
        # Create an existing task with status 'done'
        existing_task = Task.objects.create(
            title='Test Task',
            description='Test description',
            item=self.item,
            status='done',
            github_issue_id=999,
            created_by=self.user
        )
        
        # Mock GitHub service to return a closed issue
        mock_github_issues = [
            {
                'number': 999,
                'title': 'Test Issue',
                'body': 'Test body',
                'state': 'closed',
                'html_url': 'https://github.com/owner/repo/issues/999'
            }
        ]
        
        with patch('core.services.github_service.GitHubService') as mock_github_service:
            # Mock the list_issues method
            mock_service_instance = Mock()
            mock_service_instance.list_issues.return_value = {
                'success': True,
                'issues': mock_github_issues
            }
            mock_github_service.return_value = mock_service_instance
            
            # Run sync
            sync_service = GitHubTaskSyncService(self.settings)
            result = sync_service.sync_github_issues_to_tasks(
                item=self.item,
                owner='owner',
                repo='repo',
                state='all',
                created_by=self.user
            )
        
        # Verify sync was successful
        self.assertTrue(result['success'])
        
        # Verify task status remained 'done'
        existing_task.refresh_from_db()
        self.assertEqual(existing_task.status, 'done')
