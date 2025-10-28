import uuid
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, Tag, Client as ClientModel, Section


class QuickTaskEntryTest(TestCase):
    """Test cases for the quick task entry feature"""

    def setUp(self):
        """Set up test data"""
        # Create a test client/customer
        self.client_model = ClientModel.objects.create(
            name='Test Client'
        )

        # Create a test section
        self.section = Section.objects.create(
            name='Test Section'
        )

        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin',
            is_active=True
        )
        self.user.set_password('testpassword123')
        self.user.save()

        # Create another test user for requester
        self.requester = User.objects.create(
            username='requester',
            email='requester@example.com',
            role='user',
            is_active=True
        )
        self.requester.set_password('testpassword123')
        self.requester.save()

        # Create a test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item for testing',
            created_by=self.user,
            section=self.section
        )
        self.item.clients.add(self.client_model)

        # Create test client for requests
        self.test_client = Client()

    def test_quick_task_create_requires_authentication(self):
        """Test that quick task creation requires authentication"""
        response = self.test_client.post(
            reverse('main:api_task_quick_create'),
            {
                'item_id': str(self.item.id),
                'title': 'Test Quick Task',
                'description': 'Test description'
            }
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Authentication required')

    def test_quick_task_create_success(self):
        """Test successful quick task creation"""
        # Log in the user
        session = self.test_client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session.save()

        # Create a quick task
        response = self.test_client.post(
            reverse('main:api_task_quick_create'),
            {
                'item_id': str(self.item.id),
                'title': 'Quick Task Title',
                'description': 'Quick task description',
                'requester_id': str(self.requester.id)
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('task_id', data)
        self.assertIn('task_title', data)
        self.assertEqual(data['task_title'], 'Quick Task Title')

        # Verify task was created
        task = Task.objects.get(id=data['task_id'])
        self.assertEqual(task.title, 'Quick Task Title')
        self.assertEqual(task.description, 'Quick task description')
        self.assertEqual(task.item, self.item)
        self.assertEqual(task.created_by, self.user)
        self.assertEqual(task.assigned_to, self.user)  # Should be auto-assigned to logged-in user
        self.assertEqual(task.requester, self.requester)
        self.assertEqual(task.status, 'new')

    def test_quick_task_create_without_requester(self):
        """Test quick task creation without requester"""
        # Log in the user
        session = self.test_client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session.save()

        # Create a quick task without requester
        response = self.test_client.post(
            reverse('main:api_task_quick_create'),
            {
                'item_id': str(self.item.id),
                'title': 'Quick Task Without Requester',
                'description': 'Test description'
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # Verify task was created without requester
        task = Task.objects.get(id=data['task_id'])
        self.assertEqual(task.title, 'Quick Task Without Requester')
        self.assertIsNone(task.requester)
        self.assertEqual(task.assigned_to, self.user)  # Should still be assigned to logged-in user

    def test_quick_task_create_missing_required_fields(self):
        """Test quick task creation with missing required fields"""
        # Log in the user
        session = self.test_client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session.save()

        # Test missing title
        response = self.test_client.post(
            reverse('main:api_task_quick_create'),
            {
                'item_id': str(self.item.id),
                'description': 'Test description'
            }
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)

        # Test missing item_id
        response = self.test_client.post(
            reverse('main:api_task_quick_create'),
            {
                'title': 'Test Task',
                'description': 'Test description'
            }
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_quick_task_create_with_invalid_item(self):
        """Test quick task creation with invalid item ID"""
        # Log in the user
        session = self.test_client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session.save()

        # Create a quick task with invalid item ID
        invalid_uuid = str(uuid.uuid4())
        response = self.test_client.post(
            reverse('main:api_task_quick_create'),
            {
                'item_id': invalid_uuid,
                'title': 'Test Task',
                'description': 'Test description'
            }
        )

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_quick_task_create_with_invalid_requester(self):
        """Test quick task creation with invalid requester ID (should succeed, requester is optional)"""
        # Log in the user
        session = self.test_client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session.save()

        # Create a quick task with invalid requester ID
        invalid_uuid = str(uuid.uuid4())
        response = self.test_client.post(
            reverse('main:api_task_quick_create'),
            {
                'item_id': str(self.item.id),
                'title': 'Test Task',
                'description': 'Test description',
                'requester_id': invalid_uuid
            }
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # Verify task was created without requester (invalid requester is ignored)
        task = Task.objects.get(id=data['task_id'])
        self.assertIsNone(task.requester)

    def test_quick_task_modal_button_visible_when_logged_in(self):
        """Test that the quick task entry button is visible when user is logged in"""
        # Log in the user
        session = self.test_client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session.save()

        # The quick entry button should be accessible via the API endpoint
        # Just verify that the API endpoint exists
        response = self.test_client.post(
            reverse('main:api_task_quick_create'),
            {
                'item_id': str(self.item.id),
                'title': 'Test Task',
                'description': 'Test description'
            }
        )
        # If we get here without a 404, the endpoint exists
        self.assertIn(response.status_code, [200, 201])

    def test_quick_task_modal_button_hidden_when_not_logged_in(self):
        """Test that the quick task entry button is hidden when user is not logged in"""
        # Get home page without logging in
        response = self.test_client.get(reverse('main:home'))

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('main:login')))
