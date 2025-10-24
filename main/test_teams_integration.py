"""
Tests for Microsoft Teams Integration
"""
from django.test import TestCase, Client
from django.urls import reverse
from main.models import Settings, User as AppUser, Item, Section
from core.services.teams_service import TeamsService, TeamsServiceError


class TeamsIntegrationSettingsTestCase(TestCase):
    """Test suite for Teams Integration settings"""
    
    def setUp(self):
        """Set up test data"""
        # Create test admin user
        self.admin_user = AppUser.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('admin123')
        self.admin_user.save()
        
        # Get auth token
        from main.auth_utils import generate_jwt_token
        self.token = generate_jwt_token(self.admin_user)
        
        self.client = Client()
    
    def test_settings_create_with_teams_enabled(self):
        """Test creating settings with Teams integration enabled"""
        settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='test-team-id-123',
            team_welcome_post='Welcome to {{Item}} channel!',
            # Graph API settings required for Teams service
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret'
        )
        
        self.assertTrue(settings.teams_enabled)
        self.assertEqual(settings.teams_team_id, 'test-team-id-123')
        self.assertEqual(settings.team_welcome_post, 'Welcome to {{Item}} channel!')
    
    def test_settings_create_with_teams_disabled(self):
        """Test creating settings with Teams integration disabled"""
        settings = Settings.objects.create(
            teams_enabled=False,
            teams_team_id='test-team-id-123',
            team_welcome_post='Welcome to {{Item}} channel!'
        )
        
        self.assertFalse(settings.teams_enabled)
        self.assertEqual(settings.teams_team_id, 'test-team-id-123')
    
    def test_settings_update_toggle_teams_enabled(self):
        """Test updating settings to enable Teams integration"""
        settings = Settings.objects.create(
            teams_enabled=False,
            teams_team_id='test-team-id-123'
        )
        
        settings.teams_enabled = True
        settings.save()
        
        settings.refresh_from_db()
        self.assertTrue(settings.teams_enabled)
    
    def test_settings_update_toggle_teams_disabled(self):
        """Test updating settings to disable Teams integration"""
        settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='test-team-id-123'
        )
        
        settings.teams_enabled = False
        settings.save()
        
        settings.refresh_from_db()
        self.assertFalse(settings.teams_enabled)
    
    def test_settings_defaults_teams(self):
        """Test that Teams settings have correct default values"""
        settings = Settings.objects.create()
        
        self.assertFalse(settings.teams_enabled)
        self.assertEqual(settings.teams_team_id, '')
        # Check default welcome post template
        self.assertIn('{{Item}}', settings.team_welcome_post)
    
    def test_teams_service_respects_toggle_disabled(self):
        """Test that Teams service respects the enabled toggle when disabled"""
        settings = Settings.objects.create(
            teams_enabled=False,
            teams_team_id='test-team-id-123',
            # Graph API settings
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret'
        )
        
        with self.assertRaises(TeamsServiceError) as context:
            TeamsService(settings)
        
        self.assertIn("not enabled", str(context.exception))
    
    def test_teams_service_requires_team_id(self):
        """Test that Teams service requires team_id to be configured"""
        settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='',  # Empty team ID
            # Graph API settings
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret'
        )
        
        with self.assertRaises(TeamsServiceError) as context:
            TeamsService(settings)
        
        self.assertIn("Team ID not configured", str(context.exception))


class TeamsIntegrationItemTestCase(TestCase):
    """Test suite for Item model Teams integration"""
    
    def setUp(self):
        """Set up test data"""
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('test123')
        self.user.save()
        
        self.section = Section.objects.create(name='Test Section')
    
    def test_item_create_without_channel_id(self):
        """Test creating an item without a Teams channel ID"""
        item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user
        )
        
        self.assertEqual(item.channel_id, '')
        self.assertFalse(item.channel_id)
    
    def test_item_create_with_channel_id(self):
        """Test creating an item with a Teams channel ID"""
        item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user,
            channel_id='test-channel-id-123'
        )
        
        self.assertEqual(item.channel_id, 'test-channel-id-123')
        self.assertTrue(item.channel_id)
    
    def test_item_update_channel_id(self):
        """Test updating an item's Teams channel ID"""
        item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user
        )
        
        # Initially no channel ID
        self.assertEqual(item.channel_id, '')
        
        # Update with channel ID
        item.channel_id = 'new-channel-id-456'
        item.save()
        
        # Verify update
        item.refresh_from_db()
        self.assertEqual(item.channel_id, 'new-channel-id-456')


