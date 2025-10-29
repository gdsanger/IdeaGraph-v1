"""
Tests for Activity Sidebar functionality
"""

from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from django.utils import timezone

from main.views_activity import activity_sidebar
from main.templatetags.activity_extras import (
    type_to_icon, type_to_badge_color, build_activity_link,
    relative_time, truncate_title
)
from core.services.weaviate_activity_service import (
    WeaviateActivityService,
    WeaviateActivityServiceError
)
from main.models import Settings


class ActivitySidebarViewTest(TestCase):
    """Test cases for activity sidebar view"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
    
    def _create_request_with_session(self, user_id=None):
        """Helper to create request with session"""
        request = self.factory.get('/activity/sidebar')
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session.save()
        if user_id:
            request.session['user_id'] = user_id
        return request
    
    @patch('main.views_activity.WeaviateActivityService')
    @patch('main.views_activity.CacheManager')
    def test_activity_sidebar_cache_miss(self, mock_cache_manager, mock_service):
        """Test activity sidebar with cache miss"""
        # Setup
        request = self._create_request_with_session(user_id='test-user-id')
        
        # Mock cache manager
        cache_instance = Mock()
        cache_instance.get.return_value = None  # Cache miss
        mock_cache_manager.return_value = cache_instance
        
        # Mock Weaviate service
        service_instance = Mock()
        mock_activity = [
            {
                'id': 'test-id-1',
                'type': 'Task',
                'title': 'Test Task',
                'createdAt': '2025-10-29T10:00:00Z',
                'url': None,
                'itemId': None,
                'taskId': None
            }
        ]
        service_instance.get_recent_activity.return_value = mock_activity
        mock_service.return_value = service_instance
        
        # Execute
        response = activity_sidebar(request)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        service_instance.get_recent_activity.assert_called_once()
        cache_instance.set.assert_called_once()
        service_instance.close.assert_called_once()
    
    @patch('main.views_activity.CacheManager')
    def test_activity_sidebar_cache_hit(self, mock_cache_manager):
        """Test activity sidebar with cache hit"""
        # Setup
        request = self._create_request_with_session(user_id='test-user-id')
        
        # Mock cache manager with cached data
        cache_instance = Mock()
        cached_data = [
            {
                'id': 'cached-id',
                'type': 'Email',
                'title': 'Cached Email',
                'createdAt': '2025-10-29T09:00:00Z',
            }
        ]
        cache_instance.get.return_value = cached_data
        mock_cache_manager.return_value = cache_instance
        
        # Execute
        response = activity_sidebar(request)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        cache_instance.get.assert_called_once()
        # Should not call set when cache hit
        cache_instance.set.assert_not_called()
    
    @patch('main.views_activity.WeaviateActivityService')
    @patch('main.views_activity.CacheManager')
    def test_activity_sidebar_handles_weaviate_error(self, mock_cache_manager, mock_service):
        """Test activity sidebar handles Weaviate errors gracefully"""
        # Setup
        request = self._create_request_with_session(user_id='test-user-id')
        
        # Mock cache manager
        cache_instance = Mock()
        cache_instance.get.return_value = None
        mock_cache_manager.return_value = cache_instance
        
        # Mock Weaviate service to raise error
        mock_service.side_effect = WeaviateActivityServiceError("Test error", "Details")
        
        # Execute
        response = activity_sidebar(request)
        
        # Assert - should return empty list on error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Keine aktuellen Aktivitäten')


class ActivityTemplateTagsTest(TestCase):
    """Test cases for activity template tags"""
    
    def test_type_to_icon(self):
        """Test type to icon conversion"""
        self.assertEqual(type_to_icon('Email'), 'bi-envelope-fill')
        self.assertEqual(type_to_icon('Task'), 'bi-check-square-fill')
        self.assertEqual(type_to_icon('Item'), 'bi-lightbulb-fill')
        self.assertEqual(type_to_icon('GitHubPullRequest'), 'bi-git')
        self.assertEqual(type_to_icon('GitHubIssue'), 'bi-github')
        self.assertEqual(type_to_icon('File'), 'bi-file-earmark-text-fill')
        self.assertEqual(type_to_icon('Comment'), 'bi-chat-left-text-fill')
        self.assertEqual(type_to_icon('Unknown'), 'bi-file-earmark-fill')
    
    def test_type_to_badge_color(self):
        """Test type to badge color conversion"""
        self.assertEqual(type_to_badge_color('Email'), 'primary')
        self.assertEqual(type_to_badge_color('Task'), 'success')
        self.assertEqual(type_to_badge_color('Item'), 'warning')
        self.assertEqual(type_to_badge_color('GitHubPullRequest'), 'info')
        self.assertEqual(type_to_badge_color('GitHubIssue'), 'danger')
        self.assertEqual(type_to_badge_color('File'), 'secondary')
        self.assertEqual(type_to_badge_color('Comment'), 'light')
        self.assertEqual(type_to_badge_color('Unknown'), 'secondary')
    
    def test_build_activity_link_external(self):
        """Test building external link (GitHub)"""
        item = {
            'url': 'https://github.com/org/repo/pull/1',
            'type': 'GitHubPullRequest'
        }
        link = build_activity_link(item)
        self.assertEqual(link, 'https://github.com/org/repo/pull/1')
    
    def test_build_activity_link_task(self):
        """Test building task link without slug (uses id)"""
        item = {
            'type': 'Task',
            'id': 'test-id'
        }
        link = build_activity_link(item)
        self.assertEqual(link, '/tasks/test-id/')
    
    def test_build_activity_link_task_with_slug(self):
        """Test building task link with slug (for backwards compatibility)"""
        item = {
            'type': 'Task',
            'slug': 'test-task-slug',
            'id': 'test-id'
        }
        link = build_activity_link(item)
        self.assertEqual(link, '/tasks/test-task-slug/')
    
    def test_build_activity_link_item(self):
        """Test building item link"""
        item = {
            'type': 'Item',
            'id': 'item-id-123',
            'slug': None
        }
        link = build_activity_link(item)
        self.assertEqual(link, '/items/item-id-123/')
    
    def test_build_activity_link_email(self):
        """Test building email/comment link"""
        item = {
            'type': 'Email',
            'taskId': 'task-id-123',
            'id': 'comment-id-456'
        }
        link = build_activity_link(item)
        self.assertEqual(link, '/tasks/task-id-123/#comment-comment-id-456')
    
    def test_relative_time_just_now(self):
        """Test relative time for recent timestamp"""
        now = timezone.now()
        recent = now - timedelta(seconds=30)
        result = relative_time(recent)
        self.assertEqual(result, 'Gerade eben')
    
    def test_relative_time_minutes(self):
        """Test relative time for minutes ago"""
        now = timezone.now()
        minutes_ago = now - timedelta(minutes=5)
        result = relative_time(minutes_ago)
        self.assertEqual(result, 'vor 5 Min.')
    
    def test_relative_time_hours(self):
        """Test relative time for hours ago"""
        now = timezone.now()
        hours_ago = now - timedelta(hours=3)
        result = relative_time(hours_ago)
        self.assertEqual(result, 'vor 3 Std.')
    
    def test_relative_time_days(self):
        """Test relative time for days ago"""
        now = timezone.now()
        days_ago = now - timedelta(days=2)
        result = relative_time(days_ago)
        self.assertEqual(result, 'vor 2 Tagen')
    
    def test_relative_time_iso_string(self):
        """Test relative time with ISO string input"""
        # Test with ISO format string
        iso_string = '2025-10-29T10:00:00Z'
        result = relative_time(iso_string)
        # Should not crash and return a valid string
        self.assertIsInstance(result, str)
    
    def test_relative_time_none(self):
        """Test relative time with None input"""
        result = relative_time(None)
        self.assertEqual(result, 'Unbekannt')
    
    def test_truncate_title_short(self):
        """Test truncate title with short title"""
        title = 'Short title'
        result = truncate_title(title, 50)
        self.assertEqual(result, 'Short title')
    
    def test_truncate_title_long(self):
        """Test truncate title with long title"""
        title = 'This is a very long title that should be truncated to fit'
        result = truncate_title(title, 20)
        self.assertEqual(len(result), 20)
        self.assertTrue(result.endswith('...'))
    
    def test_truncate_title_none(self):
        """Test truncate title with None input"""
        result = truncate_title(None)
        self.assertEqual(result, '(ohne Titel)')


class WeaviateActivityServiceTest(TestCase):
    """Test cases for Weaviate Activity Service"""
    
    @patch('core.services.weaviate_activity_service.weaviate.connect_to_local')
    def test_service_initialization_local(self, mock_connect):
        """Test service initialization with local Weaviate"""
        
        # Mock settings
        mock_settings = Mock()
        mock_settings.weaviate_cloud_enabled = False
        
        # Mock client
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        # Create service
        service = WeaviateActivityService(settings=mock_settings)
        
        # Assert
        mock_connect.assert_called_once()
        self.assertIsNotNone(service._client)
    
    @patch('core.services.weaviate_activity_service.weaviate.connect_to_weaviate_cloud')
    def test_service_initialization_cloud(self, mock_connect):
        """Test service initialization with Weaviate Cloud"""
        
        # Mock settings
        mock_settings = Mock()
        mock_settings.weaviate_cloud_enabled = True
        mock_settings.weaviate_url = 'https://test.weaviate.cloud'
        mock_settings.weaviate_api_key = 'test-api-key'
        
        # Mock client
        mock_client = MagicMock()
        mock_connect.return_value = mock_client
        
        # Create service
        service = WeaviateActivityService(settings=mock_settings)
        
        # Assert
        mock_connect.assert_called_once()
        self.assertIsNotNone(service._client)
