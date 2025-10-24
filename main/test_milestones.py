from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
from main.models import User, Item, Milestone, Task, MilestoneContextObject


class MilestoneModelTest(TestCase):
    """Test Milestone model"""
    
    def setUp(self):
        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create a test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            created_by=self.user
        )
    
    def test_milestone_creation(self):
        """Test creating a milestone"""
        milestone = Milestone.objects.create(
            name='Version 1.0',
            due_date=date.today() + timedelta(days=30),
            item=self.item
        )
        
        self.assertEqual(milestone.name, 'Version 1.0')
        self.assertEqual(milestone.item, self.item)
        self.assertIsNotNone(milestone.id)
        self.assertEqual(milestone.status, 'planned')  # Default status
    
    def test_milestone_with_new_fields(self):
        """Test creating a milestone with new knowledge hub fields"""
        milestone = Milestone.objects.create(
            name='Knowledge Hub Test',
            description='Test description for knowledge hub',
            due_date=date.today() + timedelta(days=30),
            status='in_progress',
            summary='AI-generated summary',
            item=self.item
        )
        
        self.assertEqual(milestone.description, 'Test description for knowledge hub')
        self.assertEqual(milestone.status, 'in_progress')
        self.assertEqual(milestone.summary, 'AI-generated summary')
        self.assertIsNone(milestone.weaviate_id)
    
    def test_milestone_ordering(self):
        """Test that milestones are ordered by due_date"""
        milestone1 = Milestone.objects.create(
            name='Later Milestone',
            due_date=date.today() + timedelta(days=60),
            item=self.item
        )
        milestone2 = Milestone.objects.create(
            name='Earlier Milestone',
            due_date=date.today() + timedelta(days=30),
            item=self.item
        )
        
        milestones = list(self.item.milestones.all())
        self.assertEqual(milestones[0], milestone2)
        self.assertEqual(milestones[1], milestone1)
    
    def test_task_milestone_relationship(self):
        """Test that tasks can be associated with milestones"""
        milestone = Milestone.objects.create(
            name='Version 1.0',
            due_date=date.today() + timedelta(days=30),
            item=self.item
        )
        
        task = Task.objects.create(
            title='Test Task',
            description='Test description',
            item=self.item,
            milestone=milestone,
            created_by=self.user
        )
        
        self.assertEqual(task.milestone, milestone)
        self.assertEqual(milestone.tasks.count(), 1)
        self.assertEqual(milestone.tasks.first(), task)


class MilestoneContextObjectModelTest(TestCase):
    """Test MilestoneContextObject model"""
    
    def setUp(self):
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
            description='Test description',
            created_by=self.user
        )
        
        # Create test milestone
        self.milestone = Milestone.objects.create(
            name='Test Milestone',
            due_date=date.today() + timedelta(days=30),
            item=self.item
        )
    
    def test_context_object_creation(self):
        """Test creating a context object"""
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='file',
            title='Test Document',
            content='Test content',
            uploaded_by=self.user
        )
        
        self.assertEqual(context.milestone, self.milestone)
        self.assertEqual(context.type, 'file')
        self.assertEqual(context.title, 'Test Document')
        self.assertEqual(context.content, 'Test content')
        self.assertFalse(context.analyzed)
        self.assertEqual(context.derived_tasks, [])
    
    def test_context_object_types(self):
        """Test different context object types"""
        types = ['file', 'email', 'transcript', 'note']
        
        for ctx_type in types:
            context = MilestoneContextObject.objects.create(
                milestone=self.milestone,
                type=ctx_type,
                title=f'Test {ctx_type}',
                uploaded_by=self.user
            )
            self.assertEqual(context.type, ctx_type)
    
    def test_context_object_with_derived_tasks(self):
        """Test context object with derived tasks"""
        derived_tasks = [
            {'title': 'Task 1', 'description': 'Description 1'},
            {'title': 'Task 2', 'description': 'Description 2'}
        ]
        
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='transcript',
            title='Meeting Transcript',
            content='Meeting content',
            summary='Meeting summary',
            derived_tasks=derived_tasks,
            analyzed=True,
            uploaded_by=self.user
        )
        
        self.assertTrue(context.analyzed)
        self.assertEqual(len(context.derived_tasks), 2)
        self.assertEqual(context.derived_tasks[0]['title'], 'Task 1')
    
    def test_milestone_context_objects_relationship(self):
        """Test relationship between milestone and context objects"""
        context1 = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='file',
            title='Document 1',
            uploaded_by=self.user
        )
        
        context2 = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='email',
            title='Email 1',
            uploaded_by=self.user
        )
        
        self.assertEqual(self.milestone.context_objects.count(), 2)
        self.assertIn(context1, self.milestone.context_objects.all())
        self.assertIn(context2, self.milestone.context_objects.all())


