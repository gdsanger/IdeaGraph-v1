"""
Tests for GitHub Issue Comment Integration
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from main.models import User, Item, Task, TaskComment
from main.auth_utils import generate_jwt_token
from core.services.task_comment_service import TaskCommentService


class GitHubIssueCommentTestCase(TestCase):
    """Test cases for GitHub Issue comment creation"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create Settings for GitHub API
        from main.models import Settings
        self.settings = Settings.objects.create(
            github_api_enabled=True,
            github_token='test_token_12345'
        )
        
        # Create test item with GitHub repo
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            created_by=self.user,
            github_repo='testowner/testrepo'
        )
        
        # Create test task in ready status
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            item=self.item,
            created_by=self.user,
            status='ready'
        )
        
        # Generate JWT token
        self.token = generate_jwt_token(self.user)
        
        # Setup client
        self.client = Client()
    
    def test_ai_agent_bot_creation(self):
        """Test that AI Agent Bot user is created properly"""
        bot_user = TaskCommentService.get_or_create_ai_agent_bot()
        
        self.assertIsNotNone(bot_user)
        self.assertEqual(bot_user.username, TaskCommentService.AI_AGENT_BOT_USERNAME)
        self.assertEqual(bot_user.email, TaskCommentService.AI_AGENT_BOT_EMAIL)
        self.assertIsNotNone(bot_user.avatar_url)
        
        # Test that calling again returns same user
        bot_user2 = TaskCommentService.get_or_create_ai_agent_bot()
        self.assertEqual(bot_user.id, bot_user2.id)
    
    def test_create_github_issue_created_comment(self):
        """Test creating a comment when GitHub issue is created"""
        issue_number = 123
        issue_url = 'https://github.com/testowner/testrepo/issues/123'
        
        # Create comment
        comment = TaskCommentService.create_github_issue_created_comment(
            task=self.task,
            issue_number=issue_number,
            issue_url=issue_url
        )
        
        # Verify comment was created
        self.assertIsNotNone(comment)
        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.source, 'agent')
        self.assertIn(str(issue_number), comment.text)
        self.assertIn(issue_url, comment.text)
        self.assertIn('GitHub Issue Created', comment.text)
        
        # Verify bot user is the author
        self.assertEqual(comment.author.username, TaskCommentService.AI_AGENT_BOT_USERNAME)
        self.assertEqual(comment.author_name, TaskCommentService.AI_AGENT_BOT_NAME)
    
    def test_create_github_issue_completed_comment(self):
        """Test creating a comment when GitHub issue is completed"""
        issue_number = 456
        
        # Create comment
        comment = TaskCommentService.create_github_issue_completed_comment(
            task=self.task,
            issue_number=issue_number
        )
        
        # Verify comment was created
        self.assertIsNotNone(comment)
        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.source, 'agent')
        self.assertIn(str(issue_number), comment.text)
        self.assertIn('GitHub Issue Completed', comment.text)
        self.assertIn('closed', comment.text.lower())
        
        # Verify bot user is the author
        self.assertEqual(comment.author.username, TaskCommentService.AI_AGENT_BOT_USERNAME)
        self.assertEqual(comment.author_name, TaskCommentService.AI_AGENT_BOT_NAME)
    
    @patch('core.services.github_service.GitHubService.create_issue')
    @patch('core.services.github_service.GitHubService.create_issue_comment')
    def test_github_issue_creation_creates_comment(self, mock_create_comment, mock_create_issue):
        """Test that creating a GitHub issue also creates a task comment"""
        # Mock GitHub service responses
        mock_create_issue.return_value = {
            'success': True,
            'issue_number': 789,
            'url': 'https://github.com/testowner/testrepo/issues/789'
        }
        mock_create_comment.return_value = {
            'success': True
        }
        
        # Create GitHub issue via API
        url = reverse('main:api_task_create_github_issue', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['issue_number'], 789)
        
        # Verify task was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.github_issue_id, 789)
        self.assertIsNotNone(self.task.github_issue_url)
        
        # Verify comment was created
        comments = TaskComment.objects.filter(task=self.task, source='agent')
        self.assertEqual(comments.count(), 1)
        
        comment = comments.first()
        self.assertIn('789', comment.text)
        self.assertIn('GitHub Issue Created', comment.text)
    
    def test_multiple_comments_on_same_task(self):
        """Test that multiple GitHub-related comments can be added to the same task"""
        # Create first comment (issue created)
        comment1 = TaskCommentService.create_github_issue_created_comment(
            task=self.task,
            issue_number=111,
            issue_url='https://github.com/testowner/testrepo/issues/111'
        )
        
        # Create second comment (issue completed)
        comment2 = TaskCommentService.create_github_issue_completed_comment(
            task=self.task,
            issue_number=111
        )
        
        # Verify both comments exist
        comments = TaskComment.objects.filter(task=self.task, source='agent')
        self.assertEqual(comments.count(), 2)
        
        # Verify they have different content
        self.assertNotEqual(comment1.text, comment2.text)
        self.assertIn('Created', comment1.text)
        self.assertIn('Completed', comment2.text)
