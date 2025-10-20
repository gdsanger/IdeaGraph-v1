"""
Test for GitHub Issue display in similar tasks section.
This test validates the fixes for displaying similar GitHub issues.
"""
import json
from unittest.mock import Mock, patch
from django.test import TestCase, RequestFactory
from main.models import User, Item, Task, Section
from main.api_views import api_task_similar
from main.auth_utils import generate_jwt_token


class GitHubIssueDisplayTestCase(TestCase):
    """Test case for GitHub Issue display fixes"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('TestPassword123!')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(
            name='Test Section'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test description for finding similar tasks',
            status='new',
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        
        # Generate JWT token
        self.jwt_token = generate_jwt_token(self.user)
    
    @patch('core.services.github_issue_sync_service.GitHubIssueSyncService')
    @patch('core.services.chroma_task_sync_service.ChromaTaskSyncService')
    def test_github_issue_metadata_fields(self, mock_chroma_task_service, mock_github_sync_service):
        """Test that GitHub issue metadata uses correct field names"""
        
        # Mock ChromaTaskSyncService to return empty results
        mock_chroma_instance = Mock()
        mock_chroma_instance.search_similar.return_value = {
            'success': True,
            'results': []
        }
        mock_chroma_task_service.return_value = mock_chroma_instance
        
        # Mock GitHubIssueSyncService to return a GitHub issue with proper metadata
        mock_github_instance = Mock()
        mock_github_instance.search_similar.return_value = {
            'success': True,
            'results': [
                {
                    'id': 'issue_1',
                    'distance': 0.1,  # High similarity
                    'metadata': {
                        'github_issue_id': 42,
                        'github_issue_title': 'Test Issue Title',
                        'github_issue_state': 'open',
                        'github_issue_url': 'https://github.com/testowner/testrepo/issues/42'
                    }
                }
            ]
        }
        mock_github_instance._collection = Mock()
        mock_github_sync_service.return_value = mock_github_instance
        
        # Mock GitHubService to return current issue state
        with patch('core.services.github_service.GitHubService') as mock_github_service_class:
            mock_github_service = Mock()
            mock_github_service.get_issue.return_value = {
                'success': True,
                'issue': {
                    'state': 'closed'
                }
            }
            mock_github_service_class.return_value = mock_github_service
            
            # Make request
            request = self.factory.get(f'/api/tasks/{self.task.id}/similar')
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.jwt_token}'
            
            response = api_task_similar(request, self.task.id)
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.content)
            self.assertTrue(data.get('success'))
            
            # Verify that similar_tasks contains the GitHub issue
            similar_tasks = data.get('similar_tasks', [])
            self.assertEqual(len(similar_tasks), 1)
            
            github_issue = similar_tasks[0]
            
            # Verify the title includes owner/repo#number format
            self.assertIn('testowner/testrepo#42', github_issue['title'])
            self.assertIn('Test Issue Title', github_issue['title'])
            
            # Verify the URL is correct
            self.assertEqual(github_issue['url'], 'https://github.com/testowner/testrepo/issues/42')
            
            # Verify the status reflects the updated state from GitHub API
            self.assertEqual(github_issue['status'], 'done')
            self.assertEqual(github_issue['status_display'], 'Closed')
            
            # Verify the type is github_issue
            self.assertEqual(github_issue['type'], 'github_issue')
            
            # Verify ChromaDB was updated with the new state
            mock_github_instance._collection.update.assert_called_once()
            update_call = mock_github_instance._collection.update.call_args
            self.assertEqual(update_call[1]['ids'], ['issue_1'])
            self.assertEqual(update_call[1]['metadatas'][0]['github_issue_state'], 'closed')
    
    @patch('core.services.github_issue_sync_service.GitHubIssueSyncService')
    @patch('core.services.chroma_task_sync_service.ChromaTaskSyncService')
    def test_github_issue_without_state_update(self, mock_chroma_task_service, mock_github_sync_service):
        """Test that GitHub issue display works even if state update fails"""
        
        # Mock ChromaTaskSyncService to return empty results
        mock_chroma_instance = Mock()
        mock_chroma_instance.search_similar.return_value = {
            'success': True,
            'results': []
        }
        mock_chroma_task_service.return_value = mock_chroma_instance
        
        # Mock GitHubIssueSyncService to return a GitHub issue
        mock_github_instance = Mock()
        mock_github_instance.search_similar.return_value = {
            'success': True,
            'results': [
                {
                    'id': 'issue_2',
                    'distance': 0.15,
                    'metadata': {
                        'github_issue_id': 99,
                        'github_issue_title': 'Another Test Issue',
                        'github_issue_state': 'closed',
                        'github_issue_url': 'https://github.com/myorg/myrepo/issues/99'
                    }
                }
            ]
        }
        mock_github_instance._collection = Mock()
        mock_github_sync_service.return_value = mock_github_instance
        
        # Mock GitHubService to fail (e.g., API not configured)
        with patch('core.services.github_service.GitHubService') as mock_github_service_class:
            mock_github_service_class.side_effect = Exception('GitHub API not configured')
            
            # Make request
            request = self.factory.get(f'/api/tasks/{self.task.id}/similar')
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {self.jwt_token}'
            
            response = api_task_similar(request, self.task.id)
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.content)
            self.assertTrue(data.get('success'))
            
            # Verify that similar_tasks still contains the GitHub issue
            similar_tasks = data.get('similar_tasks', [])
            self.assertEqual(len(similar_tasks), 1)
            
            github_issue = similar_tasks[0]
            
            # Verify the title includes owner/repo#number format
            self.assertIn('myorg/myrepo#99', github_issue['title'])
            self.assertIn('Another Test Issue', github_issue['title'])
            
            # Verify the status reflects the original state (not updated)
            self.assertEqual(github_issue['status'], 'done')
            self.assertEqual(github_issue['status_display'], 'Closed')
