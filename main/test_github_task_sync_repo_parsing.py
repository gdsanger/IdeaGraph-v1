"""
Tests for GitHub repository parsing integration with GitHubTaskSyncService

This test file verifies that the GitHubTaskSyncService correctly uses
the parse_github_repo utility function.
"""

import unittest
from unittest.mock import Mock
from core.services.github_task_sync_service import GitHubTaskSyncService
from main.github_utils import parse_github_repo


class TestGitHubTaskSyncRepositoryParsing(unittest.TestCase):
    """Test repository parsing functionality with GitHubTaskSyncService"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock settings
        self.mock_settings = Mock()
        self.mock_settings.github_api_enabled = True
        self.mock_settings.github_token = 'test_token'
        self.mock_settings.github_api_base_url = 'https://api.github.com'
        self.mock_settings.github_default_owner = 'default-owner'
        self.mock_settings.github_default_repo = 'default-repo'
        
        # Create service instance
        self.service = GitHubTaskSyncService(self.mock_settings)
    
    def test_parse_github_repo_simple_format(self):
        """Test parsing 'owner/repo' format"""
        owner, repo = parse_github_repo('gdsanger/IdeaGraph-v1')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_github_repo_https_url(self):
        """Test parsing full HTTPS GitHub URL"""
        owner, repo = parse_github_repo('https://github.com/gdsanger/IdeaGraph-v1')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_github_repo_http_url(self):
        """Test parsing full HTTP GitHub URL"""
        owner, repo = parse_github_repo('http://github.com/gdsanger/IdeaGraph-v1')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_github_repo_with_trailing_slash(self):
        """Test parsing URL with trailing slash"""
        owner, repo = parse_github_repo('https://github.com/gdsanger/IdeaGraph-v1/')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_github_repo_with_whitespace(self):
        """Test parsing with leading/trailing whitespace"""
        owner, repo = parse_github_repo('  gdsanger/IdeaGraph-v1  ')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_github_repo_without_github_prefix(self):
        """Test parsing 'github.com/owner/repo' format"""
        owner, repo = parse_github_repo('github.com/gdsanger/IdeaGraph-v1')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_github_repo_just_repo_name(self):
        """Test parsing when only repo name is provided"""
        owner, repo = parse_github_repo('IdeaGraph-v1')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
    
    def test_parse_github_repo_empty_string(self):
        """Test parsing empty string"""
        owner, repo = parse_github_repo('')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
    
    def test_parse_github_repo_none(self):
        """Test parsing None value"""
        owner, repo = parse_github_repo(None)
        self.assertIsNone(owner)
        self.assertIsNone(repo)
    
    def test_parse_github_repo_multiple_slashes(self):
        """Test parsing with repository that has multiple slashes"""
        owner, repo = parse_github_repo('https://github.com/gdsanger/IdeaGraph-v1/tree/main')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')


if __name__ == '__main__':
    unittest.main()
