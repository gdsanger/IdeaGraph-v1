"""
Tests for AI Email Reply feature

Tests cover:
- RAG retrieval service (3-tier context retrieval)
- AI email reply service (draft generation and sending)
- API endpoints
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from main.models import User, Client as ClientModel, Section, Item, Task, TaskComment, Settings


class EmailReplyRAGServiceTest(TestCase):
    """Test cases for EmailReplyRAGService"""
    
    def setUp(self):
        """Set up test data"""
        # Create test client
        self.test_client = ClientModel.objects.create(
            name='Test Client'
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin',
            client=self.test_client
        )
        self.user.set_password('testpass')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(
            name='Test Section'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description for context retrieval',
            section=self.section,
            created_by=self.user
        )
        self.item.clients.add(self.test_client)
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            item=self.item,
            created_by=self.user,
            status='open'
        )
        
        # Create test comments (thread context)
        self.comment1 = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='First comment in thread',
            source='user'
        )
        
        self.comment2 = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Second comment with more context',
            source='email',
            email_direction='inbound',
            email_from='sender@example.com',
            email_subject='Test Subject'
        )
        
        # Create inbound email comment (the one we'll reply to)
        self.inbound_comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Incoming email that needs a reply',
            source='email',
            email_direction='inbound',
            email_from='sender@example.com',
            email_subject='Question about task',
            email_message_id='<test123@example.com>'
        )
        
        # Create settings
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test_token'
        )
    
    def test_retrieve_tier_a_context(self):
        """Test Tier A (thread) context retrieval"""
        from core.services.email_reply_rag_service import EmailReplyRAGService
        
        service = EmailReplyRAGService(self.settings)
        tier_a = service.retrieve_tier_a(self.task, self.inbound_comment)
        
        # Should retrieve 2 comments (excluding current)
        self.assertEqual(len(tier_a), 2)
        
        # Check structure
        self.assertEqual(tier_a[0]['tier'], 'A')
        self.assertIn('marker', tier_a[0])
        self.assertIn('excerpt', tier_a[0])
        
        # Email comments should have higher weight
        email_comment = next((c for c in tier_a if c['source'] == 'email'), None)
        user_comment = next((c for c in tier_a if c['source'] == 'user'), None)
        
        if email_comment and user_comment:
            self.assertGreater(email_comment['weight'], user_comment['weight'])
    
    def test_retrieve_tier_b_context(self):
        """Test Tier B (item) context retrieval"""
        from core.services.email_reply_rag_service import EmailReplyRAGService
        
        service = EmailReplyRAGService(self.settings)
        tier_b = service.retrieve_tier_b(self.item, self.task)
        
        # Should retrieve item and potentially other tasks
        self.assertGreater(len(tier_b), 0)
        
        # Check structure
        self.assertEqual(tier_b[0]['tier'], 'B')
        self.assertIn('marker', tier_b[0])
        
        # First item should be the item itself
        item_context = tier_b[0]
        self.assertEqual(item_context['type'], 'item')
        self.assertIn('Test item description', item_context['excerpt'])
    
    def test_retrieve_tier_c_context(self):
        """Test Tier C (global) context retrieval"""
        from core.services.email_reply_rag_service import EmailReplyRAGService
        from main.models import Tag
        
        # Create a tag and add to item
        tag = Tag.objects.create(name='test-tag')
        self.item.tags.add(tag)
        
        # Create another item with same tag
        other_item = Item.objects.create(
            title='Other Item',
            description='Another item with similar context',
            section=self.section,
            created_by=self.user
        )
        other_item.clients.add(self.test_client)
        other_item.tags.add(tag)
        
        service = EmailReplyRAGService(self.settings)
        tier_c = service.retrieve_tier_c(self.item, self.task)
        
        # Should find at least one similar item
        self.assertGreater(len(tier_c), 0)
        
        # Check structure
        if tier_c:
            self.assertEqual(tier_c[0]['tier'], 'C')
            self.assertIn('marker', tier_c[0])
    
    def test_pii_masking(self):
        """Test PII masking functionality"""
        from core.services.email_reply_rag_service import EmailReplyRAGService
        
        service = EmailReplyRAGService(self.settings)
        
        # Test email masking
        text_with_email = "Contact me at john@example.com for details"
        masked = service._mask_pii(text_with_email)
        self.assertIn('[EMAIL]', masked)
        self.assertNotIn('john@example.com', masked)
        
        # Test phone masking
        text_with_phone = "Call me at 555-123-4567"
        masked = service._mask_pii(text_with_phone)
        self.assertIn('[PHONE]', masked)
        
        # Test secret masking
        text_with_secret = "API_KEY=abc123xyz"
        masked = service._mask_pii(text_with_secret)
        self.assertIn('[SECRET]', masked)
    
    def test_snippet_truncation(self):
        """Test snippet truncation at word boundaries"""
        from core.services.email_reply_rag_service import EmailReplyRAGService
        
        service = EmailReplyRAGService(self.settings)
        
        long_text = "word " * 200  # Create long text
        truncated = service._truncate_snippet(long_text, max_length=100)
        
        # Should be truncated
        self.assertLess(len(truncated), len(long_text))
        self.assertTrue(truncated.endswith('...'))
        
        # Short text should not be truncated
        short_text = "Short text"
        not_truncated = service._truncate_snippet(short_text, max_length=100)
        self.assertEqual(short_text, not_truncated)
    
    def test_full_context_retrieval(self):
        """Test complete 3-tier context retrieval"""
        from core.services.email_reply_rag_service import EmailReplyRAGService
        
        service = EmailReplyRAGService(self.settings)
        context = service.retrieve_context(self.inbound_comment, use_cache=False)
        
        # Check structure
        self.assertIn('sources', context)
        self.assertIn('tier_a_count', context)
        self.assertIn('tier_b_count', context)
        self.assertIn('tier_c_count', context)
        self.assertIn('total_count', context)
        
        # Should have at least Tier A and B
        self.assertGreater(context['tier_a_count'], 0)
        self.assertGreater(context['tier_b_count'], 0)
        
        # Total should match sum
        expected_total = context['tier_a_count'] + context['tier_b_count'] + context['tier_c_count']
        self.assertEqual(context['total_count'], expected_total)
    
    def test_format_context_for_kigate(self):
        """Test formatting context for KiGate"""
        from core.services.email_reply_rag_service import EmailReplyRAGService
        
        service = EmailReplyRAGService(self.settings)
        context = service.retrieve_context(self.inbound_comment, use_cache=False)
        formatted = service.format_context_for_kigate(context)
        
        # Should contain markers
        self.assertIn('[#A-', formatted)
        
        # Should contain content from sources
        self.assertGreater(len(formatted), 0)


class AIEmailReplyServiceTest(TestCase):
    """Test cases for AIEmailReplyService"""
    
    def setUp(self):
        """Set up test data"""
        # Create test client
        self.test_client = ClientModel.objects.create(
            name='Test Client'
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin',
            client=self.test_client
        )
        self.user.set_password('testpass')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(
            name='Test Section'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item',
            section=self.section,
            created_by=self.user
        )
        self.item.clients.add(self.test_client)
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task',
            item=self.item,
            created_by=self.user,
            status='open'
        )
        
        # Create inbound email comment
        self.inbound_comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Question about the task',
            source='email',
            email_direction='inbound',
            email_from='sender@example.com',
            email_subject='Question',
            email_message_id='<test123@example.com>'
        )
        
        # Create settings
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test_token'
        )
    
    def test_validate_email_domain_empty_allowlist(self):
        """Test email domain validation with empty allowlist"""
        from core.services.ai_email_reply_service import AIEmailReplyService
        
        service = AIEmailReplyService(self.settings)
        service.DOMAIN_ALLOWLIST = []  # Empty = allow all
        
        self.assertTrue(service._validate_email_domain('test@example.com'))
        self.assertTrue(service._validate_email_domain('test@any-domain.com'))
    
    def test_validate_email_domain_with_allowlist(self):
        """Test email domain validation with allowlist"""
        from core.services.ai_email_reply_service import AIEmailReplyService
        
        service = AIEmailReplyService(self.settings)
        service.DOMAIN_ALLOWLIST = ['example.com', 'allowed.com']
        
        self.assertTrue(service._validate_email_domain('test@example.com'))
        self.assertTrue(service._validate_email_domain('test@allowed.com'))
        self.assertFalse(service._validate_email_domain('test@blocked.com'))
    
    def test_filter_secrets(self):
        """Test secret filtering"""
        from core.services.ai_email_reply_service import AIEmailReplyService
        
        service = AIEmailReplyService(self.settings)
        
        # Test API key filtering
        text_with_secret = "Here is the API_KEY=abc123xyz"
        filtered = service._filter_secrets(text_with_secret)
        self.assertIn('[REDACTED]', filtered)
        self.assertNotIn('abc123xyz', filtered)
        
        # Test internal URL filtering
        text_with_internal = "Visit http://localhost:8080/admin"
        filtered = service._filter_secrets(text_with_internal)
        self.assertIn('[REDACTED]', filtered)
        self.assertNotIn('localhost', filtered)
    
    @patch('core.services.ai_email_reply_service.KiGateService')
    @patch('core.services.ai_email_reply_service.EmailReplyRAGService')
    def test_generate_draft_success(self, mock_rag_service, mock_kigate_service):
        """Test successful draft generation"""
        from core.services.ai_email_reply_service import AIEmailReplyService
        
        # Mock RAG service
        mock_rag_instance = MagicMock()
        mock_rag_instance.retrieve_context.return_value = {
            'sources': [
                {'tier': 'A', 'marker': '#A-1', 'excerpt': 'Context 1', 'type': 'comment'},
            ],
            'tier_a_count': 1,
            'tier_b_count': 0,
            'tier_c_count': 0,
            'total_count': 1
        }
        mock_rag_instance.format_context_for_kigate.return_value = "[#A-1] Context 1"
        mock_rag_service.return_value = mock_rag_instance
        
        # Mock KiGate service
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.return_value = {
            'success': True,
            'result': 'Re: Question\n\nThank you for your question. Here is the answer.'
        }
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create service and generate draft
        service = AIEmailReplyService(self.settings)
        result = service.generate_draft(self.inbound_comment, self.user)
        
        # Check result
        self.assertTrue(result['success'])
        self.assertIn('subject', result)
        self.assertIn('body', result)
        self.assertIn('sources', result)
        self.assertEqual(result['subject'], 'Re: Question')
        self.assertIn('Thank you', result['body'])
    
    def test_generate_draft_invalid_comment(self):
        """Test draft generation with invalid comment type"""
        from core.services.ai_email_reply_service import AIEmailReplyService
        
        # Create non-email comment
        regular_comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Regular comment',
            source='user'
        )
        
        service = AIEmailReplyService(self.settings)
        result = service.generate_draft(regular_comment, self.user)
        
        # Should fail
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class AIEmailReplyAPITest(TestCase):
    """Test cases for AI email reply API endpoints"""
    
    def setUp(self):
        """Set up test data and client"""
        self.client = Client()
        
        # Create test client
        self.test_client_model = ClientModel.objects.create(
            name='Test Client'
        )
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin',
            client=self.test_client_model
        )
        self.user.set_password('testpass')
        self.user.save()
        
        # Create test section
        self.section = Section.objects.create(
            name='Test Section'
        )
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item',
            section=self.section,
            created_by=self.user
        )
        self.item.clients.add(self.test_client_model)
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task',
            item=self.item,
            created_by=self.user,
            status='open'
        )
        
        # Create inbound email comment
        self.inbound_comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Question about the task',
            source='email',
            email_direction='inbound',
            email_from='sender@example.com',
            email_subject='Question',
            email_message_id='<test123@example.com>'
        )
        
        # Create settings
        self.settings = Settings.objects.create(
            kigate_api_enabled=True,
            kigate_api_base_url='http://localhost:8000',
            kigate_api_token='test_token'
        )
        
        # Generate JWT token
        from main.auth_utils import generate_jwt_token
        self.token = generate_jwt_token(self.user)
    
    def test_draft_endpoint_requires_auth(self):
        """Test that draft endpoint requires authentication"""
        url = reverse('main:api_comment_ai_reply_draft', kwargs={'comment_id': self.inbound_comment.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 401)
    
    @patch('core.services.ai_email_reply_service.AIEmailReplyService')
    def test_draft_endpoint_success(self, mock_service_class):
        """Test successful draft generation via API"""
        # Mock service
        mock_service = MagicMock()
        mock_service.generate_draft.return_value = {
            'success': True,
            'subject': 'Re: Question',
            'body': 'Answer here',
            'sources': [],
            'confidence': 'high',
            'language': 'de',
            'latency_ms': 1000,
            'tier_a_count': 1,
            'tier_b_count': 0,
            'tier_c_count': 0,
            'total_sources': 1
        }
        mock_service_class.return_value = mock_service
        
        url = reverse('main:api_comment_ai_reply_draft', kwargs={'comment_id': self.inbound_comment.id})
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['subject'], 'Re: Question')
    
    def test_draft_endpoint_invalid_comment(self):
        """Test draft endpoint with non-email comment"""
        # Create regular comment
        regular_comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text='Regular comment',
            source='user'
        )
        
        url = reverse('main:api_comment_ai_reply_draft', kwargs={'comment_id': regular_comment.id})
        response = self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
    
    def test_send_endpoint_requires_auth(self):
        """Test that send endpoint requires authentication"""
        url = reverse('main:api_comment_ai_reply_send', kwargs={'comment_id': self.inbound_comment.id})
        response = self.client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 401)
    
    @patch('core.services.ai_email_reply_service.AIEmailReplyService')
    def test_send_endpoint_success(self, mock_service_class):
        """Test successful email sending via API"""
        # Mock service
        mock_service = MagicMock()
        mock_service.send_reply.return_value = {
            'success': True,
            'message': 'Email sent',
            'comment_id': 'test-uuid',
            'recipient': 'sender@example.com'
        }
        mock_service_class.return_value = mock_service
        
        url = reverse('main:api_comment_ai_reply_send', kwargs={'comment_id': self.inbound_comment.id})
        response = self.client.post(
            url,
            data=json.dumps({
                'subject': 'Re: Question',
                'body': 'Answer here'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_send_endpoint_missing_fields(self):
        """Test send endpoint with missing required fields"""
        url = reverse('main:api_comment_ai_reply_send', kwargs={'comment_id': self.inbound_comment.id})
        
        # Missing body
        response = self.client.post(
            url,
            data=json.dumps({
                'subject': 'Re: Question'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
