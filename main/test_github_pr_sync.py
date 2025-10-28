"""
Tests for GitHub Pull Request Synchronization Service
"""

import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta

from main.models import Settings, Item, GitHubPullRequest, User as AppUser
from core.services.github_pr_sync_service import GitHubPRSyncService, GitHubPRSyncServiceError


class GitHubPRSyncServiceTestCase(TestCase):
    """Test suite for GitHubPRSyncService"""
    
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
        
        # Create test user
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        
        # Create test item with GitHub repo
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            github_repo='test-owner/test-repo',
            created_by=self.user
        )
    
    def test_init_without_settings(self):
        """Test GitHubPRSyncService initialization without settings object"""
        with patch('main.models.Settings') as mock_settings_model:
            mock_settings_model.objects.first.return_value = self.settings
            service = GitHubPRSyncService()
            self.assertIsNotNone(service.settings)
    
    def test_init_with_disabled_api(self):
        """Test GitHubPRSyncService raises error when API is disabled"""
        self.settings.github_api_enabled = False
        self.settings.save()
        
        with self.assertRaises(GitHubPRSyncServiceError) as context:
            GitHubPRSyncService(self.settings)
        
        self.assertIn("not enabled", str(context.exception))
    
    def test_extract_repo_info_owner_slash_repo(self):
        """Test extracting repo info from 'owner/repo' format"""
        service = GitHubPRSyncService(self.settings)
        owner, repo = service._extract_repo_info('test-owner/test-repo')
        
        self.assertEqual(owner, 'test-owner')
        self.assertEqual(repo, 'test-repo')
    
    def test_extract_repo_info_url_format(self):
        """Test extracting repo info from GitHub URL"""
        service = GitHubPRSyncService(self.settings)
        owner, repo = service._extract_repo_info('https://github.com/test-owner/test-repo')
        
        self.assertEqual(owner, 'test-owner')
        self.assertEqual(repo, 'test-repo')
    
    def test_extract_repo_info_url_with_git_suffix(self):
        """Test extracting repo info from GitHub URL with .git suffix"""
        service = GitHubPRSyncService(self.settings)
        owner, repo = service._extract_repo_info('https://github.com/test-owner/test-repo.git')
        
        self.assertEqual(owner, 'test-owner')
        self.assertEqual(repo, 'test-repo')
    
    def test_extract_repo_info_invalid_format(self):
        """Test extracting repo info with invalid format raises error"""
        service = GitHubPRSyncService(self.settings)
        
        with self.assertRaises(GitHubPRSyncServiceError) as context:
            service._extract_repo_info('invalid-format')
        
        self.assertIn("Invalid repository format", str(context.exception))
    
    def test_parse_github_datetime_valid(self):
        """Test parsing valid GitHub datetime"""
        service = GitHubPRSyncService(self.settings)
        dt_str = '2023-01-15T10:30:00Z'
        result = service._parse_github_datetime(dt_str)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2023)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 15)
    
    def test_parse_github_datetime_none(self):
        """Test parsing None datetime returns None"""
        service = GitHubPRSyncService(self.settings)
        result = service._parse_github_datetime(None)
        
        self.assertIsNone(result)
    
    def test_store_pr_in_database_creates_new(self):
        """Test storing a new PR in the database"""
        service = GitHubPRSyncService(self.settings)
        
        pr_data = {
            'number': 123,
            'title': 'Test PR',
            'body': 'Test PR body',
            'state': 'open',
            'html_url': 'https://github.com/test-owner/test-repo/pull/123',
            'draft': False,
            'merged': False,
            'user': {
                'login': 'testauthor',
                'avatar_url': 'https://avatars.githubusercontent.com/u/123'
            },
            'head': {'ref': 'feature-branch'},
            'base': {'ref': 'main'},
            'created_at': '2023-01-15T10:30:00Z',
            'updated_at': '2023-01-15T11:00:00Z',
            'closed_at': None,
            'merged_at': None,
        }
        
        pr, was_created = service._store_pr_in_database(self.item, pr_data, 'test-owner', 'test-repo')
        
        self.assertIsNotNone(pr)
        self.assertTrue(was_created)
        self.assertEqual(pr.pr_number, 123)
        self.assertEqual(pr.title, 'Test PR')
        self.assertEqual(pr.state, 'open')
        self.assertEqual(pr.author_login, 'testauthor')
        self.assertEqual(pr.head_branch, 'feature-branch')
        self.assertEqual(pr.base_branch, 'main')
        self.assertEqual(pr.item, self.item)
    
    def test_store_pr_in_database_updates_existing(self):
        """Test updating an existing PR in the database"""
        service = GitHubPRSyncService(self.settings)
        
        # Create initial PR
        pr_data = {
            'number': 123,
            'title': 'Test PR',
            'body': 'Test PR body',
            'state': 'open',
            'html_url': 'https://github.com/test-owner/test-repo/pull/123',
            'draft': False,
            'merged': False,
            'user': {'login': 'testauthor', 'avatar_url': ''},
            'head': {'ref': 'feature-branch'},
            'base': {'ref': 'main'},
            'created_at': '2023-01-15T10:30:00Z',
            'updated_at': '2023-01-15T11:00:00Z',
            'closed_at': None,
            'merged_at': None,
        }
        
        pr1, was_created = service._store_pr_in_database(self.item, pr_data, 'test-owner', 'test-repo')
        
        # Update with closed state
        pr_data['state'] = 'closed'
        pr_data['closed_at'] = '2023-01-16T12:00:00Z'
        
        pr2, was_updated = service._store_pr_in_database(self.item, pr_data, 'test-owner', 'test-repo')
        
        # Should update the same PR
        self.assertEqual(pr1.id, pr2.id)
        self.assertTrue(was_created)
        self.assertFalse(was_updated)
        self.assertEqual(pr2.state, 'closed')
        self.assertIsNotNone(pr2.closed_at_github)
    
    def test_store_pr_with_merged_state(self):
        """Test storing a merged PR sets state to 'merged'"""
        service = GitHubPRSyncService(self.settings)
        
        pr_data = {
            'number': 123,
            'title': 'Test PR',
            'body': 'Test PR body',
            'state': 'closed',
            'html_url': 'https://github.com/test-owner/test-repo/pull/123',
            'draft': False,
            'merged': True,
            'user': {'login': 'testauthor', 'avatar_url': ''},
            'head': {'ref': 'feature-branch'},
            'base': {'ref': 'main'},
            'created_at': '2023-01-15T10:30:00Z',
            'updated_at': '2023-01-15T11:00:00Z',
            'closed_at': '2023-01-16T12:00:00Z',
            'merged_at': '2023-01-16T12:00:00Z',
        }
        
        pr, was_created = service._store_pr_in_database(self.item, pr_data, 'test-owner', 'test-repo')
        
        self.assertEqual(pr.state, 'merged')
        self.assertTrue(pr.merged)
        self.assertIsNotNone(pr.merged_at)
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_pull_requests_success(self, mock_github_service_class):
        """Test successful PR synchronization"""
        service = GitHubPRSyncService(self.settings)
        
        # Mock GitHub service
        mock_github_service = Mock()
        mock_github_service_class.return_value = mock_github_service
        
        # Mock PR data from GitHub
        mock_prs = [
            {
                'number': 1,
                'title': 'PR 1',
                'body': 'Body 1',
                'state': 'open',
                'html_url': 'https://github.com/test-owner/test-repo/pull/1',
                'draft': False,
                'merged': False,
                'user': {'login': 'author1', 'avatar_url': ''},
                'head': {'ref': 'feature1'},
                'base': {'ref': 'main'},
                'created_at': '2023-01-15T10:30:00Z',
                'updated_at': '2023-01-15T11:00:00Z',
                'closed_at': None,
                'merged_at': None,
            },
            {
                'number': 2,
                'title': 'PR 2',
                'body': 'Body 2',
                'state': 'closed',
                'html_url': 'https://github.com/test-owner/test-repo/pull/2',
                'draft': False,
                'merged': True,
                'user': {'login': 'author2', 'avatar_url': ''},
                'head': {'ref': 'feature2'},
                'base': {'ref': 'main'},
                'created_at': '2023-01-14T10:30:00Z',
                'updated_at': '2023-01-15T11:00:00Z',
                'closed_at': '2023-01-15T11:00:00Z',
                'merged_at': '2023-01-15T11:00:00Z',
            }
        ]
        
        mock_github_service.list_pull_requests.return_value = {
            'success': True,
            'pull_requests': mock_prs,
            'count': 2
        }
        
        # Mock Weaviate sync
        with patch.object(service, '_sync_pr_to_weaviate', return_value=True):
            result = service.sync_pull_requests(self.item, initial_load=True)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['prs_checked'], 2)
        self.assertEqual(result['prs_created'], 2)
        self.assertEqual(result['prs_updated'], 0)
        
        # Verify PRs were stored in database
        prs = GitHubPullRequest.objects.filter(item=self.item)
        self.assertEqual(prs.count(), 2)
        
        # Verify PR 1
        pr1 = prs.get(pr_number=1)
        self.assertEqual(pr1.title, 'PR 1')
        self.assertEqual(pr1.state, 'open')
        
        # Verify PR 2 (merged)
        pr2 = prs.get(pr_number=2)
        self.assertEqual(pr2.title, 'PR 2')
        self.assertEqual(pr2.state, 'merged')
        self.assertTrue(pr2.merged)
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_pull_requests_incremental(self, mock_github_service_class):
        """Test incremental PR synchronization (last hour)"""
        service = GitHubPRSyncService(self.settings)
        
        # Mock GitHub service
        mock_github_service = Mock()
        mock_github_service_class.return_value = mock_github_service
        
        # Create PR data with different update times
        now = timezone.now()
        recent_time = now - timedelta(minutes=30)
        old_time = now - timedelta(hours=2)
        
        mock_prs = [
            {
                'number': 1,
                'title': 'Recent PR',
                'body': 'Recently updated',
                'state': 'open',
                'html_url': 'https://github.com/test-owner/test-repo/pull/1',
                'draft': False,
                'merged': False,
                'user': {'login': 'author1', 'avatar_url': ''},
                'head': {'ref': 'feature1'},
                'base': {'ref': 'main'},
                'created_at': old_time.isoformat(),
                'updated_at': recent_time.isoformat(),
                'closed_at': None,
                'merged_at': None,
            },
            {
                'number': 2,
                'title': 'Old PR',
                'body': 'Old update',
                'state': 'open',
                'html_url': 'https://github.com/test-owner/test-repo/pull/2',
                'draft': False,
                'merged': False,
                'user': {'login': 'author2', 'avatar_url': ''},
                'head': {'ref': 'feature2'},
                'base': {'ref': 'main'},
                'created_at': old_time.isoformat(),
                'updated_at': old_time.isoformat(),
                'closed_at': None,
                'merged_at': None,
            }
        ]
        
        mock_github_service.list_pull_requests.return_value = {
            'success': True,
            'pull_requests': mock_prs,
            'count': 2
        }
        
        # Mock Weaviate sync
        with patch.object(service, '_sync_pr_to_weaviate', return_value=True):
            result = service.sync_pull_requests(self.item, initial_load=False)
        
        self.assertTrue(result['success'])
        # Only the recent PR should be processed
        self.assertEqual(result['prs_checked'], 1)
        self.assertEqual(result['prs_created'], 1)
        
        # Verify only recent PR was stored
        prs = GitHubPullRequest.objects.filter(item=self.item)
        self.assertEqual(prs.count(), 1)
        self.assertEqual(prs.first().pr_number, 1)
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_pull_requests_no_repo(self, mock_github_service_class):
        """Test sync fails when item has no GitHub repo"""
        service = GitHubPRSyncService(self.settings)
        
        # Create item without GitHub repo
        item_no_repo = Item.objects.create(
            title='Item without repo',
            github_repo='',
            created_by=self.user
        )
        
        result = service.sync_pull_requests(item_no_repo)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    @patch('core.services.github_service.GitHubService')
    def test_sync_pull_requests_github_error(self, mock_github_service_class):
        """Test sync handles GitHub API errors gracefully"""
        service = GitHubPRSyncService(self.settings)
        
        # Mock GitHub service to return error
        mock_github_service = Mock()
        mock_github_service_class.return_value = mock_github_service
        
        mock_github_service.list_pull_requests.return_value = {
            'success': False,
            'error': 'API rate limit exceeded'
        }
        
        result = service.sync_pull_requests(self.item)
        
        self.assertTrue(result['success'])  # Service continues despite errors
        self.assertIn('errors', result)
        self.assertTrue(len(result['errors']) > 0)
    
    def test_model_unique_constraint(self):
        """Test GitHubPullRequest unique constraint on item/pr_number/repo"""
        # Create first PR
        pr1 = GitHubPullRequest.objects.create(
            item=self.item,
            pr_number=123,
            title='Test PR',
            state='open',
            repo_owner='test-owner',
            repo_name='test-repo',
            html_url='https://github.com/test-owner/test-repo/pull/123',
            created_at_github=timezone.now(),
            updated_at_github=timezone.now()
        )
        
        # Try to create duplicate (should fail with unique constraint)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            GitHubPullRequest.objects.create(
                item=self.item,
                pr_number=123,
                title='Duplicate PR',
                state='open',
                repo_owner='test-owner',
                repo_name='test-repo',
                html_url='https://github.com/test-owner/test-repo/pull/123',
                created_at_github=timezone.now(),
                updated_at_github=timezone.now()
            )
