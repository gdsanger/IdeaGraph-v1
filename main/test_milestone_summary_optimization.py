"""
Test suite for Milestone Summary Optimization functionality
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from main.models import User, Item, Milestone, MilestoneSummaryVersion, Settings
from core.services.milestone_knowledge_service import MilestoneKnowledgeService, MilestoneKnowledgeServiceError


class MilestoneSummaryOptimizationServiceTest(TestCase):
    """Test MilestoneKnowledgeService summary optimization methods"""
    
    def setUp(self):
        # Create settings (required for service)
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_token='test-token',
            kigate_api_base_url='http://localhost:8000',
            openai_default_model='gpt-4'
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
        
        # Create test milestone with summary
        self.milestone = Milestone.objects.create(
            name='Test Milestone',
            due_date=date.today() + timedelta(days=30),
            item=self.item,
            summary='This is a test summary with some redundant text. This is a test summary with some redundant text.'
        )
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_optimize_summary(self, mock_kigate):
        """Test optimizing a milestone summary"""
        # Mock KiGate service
        mock_instance = MagicMock()
        mock_kigate.return_value = mock_instance
        mock_instance.execute_agent.return_value = {
            'success': True,
            'result': 'This is an optimized test summary without redundancy.'
        }
        
        service = MilestoneKnowledgeService()
        result = service.optimize_summary(self.milestone, user=self.user)
        
        self.assertTrue(result['success'])
        self.assertIn('original_summary', result)
        self.assertIn('optimized_summary', result)
        self.assertEqual(result['agent_name'], 'summary-enhancer-agent')
        self.assertEqual(result['model'], 'gpt-4')
        self.assertNotEqual(result['optimized_summary'], result['original_summary'])
        
        # Verify KiGate was called correctly
        mock_instance.execute_agent.assert_called_once()
        call_args = mock_instance.execute_agent.call_args
        self.assertEqual(call_args[1]['agent_name'], 'summary-enhancer-agent')
        self.assertEqual(call_args[1]['provider'], 'openai')
        self.assertEqual(call_args[1]['model'], 'gpt-4')
    
    def test_optimize_summary_no_summary(self):
        """Test optimizing when no summary exists"""
        milestone_no_summary = Milestone.objects.create(
            name='Empty Milestone',
            due_date=date.today() + timedelta(days=30),
            item=self.item,
            summary=''
        )
        
        service = MilestoneKnowledgeService()
        
        with self.assertRaises(MilestoneKnowledgeServiceError) as context:
            service.optimize_summary(milestone_no_summary, user=self.user)
        
        # Check that the error is about missing summary
        self.assertIn('summary', str(context.exception).lower())
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_save_optimized_summary(self, mock_kigate):
        """Test saving an optimized summary"""
        optimized_text = 'This is an optimized summary that is better structured.'
        
        service = MilestoneKnowledgeService()
        result = service.save_optimized_summary(
            milestone=self.milestone,
            optimized_summary=optimized_text,
            user=self.user,
            agent_name='summary-enhancer-agent',
            model_name='gpt-4'
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['summary'], optimized_text)
        
        # Verify milestone was updated
        self.milestone.refresh_from_db()
        self.assertEqual(self.milestone.summary, optimized_text)
        
        # Verify version was created
        versions = MilestoneSummaryVersion.objects.filter(milestone=self.milestone)
        self.assertEqual(versions.count(), 1)
        
        version = versions.first()
        self.assertEqual(version.summary_text, optimized_text)
        self.assertTrue(version.optimized_by_ai)
        self.assertEqual(version.agent_name, 'summary-enhancer-agent')
        self.assertEqual(version.model_name, 'gpt-4')
        self.assertEqual(version.created_by, self.user)
        self.assertEqual(version.version_number, 1)
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_save_multiple_versions(self, mock_kigate):
        """Test saving multiple optimized versions"""
        service = MilestoneKnowledgeService()
        
        # Save first version
        result1 = service.save_optimized_summary(
            milestone=self.milestone,
            optimized_summary='First optimized version',
            user=self.user
        )
        self.assertTrue(result1['success'])
        
        # Save second version
        result2 = service.save_optimized_summary(
            milestone=self.milestone,
            optimized_summary='Second optimized version',
            user=self.user
        )
        self.assertTrue(result2['success'])
        
        # Verify versions
        versions = MilestoneSummaryVersion.objects.filter(
            milestone=self.milestone
        ).order_by('version_number')
        
        self.assertEqual(versions.count(), 2)
        self.assertEqual(versions[0].version_number, 1)
        self.assertEqual(versions[0].summary_text, 'First optimized version')
        self.assertEqual(versions[1].version_number, 2)
        self.assertEqual(versions[1].summary_text, 'Second optimized version')
    
    def test_get_summary_history(self):
        """Test retrieving summary history"""
        # Create some versions
        MilestoneSummaryVersion.objects.create(
            milestone=self.milestone,
            summary_text='Version 1',
            version_number=1,
            optimized_by_ai=True,
            agent_name='summary-enhancer-agent',
            model_name='gpt-4',
            created_by=self.user
        )
        MilestoneSummaryVersion.objects.create(
            milestone=self.milestone,
            summary_text='Version 2',
            version_number=2,
            optimized_by_ai=True,
            agent_name='summary-enhancer-agent',
            model_name='gpt-4',
            created_by=self.user
        )
        
        service = MilestoneKnowledgeService()
        result = service.get_summary_history(self.milestone)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_versions'], 2)
        self.assertEqual(len(result['versions']), 2)
        
        # Verify versions are ordered correctly (newest first)
        self.assertEqual(result['versions'][0]['version_number'], 2)
        self.assertEqual(result['versions'][1]['version_number'], 1)
        
        # Verify version data
        version = result['versions'][0]
        self.assertIn('id', version)
        self.assertIn('summary_text', version)
        self.assertIn('optimized_by_ai', version)
        self.assertIn('agent_name', version)
        self.assertIn('created_by', version)
        self.assertIn('created_at', version)


class MilestoneSummaryOptimizationAPITest(TestCase):
    """Test API endpoints for summary optimization"""
    
    def setUp(self):
        # Create settings
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_token='test-token',
            kigate_api_base_url='http://localhost:8000',
            openai_default_model='gpt-4'
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
            item=self.item,
            summary='Original summary text for testing optimization.'
        )
        
        # Create client and authenticate using session
        self.client = Client()
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_api_optimize_summary(self, mock_kigate):
        """Test POST /api/milestones/<id>/optimize-summary"""
        # Mock KiGate service
        mock_instance = MagicMock()
        mock_kigate.return_value = mock_instance
        mock_instance.execute_agent.return_value = {
            'success': True,
            'result': 'Optimized summary text'
        }
        
        url = reverse('main:api_milestone_optimize_summary', args=[self.milestone.id])
        response = self.client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('original_summary', data)
        self.assertIn('optimized_summary', data)
        self.assertEqual(data['optimized_summary'], 'Optimized summary text')
    
    def test_api_optimize_summary_no_summary(self):
        """Test optimize API with no existing summary"""
        milestone_empty = Milestone.objects.create(
            name='Empty Milestone',
            due_date=date.today() + timedelta(days=30),
            item=self.item,
            summary=''
        )
        
        url = reverse('main:api_milestone_optimize_summary', args=[milestone_empty.id])
        response = self.client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('No summary available', data['error'])
    
    def test_api_optimize_summary_unauthorized(self):
        """Test optimize API without authentication"""
        # Create new client without session
        client = Client()
        
        url = reverse('main:api_milestone_optimize_summary', args=[self.milestone.id])
        response = client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
    
    def test_api_optimize_summary_permission_denied(self):
        """Test optimize API with wrong user"""
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='user'
        )
        
        # Create new client with different user
        client = Client()
        session = client.session
        session['user_id'] = str(other_user.id)
        session.save()
        
        url = reverse('main:api_milestone_optimize_summary', args=[self.milestone.id])
        response = client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 403)
    
    @patch('core.services.milestone_knowledge_service.KiGateService')
    def test_api_save_optimized_summary(self, mock_kigate):
        """Test POST /api/milestones/<id>/save-optimized-summary"""
        url = reverse('main:api_milestone_save_optimized_summary', args=[self.milestone.id])
        
        payload = {
            'optimized_summary': 'This is the new optimized summary',
            'agent_name': 'summary-enhancer-agent',
            'model_name': 'gpt-4'
        }
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('summary', data)
        
        # Verify milestone was updated
        self.milestone.refresh_from_db()
        self.assertEqual(self.milestone.summary, payload['optimized_summary'])
        
        # Verify version was created
        version = MilestoneSummaryVersion.objects.filter(
            milestone=self.milestone
        ).first()
        self.assertIsNotNone(version)
        self.assertEqual(version.summary_text, payload['optimized_summary'])
    
    def test_api_save_optimized_summary_missing_data(self):
        """Test save API with missing required data"""
        url = reverse('main:api_milestone_save_optimized_summary', args=[self.milestone.id])
        
        payload = {}  # Missing optimized_summary
        
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('optimized_summary is required', data['error'])
    
    def test_api_get_summary_history(self):
        """Test GET /api/milestones/<id>/summary-history"""
        # Create some versions
        MilestoneSummaryVersion.objects.create(
            milestone=self.milestone,
            summary_text='Version 1',
            version_number=1,
            optimized_by_ai=True,
            agent_name='summary-enhancer-agent',
            model_name='gpt-4',
            created_by=self.user
        )
        MilestoneSummaryVersion.objects.create(
            milestone=self.milestone,
            summary_text='Version 2',
            version_number=2,
            optimized_by_ai=True,
            agent_name='summary-enhancer-agent',
            model_name='gpt-4',
            created_by=self.user
        )
        
        url = reverse('main:api_milestone_summary_history', args=[self.milestone.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['total_versions'], 2)
        self.assertEqual(len(data['versions']), 2)
        
        # Verify ordering (newest first)
        self.assertEqual(data['versions'][0]['version_number'], 2)
        self.assertEqual(data['versions'][1]['version_number'], 1)
    
    def test_api_get_summary_history_unauthorized(self):
        """Test history API without authentication"""
        # Create new client without session
        client = Client()
        
        url = reverse('main:api_milestone_summary_history', args=[self.milestone.id])
        response = client.get(url)
        
        self.assertEqual(response.status_code, 401)
    
    def test_api_milestone_not_found(self):
        """Test API with non-existent milestone"""
        import uuid
        fake_id = uuid.uuid4()
        
        url = reverse('main:api_milestone_optimize_summary', args=[fake_id])
        response = self.client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
