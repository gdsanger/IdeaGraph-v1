"""
Test GitHub Issue ID editing functionality
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from main.models import User, Item, Task, Section


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
)
class GitHubIssueIDEditTest(TestCase):
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
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description',
            github_repo='testuser/testrepo',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task without github_issue_id
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            created_by=self.user
        )
        
        self.client = Client()
    
    def login(self):
        """Helper to log in the test user"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_add_github_issue_id(self):
        """Test adding a GitHub Issue ID to a task"""
        self.login()
        url = reverse('main:task_detail', args=[self.task.id])
        
        # Initially, the task has no github_issue_id
        self.assertIsNone(self.task.github_issue_id)
        
        # POST request to add GitHub Issue ID
        response = self.client.post(url, {
            'title': self.task.title,
            'description': self.task.description,
            'status': self.task.status,
            'type': self.task.type,
            'github_issue_id': '123'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify github_issue_id was added
        self.task.refresh_from_db()
        self.assertEqual(self.task.github_issue_id, 123)
    
    def test_update_github_issue_id(self):
        """Test updating an existing GitHub Issue ID"""
        self.login()
        
        # Set initial github_issue_id
        self.task.github_issue_id = 100
        self.task.save()
        
        url = reverse('main:task_detail', args=[self.task.id])
        
        # POST request to update GitHub Issue ID
        response = self.client.post(url, {
            'title': self.task.title,
            'description': self.task.description,
            'status': self.task.status,
            'type': self.task.type,
            'github_issue_id': '456'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify github_issue_id was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.github_issue_id, 456)
    
    def test_remove_github_issue_id(self):
        """Test removing a GitHub Issue ID from a task"""
        self.login()
        
        # Set initial github_issue_id
        self.task.github_issue_id = 100
        self.task.save()
        
        url = reverse('main:task_detail', args=[self.task.id])
        
        # POST request with empty github_issue_id
        response = self.client.post(url, {
            'title': self.task.title,
            'description': self.task.description,
            'status': self.task.status,
            'type': self.task.type,
            'github_issue_id': ''
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify github_issue_id was removed
        self.task.refresh_from_db()
        self.assertIsNone(self.task.github_issue_id)
    
    def test_invalid_github_issue_id(self):
        """Test handling of invalid GitHub Issue ID"""
        self.login()
        url = reverse('main:task_detail', args=[self.task.id])
        
        # POST request with invalid github_issue_id (non-numeric)
        response = self.client.post(url, {
            'title': self.task.title,
            'description': self.task.description,
            'status': self.task.status,
            'type': self.task.type,
            'github_issue_id': 'invalid'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Verify a warning message was added
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any('Invalid GitHub Issue ID' in str(msg) for msg in messages),
            "Expected warning message about invalid GitHub Issue ID"
        )
        
        # Verify github_issue_id was not changed
        self.task.refresh_from_db()
        self.assertIsNone(self.task.github_issue_id)

