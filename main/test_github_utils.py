"""
Tests for GitHub utility functions

This test file verifies the parse_github_repo function handles
various repository formats correctly.
"""

import unittest
from main.github_utils import parse_github_repo


class TestGitHubUtils(unittest.TestCase):
    """Test GitHub utility functions"""
    
    def test_parse_simple_format(self):
        """Test parsing 'owner/repo' format"""
        owner, repo = parse_github_repo('gdsanger/IdeaGraph-v1')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_https_url(self):
        """Test parsing full HTTPS GitHub URL"""
        owner, repo = parse_github_repo('https://github.com/gdsanger/IdeaGraph-v1')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_http_url(self):
        """Test parsing full HTTP GitHub URL"""
        owner, repo = parse_github_repo('http://github.com/gdsanger/IdeaGraph-v1')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_with_trailing_slash(self):
        """Test parsing URL with trailing slash"""
        owner, repo = parse_github_repo('https://github.com/gdsanger/IdeaGraph-v1/')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_with_whitespace(self):
        """Test parsing with leading/trailing whitespace"""
        owner, repo = parse_github_repo('  gdsanger/IdeaGraph-v1  ')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_without_github_prefix(self):
        """Test parsing 'github.com/owner/repo' format"""
        owner, repo = parse_github_repo('github.com/gdsanger/IdeaGraph-v1')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_with_path(self):
        """Test parsing URL with additional path components"""
        owner, repo = parse_github_repo('https://github.com/gdsanger/IdeaGraph-v1/tree/main')
        self.assertEqual(owner, 'gdsanger')
        self.assertEqual(repo, 'IdeaGraph-v1')
    
    def test_parse_just_repo_name(self):
        """Test parsing when only repo name is provided"""
        owner, repo = parse_github_repo('IdeaGraph-v1')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
    
    def test_parse_empty_string(self):
        """Test parsing empty string"""
        owner, repo = parse_github_repo('')
        self.assertIsNone(owner)
        self.assertIsNone(repo)
    
    def test_parse_none(self):
        """Test parsing None value"""
        owner, repo = parse_github_repo(None)
        self.assertIsNone(owner)
        self.assertIsNone(repo)
    
    def test_parse_org_repo(self):
        """Test parsing organization repository"""
        owner, repo = parse_github_repo('facebook/react')
        self.assertEqual(owner, 'facebook')
        self.assertEqual(repo, 'react')
    
    def test_parse_repo_with_hyphen(self):
        """Test parsing repository name with hyphens"""
        owner, repo = parse_github_repo('my-org/my-awesome-repo')
        self.assertEqual(owner, 'my-org')
        self.assertEqual(repo, 'my-awesome-repo')
    
    def test_parse_repo_with_underscore(self):
        """Test parsing repository name with underscores"""
        owner, repo = parse_github_repo('my_org/my_repo')
        self.assertEqual(owner, 'my_org')
        self.assertEqual(repo, 'my_repo')


if __name__ == '__main__':
    unittest.main()
