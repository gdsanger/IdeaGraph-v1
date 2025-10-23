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
    def test_convert_html_to_markdown_success(self, mock_weaviate_init, mock_execute):
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
    def test_convert_html_to_markdown_failure(self, mock_weaviate_init, mock_execute):
        """Test HTML to Markdown conversion fallback on failure"""
        mock_execute.side_effect = Exception('KiGate error')
        
        service = MailProcessingService(self.settings)
        html = '<h1>Test Heading</h1>'
        markdown = service.convert_html_to_markdown(html)
        
        # Should return original HTML on error
        self.assertEqual(markdown, html)
    
    def test_convert_html_to_markdown_no_kigate(self, mock_weaviate_init):
        """Test HTML to Markdown conversion without KiGate service"""
        self.settings.kigate_api_enabled = False
        self.settings.save()
        
        service = MailProcessingService(self.settings)
        html = '<h1>Test Heading</h1>'
        markdown = service.convert_html_to_markdown(html)
        
        # Should return original HTML when service not available
        self.assertEqual(markdown, html)
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    def test_convert_markdown_to_html_success(self, mock_weaviate_init, mock_execute):
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
    def test_find_matching_item_success(self, mock_weaviate_init, mock_search):
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
    def test_find_matching_item_no_results(self, mock_weaviate_init, mock_search):
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
    def test_find_matching_item_with_ai_selection(self, mock_weaviate_init, mock_chat, mock_search):
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
    
    @patch('core.services.openai_service.OpenAIService.chat_completion')
    def test_generate_normalized_description_success(self, mock_weaviate_init, mock_chat):
        """Test generating normalized description successfully"""
        mock_chat.return_value = {
            'success': True,
            'content': 'Normalisierte Aufgabenbeschreibung\n\nggf. noch zu klären:\n- Punkt 1\n\n---\nOriginale E-Mail:\n\nBetreff: Test\n\nOriginaler Inhalt'
        }
        
        service = MailProcessingService(self.settings)
        result = service.generate_normalized_description(
            mail_subject='Test',
            mail_body='Original content',
            item_context={
                'metadata': {
                    'title': self.item.title,
                    'description': self.item.description,
                    'section': self.section.name
                }
            }
        )
        
        self.assertIn('Normalisierte Aufgabenbeschreibung', result)
        self.assertIn('Originale E-Mail', result)
    
    def test_generate_normalized_description_no_openai(self, mock_weaviate_init):
        """Test generating normalized description without OpenAI"""
        self.settings.openai_api_enabled = False
        self.settings.save()
        
        service = MailProcessingService(self.settings)
        result = service.generate_normalized_description(
            mail_subject='Test',
            mail_body='Original content'
        )
        
        # Should return formatted original content
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
    
    def test_create_task_from_mail_invalid_item(self):
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
    def test_send_confirmation_email_success(self, mock_weaviate_init, mock_send, mock_execute):
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
        
        self.assertTrue(result)
        mock_send.assert_called_once()
    
    @patch('core.services.graph_service.GraphService.send_mail')
    def test_send_confirmation_email_failure(self, mock_weaviate_init, mock_send):
        """Test sending confirmation email failure"""
        mock_send.side_effect = Exception('Send mail error')
        
        service = MailProcessingService(self.settings)
        result = service.send_confirmation_email(
            recipient_email='test@example.com',
            mail_subject='Test Subject',
            normalized_description='Test description',
            item_title=self.item.title
        )
        
        self.assertFalse(result)
    
    @patch('core.services.kigate_service.KiGateService.execute_agent')
    @patch('core.services.weaviate_sync_service.WeaviateItemSyncService.search_similar')
    @patch('core.services.openai_service.OpenAIService.chat_completion')
    @patch('core.services.graph_service.GraphService.send_mail')
    @patch('core.services.graph_service.GraphService.mark_message_as_read')
    @patch('core.services.graph_service.GraphService.move_message')
    def test_process_mail_success(self, mock_weaviate_init, mock_move, mock_mark_read, mock_send, mock_chat, mock_search, mock_execute):
        """Test processing a single mail successfully"""
        # Setup mocks
        mock_execute.return_value = {
            'success': True,
            'result': 'Converted content'
        }
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
        mock_chat.return_value = {
            'success': True,
            'content': 'Normalisierte Beschreibung\n\n---\nOriginale E-Mail:\n\nTest'
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
    def test_process_mail_archive_failure(self, mock_weaviate_init, mock_move, mock_mark_read, mock_send, mock_chat, mock_search, mock_execute):
        """Test processing mail when archiving fails - should still succeed"""
        # Setup mocks
        mock_execute.return_value = {
            'success': True,
            'result': 'Converted content'
        }
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
        mock_chat.return_value = {
            'success': True,
            'content': 'Normalisierte Beschreibung\n\n---\nOriginale E-Mail:\n\nTest'
        }
        mock_send.return_value = {'success': True}
        mock_mark_read.return_value = {'success': True}
        # Archiving fails
        mock_move.side_effect = Exception('Archive folder not found')
        
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
    def test_process_mail_no_matching_item(self, mock_weaviate_init, mock_search):
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
    def test_process_mailbox_success(self, mock_weaviate_init, mock_move, mock_mark_read, mock_send, mock_chat, mock_search, mock_execute, mock_get_messages):
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
        
        mock_execute.return_value = {
            'success': True,
            'result': 'Converted'
        }
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
        mock_chat.return_value = {
            'success': True,
            'content': 'Normalisiert\n\n---\nOriginale E-Mail:\n\nTest'
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
    def test_process_mailbox_no_messages(self, mock_weaviate_init, mock_get_messages):
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
