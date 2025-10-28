"""
Test for api_user_list endpoint fix for requester dropdown
"""
from django.test import TestCase, Client
from main.models import User
import json


class ApiUserListTest(TestCase):
    """Test API user list endpoint for requester dropdown functionality"""
    
    def setUp(self):
        """Set up test users and client"""
        # Create test users
        self.admin_user = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('admin123')
        self.admin_user.save()
        
        self.regular_user = User.objects.create(
            username='regular',
            email='regular@example.com',
            role='user',
            is_active=True
        )
        self.regular_user.set_password('user123')
        self.regular_user.save()
        
        self.inactive_user = User.objects.create(
            username='inactive',
            email='inactive@example.com',
            role='user',
            is_active=False
        )
        self.inactive_user.set_password('inactive123')
        self.inactive_user.save()
        
        self.client = Client()
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access the endpoint"""
        response = self.client.get('/api/users')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Authentication required')
    
    def test_regular_user_can_access(self):
        """Test that regular users can access the endpoint (needed for requester dropdown)"""
        # Simulate session-based authentication
        session = self.client.session
        session['user_id'] = str(self.regular_user.id)
        session.save()
        
        response = self.client.get('/api/users')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('users', data)
        self.assertIn('total', data)
    
    def test_admin_user_can_access(self):
        """Test that admin users can access the endpoint"""
        # Simulate session-based authentication
        session = self.client.session
        session['user_id'] = str(self.admin_user.id)
        session.save()
        
        response = self.client.get('/api/users')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('users', data)
    
    def test_only_active_users_returned(self):
        """Test that only active users are returned in the list"""
        # Login as regular user
        session = self.client.session
        session['user_id'] = str(self.regular_user.id)
        session.save()
        
        response = self.client.get('/api/users')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        users = data['users']
        
        # Check that inactive user is not in the list
        user_ids = [u['id'] for u in users]
        self.assertNotIn(str(self.inactive_user.id), user_ids)
        
        # Check that active users are in the list
        self.assertIn(str(self.admin_user.id), user_ids)
        self.assertIn(str(self.regular_user.id), user_ids)
    
    def test_users_ordered_by_username(self):
        """Test that users are ordered by username for better UX"""
        # Create additional users to test ordering
        User.objects.create(
            username='charlie',
            email='charlie@example.com',
            role='user',
            is_active=True
        )
        User.objects.create(
            username='alice',
            email='alice@example.com',
            role='user',
            is_active=True
        )
        
        # Login as regular user
        session = self.client.session
        session['user_id'] = str(self.regular_user.id)
        session.save()
        
        response = self.client.get('/api/users')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        users = data['users']
        usernames = [u['username'] for u in users]
        
        # Check that usernames are in alphabetical order
        self.assertEqual(usernames, sorted(usernames))
        self.assertEqual(usernames[0], 'admin')  # 'admin' comes first alphabetically
        self.assertEqual(usernames[1], 'alice')
    
    def test_pagination_works(self):
        """Test that pagination parameters work correctly"""
        # Login as regular user
        session = self.client.session
        session['user_id'] = str(self.regular_user.id)
        session.save()
        
        response = self.client.get('/api/users?page=1&per_page=1')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(len(data['users']), 1)
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['per_page'], 1)
        self.assertGreaterEqual(data['total'], 2)  # At least admin and regular user
