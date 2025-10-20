"""
Tests for Weaviate Cloud configuration in Settings
"""
from django.test import TestCase
from main.models import Settings
from unittest.mock import patch, MagicMock


class SettingsWeaviateCloudTestCase(TestCase):
    """Test suite for Weaviate Cloud configuration in Settings"""
    
    def test_settings_create_with_weaviate_cloud_disabled(self):
        """Test creating settings with Weaviate Cloud disabled (default)"""
        settings = Settings.objects.create()
        
        self.assertFalse(settings.weaviate_cloud_enabled)
        self.assertEqual(settings.weaviate_url, '')
        self.assertEqual(settings.weaviate_api_key, '')
    
    def test_settings_create_with_weaviate_cloud_enabled(self):
        """Test creating settings with Weaviate Cloud enabled"""
        settings = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='https://test-cluster.weaviate.network',
            weaviate_api_key='test-api-key-123'
        )
        
        self.assertTrue(settings.weaviate_cloud_enabled)
        self.assertEqual(settings.weaviate_url, 'https://test-cluster.weaviate.network')
        self.assertEqual(settings.weaviate_api_key, 'test-api-key-123')
    
    def test_settings_update_toggle_cloud_enabled(self):
        """Test updating settings to enable Weaviate Cloud"""
        settings = Settings.objects.create(
            weaviate_cloud_enabled=False,
            weaviate_url='',
            weaviate_api_key=''
        )
        
        settings.weaviate_cloud_enabled = True
        settings.weaviate_url = 'https://my-cluster.weaviate.network'
        settings.weaviate_api_key = 'my-api-key'
        settings.save()
        
        settings.refresh_from_db()
        self.assertTrue(settings.weaviate_cloud_enabled)
        self.assertEqual(settings.weaviate_url, 'https://my-cluster.weaviate.network')
        self.assertEqual(settings.weaviate_api_key, 'my-api-key')
    
    def test_settings_update_toggle_cloud_disabled(self):
        """Test updating settings to disable Weaviate Cloud"""
        settings = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='https://test-cluster.weaviate.network',
            weaviate_api_key='test-key'
        )
        
        settings.weaviate_cloud_enabled = False
        settings.save()
        
        settings.refresh_from_db()
        self.assertFalse(settings.weaviate_cloud_enabled)
        # URL and API key should remain unchanged (preserved for re-enabling)
        self.assertEqual(settings.weaviate_url, 'https://test-cluster.weaviate.network')
        self.assertEqual(settings.weaviate_api_key, 'test-key')
    
    def test_weaviate_service_uses_local_when_cloud_disabled(self):
        """Test that Weaviate sync service uses local connection when cloud is disabled"""
        from core.services.weaviate_sync_service import WeaviateItemSyncService
        
        settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
        
        with patch('core.services.weaviate_sync_service.weaviate.connect_to_local') as mock_local:
            mock_client = MagicMock()
            mock_local.return_value = mock_client
            
            service = WeaviateItemSyncService(settings)
            
            # Verify local connection was used
            mock_local.assert_called_once_with(host="localhost", port=8081)
            self.assertIsNotNone(service._client)
    
    def test_weaviate_service_uses_cloud_when_enabled(self):
        """Test that Weaviate sync service uses cloud connection when enabled"""
        from core.services.weaviate_sync_service import WeaviateItemSyncService
        
        settings = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='https://test-cluster.weaviate.network',
            weaviate_api_key='test-api-key'
        )
        
        with patch('core.services.weaviate_sync_service.weaviate.connect_to_weaviate_cloud') as mock_cloud:
            with patch('core.services.weaviate_sync_service.Auth.api_key') as mock_auth:
                mock_client = MagicMock()
                mock_cloud.return_value = mock_client
                mock_auth_obj = MagicMock()
                mock_auth.return_value = mock_auth_obj
                
                service = WeaviateItemSyncService(settings)
                
                # Verify cloud connection was used with correct parameters
                mock_auth.assert_called_once_with('test-api-key')
                mock_cloud.assert_called_once_with(
                    cluster_url='https://test-cluster.weaviate.network',
                    auth_credentials=mock_auth_obj
                )
                self.assertIsNotNone(service._client)
    
    def test_weaviate_service_raises_error_when_cloud_enabled_without_url(self):
        """Test that service raises error when cloud is enabled but URL is missing"""
        from core.services.weaviate_sync_service import WeaviateItemSyncService, WeaviateItemSyncServiceError
        
        settings = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='',  # Missing URL
            weaviate_api_key='test-api-key'
        )
        
        with self.assertRaises(WeaviateItemSyncServiceError) as context:
            WeaviateItemSyncService(settings)
        
        # The error is caught and re-raised, so check the details attribute
        error = context.exception
        self.assertTrue(
            "URL or API key not configured" in (error.details or '') or
            "Failed to initialize Weaviate client" in str(error)
        )
    
    def test_weaviate_service_raises_error_when_cloud_enabled_without_api_key(self):
        """Test that service raises error when cloud is enabled but API key is missing"""
        from core.services.weaviate_sync_service import WeaviateItemSyncService, WeaviateItemSyncServiceError
        
        settings = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='https://test-cluster.weaviate.network',
            weaviate_api_key=''  # Missing API key
        )
        
        with self.assertRaises(WeaviateItemSyncServiceError) as context:
            WeaviateItemSyncService(settings)
        
        # The error is caught and re-raised, so check the details attribute
        error = context.exception
        self.assertTrue(
            "URL or API key not configured" in (error.details or '') or
            "Failed to initialize Weaviate client" in str(error)
        )
    
    def test_weaviate_task_service_respects_cloud_toggle(self):
        """Test that Task sync service respects the cloud toggle"""
        from core.services.weaviate_task_sync_service import WeaviateTaskSyncService
        
        # Test with cloud enabled
        settings = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='https://test-cluster.weaviate.network',
            weaviate_api_key='test-key'
        )
        
        with patch('core.services.weaviate_task_sync_service.weaviate.connect_to_weaviate_cloud') as mock_cloud:
            with patch('core.services.weaviate_task_sync_service.Auth.api_key'):
                mock_cloud.return_value = MagicMock()
                service = WeaviateTaskSyncService(settings)
                self.assertTrue(mock_cloud.called)
    
    def test_weaviate_tag_service_respects_cloud_toggle(self):
        """Test that Tag sync service respects the cloud toggle"""
        from core.services.weaviate_tag_sync_service import WeaviateTagSyncService
        
        # Test with cloud disabled (use local)
        settings = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
        
        with patch('core.services.weaviate_tag_sync_service.weaviate.connect_to_local') as mock_local:
            mock_local.return_value = MagicMock()
            service = WeaviateTagSyncService(settings)
            self.assertTrue(mock_local.called)
    
    def test_weaviate_github_issue_service_respects_cloud_toggle(self):
        """Test that GitHub Issue sync service respects the cloud toggle"""
        from core.services.weaviate_github_issue_sync_service import WeaviateGitHubIssueSyncService
        
        # Test with cloud enabled
        settings = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='https://test-cluster.weaviate.network',
            weaviate_api_key='test-key'
        )
        
        with patch('core.services.weaviate_github_issue_sync_service.weaviate.connect_to_weaviate_cloud') as mock_cloud:
            with patch('core.services.weaviate_github_issue_sync_service.Auth.api_key'):
                mock_cloud.return_value = MagicMock()
                service = WeaviateGitHubIssueSyncService(settings)
                self.assertTrue(mock_cloud.called)
    
    def test_multiple_settings_can_have_different_weaviate_configs(self):
        """Test that different settings instances can have different Weaviate configurations"""
        settings1 = Settings.objects.create(
            weaviate_cloud_enabled=False
        )
        
        settings2 = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='https://cluster1.weaviate.network',
            weaviate_api_key='key1'
        )
        
        settings3 = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='https://cluster2.weaviate.network',
            weaviate_api_key='key2'
        )
        
        self.assertFalse(settings1.weaviate_cloud_enabled)
        self.assertTrue(settings2.weaviate_cloud_enabled)
        self.assertTrue(settings3.weaviate_cloud_enabled)
        self.assertNotEqual(settings2.weaviate_url, settings3.weaviate_url)
        self.assertNotEqual(settings2.weaviate_api_key, settings3.weaviate_api_key)


