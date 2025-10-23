"""
Test suite for Milestone Knowledge Hub functionality
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from main.models import User, Item, Milestone, MilestoneContextObject, Task, Settings
from core.services.milestone_knowledge_service import MilestoneKnowledgeService, MilestoneKnowledgeServiceError


class MilestoneKnowledgeServiceTest(TestCase):
    """Test MilestoneKnowledgeService"""
    
    def setUp(self):
        # Create settings (required for service)
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_token='test-token',
            kigate_api_base_url='http://localhost:8000'
        )
        
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
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_add_context_object(self, mock_kigate):
        """Test adding a context object to a milestone"""
        # Mock KiGate service to avoid actual API calls
        mock_instance = MagicMock()
        mock_kigate.return_value = mock_instance
        mock_instance.execute_agent.return_value = {
            'success': True,
            'result': {'summary': 'Test summary', 'tasks': []}
        }
        
        service = MilestoneKnowledgeService()
        result = service.add_context_object(
            milestone=self.milestone,
            context_type='file',
            title='Test Document',
            content='This is test content for analysis',
            user=self.user,
            auto_analyze=False  # Disable auto-analyze to avoid mocking
        )
        
        self.assertTrue(result['success'])
        self.assertIn('context_object_id', result)
        
        # Verify context object was created
        self.assertEqual(self.milestone.context_objects.count(), 1)
        context = self.milestone.context_objects.first()
        self.assertEqual(context.title, 'Test Document')
        self.assertEqual(context.type, 'file')
    
    def test_add_context_object_invalid_type(self):
        """Test adding context object with invalid type"""
        service = MilestoneKnowledgeService()
        
        with self.assertRaises(MilestoneKnowledgeServiceError):
            service.add_context_object(
                milestone=self.milestone,
                context_type='invalid_type',
                title='Test',
                content='Test content',
                user=self.user,
                auto_analyze=False
            )
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_analyze_context_object(self, mock_kigate):
        """Test analyzing a context object"""
        # Create a context object
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='transcript',
            title='Meeting Transcript',
            content='Discussed project requirements and timeline',
            uploaded_by=self.user
        )
        
        # Mock KiGate responses
        mock_instance = MagicMock()
        mock_kigate.return_value = mock_instance
        
        # Mock summary agent response
        mock_instance.execute_agent.side_effect = [
            {
                'success': True,
                'result': {'summary': 'Meeting about project requirements'}
            },
            {
                'success': True,
                'result': {
                    'tasks': [
                        {'title': 'Define requirements', 'description': 'Create requirement document'},
                        {'title': 'Set timeline', 'description': 'Establish project timeline'}
                    ]
                }
            }
        ]
        
        service = MilestoneKnowledgeService()
        result = service.analyze_context_object(context)
        
        self.assertTrue(result['success'])
        self.assertIn('summary', result)
        self.assertIn('derived_tasks', result)
        self.assertEqual(result['task_count'], 2)
        
        # Verify context object was updated
        context.refresh_from_db()
        self.assertTrue(context.analyzed)
        self.assertEqual(len(context.derived_tasks), 2)
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_generate_milestone_summary(self, mock_kigate):
        """Test generating milestone summary from context objects"""
        # Create multiple context objects
        MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='file',
            title='Document 1',
            summary='First document summary',
            uploaded_by=self.user
        )
        
        MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='email',
            title='Email 1',
            summary='Email discussion summary',
            uploaded_by=self.user
        )
        
        # Mock KiGate response
        mock_instance = MagicMock()
        mock_kigate.return_value = mock_instance
        mock_instance.execute_agent.return_value = {
            'success': True,
            'result': {'summary': 'Overall milestone summary combining all contexts'}
        }
        
        service = MilestoneKnowledgeService()
        result = service.generate_milestone_summary(self.milestone)
        
        self.assertTrue(result['success'])
        self.assertIn('summary', result)
        self.assertEqual(result['context_count'], 2)
        
        # Verify milestone was updated
        self.milestone.refresh_from_db()
        self.assertIsNotNone(self.milestone.summary)
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_enhance_summary(self, mock_kigate):
        """Test enhancing a context object's summary"""
        # Create context with existing summary
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='note',
            title='Test Note',
            content='Test content',
            summary='Original summary',
            analyzed=True,
            uploaded_by=self.user
        )
        
        # Mock KiGate response
        mock_instance = MagicMock()
        mock_kigate.return_value = mock_instance
        mock_instance.execute_agent.return_value = {
            'success': True,
            'result': {
                'enhanced_summary': 'This is an enhanced and improved summary.'
            }
        }
        
        service = MilestoneKnowledgeService()
        result = service.enhance_summary(context)
        
        self.assertTrue(result['success'])
        self.assertIn('enhanced_summary', result)
        
        # Verify context was updated
        context.refresh_from_db()
        self.assertEqual(context.summary, 'This is an enhanced and improved summary.')
    
    def test_accept_analysis_results(self):
        """Test accepting analysis results with edited data"""
        # Create context with analysis results
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='file',
            title='Document.pdf',
            content='Document content',
            summary='Original summary',
            derived_tasks=[
                {'Titel': 'Task 1', 'Beschreibung': 'Description 1'}
            ],
            analyzed=False,
            uploaded_by=self.user
        )
        
        service = MilestoneKnowledgeService()
        result = service.accept_analysis_results(
            context,
            summary='Edited summary after review',
            derived_tasks=[
                {'Titel': 'Edited Task', 'Beschreibung': 'Edited description'},
                {'Titel': 'New Task', 'Beschreibung': 'New task description'}
            ]
        )
        
        self.assertTrue(result['success'])
        
        # Verify context was updated
        context.refresh_from_db()
        self.assertEqual(context.summary, 'Edited summary after review')
        self.assertEqual(len(context.derived_tasks), 2)
        self.assertTrue(context.analyzed)
        
        # Verify milestone summary was updated with source reference
        self.milestone.refresh_from_db()
        self.assertIn('Edited summary after review', self.milestone.summary)
        self.assertIn('– aus ContextObject [Document.pdf]', self.milestone.summary)
    
    def test_create_tasks_from_context(self):
        """Test creating tasks from derived tasks in context"""
        # Create context with derived tasks
        derived_tasks = [
            {'title': 'Task 1', 'description': 'First task'},
            {'title': 'Task 2', 'description': 'Second task'}
        ]
        
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='transcript',
            title='Meeting Notes',
            derived_tasks=derived_tasks,
            analyzed=True,
            uploaded_by=self.user
        )
        
        service = MilestoneKnowledgeService()
        result = service.create_tasks_from_context(context, self.milestone, self.user)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['tasks_created'], 2)
        
        # Verify tasks were created
        tasks = Task.objects.filter(milestone=self.milestone)
        self.assertEqual(tasks.count(), 2)
        self.assertTrue(tasks.first().ai_generated)


