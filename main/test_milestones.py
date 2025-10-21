from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
from main.models import User, Item, Milestone, Task


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
        """Test milestone creation via POST"""
        response = self.client.post(
            reverse('main:milestone_create', kwargs={'item_id': self.item.id}),
            {
                'name': 'Test Milestone',
                'due_date': (date.today() + timedelta(days=30)).isoformat(),
            }
        )
        
        # Should redirect to item detail
        self.assertEqual(response.status_code, 302)
        
        # Check milestone was created
        self.assertEqual(Milestone.objects.count(), 1)
        milestone = Milestone.objects.first()
        self.assertEqual(milestone.name, 'Test Milestone')
        self.assertEqual(milestone.item, self.item)
    
    def test_milestone_edit_view(self):
        """Test milestone edit view"""
        milestone = Milestone.objects.create(
            name='Test Milestone',
            due_date=date.today() + timedelta(days=30),
            item=self.item
        )
        
        response = self.client.post(
            reverse('main:milestone_edit', kwargs={'milestone_id': milestone.id}),
            {
                'name': 'Updated Milestone',
                'due_date': (date.today() + timedelta(days=60)).isoformat(),
            }
        )
        
        # Should redirect to item detail
        self.assertEqual(response.status_code, 302)
        
        # Check milestone was updated
        milestone.refresh_from_db()
        self.assertEqual(milestone.name, 'Updated Milestone')
    
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
