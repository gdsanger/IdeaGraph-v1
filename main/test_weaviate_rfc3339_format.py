"""
Tests for Weaviate RFC3339 Date Format

This test ensures that all datetime fields sent to Weaviate
are properly formatted in RFC3339 format with timezone information.
"""
from django.test import TestCase
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import re


class WeaviateRFC3339FormatTestCase(TestCase):
    """Test suite for RFC3339 date format compliance"""
    
    def setUp(self):
        """Set up test fixtures"""
        from main.models import Settings
        self.settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
    
    def _is_rfc3339_format(self, date_string):
        """
        Verify if a date string is in RFC3339 format.
        RFC3339 requires timezone information (either +HH:MM, -HH:MM, or Z)
        
        Args:
            date_string: String to validate
            
        Returns:
            bool: True if valid RFC3339 format, False otherwise
        """
        if not date_string:
            return False
        
        # RFC3339 format must have timezone suffix
        # Examples: 2025-10-28T17:10:55+00:00, 2025-10-28T17:10:55Z
        rfc3339_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)'
        return bool(re.match(rfc3339_pattern, date_string))
    
    def _get_insert_properties(self, mock_data):
        """
        Helper method to extract properties from insert call
        
        Args:
            mock_data: Mocked collection.data object
            
        Returns:
            dict: Properties passed to insert()
        """
        call_args = mock_data.insert.call_args
        call_kwargs = call_args.kwargs if hasattr(call_args, 'kwargs') else call_args[1]
        return call_kwargs['properties']
    
    @patch('core.services.weaviate_sync_service.weaviate.connect_to_local')
    def test_sync_knowledge_object_createdAt_is_rfc3339(self, mock_connect):
        """Test that sync_knowledge_object uses RFC3339 format for createdAt"""
        from core.services.weaviate_sync_service import WeaviateItemSyncService
        
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_data.insert.return_value = "test-uuid"
        
        # Initialize service
        service = WeaviateItemSyncService(settings=self.settings)
        
        # Call sync_knowledge_object
        result = service.sync_knowledge_object(
            title="Test Object",
            content="Test content",
            metadata={'object_type': 'Test'}
        )
        
        # Verify insert was called
        self.assertTrue(mock_data.insert.called)
        
        # Extract properties
        properties = self._get_insert_properties(mock_data)
        
        # Verify createdAt field exists
        self.assertIn('createdAt', properties)
        
        # Verify createdAt is in RFC3339 format
        created_at = properties['createdAt']
        self.assertTrue(
            self._is_rfc3339_format(created_at),
            f"createdAt '{created_at}' is not in RFC3339 format. "
            f"RFC3339 requires timezone information (e.g., +00:00 or Z)"
        )
    
    @patch('core.services.weaviate_task_sync_service.weaviate.connect_to_local')
    def test_task_sync_createdAt_is_rfc3339(self, mock_connect):
        """Test that task sync uses RFC3339 format for createdAt"""
        from core.services.weaviate_task_sync_service import WeaviateTaskSyncService
        from main.models import Item, Task, User, Section
        
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        
        # Create test data
        user = User.objects.create_user(username='testuser', password='testpass')
        section = Section.objects.create(name='Test Section')
        item = Item.objects.create(
            title='Test Item',
            section=section,
            created_by=user
        )
        task = Task.objects.create(
            title='Test Task',
            item=item,
            created_by=user
        )
        
        # Initialize service
        service = WeaviateTaskSyncService(settings=self.settings)
        
        # Call sync_create
        result = service.sync_create(task)
        
        # Verify insert was called
        self.assertTrue(mock_data.insert.called)
        
        # Extract properties
        properties = self._get_insert_properties(mock_data)
        
        # Verify createdAt field exists
        self.assertIn('createdAt', properties)
        
        # Verify createdAt is in RFC3339 format
        created_at = properties['createdAt']
        self.assertTrue(
            self._is_rfc3339_format(created_at),
            f"createdAt '{created_at}' is not in RFC3339 format. "
            f"RFC3339 requires timezone information (e.g., +00:00 or Z)"
        )
    
    @patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_local')
    def test_github_issue_sync_createdAt_fallback_is_rfc3339(self, mock_connect):
        """Test that GitHub issue sync uses RFC3339 format for createdAt fallback"""
        from core.services.weaviate_github_issue_sync_service import WeaviateGitHubIssueSyncService
        
        # Setup mocks
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_data = MagicMock()
        
        mock_connect.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        mock_collection.data = mock_data
        mock_collection.data.exists.return_value = False
        
        # Initialize service
        service = WeaviateGitHubIssueSyncService(settings=self.settings)
        
        # Call sync_issue_to_weaviate with issue missing created_at
        # This will trigger the datetime.now() fallback
        issue_data = {
            'number': 123,
            'title': 'Test Issue',
            'body': 'Test body',
            'state': 'open',
            'html_url': 'https://github.com/test/repo/issues/123'
            # Note: no 'created_at' field, will use fallback
        }
        
        result = service.sync_issue_to_weaviate(issue_data)
        
        # Verify insert was called
        self.assertTrue(mock_data.insert.called)
        
        # Extract properties
        properties = self._get_insert_properties(mock_data)
        
        # Verify createdAt field exists
        self.assertIn('createdAt', properties)
        
        # Verify createdAt is in RFC3339 format
        created_at = properties['createdAt']
        self.assertTrue(
            self._is_rfc3339_format(created_at),
            f"createdAt '{created_at}' is not in RFC3339 format. "
            f"RFC3339 requires timezone information (e.g., +00:00 or Z)"
        )
    
    def test_datetime_now_with_timezone_produces_rfc3339(self):
        """Test that datetime.now(timezone.utc).isoformat() produces RFC3339 format"""
        # Generate a timestamp using the corrected approach
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Verify it's in RFC3339 format
        self.assertTrue(
            self._is_rfc3339_format(timestamp),
            f"timestamp '{timestamp}' is not in RFC3339 format"
        )
        
        # Verify it has timezone suffix
        self.assertTrue(
            '+' in timestamp or 'Z' in timestamp,
            f"timestamp '{timestamp}' missing timezone suffix"
        )
    
    def test_datetime_now_without_timezone_is_not_rfc3339(self):
        """Test that datetime.now().isoformat() does NOT produce RFC3339 format"""
        # Generate a timestamp using the problematic approach
        timestamp = datetime.now().isoformat()
        
        # Verify it's NOT in RFC3339 format (should fail)
        self.assertFalse(
            self._is_rfc3339_format(timestamp),
            f"timestamp '{timestamp}' should NOT be RFC3339 format without timezone"
        )