class MilestoneKnowledgeAPITest(TestCase):
    """Test Milestone Knowledge Hub API endpoints"""
    
    def setUp(self):
        # Create settings (required for service)
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_token='test-token',
            kigate_api_base_url='http://localhost:8000'
        )
        
        self.client = Client()
        
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
        
        # Log in user
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_api_milestone_context_add(self, mock_kigate):
        """Test API endpoint for adding context"""
        # Mock KiGate to avoid actual API calls
        mock_instance = MagicMock()
        mock_kigate.return_value = mock_instance
        mock_instance.execute_agent.return_value = {
            'success': True,
            'result': {'summary': 'Test summary'}
        }
        
        url = reverse('main:api_milestone_context_add', kwargs={'milestone_id': self.milestone.id})
        data = {
            'type': 'file',
            'title': 'Test Document',
            'content': 'Test content',
            'auto_analyze': False
        }
        
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify context was created
        self.assertEqual(self.milestone.context_objects.count(), 1)
    
    def test_api_milestone_context_list(self):
        """Test API endpoint for listing context objects"""
        # Create test context objects
        MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='file',
            title='Document 1',
            uploaded_by=self.user
        )
        
        MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='email',
            title='Email 1',
            uploaded_by=self.user
        )
        
        url = reverse('main:api_milestone_context_list', kwargs={'milestone_id': self.milestone.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['context_objects']), 2)
    
    def test_api_milestone_context_remove(self):
        """Test API endpoint for removing context"""
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='note',
            title='Test Note',
            uploaded_by=self.user
        )
        
        url = reverse('main:api_milestone_context_remove', kwargs={'context_id': context.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify context was deleted
        self.assertEqual(self.milestone.context_objects.count(), 0)
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_api_milestone_context_analyze(self, mock_kigate):
        """Test API endpoint for analyzing context"""
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='transcript',
            title='Meeting Transcript',
            content='Meeting content to analyze',
            uploaded_by=self.user
        )
        
        # Mock KiGate responses
        mock_instance = MagicMock()
        mock_kigate.return_value = mock_instance
        mock_instance.execute_agent.side_effect = [
            {'success': True, 'result': {'summary': 'Test summary'}},
            {'success': True, 'result': {'tasks': [{'title': 'Task 1'}]}}
        ]
        
        url = reverse('main:api_milestone_context_analyze', kwargs={'context_id': context.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('summary', response_data)
        self.assertIn('derived_tasks', response_data)
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_api_milestone_context_summarize(self, mock_kigate):
        """Test API endpoint for summarizing milestone"""
        # Create context objects
        MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='file',
            title='Document 1',
            summary='First summary',
            uploaded_by=self.user
        )
        
        # Mock KiGate response
        mock_instance = MagicMock()
        mock_kigate.return_value = mock_instance
        mock_instance.execute_agent.return_value = {
            'success': True,
            'result': {'summary': 'Milestone summary'}
        }
        
        url = reverse('main:api_milestone_context_summarize', kwargs={'milestone_id': self.milestone.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('summary', response_data)
    
    def test_api_milestone_context_create_tasks(self):
        """Test API endpoint for creating tasks from context"""
        derived_tasks = [
            {'title': 'Task 1', 'description': 'Description 1'},
            {'title': 'Task 2', 'description': 'Description 2'}
        ]
        
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='transcript',
            title='Meeting Notes',
            derived_tasks=derived_tasks,
            analyzed=True,
            uploaded_by=self.user
        )
        
        url = reverse('main:api_milestone_context_create_tasks', kwargs={'context_id': context.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['tasks_created'], 2)
        
        # Verify tasks were created
        self.assertEqual(Task.objects.filter(milestone=self.milestone).count(), 2)
    
    def test_api_requires_authentication(self):
        """Test that API endpoints require authentication"""
        # Clear session
        self.client.logout()
        
        url = reverse('main:api_milestone_context_list', kwargs={'milestone_id': self.milestone.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 401)
    
    def test_api_requires_permissions(self):
        """Test that API endpoints check permissions"""
        # Create another user
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='developer'
        )
        other_user.set_password('password')
        other_user.save()
        
        # Log in as other user
        session = self.client.session
        session['user_id'] = str(other_user.id)
        session.save()
        
        url = reverse('main:api_milestone_context_list', kwargs={'milestone_id': self.milestone.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_api_milestone_context_enhance_summary(self, mock_kigate):
        """Test API endpoint for enhancing summary"""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.execute_agent.return_value = {
            'success': True,
            'result': {'enhanced_summary': 'This is an enhanced summary with better clarity.'}
        }
        mock_kigate.return_value = mock_instance
        
        # Create context with existing summary
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='note',
            title='Test Note',
            content='Test content',
            summary='Original summary',
            analyzed=True,
            uploaded_by=self.user
        )
        
        # Login
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        url = reverse('main:api_milestone_context_enhance_summary', kwargs={'context_id': context.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('enhanced_summary', data)
        
        # Verify context object was updated
        context.refresh_from_db()
        self.assertEqual(context.summary, 'This is an enhanced summary with better clarity.')
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_api_milestone_context_accept_results(self, mock_kigate):
        """Test API endpoint for accepting results"""
        # Create context with analysis results
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='note',
            title='Test Note',
            content='Test content',
            summary='Test summary',
            derived_tasks=[
                {'Titel': 'Task 1', 'Beschreibung': 'Description 1'},
                {'Titel': 'Task 2', 'Beschreibung': 'Description 2'}
            ],
            analyzed=False,
            uploaded_by=self.user
        )
        
        # Login
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        # Accept results with edited data
        url = reverse('main:api_milestone_context_accept_results', kwargs={'context_id': context.id})
        response = self.client.post(
            url,
            data=json.dumps({
                'summary': 'Edited summary',
                'derived_tasks': [
                    {'Titel': 'Edited Task', 'Beschreibung': 'Edited description'}
                ]
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify context was updated
        context.refresh_from_db()
        self.assertEqual(context.summary, 'Edited summary')
        self.assertEqual(len(context.derived_tasks), 1)
        self.assertTrue(context.analyzed)
        
        # Verify milestone summary was updated with source reference
        self.milestone.refresh_from_db()
        self.assertIn('Edited summary', self.milestone.summary)
        self.assertIn('– aus ContextObject [Test Note]', self.milestone.summary)
    
    def test_api_milestone_context_analyze_get(self, ):
        """Test GET request to analyze endpoint returns existing analysis"""
        # Create context with analysis results
        context = MilestoneContextObject.objects.create(
            milestone=self.milestone,
            type='note',
            title='Test Note',
            content='Test content',
            summary='Existing summary',
            derived_tasks=[{'Titel': 'Task 1'}],
            analyzed=True,
            uploaded_by=self.user
        )
        
        # Login
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        url = reverse('main:api_milestone_context_analyze', kwargs={'context_id': context.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['context']['summary'], 'Existing summary')
        self.assertEqual(len(data['context']['derived_tasks']), 1)