class TeamsIntegrationViewTestCase(TestCase):
    """Test suite for Teams integration views"""
    
    def setUp(self):
        """Set up test data"""
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('test123')
        self.user.save()
        
        self.section = Section.objects.create(name='Test Section')
        
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user
        )
        
        self.client = Client()
        
        # Simulate login
        from main.auth_utils import generate_jwt_token
        self.token = generate_jwt_token(self.user)
    
    def test_settings_view_integration_create_teams_enabled(self):
        """Integration test: Create settings with Teams enabled via view logic simulation"""
        post_data = {
            'teams_enabled': 'on',
            'teams_team_id': 'test-team-123',
            'team_welcome_post': 'Welcome to {{Item}}!',
            'max_tags_per_idea': '5'
        }
        
        # Create settings object as the view does
        settings = Settings.objects.create(
            teams_enabled=post_data.get('teams_enabled') == 'on',
            teams_team_id=post_data.get('teams_team_id', ''),
            team_welcome_post=post_data.get('team_welcome_post', ''),
            max_tags_per_idea=int(post_data.get('max_tags_per_idea') or 5)
        )
        
        # Verify results
        self.assertTrue(settings.teams_enabled)
        self.assertEqual(settings.teams_team_id, 'test-team-123')
        self.assertEqual(settings.team_welcome_post, 'Welcome to {{Item}}!')
    
    def test_settings_view_integration_create_teams_disabled(self):
        """Integration test: Create settings with Teams disabled via view logic simulation"""
        post_data = {
            'teams_team_id': 'test-team-123',
            'max_tags_per_idea': '5'
        }
        
        # Create settings object as the view does
        settings = Settings.objects.create(
            teams_enabled=post_data.get('teams_enabled') == 'on',  # False when not present
            teams_team_id=post_data.get('teams_team_id', ''),
            team_welcome_post=post_data.get('team_welcome_post', ''),
            max_tags_per_idea=int(post_data.get('max_tags_per_idea') or 5)
        )
        
        # Verify toggle is disabled
        self.assertFalse(settings.teams_enabled)
        self.assertEqual(settings.teams_team_id, 'test-team-123')