class SettingsWeaviateCloudViewTestCase(TestCase):
    """Test suite for Settings views with Weaviate Cloud configuration"""
    
    def test_settings_view_integration_create_cloud_enabled(self):
        """Integration test: Create settings with Weaviate Cloud enabled"""
        post_data = {
            'weaviate_cloud_enabled': 'on',
            'weaviate_url': 'https://my-cluster.weaviate.network',
            'weaviate_api_key': 'my-secure-api-key',
            'max_tags_per_idea': '5'
        }
        
        # Create settings object as the view does
        settings = Settings.objects.create(
            weaviate_cloud_enabled=post_data.get('weaviate_cloud_enabled') == 'on',
            weaviate_url=post_data.get('weaviate_url', ''),
            weaviate_api_key=post_data.get('weaviate_api_key', ''),
            max_tags_per_idea=int(post_data.get('max_tags_per_idea') or 5)
        )
        
        # Verify results
        self.assertTrue(settings.weaviate_cloud_enabled)
        self.assertEqual(settings.weaviate_url, 'https://my-cluster.weaviate.network')
        self.assertEqual(settings.weaviate_api_key, 'my-secure-api-key')
    
    def test_settings_view_integration_create_cloud_disabled(self):
        """Integration test: Create settings with Weaviate Cloud disabled"""
        post_data = {
            # weaviate_cloud_enabled not present means checkbox unchecked
            'weaviate_url': '',
            'weaviate_api_key': '',
            'max_tags_per_idea': '5'
        }
        
        # Create settings object as the view does
        settings = Settings.objects.create(
            weaviate_cloud_enabled=post_data.get('weaviate_cloud_enabled') == 'on',
            weaviate_url=post_data.get('weaviate_url', ''),
            weaviate_api_key=post_data.get('weaviate_api_key', ''),
            max_tags_per_idea=int(post_data.get('max_tags_per_idea') or 5)
        )
        
        # Verify toggle is disabled
        self.assertFalse(settings.weaviate_cloud_enabled)
        self.assertEqual(settings.weaviate_url, '')
        self.assertEqual(settings.weaviate_api_key, '')
    
    def test_settings_view_integration_update_to_cloud(self):
        """Integration test: Update settings from local to cloud"""
        settings = Settings.objects.create(
            weaviate_cloud_enabled=False,
            weaviate_url='',
            weaviate_api_key=''
        )
        
        post_data = {
            'weaviate_cloud_enabled': 'on',
            'weaviate_url': 'https://new-cluster.weaviate.network',
            'weaviate_api_key': 'new-api-key',
            'max_tags_per_idea': '5'
        }
        
        # Update as the view does
        settings.weaviate_cloud_enabled = post_data.get('weaviate_cloud_enabled') == 'on'
        settings.weaviate_url = post_data.get('weaviate_url', '')
        settings.weaviate_api_key = post_data.get('weaviate_api_key', '')
        settings.save()
        
        # Verify update
        settings.refresh_from_db()
        self.assertTrue(settings.weaviate_cloud_enabled)
        self.assertEqual(settings.weaviate_url, 'https://new-cluster.weaviate.network')
        self.assertEqual(settings.weaviate_api_key, 'new-api-key')
    
    def test_settings_view_integration_update_to_local(self):
        """Integration test: Update settings from cloud to local"""
        settings = Settings.objects.create(
            weaviate_cloud_enabled=True,
            weaviate_url='https://old-cluster.weaviate.network',
            weaviate_api_key='old-key'
        )
        
        post_data = {
            # weaviate_cloud_enabled not present (checkbox unchecked)
            'weaviate_url': 'https://old-cluster.weaviate.network',  # Keep URL
            'weaviate_api_key': 'old-key',  # Keep API key
            'max_tags_per_idea': '5'
        }
        
        # Update as the view does
        settings.weaviate_cloud_enabled = post_data.get('weaviate_cloud_enabled') == 'on'
        settings.weaviate_url = post_data.get('weaviate_url', '')
        settings.weaviate_api_key = post_data.get('weaviate_api_key', '')
        settings.save()
        
        # Verify toggle is disabled but credentials preserved
        settings.refresh_from_db()
        self.assertFalse(settings.weaviate_cloud_enabled)
        self.assertEqual(settings.weaviate_url, 'https://old-cluster.weaviate.network')
        self.assertEqual(settings.weaviate_api_key, 'old-key')
