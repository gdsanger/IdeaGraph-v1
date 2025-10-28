"""
Test Task Close functionality
"""
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, Section, Settings
import json


class TaskCloseTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create requester user
        self.requester = User.objects.create(
            username='requester',
            email='requester@example.com',
            role='user',
            is_active=True
        )
        self.requester.set_password('testpass123')
        self.requester.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            type='feature',
            item=self.item,
            created_by=self.user,
            requester=self.requester
        )
        
        # Create settings for testing
        self.settings = Settings.objects.create(
            openai_api_enabled=False,
            kigate_api_enabled=False
        )
        
        # Create test client
        self.client = Client()
        
    def test_close_task_no_email(self):
        """Test closing task without sending email"""
        # Log in
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        url = reverse('main:api_task_close', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            data=json.dumps({'close_type': 'no_email'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(data['email_sent'])
        
        # Verify task is marked as done
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'done')
        self.assertIsNotNone(self.task.completed_at)
    
    def test_close_task_success_type(self):
        """Test closing task with success type (without actual email sending)"""
        # Log in
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        url = reverse('main:api_task_close', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            data=json.dumps({'close_type': 'success'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify task is marked as done
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'done')
        self.assertIsNotNone(self.task.completed_at)
    
    def test_close_task_next_update_type(self):
        """Test closing task with next_update type"""
        # Log in
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        url = reverse('main:api_task_close', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            data=json.dumps({'close_type': 'next_update'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify task is marked as done
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'done')
        self.assertIsNotNone(self.task.completed_at)
    
    def test_close_task_without_authentication(self):
        """Test that closing task requires authentication"""
        url = reverse('main:api_task_close', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            data=json.dumps({'close_type': 'no_email'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_close_task_invalid_close_type(self):
        """Test that invalid close_type is rejected"""
        # Log in
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        url = reverse('main:api_task_close', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            data=json.dumps({'close_type': 'invalid'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_close_task_without_close_type(self):
        """Test that close_type is required"""
        # Log in
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        url = reverse('main:api_task_close', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_close_task_nonexistent(self):
        """Test closing a nonexistent task"""
        # Log in
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        # Use a random UUID that doesn't exist
        from uuid import uuid4
        fake_id = uuid4()
        url = reverse('main:api_task_close', kwargs={'task_id': fake_id})
        response = self.client.post(
            url,
            data=json.dumps({'close_type': 'no_email'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_close_task_without_requester(self):
        """Test closing task without a requester (should work with no_email)"""
        # Create task without requester
        task_no_requester = Task.objects.create(
            title='Test Task No Requester',
            description='Test task without requester',
            status='new',
            type='feature',
            item=self.item,
            created_by=self.user,
            requester=None
        )
        
        # Log in
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        url = reverse('main:api_task_close', kwargs={'task_id': task_no_requester.id})
        response = self.client.post(
            url,
            data=json.dumps({'close_type': 'no_email'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(data['email_sent'])
        
        # Verify task is marked as done
        task_no_requester.refresh_from_db()
        self.assertEqual(task_no_requester.status, 'done')
    
    def test_close_already_done_task(self):
        """Test closing a task that's already done"""
        # Mark task as done first
        self.task.mark_as_done()
        
        # Log in
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        url = reverse('main:api_task_close', kwargs={'task_id': self.task.id})
        response = self.client.post(
            url,
            data=json.dumps({'close_type': 'no_email'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify task is still marked as done
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'done')