class TeamsChannelCreationAPITestCase(TestCase):
    """Test suite for Teams channel creation API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin',  # Make user admin for testing poll endpoint
            is_active=True
        )
        self.user.set_password('test123')
        self.user.save()
        
        self.section = Section.objects.create(name='Test Section')
        
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user
        )
        
        self.client = Client()
        
        # Create session for user - convert UUID to string
        from django.contrib.sessions.models import Session
        session = self.client.session
        session['user_id'] = str(self.user.id)  # Convert UUID to string
        session.save()
    
    def test_create_teams_channel_csrf_exempt(self):
        """Test that create_teams_channel endpoint works without CSRF token"""
        
        url = f'/api/items/{self.item.id}/create-teams-channel'
        
        # Make POST request without CSRF token
        # This should not raise a 403 Forbidden error if @csrf_exempt is properly applied
        response = self.client.post(
            url,
            content_type='application/json'
        )
        
        # We expect a 401 or other error (due to missing Teams configuration),
        # but NOT a 403 CSRF error
        self.assertNotEqual(response.status_code, 403, 
                          "Endpoint should be CSRF exempt but returned 403 Forbidden")
    
    def test_poll_teams_messages_csrf_exempt(self):
        """Test that poll_teams_messages endpoint works without CSRF token"""
        
        url = '/api/teams/poll'
        
        # Make POST request without CSRF token
        response = self.client.post(
            url,
            content_type='application/json'
        )
        
        # Should not return 403 CSRF error
        self.assertNotEqual(response.status_code, 403,
                          "Endpoint should be CSRF exempt but returned 403 Forbidden")
    
    def test_teams_integration_status_csrf_exempt(self):
        """Test that teams_integration_status endpoint works without CSRF token"""
        
        url = '/api/teams/status'
        
        # Make GET request without CSRF token
        response = self.client.get(url)
        
        # Should not return 403 CSRF error
        self.assertNotEqual(response.status_code, 403,
                          "Endpoint should be CSRF exempt but returned 403 Forbidden")


class TeamsChannelDescriptionTestCase(TestCase):
    """Test suite for Teams channel description length validation"""
    
    def setUp(self):
        """Set up test data"""
        # Create settings for Teams service
        self.settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='test-team-id-123',
            team_welcome_post='Willkommen im Channel für {{Item}}!',
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret'
        )
    
    def test_channel_description_simple_format(self):
        """Test that channel description uses simple format"""
        from unittest.mock import Mock, patch, call
        
        # Mock the graph service to avoid actual API calls
        with patch('core.services.teams_service.GraphService') as mock_graph_service:
            mock_graph_instance = Mock()
            mock_graph_service.return_value = mock_graph_instance
            
            # Mock successful channel creation response
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                'id': 'test-channel-id',
                'displayName': 'Test Channel',
                'description': 'Projekt Channel für Test Channel',
                'webUrl': 'https://teams.microsoft.com/test'
            }
            mock_graph_instance._make_request.return_value = mock_response
            
            # Create Teams service and test channel creation
            teams_service = TeamsService(settings=self.settings)
            
            # Test with a long item description (should be ignored)
            long_description = "A" * 2000  # 2000 characters, way over the limit
            result = teams_service.create_channel_for_item(
                item_title="Test Channel",
                item_description=long_description
            )
            
            # Verify the service called _make_request with proper data
            self.assertTrue(mock_graph_instance._make_request.called)
            
            # Get the first call to _make_request (for channel creation, not message posting)
            first_call = mock_graph_instance._make_request.call_args_list[0]
            call_kwargs = first_call.kwargs
            
            # Verify json_data was passed
            self.assertIn('json_data', call_kwargs, "json_data should be in call arguments")
            json_data = call_kwargs['json_data']
            
            # Verify description uses simple format and is within limit
            description = json_data.get('description')
            self.assertIsNotNone(description, f"Description is None, json_data: {json_data}")
            self.assertEqual(description, 'Projekt Channel für Test Channel')
            self.assertLessEqual(len(description), 1024)
            
            # Verify result is successful
            self.assertTrue(result.get('success'))
    
    def test_channel_description_length_limit(self):
        """Test that excessively long descriptions are truncated"""
        from unittest.mock import Mock, patch
        
        with patch('core.services.teams_service.GraphService') as mock_graph_service:
            mock_graph_instance = Mock()
            mock_graph_service.return_value = mock_graph_instance
            
            # Mock successful channel creation response
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                'id': 'test-channel-id',
                'displayName': 'Test Channel',
                'description': 'Truncated description...',
                'webUrl': 'https://teams.microsoft.com/test'
            }
            mock_graph_instance._make_request.return_value = mock_response
            
            teams_service = TeamsService(settings=self.settings)
            
            # Test create_channel directly with a very long description
            very_long_description = "X" * 2000
            result = teams_service.create_channel(
                display_name="Test Channel",
                description=very_long_description
            )
            
            # Verify the service called _make_request
            self.assertTrue(mock_graph_instance._make_request.called)
            
            # Get the call arguments
            call_kwargs = mock_graph_instance._make_request.call_args.kwargs
            
            # Verify json_data was passed
            self.assertIn('json_data', call_kwargs, "json_data should be in call arguments")
            json_data = call_kwargs['json_data']
            
            # Check the description was truncated to fit within 1024 characters
            description = json_data.get('description')
            self.assertLessEqual(len(description), 1024)
            self.assertTrue(description.endswith('...'))