class MilestoneViewTest(TestCase):
    """Test Milestone views"""
    
    def setUp(self):
        self.client = Client()
        
        # Create a test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create a test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            created_by=self.user
        )
        
        # Log in the user
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_milestone_create_view_get(self):
        """Test milestone create view GET"""
        response = self.client.get(
            reverse('main:milestone_create', kwargs={'item_id': self.item.id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Milestone')
        self.assertContains(response, 'Name')
        self.assertContains(response, 'Due Date')
    
    def test_milestone_create_view_post(self):
        """Test milestone creation via POST with new fields"""
        response = self.client.post(
            reverse('main:milestone_create', kwargs={'item_id': self.item.id}),
            {
                'name': 'Test Milestone',
                'description': 'Test description',
                'due_date': (date.today() + timedelta(days=30)).isoformat(),
                'status': 'planned',
            }
        )
        
        # Should redirect to item detail
        self.assertEqual(response.status_code, 302)
        
        # Check milestone was created
        self.assertEqual(Milestone.objects.count(), 1)
        milestone = Milestone.objects.first()
        self.assertEqual(milestone.name, 'Test Milestone')
        self.assertEqual(milestone.description, 'Test description')
        self.assertEqual(milestone.status, 'planned')
        self.assertEqual(milestone.item, self.item)
    
    def test_milestone_edit_view(self):
        """Test milestone edit view with new fields"""
        milestone = Milestone.objects.create(
            name='Test Milestone',
            description='Original description',
            due_date=date.today() + timedelta(days=30),
            status='planned',
            item=self.item
        )
        
        response = self.client.post(
            reverse('main:milestone_edit', kwargs={'milestone_id': milestone.id}),
            {
                'name': 'Updated Milestone',
                'description': 'Updated description',
                'due_date': (date.today() + timedelta(days=60)).isoformat(),
                'status': 'in_progress',
            }
        )
        
        # Should redirect to item detail
        self.assertEqual(response.status_code, 302)
        
        # Check milestone was updated
        milestone.refresh_from_db()
        self.assertEqual(milestone.name, 'Updated Milestone')
        self.assertEqual(milestone.description, 'Updated description')
        self.assertEqual(milestone.status, 'in_progress')
    
    def test_milestone_delete_view(self):
        """Test milestone delete view"""
        milestone = Milestone.objects.create(
            name='Test Milestone',
            due_date=date.today() + timedelta(days=30),
            item=self.item
        )
        
        response = self.client.post(
            reverse('main:milestone_delete', kwargs={'milestone_id': milestone.id})
        )
        
        # Should redirect to item detail
        self.assertEqual(response.status_code, 302)
        
        # Check milestone was deleted
        self.assertEqual(Milestone.objects.count(), 0)
    
    def test_milestones_tab_in_item_detail(self):
        """Test that milestones tab appears in item detail"""
        milestone = Milestone.objects.create(
            name='Test Milestone',
            due_date=date.today() + timedelta(days=30),
            item=self.item
        )
        
        response = self.client.get(
            reverse('main:item_detail', kwargs={'item_id': self.item.id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Milestones')
        self.assertContains(response, 'Test Milestone')
    
    def test_task_form_includes_milestone_field(self):
        """Test that task form includes milestone selection"""
        milestone = Milestone.objects.create(
            name='Test Milestone',
            due_date=date.today() + timedelta(days=30),
            item=self.item
        )
        
        response = self.client.get(
            reverse('main:task_create', kwargs={'item_id': self.item.id})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Milestone')
        self.assertContains(response, 'Test Milestone')
    
    def test_milestone_edit_with_summary_and_tasks(self):
        """Test milestone edit with summary field and task list generation"""
        milestone = Milestone.objects.create(
            name='Test Milestone',
            description='Test description',
            due_date=date.today() + timedelta(days=30),
            status='planned',
            item=self.item
        )
        
        # Create some tasks associated with this milestone
        task1 = Task.objects.create(
            title='Task 1',
            description='First task',
            item=self.item,
            milestone=milestone,
            created_by=self.user
        )
        task2 = Task.objects.create(
            title='Task 2',
            description='Second task',
            item=self.item,
            milestone=milestone,
            created_by=self.user
        )
        
        # Edit the milestone with a summary
        response = self.client.post(
            reverse('main:milestone_edit', kwargs={'milestone_id': milestone.id}),
            {
                'name': 'Updated Milestone',
                'description': 'Updated description',
                'due_date': (date.today() + timedelta(days=60)).isoformat(),
                'status': 'in_progress',
                'summary': 'This is a test summary'
            }
        )
        
        # Should redirect to item detail
        self.assertEqual(response.status_code, 302)
        
        # Check milestone was updated with summary and task list
        milestone.refresh_from_db()
        self.assertEqual(milestone.name, 'Updated Milestone')
        self.assertIn('This is a test summary', milestone.summary)
        self.assertIn('Aufgaben:', milestone.summary)
        self.assertIn('- Task 1', milestone.summary)
        self.assertIn('- Task 2', milestone.summary)
    
    def test_milestone_create_with_summary(self):
        """Test milestone creation with summary field"""
        response = self.client.post(
            reverse('main:milestone_create', kwargs={'item_id': self.item.id}),
            {
                'name': 'Test Milestone',
                'description': 'Test description',
                'due_date': (date.today() + timedelta(days=30)).isoformat(),
                'status': 'planned',
                'summary': 'Initial summary text'
            }
        )
        
        # Should redirect to item detail
        self.assertEqual(response.status_code, 302)
        
        # Check milestone was created with summary
        self.assertEqual(Milestone.objects.count(), 1)
        milestone = Milestone.objects.first()
        self.assertEqual(milestone.name, 'Test Milestone')
        self.assertEqual(milestone.summary, 'Initial summary text')
