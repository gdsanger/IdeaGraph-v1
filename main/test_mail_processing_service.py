"""
Tests for Mail Processing Service
"""

import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.cache import cache

from main.models import Settings, User as AppUser, Item, Task, Section
from core.services.mail_processing_service import MailProcessingService, MailProcessingServiceError


# Patch Weaviate initialization for all tests in this module
@patch('core.services.weaviate_sync_service.WeaviateItemSyncService._initialize_client')
class MailProcessingServiceTestCase(TestCase):
    """Test suite for MailProcessingService"""
    
    def setUp(self):
        """Set up test data"""
        # Clear cache before each test
        cache.clear()
        
        # Create test user
        self.user = AppUser.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description for testing mail processing',
            status='working',
            section=self.section,
            created_by=self.user
        )
        
        # Create settings with all APIs enabled
        self.settings = Settings.objects.create(
            graph_api_enabled=True,
            tenant_id='test-tenant-id',
            client_id='test-client-id',
            client_secret='test-client-secret',
            default_mail_sender='idea@angermeier.net',
            openai_api_enabled=True,
            openai_api_key='test-openai-key',
            openai_default_model='gpt-4',
            kigate_api_enabled=True,
            kigate_api_token='test-kigate-token',
            kigate_api_base_url='http://localhost:8000',
            weaviate_cloud_enabled=False
        )
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
    
    def test_init_without_settings(self, mock_weaviate_init):
        """Test MailProcessingService initialization without settings object"""
        with patch('main.models.Settings') as mock_settings_model:
            mock_settings_model.objects.first.return_value = self.settings
            service = MailProcessingService()
            self.assertIsNotNone(service.settings)
            self.assertIsNotNone(service.graph_service)
            self.assertIsNotNone(service.weaviate_service)
            self.assertIsNotNone(service.kigate_service)
            self.assertIsNotNone(service.openai_service)
    
    def test_init_with_disabled_services(self, mock_weaviate_init):
        """Test MailProcessingService initialization with some services disabled"""
        self.settings.kigate_api_enabled = False
        self.settings.openai_api_enabled = False
        self.settings.save()
        
        service = MailProcessingService(self.settings)
        self.assertIsNone(service.kigate_service)
        self.assertIsNone(service.openai_service)
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    def test_convert_html_to_markdown_success(self, mock_execute, mock_weaviate_init):
        """Test successful HTML to Markdown conversion"""
        mock_execute.return_value = {
            'success': True,
            'result': '# Test Heading\n\nTest paragraph'
        }
        
        service = MailProcessingService(self.settings)
        html = '<h1>Test Heading</h1><p>Test paragraph</p>'
        markdown = service.convert_html_to_markdown(html)
        
        self.assertEqual(markdown, '# Test Heading\n\nTest paragraph')
        mock_execute.assert_called_once()
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    def test_convert_html_to_markdown_failure(self, mock_execute, mock_weaviate_init):
        """Test HTML to Markdown conversion fallback on failure"""
        from core.services.kigate_service import KiGateServiceError
        mock_execute.side_effect = KiGateServiceError('KiGate error')
        
        service = MailProcessingService(self.settings)
        html = '<h1>Test Heading</h1>'
        markdown = service.convert_html_to_markdown(html)
        
        # Should fallback to basic HTML-to-Markdown conversion
        self.assertIn('Test Heading', markdown)
    
    def test_convert_html_to_markdown_no_kigate(self, mock_weaviate_init):
        """Test HTML to Markdown conversion without KiGate service"""
        self.settings.kigate_api_enabled = False
        self.settings.save()
        
        service = MailProcessingService(self.settings)
        html = '<h1>Test Heading</h1><p>Test paragraph</p>'
        markdown = service.convert_html_to_markdown(html)
        
        # Should return Markdown using fallback converter
        self.assertIn('# Test Heading', markdown)
        self.assertIn('Test paragraph', markdown)
        # Should NOT contain HTML tags
        self.assertNotIn('<h1>', markdown)
        self.assertNotIn('<p>', markdown)
    
    def test_convert_html_to_markdown_with_fallback_comprehensive(self, mock_weaviate_init):
        """Test comprehensive HTML to Markdown conversion with fallback converter"""
        self.settings.kigate_api_enabled = False
        self.settings.save()
        
        service = MailProcessingService(self.settings)
        
        # Test various HTML elements
        html = '''
        <h1>Main Heading</h1>
        <h2>Subheading</h2>
        <p>This is a <strong>bold</strong> and <em>italic</em> text.</p>
        <p>Here is a <a href="https://example.com">link</a>.</p>
        <ul>
            <li>First item</li>
            <li>Second item</li>
        </ul>
        <blockquote>A quote</blockquote>
        <p>Inline <code>code</code> example.</p>
        <pre><code>Code block</code></pre>
        '''
        
        markdown = service.convert_html_to_markdown(html)
        
        # Verify conversions
        self.assertIn('# Main Heading', markdown)
        self.assertIn('## Subheading', markdown)
        self.assertIn('**bold**', markdown)
        self.assertIn('*italic*', markdown)
        self.assertIn('[link](https://example.com)', markdown)
        self.assertIn('- First item', markdown)
        self.assertIn('- Second item', markdown)
        self.assertIn('`code`', markdown)
        
        # Verify no HTML tags remain
        self.assertNotIn('<h1>', markdown)
        self.assertNotIn('<p>', markdown)
        self.assertNotIn('<strong>', markdown)
        self.assertNotIn('<em>', markdown)
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    def test_convert_markdown_to_html_success(self, mock_execute, mock_weaviate_init):
        """Test successful Markdown to HTML conversion"""
        mock_execute.return_value = {
            'success': True,
            'result': '<h1>Test Heading</h1><p>Test paragraph</p>'
        }
        
        service = MailProcessingService(self.settings)
        markdown = '# Test Heading\n\nTest paragraph'
        html = service.convert_markdown_to_html(markdown)
        
        # Should return the HTML from KiGate
        self.assertIn('<h1>Test Heading</h1>', html)
        self.assertIn('<p>Test paragraph</p>', html)
        mock_execute.assert_called_once()
    
    def test_convert_markdown_to_html_with_fallback(self, mock_weaviate_init):
        """Test Markdown to HTML conversion using fallback converter"""
        # Disable KiGate to force fallback
        self.settings.kigate_api_enabled = False
        self.settings.save()
        
        service = MailProcessingService(self.settings)
        markdown = '# Heading\n\n**Bold** and *italic* text.\n\n- Item 1\n- Item 2'
        html = service.convert_markdown_to_html(markdown)
        
        # Should contain HTML elements
        self.assertIn('<h1>Heading</h1>', html)
        self.assertIn('<strong>Bold</strong>', html)
        self.assertIn('<em>italic</em>', html)
        self.assertIn('<ul>', html)
        self.assertIn('<li>Item 1</li>', html)
    
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    def test_find_matching_item_success(self, mock_search, mock_weaviate_init):
        """Test finding matching item successfully"""
        mock_search.return_value = {
            'success': True,
            'results': [
                {
                    'id': str(self.item.id),
                    'metadata': {
                        'title': self.item.title,
                        'description': self.item.description,
                        'section': self.section.name,
                        'status': self.item.status
                    },
                    'distance': 0.1
                }
            ]
        }
        
        service = MailProcessingService(self.settings)
        mail_content = 'Subject: Test\n\nTest mail content'
        result = service.find_matching_item(mail_content)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], str(self.item.id))
        self.assertEqual(result['metadata']['title'], self.item.title)
    
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    def test_find_matching_item_no_results(self, mock_search, mock_weaviate_init):
        """Test finding matching item when no results found"""
        mock_search.return_value = {
            'success': True,
            'results': []
        }
        
        service = MailProcessingService(self.settings)
        mail_content = 'Subject: Test\n\nTest mail content'
        result = service.find_matching_item(mail_content)
        
        self.assertIsNone(result)
    
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    @patch('core.services.openai_service.OpenAIService.chat_completion')
    def test_find_matching_item_with_ai_selection(self, mock_chat, mock_search, mock_weaviate_init):
        """Test finding matching item with AI selection from multiple results"""
        # Create second item
        item2 = Item.objects.create(
            title='Another Item',
            description='Another description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        mock_search.return_value = {
            'success': True,
            'results': [
                {
                    'id': str(self.item.id),
                    'metadata': {
                        'title': self.item.title,
                        'description': self.item.description,
                        'section': self.section.name,
                        'status': self.item.status
                    },
                    'distance': 0.1
                },
                {
                    'id': str(item2.id),
                    'metadata': {
                        'title': item2.title,
                        'description': item2.description,
                        'section': self.section.name,
                        'status': item2.status
                    },
                    'distance': 0.2
                }
            ]
        }
        
        # AI selects the second item
        mock_chat.return_value = {
            'success': True,
            'content': str(item2.id)
        }
        
        service = MailProcessingService(self.settings)
        mail_content = 'Subject: Test\n\nTest mail content'
        result = service.find_matching_item(mail_content)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], str(item2.id))
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    def test_generate_normalized_description_success(self, mock_execute, mock_weaviate_init):
        """Test generating normalized description successfully with KiGate agent"""
        mock_execute.return_value = {
            'success': True,
            'result': 'Normalisierte Aufgabenbeschreibung\n\nggf. noch zu klären:\n- Punkt 1\n\n---\nOriginale E-Mail:\n\nBetreff: Test\n\nOriginaler Inhalt'
        }
        
        service = MailProcessingService(self.settings)
        result = service.generate_normalized_description(
            mail_subject='Test',
            mail_body='Original content',
            item_context={
                'id': str(self.item.id),
                'metadata': {
                    'title': self.item.title,
                    'description': self.item.description,
                    'section': self.section.name
                }
            }
        )
        
        self.assertIn('Normalisierte Aufgabenbeschreibung', result)
        self.assertIn('Originale E-Mail', result)
        # Verify the KiGate agent was called
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        self.assertEqual(call_args[1]['agent_name'], 'teams-support-analysis-agent')
        self.assertEqual(call_args[1]['provider'], 'openai')
        self.assertEqual(call_args[1]['model'], 'gpt-4o-mini')
    
    def test_generate_normalized_description_no_kigate(self, mock_weaviate_init):
        """Test generating normalized description without KiGate"""
        self.settings.kigate_api_enabled = False
        self.settings.save()
        
        service = MailProcessingService(self.settings)
        result = service.generate_normalized_description(
            mail_subject='Test',
            mail_body='Original content'
        )
        
        # Should return formatted original content
        self.assertIn('Original content', result)
        self.assertIn('Originale E-Mail', result)
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    def test_generate_normalized_description_kigate_failure(self, mock_execute, mock_weaviate_init):
        """Test generating normalized description when KiGate fails"""
        mock_execute.return_value = {
            'success': False,
            'error': 'Agent execution failed'
        }
        
        service = MailProcessingService(self.settings)
        result = service.generate_normalized_description(
            mail_subject='Test',
            mail_body='Original content'
        )
        
        # Should return formatted original content as fallback
        self.assertIn('Original content', result)
        self.assertIn('Originale E-Mail', result)
    
    def test_create_task_from_mail_success(self, mock_weaviate_init):
        """Test creating task from mail successfully"""
        service = MailProcessingService(self.settings)
        
        result = service.create_task_from_mail(
            mail_subject='Test Task',
            mail_body_markdown='Test task description',
            item_id=str(self.item.id),
            sender_email=self.user.email
        )
        
        self.assertIsNotNone(result)
        self.assertIn('id', result)
        self.assertEqual(result['title'], 'Test Task')
        self.assertEqual(result['item_id'], str(self.item.id))
        
        # Verify task was created
        task = Task.objects.get(id=result['id'])
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.description, 'Test task description')
        self.assertEqual(task.status, 'new')
        self.assertEqual(task.item, self.item)
        self.assertEqual(task.requester, self.user)
        self.assertEqual(task.created_by, self.user)
    
    def test_create_task_from_mail_unknown_sender(self, mock_weaviate_init):
        """Test creating task from mail with unknown sender - auto-creates user"""
        service = MailProcessingService(self.settings)
        
        result = service.create_task_from_mail(
            mail_subject='Test Task',
            mail_body_markdown='Test task description',
            item_id=str(self.item.id),
            sender_email='unknown@example.com'
        )
        
        self.assertIsNotNone(result)
        
        # Verify task was created with auto-created requester
        task = Task.objects.get(id=result['id'])
        self.assertIsNotNone(task.requester)
        self.assertEqual(task.requester.email, 'unknown@example.com')
        self.assertEqual(task.requester.username, 'unknown@example.com')
        self.assertEqual(task.requester.role, 'user')
        self.assertTrue(task.requester.is_active)
        self.assertIsNotNone(task.created_by)
        self.assertEqual(task.created_by, task.requester)
    
    def test_create_task_from_mail_with_sender_name(self, mock_weaviate_init):
        """Test creating task from mail with sender name - extracts first and last name"""
        service = MailProcessingService(self.settings)
        
        result = service.create_task_from_mail(
            mail_subject='Test Task',
            mail_body_markdown='Test task description',
            item_id=str(self.item.id),
            sender_email='john.doe@example.com',
            sender_name='John Doe'
        )
        
        self.assertIsNotNone(result)
        
        # Verify task was created with auto-created requester
        task = Task.objects.get(id=result['id'])
        self.assertIsNotNone(task.requester)
        self.assertEqual(task.requester.email, 'john.doe@example.com')
        self.assertEqual(task.requester.username, 'john.doe@example.com')
        self.assertEqual(task.requester.first_name, 'John')
        self.assertEqual(task.requester.last_name, 'Doe')
        self.assertEqual(task.requester.role, 'user')
        self.assertTrue(task.requester.is_active)
    
    def test_create_task_from_mail_with_single_name(self, mock_weaviate_init):
        """Test creating task from mail with single name - sets only first name"""
        service = MailProcessingService(self.settings)
        
        result = service.create_task_from_mail(
            mail_subject='Test Task',
            mail_body_markdown='Test task description',
            item_id=str(self.item.id),
            sender_email='madonna@example.com',
            sender_name='Madonna'
        )
        
        self.assertIsNotNone(result)
        
        # Verify task was created with auto-created requester
        task = Task.objects.get(id=result['id'])
        self.assertIsNotNone(task.requester)
        self.assertEqual(task.requester.email, 'madonna@example.com')
        self.assertEqual(task.requester.first_name, 'Madonna')
        self.assertEqual(task.requester.last_name, '')
        self.assertEqual(task.requester.role, 'user')
    
    def test_create_task_from_mail_with_compound_last_name(self, mock_weaviate_init):
        """Test creating task from mail with compound last name"""
        service = MailProcessingService(self.settings)
        
        result = service.create_task_from_mail(
            mail_subject='Test Task',
            mail_body_markdown='Test task description',
            item_id=str(self.item.id),
            sender_email='maria.garcia@example.com',
            sender_name='Maria Garcia Lopez'
        )
        
        self.assertIsNotNone(result)
        
        # Verify task was created with auto-created requester
        task = Task.objects.get(id=result['id'])
        self.assertIsNotNone(task.requester)
        self.assertEqual(task.requester.first_name, 'Maria')
        self.assertEqual(task.requester.last_name, 'Garcia Lopez')
    
    def test_create_task_from_mail_invalid_item(self, mock_weaviate_init):
        """Test creating task with invalid item ID"""
        service = MailProcessingService(self.settings)
        
        result = service.create_task_from_mail(
            mail_subject='Test Task',
            mail_body_markdown='Test task description',
            item_id='00000000-0000-0000-0000-000000000000',
            sender_email=self.user.email
        )
        
        self.assertIsNone(result)
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.graph_service.GraphService.send_mail')
    def test_send_confirmation_email_success(self, mock_send, mock_execute, mock_weaviate_init):
        """Test sending confirmation email successfully"""
        mock_execute.return_value = {
            'success': True,
            'result': '<p>Test HTML</p>'
        }
        mock_send.return_value = {'success': True}
        
        service = MailProcessingService(self.settings)
        result = service.send_confirmation_email(
            recipient_email='test@example.com',
            mail_subject='Test Subject',
            normalized_description='Test description',
            item_title=self.item.title
        )
        
        self.assertTrue(result['success'])
        self.assertIn('email_body_markdown', result)
        self.assertIn('email_body_html', result)
        mock_send.assert_called_once()
    
    @patch('core.services.graph_service.GraphService.send_mail')
    def test_send_confirmation_email_failure(self, mock_send, mock_weaviate_init):
        """Test sending confirmation email failure"""
        mock_send.side_effect = Exception('Send mail error')
        
        service = MailProcessingService(self.settings)
        result = service.send_confirmation_email(
            recipient_email='test@example.com',
            mail_subject='Test Subject',
            normalized_description='Test description',
            item_title=self.item.title
        )
        
        self.assertFalse(result['success'])
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    @patch('core.services.openai_service.OpenAIService.chat_completion')
    @patch('core.services.graph_service.GraphService.send_mail')
    @patch('core.services.graph_service.GraphService.mark_message_as_read')
    @patch('core.services.graph_service.GraphService.move_message')
    def test_process_mail_success(self, mock_move, mock_mark_read, mock_send, mock_chat, mock_search, mock_execute, mock_weaviate_init):
        """Test processing a single mail successfully"""
        # Setup mocks
        # Mock execute_agent returns different values based on agent
        def execute_agent_side_effect(*args, **kwargs):
            agent_name = kwargs.get('agent_name', '')
            if agent_name == 'html-to-markdown-converter':
                return {'success': True, 'result': 'Converted content'}
            elif agent_name == 'teams-support-analysis-agent':
                return {'success': True, 'result': 'Normalisierte Beschreibung\n\n---\nOriginale E-Mail:\n\nTest'}
            elif agent_name == 'markdown-to-html-converter':
                return {'success': True, 'result': '<p>HTML content</p>'}
            return {'success': False}
        
        mock_execute.side_effect = execute_agent_side_effect
        
        mock_search.return_value = {
            'success': True,
            'results': [
                {
                    'id': str(self.item.id),
                    'metadata': {
                        'title': self.item.title,
                        'description': self.item.description,
                        'section': self.section.name,
                        'status': self.item.status
                    },
                    'distance': 0.1
                }
            ]
        }
        mock_send.return_value = {'success': True}
        mock_mark_read.return_value = {'success': True}
        mock_move.return_value = {'success': True}
        
        # Create test message
        message = {
            'id': 'msg-123',
            'subject': 'Test Mail',
            'body': {
                'content': '<p>Test content</p>'
            },
            'from': {
                'emailAddress': {
                    'address': self.user.email
                }
            }
        }
        
        service = MailProcessingService(self.settings)
        result = service.process_mail(message)
        
        self.assertTrue(result['success'])
        self.assertIn('task_id', result)
        self.assertEqual(result['item_id'], str(self.item.id))
        self.assertTrue(result['confirmation_sent'])
        self.assertTrue(result.get('archived', False))
        
        # Verify task was created
        task = Task.objects.get(id=result['task_id'])
        self.assertEqual(task.title, 'Test Mail')
        
        # Verify that move_message was called
        mock_move.assert_called_once_with('msg-123', destination_folder='archive')
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    @patch('core.services.openai_service.OpenAIService.chat_completion')
    @patch('core.services.graph_service.GraphService.send_mail')
    @patch('core.services.graph_service.GraphService.mark_message_as_read')
    @patch('core.services.graph_service.GraphService.move_message')
    def test_process_mail_extracts_sender_name(self, mock_move, mock_mark_read, mock_send, mock_chat, mock_search, mock_execute, mock_weaviate_init):
        """Test that process_mail extracts sender name and creates user with proper first/last name"""
        # Setup mocks
        def execute_agent_side_effect(*args, **kwargs):
            agent_name = kwargs.get('agent_name', '')
            if agent_name == 'html-to-markdown-converter':
                return {'success': True, 'result': 'Converted content'}
            elif agent_name == 'teams-support-analysis-agent':
                return {'success': True, 'result': 'Normalisierte Beschreibung\n\n---\nOriginale E-Mail:\n\nTest'}
            elif agent_name == 'markdown-to-html-converter':
                return {'success': True, 'result': '<p>HTML content</p>'}
            return {'success': False}
        
        mock_execute.side_effect = execute_agent_side_effect
        
        mock_search.return_value = {
            'success': True,
            'results': [
                {
                    'id': str(self.item.id),
                    'metadata': {
                        'title': self.item.title,
                        'description': self.item.description,
                        'section': self.section.name,
                        'status': self.item.status
                    },
                    'distance': 0.1
                }
            ]
        }
        mock_send.return_value = {'success': True}
        mock_mark_read.return_value = {'success': True}
        mock_move.return_value = {'success': True}
        
        # Create test message with sender name
        message = {
            'id': 'msg-456',
            'subject': 'Test Mail from New User',
            'body': {
                'content': '<p>Test content from new user</p>'
            },
            'from': {
                'emailAddress': {
                    'address': 'jane.smith@example.com',
                    'name': 'Jane Smith'
                }
            }
        }
        
        service = MailProcessingService(self.settings)
        result = service.process_mail(message)
        
        self.assertTrue(result['success'])
        self.assertIn('task_id', result)
        
        # Verify task was created with requester having proper name
        task = Task.objects.get(id=result['task_id'])
        self.assertIsNotNone(task.requester)
        self.assertEqual(task.requester.email, 'jane.smith@example.com')
        self.assertEqual(task.requester.username, 'jane.smith@example.com')
        self.assertEqual(task.requester.first_name, 'Jane')
        self.assertEqual(task.requester.last_name, 'Smith')
        self.assertEqual(task.requester.role, 'user')
        self.assertTrue(task.requester.is_active)
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    @patch('core.services.openai_service.OpenAIService.chat_completion')
    @patch('core.services.graph_service.GraphService.send_mail')
    @patch('core.services.graph_service.GraphService.mark_message_as_read')
    @patch('core.services.graph_service.GraphService.move_message')
    def test_process_mail_archive_failure(self, mock_move, mock_mark_read, mock_send, mock_chat, mock_search, mock_execute, mock_weaviate_init):
        """Test processing mail when archiving fails - should still succeed"""
        # Setup mocks
        # Mock execute_agent returns different values based on agent
        def execute_agent_side_effect(*args, **kwargs):
            agent_name = kwargs.get('agent_name', '')
            if agent_name == 'html-to-markdown-converter':
                return {'success': True, 'result': 'Converted content'}
            elif agent_name == 'teams-support-analysis-agent':
                return {'success': True, 'result': 'Normalisierte Beschreibung\n\n---\nOriginale E-Mail:\n\nTest'}
            elif agent_name == 'markdown-to-html-converter':
                return {'success': True, 'result': '<p>HTML content</p>'}
            return {'success': False}
        
        mock_execute.side_effect = execute_agent_side_effect
        
        mock_search.return_value = {
            'success': True,
            'results': [
                {
                    'id': str(self.item.id),
                    'metadata': {
                        'title': self.item.title,
                        'description': self.item.description,
                        'section': self.section.name,
                        'status': self.item.status
                    },
                    'distance': 0.1
                }
            ]
        }
        mock_send.return_value = {'success': True}
        mock_mark_read.return_value = {'success': True}
        # Archiving fails with GraphServiceError (not generic Exception)
        from core.services.graph_service import GraphServiceError
        mock_move.side_effect = GraphServiceError('Archive folder not found')
        
        # Create test message
        message = {
            'id': 'msg-123',
            'subject': 'Test Mail',
            'body': {
                'content': '<p>Test content</p>'
            },
            'from': {
                'emailAddress': {
                    'address': self.user.email
                }
            }
        }
        
        service = MailProcessingService(self.settings)
        result = service.process_mail(message)
        
        # Should still succeed even if archiving fails
        self.assertTrue(result['success'])
        self.assertIn('task_id', result)
        self.assertEqual(result['item_id'], str(self.item.id))
        self.assertTrue(result['confirmation_sent'])
        self.assertFalse(result.get('archived', True))  # archived should be False
        
        # Verify task was created
        task = Task.objects.get(id=result['task_id'])
        self.assertEqual(task.title, 'Test Mail')
    
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    def test_process_mail_no_matching_item(self, mock_search, mock_weaviate_init):
        """Test processing mail when no matching item found"""
        mock_search.return_value = {
            'success': True,
            'results': []
        }
        
        message = {
            'id': 'msg-123',
            'subject': 'Test Mail',
            'body': {
                'content': '<p>Test content</p>'
            },
            'from': {
                'emailAddress': {
                    'address': self.user.email
                }
            }
        }
        
        service = MailProcessingService(self.settings)
        result = service.process_mail(message)
        
        self.assertFalse(result['success'])
        self.assertIn('No matching item', result['message'])
    
    @patch('core.services.graph_service.GraphService.get_mailbox_messages')
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    @patch('core.services.openai_service.OpenAIService.chat_completion')
    @patch('core.services.graph_service.GraphService.send_mail')
    @patch('core.services.graph_service.GraphService.mark_message_as_read')
    @patch('core.services.graph_service.GraphService.move_message')
    def test_process_mailbox_success(self, mock_move, mock_mark_read, mock_send, mock_chat, mock_search, mock_execute, mock_get_messages, mock_weaviate_init):
        """Test processing entire mailbox successfully"""
        # Setup mocks
        mock_get_messages.return_value = {
            'success': True,
            'messages': [
                {
                    'id': 'msg-1',
                    'subject': 'Test Mail 1',
                    'body': {'content': '<p>Content 1</p>'},
                    'from': {'emailAddress': {'address': self.user.email}}
                },
                {
                    'id': 'msg-2',
                    'subject': 'Test Mail 2',
                    'body': {'content': '<p>Content 2</p>'},
                    'from': {'emailAddress': {'address': self.user.email}}
                }
            ]
        }
        
        # Mock execute_agent returns different values based on agent
        def execute_agent_side_effect(*args, **kwargs):
            agent_name = kwargs.get('agent_name', '')
            if agent_name == 'html-to-markdown-converter':
                return {'success': True, 'result': 'Converted'}
            elif agent_name == 'teams-support-analysis-agent':
                return {'success': True, 'result': 'Normalisiert\n\n---\nOriginale E-Mail:\n\nTest'}
            elif agent_name == 'markdown-to-html-converter':
                return {'success': True, 'result': '<p>HTML content</p>'}
            return {'success': False}
        
        mock_execute.side_effect = execute_agent_side_effect
        
        mock_search.return_value = {
            'success': True,
            'results': [
                {
                    'id': str(self.item.id),
                    'metadata': {
                        'title': self.item.title,
                        'description': self.item.description,
                        'section': self.section.name,
                        'status': self.item.status
                    },
                    'distance': 0.1
                }
            ]
        }
        mock_send.return_value = {'success': True}
        mock_mark_read.return_value = {'success': True}
        mock_move.return_value = {'success': True}
        
        service = MailProcessingService(self.settings)
        result = service.process_mailbox(max_messages=10)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_messages'], 2)
        self.assertEqual(result['processed'], 2)
        self.assertEqual(result['failed'], 0)
    
    @patch('core.services.graph_service.GraphService.get_mailbox_messages')
    def test_process_mailbox_no_messages(self, mock_get_messages, mock_weaviate_init):
        """Test processing mailbox with no messages"""
        mock_get_messages.return_value = {
            'success': True,
            'messages': []
        }
        
        service = MailProcessingService(self.settings)
        result = service.process_mailbox()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_messages'], 0)
        self.assertEqual(result['processed'], 0)
    
    def test_add_comment_to_task_with_user(self, mock_weaviate_init):
        """Test adding a comment to a task with a user as author"""
        # Create a task first
        task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            item=self.item,
            created_by=self.user,
            status='new'
        )
        
        service = MailProcessingService(self.settings)
        success = service.add_comment_to_task(
            task_id=str(task.id),
            comment_text='This is a test comment',
            author_user=self.user,
            author_name='',
            source='user'
        )
        
        self.assertTrue(success)
        
        # Verify comment was created
        from main.models import TaskComment
        comments = TaskComment.objects.filter(task=task)
        self.assertEqual(comments.count(), 1)
        comment = comments.first()
        self.assertEqual(comment.text, 'This is a test comment')
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.source, 'user')
    
    def test_add_comment_to_task_with_agent(self, mock_weaviate_init):
        """Test adding a comment to a task with agent as author"""
        # Create a task first
        task = Task.objects.create(
            title='Test Task',
            description='Test Description',
            item=self.item,
            created_by=self.user,
            status='new'
        )
        
        service = MailProcessingService(self.settings)
        success = service.add_comment_to_task(
            task_id=str(task.id),
            comment_text='This is an agent comment',
            author_user=None,
            author_name='AI Agent Bot',
            source='agent'
        )
        
        self.assertTrue(success)
        
        # Verify comment was created
        from main.models import TaskComment
        comments = TaskComment.objects.filter(task=task)
        self.assertEqual(comments.count(), 1)
        comment = comments.first()
        self.assertEqual(comment.text, 'This is an agent comment')
        self.assertIsNone(comment.author)
        self.assertEqual(comment.author_name, 'AI Agent Bot')
        self.assertEqual(comment.source, 'agent')
    
    def test_add_comment_to_nonexistent_task(self, mock_weaviate_init):
        """Test adding a comment to a non-existent task fails gracefully"""
        service = MailProcessingService(self.settings)
        success = service.add_comment_to_task(
            task_id='00000000-0000-0000-0000-000000000000',
            comment_text='This should fail',
            author_user=self.user,
            author_name='',
            source='user'
        )
        
        self.assertFalse(success)
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    @patch('core.services.graph_service.GraphService.send_mail')
    @patch('core.services.graph_service.GraphService.mark_message_as_read')
    @patch('core.services.graph_service.GraphService.move_message')
    def test_process_mail_creates_comments(self, mock_move, mock_mark_read, mock_send, mock_search, mock_execute, mock_weaviate_init):
        """Test that processing mail creates both incoming and outgoing comments"""
        # Setup mocks
        def execute_agent_side_effect(*args, **kwargs):
            agent_name = kwargs.get('agent_name', '')
            if agent_name == 'html-to-markdown-converter':
                return {'success': True, 'result': 'Converted mail content'}
            elif agent_name == 'teams-support-analysis-agent':
                return {'success': True, 'result': 'Normalized description'}
            elif agent_name == 'markdown-to-html-converter':
                return {'success': True, 'result': '<p>HTML content</p>'}
            return {'success': False}
        
        mock_execute.side_effect = execute_agent_side_effect
        
        mock_search.return_value = {
            'success': True,
            'results': [
                {
                    'id': str(self.item.id),
                    'metadata': {
                        'title': self.item.title,
                        'description': self.item.description,
                        'section': self.section.name,
                        'status': self.item.status
                    },
                    'distance': 0.1
                }
            ]
        }
        mock_send.return_value = {'success': True}
        mock_mark_read.return_value = {'success': True}
        mock_move.return_value = {'success': True}
        
        # Create test message
        message = {
            'id': 'msg-123',
            'subject': 'Test Mail Subject',
            'body': {
                'content': '<p>Test mail body</p>'
            },
            'from': {
                'emailAddress': {
                    'address': self.user.email,
                    'name': 'Test User'
                }
            }
        }
        
        service = MailProcessingService(self.settings)
        result = service.process_mail(message)
        
        self.assertTrue(result['success'])
        self.assertIn('task_id', result)
        
        # Verify task was created
        task = Task.objects.get(id=result['task_id'])
        self.assertEqual(task.title, 'Test Mail Subject')
        
        # Verify comments were created
        from main.models import TaskComment
        comments = TaskComment.objects.filter(task=task).order_by('created_at')
        self.assertEqual(comments.count(), 2)
        
        # First comment should be the original mail (from user)
        original_comment = comments[0]
        self.assertEqual(original_comment.source, 'user')
        self.assertEqual(original_comment.author, self.user)
        self.assertIn('Test Mail Subject', original_comment.text)
        self.assertIn('Converted mail content', original_comment.text)
        
        # Second comment should be the confirmation email (from agent)
        confirmation_comment = comments[1]
        self.assertEqual(confirmation_comment.source, 'agent')
        self.assertIsNone(confirmation_comment.author)
        self.assertEqual(confirmation_comment.author_name, 'AI Agent Bot')
        self.assertIn('Ihr Anliegen wurde erfolgreich erfasst', confirmation_comment.text)
