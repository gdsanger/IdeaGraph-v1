"""
Tests for Milestone Semantic Network Feature

This module tests the semantic network generation for milestones.
"""
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import Mock, MagicMock, patch
import uuid
import json


class MilestoneSemanticNetworkAPITest(TestCase):
    """Test cases for Milestone Semantic Network API"""
    
    def setUp(self):
        """Set up test fixtures"""
        from main.models import User, Item, Milestone, Settings
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        self.user.set_password('testpass')
        self.user.save()
        
        # Create settings
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False,
            openai_api_key='test-key'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            created_by=self.user
        )
        
        # Create test milestone
        from datetime import date, timedelta
        self.milestone = Milestone.objects.create(
            name='Test Milestone',
            description='Test milestone description',
            due_date=date.today() + timedelta(days=30),
            status='planned',
            item=self.item
        )
        
        # Set up client
        self.client = Client()
    
    def test_milestone_semantic_network_url(self):
        """Test that milestone semantic network URL is correctly configured"""
        url = reverse('main:api_milestone_semantic_network', kwargs={
            'milestone_id': self.milestone.id
        })
        self.assertEqual(url, f'/api/milestones/{self.milestone.id}/semantic-network')
    
    def test_milestone_semantic_network_requires_authentication(self):
        """Test that API requires authentication"""
        url = reverse('main:api_milestone_semantic_network', kwargs={
            'milestone_id': self.milestone.id
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Authentication required', data['error'])
    
    def test_milestone_semantic_network_nonexistent_milestone(self):
        """Test API with non-existent milestone"""
        from main.auth_utils import generate_jwt_token
        
        # Create JWT token for authentication
        token = generate_jwt_token(self.user)
        
        # Use a random UUID that doesn't exist
        fake_id = uuid.uuid4()
        url = reverse('main:api_milestone_semantic_network', kwargs={
            'milestone_id': fake_id
        })
        
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Milestone not found', data['error'])
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_milestone_semantic_network_success(self, mock_weaviate):
        """Test successful semantic network generation for milestone"""
        from main.auth_utils import generate_jwt_token
        
        # Mock Weaviate client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        
        # Mock object fetch - return a valid milestone object
        mock_obj = MagicMock()
        mock_obj.uuid = self.milestone.id
        mock_obj.properties = {
            'type': 'Milestone',
            'title': 'Test Milestone',
            'description': 'Test milestone description'
        }
        mock_obj.vector = [0.1] * 1536  # Dummy vector
        mock_collection.query.fetch_object_by_id.return_value = mock_obj
        
        # Mock near_object query - return empty results for simplicity
        mock_near_result = MagicMock()
        mock_near_result.objects = []
        mock_collection.query.near_object.return_value = mock_near_result
        
        # Create JWT token for authentication
        token = generate_jwt_token(self.user)
        
        url = reverse('main:api_milestone_semantic_network', kwargs={
            'milestone_id': self.milestone.id
        })
        
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('nodes', data)
        self.assertIn('edges', data)
        self.assertIn('levels', data)
        self.assertEqual(data['source_type'], 'milestone')
        self.assertEqual(data['source_id'], str(self.milestone.id))
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_milestone_semantic_network_with_depth_parameter(self, mock_weaviate):
        """Test semantic network generation with custom depth parameter"""
        from main.auth_utils import generate_jwt_token
        
        # Mock Weaviate client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        
        # Mock object fetch
        mock_obj = MagicMock()
        mock_obj.uuid = self.milestone.id
        mock_obj.properties = {
            'type': 'Milestone',
            'title': 'Test Milestone',
            'description': 'Test milestone description'
        }
        mock_obj.vector = [0.1] * 1536
        mock_collection.query.fetch_object_by_id.return_value = mock_obj
        
        # Mock near_object query
        mock_near_result = MagicMock()
        mock_near_result.objects = []
        mock_collection.query.near_object.return_value = mock_near_result
        
        # Create JWT token
        token = generate_jwt_token(self.user)
        
        url = reverse('main:api_milestone_semantic_network', kwargs={
            'milestone_id': self.milestone.id
        })
        
        # Test with depth=2
        response = self.client.get(
            url + '?depth=2',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['depth'], 2)
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_milestone_semantic_network_no_summaries(self, mock_weaviate):
        """Test semantic network generation without AI summaries"""
        from main.auth_utils import generate_jwt_token
        
        # Mock Weaviate client
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        
        # Mock object fetch
        mock_obj = MagicMock()
        mock_obj.uuid = self.milestone.id
        mock_obj.properties = {
            'type': 'Milestone',
            'title': 'Test Milestone',
            'description': 'Test milestone description'
        }
        mock_obj.vector = [0.1] * 1536
        mock_collection.query.fetch_object_by_id.return_value = mock_obj
        
        # Mock near_object query
        mock_near_result = MagicMock()
        mock_near_result.objects = []
        mock_collection.query.near_object.return_value = mock_near_result
        
        # Create JWT token
        token = generate_jwt_token(self.user)
        
        url = reverse('main:api_milestone_semantic_network', kwargs={
            'milestone_id': self.milestone.id
        })
        
        # Test with summaries=false
        response = self.client.get(
            url + '?summaries=false',
            HTTP_AUTHORIZATION=f'Bearer {token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check that summaries are empty strings when disabled
        for level_data in data.get('levels', {}).values():
            self.assertEqual(level_data.get('summary', ''), '')
