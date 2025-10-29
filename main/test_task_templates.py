"""
Test TaskTemplate and Task Cloning functionality
"""
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, TaskTemplate, Tag, Section
import json


class TaskTemplateTest(TestCase):
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
        
        # Create test tags
        self.tag1 = Tag.objects.create(name='test-tag-1', color='#3b82f6')
        self.tag2 = Tag.objects.create(name='test-tag-2', color='#10b981')
        
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
            item=self.item,
            created_by=self.user,
            assigned_to=self.user
        )
        self.task.tags.add(self.tag1, self.tag2)
        
        # Create client
        self.client = Client()
    
    def login(self):
        """Helper to log in the test user"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_save_task_as_template(self):
        """Test saving a task as a template"""
        self.login()
        
        url = reverse('main:task_save_as_template', args=[self.task.id])
        data = {
            'title': 'Test Template',
            'include_description': True,
            'include_tags': True,
            'include_assignees': False,
            'include_checklist': False
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        # Check template was created
        template = TaskTemplate.objects.get(id=result['template_id'])
        self.assertEqual(template.title, 'Test Template')
        self.assertEqual(template.description, self.task.description)
        self.assertEqual(template.created_by, self.user)
        self.assertEqual(template.tags.count(), 2)
    
    def test_save_template_without_tags(self):
        """Test saving a template without tags"""
        self.login()
        
        url = reverse('main:task_save_as_template', args=[self.task.id])
        data = {
            'title': 'Template Without Tags',
            'include_description': True,
            'include_tags': False,
            'include_assignees': False,
            'include_checklist': False
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        template = TaskTemplate.objects.get(id=result['template_id'])
        self.assertEqual(template.tags.count(), 0)
    
    def test_save_template_requires_title(self):
        """Test that template title is required"""
        self.login()
        
        url = reverse('main:task_save_as_template', args=[self.task.id])
        data = {
            'title': '',
            'include_description': True,
            'include_tags': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        result = json.loads(response.content)
        self.assertFalse(result['success'])
    
    def test_clone_task(self):
        """Test cloning a task to another item"""
        self.login()
        
        # Create target item
        target_item = Item.objects.create(
            title='Target Item',
            description='Target item description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        url = reverse('main:task_clone', args=[self.task.id])
        data = {
            'target_item_id': str(target_item.id),
            'title_prefix': 'Kopie von ',
            'include_description': True,
            'include_tags': True,
            'include_assignees': True,
            'include_comments': False
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        # Check cloned task was created
        cloned_task = Task.objects.get(id=result['task_id'])
        self.assertEqual(cloned_task.title, f"Kopie von {self.task.title}")
        self.assertEqual(cloned_task.description, self.task.description)
        self.assertEqual(cloned_task.item, target_item)
        self.assertEqual(cloned_task.status, 'new')
        self.assertEqual(cloned_task.assigned_to, self.task.assigned_to)
        self.assertEqual(cloned_task.tags.count(), 2)
    
    def test_clone_task_without_description(self):
        """Test cloning a task without description"""
        self.login()
        
        target_item = Item.objects.create(
            title='Target Item',
            description='Target item description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        url = reverse('main:task_clone', args=[self.task.id])
        data = {
            'target_item_id': str(target_item.id),
            'title_prefix': 'Clone: ',
            'include_description': False,
            'include_tags': False,
            'include_assignees': False,
            'include_comments': False
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        
        cloned_task = Task.objects.get(id=result['task_id'])
        self.assertEqual(cloned_task.description, '')
        self.assertEqual(cloned_task.tags.count(), 0)
        self.assertIsNone(cloned_task.assigned_to)
    
    def test_clone_task_requires_target_item(self):
        """Test that target item is required for cloning"""
        self.login()
        
        url = reverse('main:task_clone', args=[self.task.id])
        data = {
            'target_item_id': '',
            'title_prefix': 'Copy: ',
            'include_description': True,
            'include_tags': True
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        result = json.loads(response.content)
        self.assertFalse(result['success'])
    
    def test_api_task_template_list(self):
        """Test API endpoint for listing templates"""
        self.login()
        
        # Create test templates
        template1 = TaskTemplate.objects.create(
            title='Template 1',
            description='Description 1',
            created_by=self.user
        )
        template1.tags.add(self.tag1)
        
        template2 = TaskTemplate.objects.create(
            title='Template 2',
            description='Description 2',
            created_by=self.user
        )
        
        url = reverse('main:api_task_template_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['templates']), 2)
        
        # Check template data
        template_titles = [t['title'] for t in result['templates']]
        self.assertIn('Template 1', template_titles)
        self.assertIn('Template 2', template_titles)
    
    def test_task_create_with_template(self):
        """Test creating a task from a template"""
        self.login()
        
        # Create template
        template = TaskTemplate.objects.create(
            title='Bug Fix Template',
            description='Bug fix description template',
            created_by=self.user
        )
        template.tags.add(self.tag1)
        
        # Get task creation form with template
        url = reverse('main:task_create', args=[self.item.id])
        response = self.client.get(url + f'?template_id={template.id}')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bug Fix Template')
        
        # Create task from form
        response = self.client.post(url, {
            'title': 'New Bug Fix',
            'description': template.description,
            'status': 'new',
            'tags': [str(self.tag1.id)],
        })
        
        # Should redirect to task detail
        self.assertEqual(response.status_code, 302)
        
        # Check task was created with template values
        task = Task.objects.filter(title='New Bug Fix').first()
        self.assertIsNotNone(task)
        self.assertEqual(task.description, template.description)
    
    def test_template_permissions(self):
        """Test that users can only access their own templates or admin/developer templates"""
        # Create another user
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='user',
            is_active=True
        )
        other_user.set_password('testpass123')
        other_user.save()
        
        # Create template as first user
        self.login()
        template = TaskTemplate.objects.create(
            title='Private Template',
            description='Private description',
            created_by=self.user
        )
        
        # Login as other user
        session = self.client.session
        session['user_id'] = str(other_user.id)
        session.save()
        
        # Try to access API - should only see admin/developer templates (none in this case)
        url = reverse('main:api_task_template_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.content)
        self.assertTrue(result['success'])
        # Other user shouldn't see the template created by first user
        self.assertEqual(len(result['templates']), 0)
