"""
Tests for Task Comments feature
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, TaskComment
from main.auth_utils import generate_jwt_token


class TaskCommentTestCase(TestCase):
    """Test cases for Task Comments functionality"""
    
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
        
        # Create another user for permission tests
        self.other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='user'
        )
        self.other_user.set_password('testpass123')
        self.other_user.save()
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            item=self.item,
            created_by=self.user,
            status='new'
        )
        
        # Generate JWT token
        self.token = generate_jwt_token(self.user)
        
        # Setup client
        self.client = Client()
    
    def test_create_comment(self):
        """Test creating a comment on a task"""
        url = reverse('main:api_task_comment_create', kwargs={'task_id': self.task.id})
        
        response = self.client.post(
            url,
            data=json.dumps({
                'text': 'This is a test comment',
                'source': 'user'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['comment']['text'], 'This is a test comment')
        self.assertEqual(data['comment']['source'], 'user')
        
        # Verify comment was created in database
        comment = TaskComment.objects.get(task=self.task)
        self.assertEqual(comment.text, 'This is a test comment')
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.source, 'user')
    
    def test_list_comments(self):
        """Test listing comments for a task"""
        # Create some comments
        comment1 = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='First comment',
            source='user'
        )
        comment2 = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Second comment',
            source='user'
        )
        
        url = reverse('main:api_task_comments', kwargs={'task_id': self.task.id})
        
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['comments']), 2)
        self.assertEqual(data['comments'][0]['text'], 'First comment')
        self.assertEqual(data['comments'][1]['text'], 'Second comment')
    
    def test_update_comment(self):
        """Test updating a comment"""
        # Create a comment
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Original text',
            source='user'
        )
        
        url = reverse('main:api_task_comment_update', kwargs={'comment_id': comment.id})
        
        response = self.client.put(
            url,
            data=json.dumps({
                'text': 'Updated text'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['comment']['text'], 'Updated text')
        
        # Verify in database
        comment.refresh_from_db()
        self.assertEqual(comment.text, 'Updated text')
    
    def test_update_comment_permission_denied(self):
        """Test that users cannot update other users' comments"""
        # Create a comment by user1
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Original text',
            source='user'
        )
        
        # Try to update as other_user
        other_token = generate_jwt_token(self.other_user)
        url = reverse('main:api_task_comment_update', kwargs={'comment_id': comment.id})
        
        response = self.client.put(
            url,
            data=json.dumps({
                'text': 'Hacked text'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {other_token}'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        
        # Verify text wasn't changed
        comment.refresh_from_db()
        self.assertEqual(comment.text, 'Original text')
    
    def test_delete_comment(self):
        """Test deleting a comment"""
        # Create a comment
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='To be deleted',
            source='user'
        )
        
        url = reverse('main:api_task_comment_delete', kwargs={'comment_id': comment.id})
        
        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        
        # Verify comment was deleted
        self.assertFalse(TaskComment.objects.filter(id=comment.id).exists())
    
    def test_delete_comment_permission_denied(self):
        """Test that users cannot delete other users' comments (unless admin)"""
        # Create a comment by user1
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Cannot delete this',
            source='user'
        )
        
        # Try to delete as other_user (not admin)
        other_token = generate_jwt_token(self.other_user)
        url = reverse('main:api_task_comment_delete', kwargs={'comment_id': comment.id})
        
        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=f'Bearer {other_token}'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        
        # Verify comment still exists
        self.assertTrue(TaskComment.objects.filter(id=comment.id).exists())
    
    def test_create_agent_comment(self):
        """Test creating an agent comment"""
        url = reverse('main:api_task_comment_create', kwargs={'task_id': self.task.id})
        
        response = self.client.post(
            url,
            data=json.dumps({
                'text': 'This is an agent comment',
                'source': 'agent',
                'author_name': 'AI Assistant'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['comment']['text'], 'This is an agent comment')
        self.assertEqual(data['comment']['source'], 'agent')
        
        # Verify comment was created in database
        comment = TaskComment.objects.get(task=self.task)
        self.assertEqual(comment.text, 'This is an agent comment')
        self.assertEqual(comment.author, None)
        self.assertEqual(comment.author_name, 'AI Assistant')
        self.assertEqual(comment.source, 'agent')
    
    def test_comment_requires_authentication(self):
        """Test that comment endpoints require authentication"""
        url = reverse('main:api_task_comments', kwargs={'task_id': self.task.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Authentication required')
    
    def test_create_comment_empty_text(self):
        """Test that empty comment text is rejected"""
        url = reverse('main:api_task_comment_create', kwargs={'task_id': self.task.id})
        
        response = self.client.post(
            url,
            data=json.dumps({
                'text': '   ',  # Only whitespace
                'source': 'user'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Comment text is required')
