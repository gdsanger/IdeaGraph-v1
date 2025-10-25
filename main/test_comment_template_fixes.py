"""
Tests for comment template timestamp and JavaScript fixes
"""
from django.test import TestCase, RequestFactory
from django.utils import timezone
from datetime import datetime
from main.models import User, Item, Task, TaskComment
from main.api_views import api_task_comments


class CommentTemplateFixes(TestCase):
    """Test cases for comment timestamp display and JavaScript fixes"""
    
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
            status='working'
        )
        
        # Create test comment
        self.comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Test comment text',
            source='user'
        )
        
        self.factory = RequestFactory()
    
    def test_htmx_request_returns_datetime_objects(self):
        """Test that htmx requests receive datetime objects for proper template rendering"""
        request = self.factory.get(f'/api/tasks/{self.task.id}/comments')
        request.headers = {'HX-Request': 'true'}
        
        # Mock authentication
        from unittest.mock import patch
        with patch('main.api_views.get_user_from_request', return_value=self.user):
            response = api_task_comments(request, str(self.task.id))
        
        # Response should be HTML (200 status)
        self.assertEqual(response.status_code, 200)
        
        # Check that response contains formatted timestamp
        content = response.content.decode('utf-8')
        
        # The timestamp should be formatted as "dd.mm.YYYY HH:MM"
        # Check that it contains date formatting elements
        self.assertIn('comment-meta', content)
        
        # Verify the template rendered successfully (contains comment structure)
        self.assertIn('comment-card', content)
        self.assertIn('Test comment text', content)
        self.assertIn(self.user.username, content)
    
    def test_json_request_returns_iso_strings(self):
        """Test that regular API requests receive ISO formatted strings"""
        request = self.factory.get(f'/api/tasks/{self.task.id}/comments')
        request.headers = {}
        
        # Mock authentication
        from unittest.mock import patch
        with patch('main.api_views.get_user_from_request', return_value=self.user):
            response = api_task_comments(request, str(self.task.id))
        
        # Response should be JSON
        self.assertEqual(response.status_code, 200)
        
        import json
        data = json.loads(response.content)
        
        # Check that response contains comments
        self.assertTrue(data['success'])
        self.assertEqual(len(data['comments']), 1)
        
        # Check that timestamps are ISO strings
        comment_data = data['comments'][0]
        self.assertIn('created_at', comment_data)
        self.assertIn('updated_at', comment_data)
        
        # Verify ISO format (contains 'T' separator)
        self.assertIn('T', comment_data['created_at'])
        self.assertIn('T', comment_data['updated_at'])
    
    def test_javascript_iife_prevents_redeclaration(self):
        """Test that the template contains JavaScript wrapped in IIFE"""
        request = self.factory.get(f'/api/tasks/{self.task.id}/comments')
        request.headers = {'HX-Request': 'true'}
        
        # Mock authentication
        from unittest.mock import patch
        with patch('main.api_views.get_user_from_request', return_value=self.user):
            response = api_task_comments(request, str(self.task.id))
        
        content = response.content.decode('utf-8')
        
        # Check that JavaScript is wrapped in IIFE
        self.assertIn('(function() {', content)
        self.assertIn('MAX_LINES_COLLAPSED', content)
        self.assertIn('})();', content)
        
        # Verify that MAX_LINES_COLLAPSED is within the IIFE (not at global scope)
        # Find the IIFE start and end positions
        iife_start = content.find('(function() {')
        iife_end = content.find('})();', iife_start)
        max_lines_pos = content.find('MAX_LINES_COLLAPSED', iife_start)
        
        # MAX_LINES_COLLAPSED should be within the IIFE boundaries
        self.assertGreater(max_lines_pos, iife_start)
        self.assertLess(max_lines_pos, iife_end)
