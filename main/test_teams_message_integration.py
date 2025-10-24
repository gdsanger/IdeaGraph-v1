"""
Tests for Teams Message Integration
"""

from django.test import TestCase, Client
from unittest.mock import Mock, patch, MagicMock
from main.models import Settings, User as AppUser, Item, Section, Task
from core.services.teams_listener_service import TeamsListenerService
from core.services.message_processing_service import MessageProcessingService
from core.services.graph_response_service import GraphResponseService
from core.services.teams_integration_service import TeamsIntegrationService


class TeamsListenerServiceTestCase(TestCase):
    """Test suite for TeamsListenerService"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create settings with Teams enabled
        self.settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='test-team-id',
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret',
            default_mail_sender='bot@example.com'
        )
        
        # Create item with channel
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user,
            channel_id='test-channel-id'
        )
    
    def test_initialization_with_teams_disabled(self):
        """Test that service raises error when Teams is disabled"""
        self.settings.teams_enabled = False
        self.settings.save()
        
        from core.services.teams_listener_service import TeamsListenerServiceError
        
        with self.assertRaises(TeamsListenerServiceError):
            TeamsListenerService(settings=self.settings)
    
    def test_get_items_with_channels(self):
        """Test getting items with channel IDs"""
        with patch('core.services.teams_listener_service.GraphService'):
            service = TeamsListenerService(settings=self.settings)
            items = service.get_items_with_channels()
            
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].id, self.item.id)
    
    def test_get_items_with_channels_excludes_empty(self):
        """Test that items without channels are excluded"""
        # Create item without channel
        item_no_channel = Item.objects.create(
            title='No Channel Item',
            description='No channel',
            section=self.section,
            created_by=self.user,
            channel_id=''
        )
        
        with patch('core.services.teams_listener_service.GraphService'):
            service = TeamsListenerService(settings=self.settings)
            items = service.get_items_with_channels()
            
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].id, self.item.id)
    
    @patch('core.services.teams_listener_service.GraphService')
    def test_get_new_messages_filters_bot_messages(self, mock_graph_service):
        """Test that messages from IdeaGraph Bot are filtered out"""
        # Mock graph service response
        mock_instance = mock_graph_service.return_value
        mock_instance.get_channel_messages.return_value = {
            'success': True,
            'messages': [
                {
                    'id': 'msg-1',
                    'from': {
                        'user': {
                            'displayName': 'IdeaGraph Bot',
                            'userPrincipalName': 'bot@example.com'
                        }
                    },
                    'body': {'content': 'Bot message', 'contentType': 'text'}
                },
                {
                    'id': 'msg-2',
                    'from': {
                        'user': {
                            'displayName': 'Real User',
                            'userPrincipalName': 'user@example.com'
                        }
                    },
                    'body': {'content': 'User message', 'contentType': 'text'}
                }
            ]
        }
        
        service = TeamsListenerService(settings=self.settings)
        messages = service.get_new_messages_for_item(self.item)
        
        # Should only get one message (not from bot)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['id'], 'msg-2')
    
    @patch('core.services.teams_listener_service.GraphService')
    def test_get_new_messages_filters_bot_by_upn(self, mock_graph_service):
        """Test that messages from bot UPN (userPrincipalName) are filtered out"""
        # Mock graph service response with bot message using different display name
        # but matching UPN from settings
        mock_instance = mock_graph_service.return_value
        mock_instance.get_channel_messages.return_value = {
            'success': True,
            'messages': [
                {
                    'id': 'msg-1',
                    'from': {
                        'user': {
                            'displayName': 'ISARtec IdeaGraph Bot',  # Different display name
                            'userPrincipalName': 'bot@example.com'  # Matches settings
                        }
                    },
                    'body': {'content': 'Bot message', 'contentType': 'text'}
                },
                {
                    'id': 'msg-2',
                    'from': {
                        'user': {
                            'displayName': 'Real User',
                            'userPrincipalName': 'user@example.com'
                        }
                    },
                    'body': {'content': 'User message', 'contentType': 'text'}
                },
                {
                    'id': 'msg-3',
                    'from': {
                        'user': {
                            'displayName': 'Another User',
                            'userPrincipalName': 'BOT@EXAMPLE.COM'  # Case insensitive match
                        }
                    },
                    'body': {'content': 'Another bot message', 'contentType': 'text'}
                }
            ]
        }
        
        service = TeamsListenerService(settings=self.settings)
        messages = service.get_new_messages_for_item(self.item)
        
        # Should only get one message (not from bot by UPN, case insensitive)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['id'], 'msg-2')
        self.assertEqual(messages[0]['from']['user']['userPrincipalName'], 'user@example.com')
    
    @patch('core.services.teams_listener_service.GraphService')
    def test_get_new_messages_filters_bot_isartec_scenario(self, mock_graph_service):
        """Test the exact scenario from the issue: ISARtec IdeaGraph Bot with idea@isartec.de UPN"""
        # Update settings to use the real bot UPN from the issue
        self.settings.default_mail_sender = 'idea@isartec.de'
        self.settings.save()
        
        # Mock graph service response with the exact bot from the issue
        mock_instance = mock_graph_service.return_value
        mock_instance.get_channel_messages.return_value = {
            'success': True,
            'messages': [
                {
                    'id': 'msg-bot',
                    'from': {
                        'user': {
                            'displayName': 'ISARtec IdeaGraph Bot',
                            'userPrincipalName': 'idea@isartec.de',
                            'id': 'd00107be-fe52-4ec6-9a8a-a596e7a50434'
                        }
                    },
                    'body': {'content': 'Bot response message', 'contentType': 'text'}
                },
                {
                    'id': 'msg-user',
                    'from': {
                        'user': {
                            'displayName': 'Real User',
                            'userPrincipalName': 'user@isartec.de'
                        }
                    },
                    'body': {'content': 'User message', 'contentType': 'text'}
                }
            ]
        }
        
        service = TeamsListenerService(settings=self.settings)
        messages = service.get_new_messages_for_item(self.item)
        
        # Should only get the user message, not the bot message
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['id'], 'msg-user')
        self.assertEqual(messages[0]['from']['user']['userPrincipalName'], 'user@isartec.de')
    
    @patch('core.services.teams_listener_service.GraphService')
    def test_get_new_messages_filters_existing_tasks(self, mock_graph_service):
        """Test that messages with existing tasks are filtered out"""
        # Create task with message_id
        Task.objects.create(
            title='Existing Task',
            description='Task from message',
            item=self.item,
            message_id='msg-1'
        )
        
        # Mock graph service response
        mock_instance = mock_graph_service.return_value
        mock_instance.get_channel_messages.return_value = {
            'success': True,
            'messages': [
                {
                    'id': 'msg-1',
                    'from': {
                        'user': {
                            'displayName': 'User 1',
                            'userPrincipalName': 'user1@example.com'
                        }
                    },
                    'body': {'content': 'Message 1', 'contentType': 'text'}
                },
                {
                    'id': 'msg-2',
                    'from': {
                        'user': {
                            'displayName': 'User 2',
                            'userPrincipalName': 'user2@example.com'
                        }
                    },
                    'body': {'content': 'Message 2', 'contentType': 'text'}
                }
            ]
        }
        
        service = TeamsListenerService(settings=self.settings)
        messages = service.get_new_messages_for_item(self.item)
        
        # Should only get msg-2 (msg-1 already has a task)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['id'], 'msg-2')


class MessageProcessingServiceTestCase(TestCase):
    """Test suite for MessageProcessingService"""
    
    def setUp(self):
        """Set up test data"""
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        
        self.section = Section.objects.create(name='Test Section')
        
        self.settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='test-team-id',
            kigate_api_enabled=True,
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test-token'
        )
        
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user,
            channel_id='test-channel-id'
        )
    
    def test_extract_message_content_plain_text(self):
        """Test extracting content from plain text message"""
        with patch('core.services.message_processing_service.KiGateService'):
            service = MessageProcessingService(settings=self.settings)
            
            message = {
                'body': {
                    'content': 'This is a test message',
                    'contentType': 'text'
                }
            }
            
            content = service.extract_message_content(message)
            self.assertEqual(content, 'This is a test message')
    
    def test_extract_message_content_html(self):
        """Test extracting content from HTML message"""
        with patch('core.services.message_processing_service.KiGateService'):
            service = MessageProcessingService(settings=self.settings)
            
            message = {
                'body': {
                    'content': '<p>This is a <strong>test</strong> message</p>',
                    'contentType': 'html'
                }
            }
            
            content = service.extract_message_content(message)
            self.assertEqual(content, 'This is a test message')
    
    def test_get_or_create_user_existing(self):
        """Test getting existing user by UPN"""
        with patch('core.services.message_processing_service.KiGateService'):
            service = MessageProcessingService(settings=self.settings)
            
            # Use the existing user's username which matches the email
            user = service.get_or_create_user_from_upn('testuser', 'Test User')
            
            self.assertEqual(user.username, 'testuser')
            self.assertEqual(user.email, 'test@example.com')
    
    def test_get_or_create_user_new(self):
        """Test creating new user from UPN"""
        with patch('core.services.message_processing_service.KiGateService'):
            service = MessageProcessingService(settings=self.settings)
            
            user = service.get_or_create_user_from_upn('newuser@example.com', 'New User')
            
            self.assertEqual(user.username, 'newuser@example.com')
            self.assertEqual(user.email, 'newuser@example.com')
            self.assertEqual(user.first_name, 'New')
            self.assertEqual(user.last_name, 'User')
            self.assertEqual(user.role, 'user')
            self.assertEqual(user.auth_type, 'msauth')
    
    def test_should_create_task_positive(self):
        """Test detecting when task should be created"""
        with patch('core.services.message_processing_service.KiGateService'):
            service = MessageProcessingService(settings=self.settings)
            
            ai_response = "Task: Fix the bug\nDescription: This needs to be fixed"
            should_create = service._should_create_task(ai_response)
            
            self.assertTrue(should_create)
    
    def test_should_create_task_negative(self):
        """Test detecting when task should NOT be created"""
        with patch('core.services.message_processing_service.KiGateService'):
            service = MessageProcessingService(settings=self.settings)
            
            ai_response = "No task needed. This is just information."
            should_create = service._should_create_task(ai_response)
            
            self.assertFalse(should_create)
    
    @patch('core.services.message_processing_service.KiGateService')
    def test_create_task_from_analysis(self, mock_kigate_service):
        """Test creating task from analysis result"""
        service = MessageProcessingService(settings=self.settings)
        
        # Use a different email that doesn't exist yet
        message = {
            'id': 'msg-123',
            'from': {
                'user': {
                    'displayName': 'New Test User',
                    'userPrincipalName': 'newtest@example.com'
                }
            },
            'body': {'content': 'Need help with bug', 'contentType': 'text'}
        }
        
        analysis_result = {
            'success': True,
            'ai_response': 'I will help you fix this bug',
            'message_content': 'Need help with bug',
            'sender_upn': 'newtest@example.com',
            'sender_name': 'New Test User',
            'should_create_task': True
        }
        
        task = service.create_task_from_analysis(self.item, message, analysis_result)
        
        self.assertIsNotNone(task)
        self.assertEqual(task.item, self.item)
        self.assertEqual(task.message_id, 'msg-123')
        self.assertTrue(task.ai_generated)
        self.assertIn('Need help with bug', task.description)


class TeamsIntegrationAPITestCase(TestCase):
    """Test suite for Teams Integration API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create admin user
        self.admin_user = AppUser.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('admin123')
        self.admin_user.save()
        
        # Create regular user
        self.user = AppUser.objects.create(
            username='user',
            email='user@example.com',
            role='user',
            is_active=True
        )
        self.user.set_password('user123')
        self.user.save()
        
        # Get auth tokens
        from main.auth_utils import generate_jwt_token
        self.admin_token = generate_jwt_token(self.admin_user)
        self.user_token = generate_jwt_token(self.user)
        
        # Create settings
        self.settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='test-team-id',
            graph_api_enabled=True,
            tenant_id='test-tenant',
            client_id='test-client',
            client_secret='test-secret',
            kigate_api_enabled=True,
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test-token'
        )
        
        self.client = Client()
    
    def test_teams_status_endpoint_authenticated(self):
        """Test getting Teams status with authentication"""
        response = self.client.get(
            '/api/teams/status',
            HTTP_AUTHORIZATION=f'Bearer {self.user_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['status']['enabled'])
    
    def test_teams_status_endpoint_unauthenticated(self):
        """Test that unauthenticated requests are rejected"""
        response = self.client.get('/api/teams/status')
        
        self.assertEqual(response.status_code, 401)
    
    @patch('core.services.teams_integration_service.TeamsIntegrationService')
    def test_poll_endpoint_admin_only(self, mock_service):
        """Test that only admins can trigger polling"""
        # Regular user should be rejected
        response = self.client.post(
            '/api/teams/poll',
            HTTP_AUTHORIZATION=f'Bearer {self.user_token}'
        )
        
        self.assertEqual(response.status_code, 403)
    
    @patch('core.services.teams_integration_service.TeamsIntegrationService')
    def test_poll_endpoint_admin_success(self, mock_service):
        """Test successful polling by admin"""
        # Mock service response
        mock_instance = mock_service.return_value
        mock_instance.poll_and_process.return_value = {
            'success': True,
            'items_checked': 2,
            'messages_found': 5,
            'messages_processed': 5,
            'tasks_created': 2,
            'responses_posted': 5,
            'errors': []
        }
        
        response = self.client.post(
            '/api/teams/poll',
            HTTP_AUTHORIZATION=f'Bearer {self.admin_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['result']['messages_found'], 5)
        self.assertEqual(data['result']['tasks_created'], 2)


class TeamsManagementCommandTestCase(TestCase):
    """Test suite for poll_teams_messages management command"""
    
    def setUp(self):
        """Set up test data"""
        self.settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='test-team-id',
            graph_api_enabled=True,
            tenant_id='test-tenant',
            client_id='test-client',
            client_secret='test-secret',
            kigate_api_enabled=True,
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test-token',
            graph_poll_interval=60
        )
    
    @patch('main.management.commands.poll_teams_messages.TeamsIntegrationService')
    def test_command_runs_once(self, mock_service):
        """Test that command can run once and exit"""
        from django.core.management import call_command
        from io import StringIO
        
        # Mock service response
        mock_instance = mock_service.return_value
        mock_instance.poll_and_process.return_value = {
            'success': True,
            'items_checked': 1,
            'messages_found': 2,
            'messages_processed': 2,
            'tasks_created': 1,
            'responses_posted': 2,
            'errors': []
        }
        
        out = StringIO()
        call_command('poll_teams_messages', '--once', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Poll complete', output)
        mock_instance.poll_and_process.assert_called_once()


class MessageProcessingServiceRAGTestCase(TestCase):
    """Test suite for MessageProcessingService RAG functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        
        self.section = Section.objects.create(name='Test Section')
        
        self.settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='test-team-id',
            kigate_api_enabled=True,
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test-token'
        )
        
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user,
            channel_id='test-channel-id'
        )
    
    @patch('core.services.message_processing_service.WeaviateTaskSyncService')
    @patch('core.services.message_processing_service.WeaviateItemSyncService')
    @patch('core.services.message_processing_service.KiGateService')
    def test_search_similar_context_success(self, mock_kigate, mock_item_service, mock_task_service):
        """Test successful RAG context search"""
        # Mock task search results
        mock_task_instance = mock_task_service.return_value
        mock_task_instance.search_similar.return_value = {
            'success': True,
            'results': [
                {
                    'id': 'task-1',
                    'metadata': {
                        'title': 'Similar Task 1',
                        'description': 'This is a similar task',
                        'status': 'completed',
                        'owner': 'testuser',
                        'created_at': '2024-01-01T00:00:00'
                    },
                    'document': 'This is a similar task about fixing bugs',
                    'distance': 0.1
                }
            ]
        }
        
        # Mock item search results
        mock_item_instance = mock_item_service.return_value
        mock_item_instance.search_similar.return_value = {
            'success': True,
            'results': [
                {
                    'id': 'item-1',
                    'metadata': {
                        'title': 'Similar Item 1',
                        'description': 'This is a similar item',
                        'status': 'active',
                        'owner': 'testuser'
                    },
                    'document': 'This is a similar item about development',
                    'distance': 0.15
                }
            ]
        }
        
        service = MessageProcessingService(settings=self.settings)
        similar_objects = service.search_similar_context('bug fix help', max_results=3)
        
        self.assertEqual(len(similar_objects), 2)
        self.assertEqual(similar_objects[0]['type'], 'task')
        self.assertEqual(similar_objects[0]['title'], 'Similar Task 1')
        self.assertEqual(similar_objects[1]['type'], 'item')
        self.assertEqual(similar_objects[1]['title'], 'Similar Item 1')
    
    @patch('core.services.message_processing_service.WeaviateTaskSyncService')
    @patch('core.services.message_processing_service.WeaviateItemSyncService')
    @patch('core.services.message_processing_service.KiGateService')
    def test_search_similar_context_no_results(self, mock_kigate, mock_item_service, mock_task_service):
        """Test RAG context search with no results"""
        # Mock empty search results
        mock_task_instance = mock_task_service.return_value
        mock_task_instance.search_similar.return_value = {
            'success': True,
            'results': []
        }
        
        mock_item_instance = mock_item_service.return_value
        mock_item_instance.search_similar.return_value = {
            'success': True,
            'results': []
        }
        
        service = MessageProcessingService(settings=self.settings)
        similar_objects = service.search_similar_context('test query', max_results=3)
        
        self.assertEqual(len(similar_objects), 0)
    
    @patch('core.services.message_processing_service.KiGateService')
    def test_search_similar_context_weaviate_unavailable(self, mock_kigate):
        """Test RAG context search when Weaviate is unavailable"""
        # Don't mock Weaviate services to simulate unavailability
        with patch('core.services.message_processing_service.WeaviateItemSyncService', side_effect=Exception("Weaviate unavailable")):
            with patch('core.services.message_processing_service.WeaviateTaskSyncService', side_effect=Exception("Weaviate unavailable")):
                service = MessageProcessingService(settings=self.settings)
                
                # Service should initialize without Weaviate
                self.assertIsNone(service.weaviate_item_service)
                self.assertIsNone(service.weaviate_task_service)
                
                # Search should return empty list without failing
                similar_objects = service.search_similar_context('test query', max_results=3)
                self.assertEqual(len(similar_objects), 0)
    
    @patch('core.services.message_processing_service.WeaviateTaskSyncService')
    @patch('core.services.message_processing_service.WeaviateItemSyncService')
    @patch('core.services.message_processing_service.KiGateService')
    def test_analyze_message_with_rag_context(self, mock_kigate, mock_item_service, mock_task_service):
        """Test message analysis with RAG context enrichment"""
        # Mock Weaviate search results
        mock_task_instance = mock_task_service.return_value
        mock_task_instance.search_similar.return_value = {
            'success': True,
            'results': [
                {
                    'id': 'task-1',
                    'metadata': {
                        'title': 'Fix login bug',
                        'description': 'Users cannot log in',
                        'status': 'completed'
                    },
                    'document': 'Users cannot log in. Issue was fixed by updating auth module.',
                    'distance': 0.1
                }
            ]
        }
        
        mock_item_instance = mock_item_service.return_value
        mock_item_instance.search_similar.return_value = {
            'success': True,
            'results': []
        }
        
        # Mock KiGate response
        mock_kigate_instance = mock_kigate.return_value
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': 'Based on similar task "Fix login bug", I recommend checking the auth module. Task should be created: yes'
        }
        
        service = MessageProcessingService(settings=self.settings)
        
        message = {
            'id': 'msg-1',
            'from': {
                'user': {
                    'displayName': 'Test User',
                    'userPrincipalName': 'test@example.com'
                }
            },
            'body': {
                'content': 'Help! Users cannot login to the system',
                'contentType': 'text'
            }
        }
        
        result = service.analyze_message(message, self.item)
        
        self.assertTrue(result['success'])
        self.assertTrue(result.get('rag_context_used'))
        self.assertEqual(result.get('similar_objects_count'), 1)
        self.assertIn('auth module', result['ai_response'])
        
        # Verify KiGate was called with RAG context in prompt
        call_args = mock_kigate_instance.execute_agent.call_args
        prompt = call_args[1]['message']
        self.assertIn('Ähnliche Objekte aus der Wissensbasis', prompt)
        self.assertIn('Fix login bug', prompt)
    
    @patch('core.services.message_processing_service.WeaviateTaskSyncService')
    @patch('core.services.message_processing_service.WeaviateItemSyncService')
    @patch('core.services.message_processing_service.KiGateService')
    def test_format_rag_context(self, mock_kigate, mock_item_service, mock_task_service):
        """Test formatting of RAG context for AI prompt"""
        service = MessageProcessingService(settings=self.settings)
        
        similar_objects = [
            {
                'type': 'task',
                'title': 'Test Task 1',
                'description': 'This is a test task description'
            },
            {
                'type': 'item',
                'title': 'Test Item 1',
                'description': 'This is a test item description'
            }
        ]
        
        formatted = service._format_rag_context(similar_objects)
        
        self.assertIn('Ähnliche Objekte aus der Wissensbasis', formatted)
        self.assertIn('Task 1: Test Task 1', formatted)
        self.assertIn('Item 2: Test Item 1', formatted)
        self.assertIn('This is a test task description', formatted)
        self.assertIn('This is a test item description', formatted)
    
    @patch('core.services.message_processing_service.KiGateService')
    def test_format_rag_context_empty(self, mock_kigate):
        """Test formatting empty RAG context"""
        service = MessageProcessingService(settings=self.settings)
        
        formatted = service._format_rag_context([])
        
        self.assertEqual(formatted, "")


class TeamsMessageDeduplicationTestCase(TestCase):
    """Test suite for ensuring messages are not processed multiple times"""
    
    def setUp(self):
        """Set up test data"""
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='user',
            is_active=True
        )
        
        self.section = Section.objects.create(name='Test Section')
        
        self.settings = Settings.objects.create(
            teams_enabled=True,
            teams_team_id='test-team-id',
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret',
            default_mail_sender='bot@example.com',
            kigate_api_enabled=True,
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test-token'
        )
        
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            section=self.section,
            created_by=self.user,
            channel_id='test-channel-id'
        )
    
    @patch('core.services.teams_integration_service.WeaviateConversationSyncService')
    @patch('core.services.teams_integration_service.GraphResponseService')
    @patch('core.services.message_processing_service.KiGateService')
    @patch('core.services.teams_listener_service.GraphService')
    def test_message_processed_only_once(self, mock_graph_service, mock_kigate_service, 
                                        mock_response_service, mock_weaviate_service):
        """Test that a message is only processed once even if polled multiple times"""
        
        # Mock graph service response with the same message
        mock_graph_instance = mock_graph_service.return_value
        mock_graph_instance.get_channel_messages.return_value = {
            'success': True,
            'messages': [
                {
                    'id': 'msg-unique-123',
                    'from': {
                        'user': {
                            'displayName': 'Test User',
                            'userPrincipalName': 'testuser@example.com'
                        }
                    },
                    'body': {'content': 'This is a test message', 'contentType': 'text'}
                }
            ]
        }
        
        # Mock KiGate response
        mock_kigate_instance = mock_kigate_service.return_value
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': 'This is just informational. No task needed.'
        }
        
        # Mock response service
        mock_response_instance = mock_response_service.return_value
        mock_response_instance.post_response.return_value = {'success': True}
        
        # Mock Weaviate service
        mock_weaviate_instance = mock_weaviate_service.return_value
        mock_weaviate_instance.sync_conversation.return_value = {'success': True}
        
        # First poll - should process the message and create a task
        integration_service = TeamsIntegrationService(settings=self.settings)
        result1 = integration_service.poll_and_process()
        
        self.assertTrue(result1['success'])
        self.assertEqual(result1['messages_found'], 1)
        self.assertEqual(result1['messages_processed'], 1)
        self.assertEqual(result1['tasks_created'], 1)
        
        # Verify task was created with message_id
        tasks = Task.objects.filter(message_id='msg-unique-123')
        self.assertEqual(tasks.count(), 1)
        task = tasks.first()
        self.assertEqual(task.message_id, 'msg-unique-123')
        self.assertIn('This is a test message', task.description)
        
        # Second poll - should skip the message because task already exists
        result2 = integration_service.poll_and_process()
        
        self.assertTrue(result2['success'])
        self.assertEqual(result2['messages_found'], 0)  # Message filtered out
        self.assertEqual(result2['messages_processed'], 0)
        
        # Verify no duplicate task was created
        tasks = Task.objects.filter(message_id='msg-unique-123')
        self.assertEqual(tasks.count(), 1, "Should still only have one task")
        
        # Verify KiGate was only called once (first poll)
        self.assertEqual(mock_kigate_instance.execute_agent.call_count, 1)
    
    @patch('core.services.teams_integration_service.WeaviateConversationSyncService')
    @patch('core.services.teams_integration_service.GraphResponseService')
    @patch('core.services.message_processing_service.KiGateService')
    @patch('core.services.teams_listener_service.GraphService')
    def test_all_messages_create_tasks(self, mock_graph_service, mock_kigate_service,
                                       mock_response_service, mock_weaviate_service):
        """Test that all processed messages create tasks, even informational ones"""
        
        # Mock graph service response
        mock_graph_instance = mock_graph_service.return_value
        mock_graph_instance.get_channel_messages.return_value = {
            'success': True,
            'messages': [
                {
                    'id': 'msg-info-only',
                    'from': {
                        'user': {
                            'displayName': 'Test User',
                            'userPrincipalName': 'testuser@example.com'
                        }
                    },
                    'body': {'content': 'Just an FYI message', 'contentType': 'text'}
                }
            ]
        }
        
        # Mock KiGate response saying no task needed
        mock_kigate_instance = mock_kigate_service.return_value
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': 'No task needed. This is just information.'
        }
        
        # Mock response service
        mock_response_instance = mock_response_service.return_value
        mock_response_instance.post_response.return_value = {'success': True}
        
        # Mock Weaviate service
        mock_weaviate_instance = mock_weaviate_service.return_value
        mock_weaviate_instance.sync_conversation.return_value = {'success': True}
        
        # Process the message
        integration_service = TeamsIntegrationService(settings=self.settings)
        result = integration_service.poll_and_process()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['messages_found'], 1)
        self.assertEqual(result['messages_processed'], 1)
        
        # Verify task was created even though AI said "no task needed"
        self.assertEqual(result['tasks_created'], 1)
        tasks = Task.objects.filter(message_id='msg-info-only')
        self.assertEqual(tasks.count(), 1, "Task should be created for all messages")
        
        # Verify the task has the correct message_id for deduplication
        task = tasks.first()
        self.assertEqual(task.message_id, 'msg-info-only')
