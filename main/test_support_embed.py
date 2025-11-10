"""
Tests for Support Embed Feature
"""
import json
import time
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.core.cache import cache
from main.models import User, Item, Section, Task, Settings
from core.services.support_auth_service import SupportAuthService
from core.services.support_rate_limiter import SupportRateLimiter
from core.services.support_submit_service import SupportSubmitService


# Test constants
NON_EXISTENT_UUID = '00000000-0000-0000-0000-000000000000'


class SupportAuthServiceTest(TestCase):
    """Test Support Authentication Service"""
    
    def setUp(self):
        """Set up test data"""
        self.auth_service = SupportAuthService()
        self.test_item_id = '12345678-1234-1234-1234-123456789012'
    
    def test_generate_and_verify_jwt(self):
        """Test JWT token generation and verification"""
        # Generate token
        token = self.auth_service.generate_jwt(self.test_item_id)
        
        # Verify token
        result = self.auth_service.verify_jwt(token)
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['item_id'], self.test_item_id)
    
    def test_verify_jwt_expired(self):
        """Test JWT token expiration"""
        # Generate token with 0 second expiry (immediately expired)
        token = self.auth_service.generate_jwt(self.test_item_id, expires_in=-1)
        
        # Verify token
        result = self.auth_service.verify_jwt(token)
        
        self.assertFalse(result['valid'])
        self.assertIn('expired', result['error'].lower())
    
    def test_verify_jwt_invalid(self):
        """Test invalid JWT token"""
        result = self.auth_service.verify_jwt('invalid_token')
        
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
    
    def test_generate_and_verify_hmac(self):
        """Test HMAC signature generation and verification"""
        secret = 'test_secret_key'
        
        # Generate signature
        hmac_data = self.auth_service.generate_hmac(self.test_item_id, secret)
        
        # Verify signature
        result = self.auth_service.verify_hmac(
            item_id=self.test_item_id,
            signature=hmac_data['signature'],
            timestamp=hmac_data['timestamp'],
            secret=secret
        )
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['item_id'], self.test_item_id)
    
    def test_verify_hmac_expired(self):
        """Test HMAC signature expiration"""
        secret = 'test_secret_key'
        old_timestamp = str(int(time.time()) - 400)  # 400 seconds ago (> 300 max)
        
        # Generate signature with old timestamp
        import hmac
        import hashlib
        message = f"{self.test_item_id}|{old_timestamp}"
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Verify signature
        result = self.auth_service.verify_hmac(
            item_id=self.test_item_id,
            signature=signature,
            timestamp=old_timestamp,
            secret=secret
        )
        
        self.assertFalse(result['valid'])
        self.assertIn('expired', result['error'].lower())
    
    def test_verify_hmac_wrong_secret(self):
        """Test HMAC signature with wrong secret"""
        secret = 'test_secret_key'
        wrong_secret = 'wrong_secret_key'
        
        # Generate signature with correct secret
        hmac_data = self.auth_service.generate_hmac(self.test_item_id, secret)
        
        # Verify with wrong secret
        result = self.auth_service.verify_hmac(
            item_id=self.test_item_id,
            signature=hmac_data['signature'],
            timestamp=hmac_data['timestamp'],
            secret=wrong_secret
        )
        
        self.assertFalse(result['valid'])
        self.assertIn('signature', result['error'].lower())
    
    def test_generate_and_verify_refresh_token(self):
        """Test refresh token generation and verification"""
        # Generate refresh token
        refresh_token = self.auth_service.generate_refresh_token(self.test_item_id)
        
        # Verify refresh token
        result = self.auth_service.verify_refresh_token(refresh_token)
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['item_id'], self.test_item_id)
        self.assertEqual(result['payload']['type'], 'refresh')
    
    def test_verify_refresh_token_expired(self):
        """Test expired refresh token"""
        # Generate refresh token with 0 second expiry (immediately expired)
        refresh_token = self.auth_service.generate_refresh_token(self.test_item_id, expires_in=-1)
        
        # Verify token
        result = self.auth_service.verify_refresh_token(refresh_token)
        
        self.assertFalse(result['valid'])
        self.assertIn('expired', result['error'].lower())
        self.assertTrue(result.get('expired', False))
    
    def test_verify_access_token_as_refresh_token(self):
        """Test that access tokens cannot be used as refresh tokens"""
        # Generate regular access token
        access_token = self.auth_service.generate_jwt(self.test_item_id)
        
        # Try to verify as refresh token
        result = self.auth_service.verify_refresh_token(access_token)
        
        self.assertFalse(result['valid'])
        self.assertIn('audience', result['error'].lower())
    
    def test_refresh_access_token(self):
        """Test refreshing access token using refresh token"""
        # Generate refresh token
        refresh_token = self.auth_service.generate_refresh_token(self.test_item_id)
        
        # Refresh access token
        result = self.auth_service.refresh_access_token(refresh_token)
        
        self.assertTrue(result['success'])
        self.assertIn('access_token', result)
        self.assertEqual(result['expires_in'], self.auth_service.JWT_MAX_AGE_SECONDS)
        
        # Verify the new access token works
        verify_result = self.auth_service.verify_jwt(result['access_token'])
        self.assertTrue(verify_result['valid'])
        self.assertEqual(verify_result['item_id'], self.test_item_id)
    
    def test_refresh_access_token_with_expired_refresh_token(self):
        """Test that expired refresh tokens cannot be used"""
        # Generate expired refresh token
        refresh_token = self.auth_service.generate_refresh_token(self.test_item_id, expires_in=-1)
        
        # Try to refresh access token
        result = self.auth_service.refresh_access_token(refresh_token)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_refresh_access_token_with_invalid_token(self):
        """Test that invalid tokens cannot be used for refresh"""
        # Try to refresh with invalid token
        result = self.auth_service.refresh_access_token('invalid_token')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class SupportRateLimiterTest(TestCase):
    """Test Support Rate Limiter"""
    
    def setUp(self):
        """Set up test data"""
        # Clear cache before each test
        cache.clear()
        self.rate_limiter = SupportRateLimiter(limit=5, window=60)
        self.test_referrer = 'https://example.com'
        self.test_item_id = '12345678-1234-1234-1234-123456789012'
    
    def tearDown(self):
        """Clean up after test"""
        cache.clear()
    
    def test_rate_limit_allows_within_limit(self):
        """Test rate limiter allows requests within limit"""
        # Make 5 requests (within limit)
        for i in range(5):
            result = self.rate_limiter.check_rate_limit(
                referrer=self.test_referrer,
                item_id=self.test_item_id
            )
            self.assertTrue(result['allowed'])
            self.assertEqual(result['remaining'], 4 - i)
    
    def test_rate_limit_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit"""
        # Make 5 requests (hit limit)
        for i in range(5):
            self.rate_limiter.check_rate_limit(
                referrer=self.test_referrer,
                item_id=self.test_item_id
            )
        
        # 6th request should be blocked
        result = self.rate_limiter.check_rate_limit(
            referrer=self.test_referrer,
            item_id=self.test_item_id
        )
        
        self.assertFalse(result['allowed'])
        self.assertEqual(result['remaining'], 0)
    
    def test_rate_limit_different_keys(self):
        """Test rate limiter tracks different keys separately"""
        # Use different item IDs
        item_id_1 = '12345678-1234-1234-1234-123456789012'
        item_id_2 = '87654321-4321-4321-4321-210987654321'
        
        # Make 5 requests for item 1
        for i in range(5):
            self.rate_limiter.check_rate_limit(
                referrer=self.test_referrer,
                item_id=item_id_1
            )
        
        # Request for item 2 should still be allowed
        result = self.rate_limiter.check_rate_limit(
            referrer=self.test_referrer,
            item_id=item_id_2
        )
        
        self.assertTrue(result['allowed'])
    
    def test_rate_limit_reset(self):
        """Test rate limiter reset"""
        # Make 5 requests
        for i in range(5):
            self.rate_limiter.check_rate_limit(
                referrer=self.test_referrer,
                item_id=self.test_item_id
            )
        
        # Reset
        self.rate_limiter.reset(
            referrer=self.test_referrer,
            item_id=self.test_item_id
        )
        
        # Should be allowed again
        result = self.rate_limiter.check_rate_limit(
            referrer=self.test_referrer,
            item_id=self.test_item_id
        )
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['remaining'], 4)


class SupportSubmitServiceTest(TestCase):
    """Test Support Submit Service"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        self.submit_service = SupportSubmitService()
    
    def test_submit_basic_task(self):
        """Test basic task submission"""
        result = self.submit_service.submit(
            item_id=str(self.item.id),
            title='Test Support Request',
            description='This is a test support request',
            task_type='support'
        )
        
        self.assertTrue(result['success'])
        self.assertIn('task_id', result)
        self.assertIn('url', result)
        
        # Verify task was created
        task = Task.objects.get(id=result['task_id'])
        self.assertEqual(task.title, 'Test Support Request')
        self.assertEqual(task.type, 'support')
        self.assertEqual(task.source, 'support')
    
    def test_submit_with_reporter_email(self):
        """Test task submission with reporter email"""
        result = self.submit_service.submit(
            item_id=str(self.item.id),
            title='Test Support Request',
            description='Test description',
            task_type='support',
            reporter_email='reporter@example.com',
            reporter_referrer='https://example.com'
        )
        
        self.assertTrue(result['success'])
        
        # Verify reporter fields
        task = Task.objects.get(id=result['task_id'])
        self.assertEqual(task.reporter_email, 'reporter@example.com')
        self.assertEqual(task.reporter_referrer, 'https://example.com')
    
    def test_submit_with_auto_answer(self):
        """Test task submission with auto-answer metadata"""
        auto_answer = {
            'offered': True,
            'accepted': False,
            'summary': 'This is an auto-generated answer'
        }
        
        result = self.submit_service.submit(
            item_id=str(self.item.id),
            title='Test Support Request',
            description='Test description',
            task_type='support',
            auto_answer=auto_answer
        )
        
        self.assertTrue(result['success'])
        
        # Verify auto-answer fields
        task = Task.objects.get(id=result['task_id'])
        self.assertTrue(task.auto_answer_offered)
        self.assertFalse(task.auto_answer_accepted)
        self.assertEqual(task.auto_answer_text, 'This is an auto-generated answer')
    
    def test_submit_with_duplicate_reference(self):
        """Test task submission with duplicate reference"""
        # Create an existing task
        existing_task = Task.objects.create(
            item=self.item,
            title='Existing Task',
            description='Existing description',
            type='support',
            status='new'
        )
        
        result = self.submit_service.submit(
            item_id=str(self.item.id),
            title='New Task (Duplicate)',
            description='Test description',
            task_type='support',
            duplicate_of_task_id=str(existing_task.id)
        )
        
        self.assertTrue(result['success'])
        
        # Verify duplicate reference
        task = Task.objects.get(id=result['task_id'])
        self.assertEqual(str(task.duplicate_of_task_id), str(existing_task.id))
    
    def test_submit_enriches_description(self):
        """Test that description is enriched with metadata"""
        auto_answer = {
            'offered': True,
            'accepted': False,
            'summary': 'Auto answer summary'
        }
        
        result = self.submit_service.submit(
            item_id=str(self.item.id),
            title='Test Request',
            description='Original description',
            auto_answer=auto_answer
        )
        
        self.assertTrue(result['success'])
        
        # Verify description contains enrichments
        task = Task.objects.get(id=result['task_id'])
        self.assertIn('Original description', task.description)
        self.assertIn('Automatische Antwort', task.description)
        self.assertIn('Auto answer summary', task.description)
        self.assertIn('Support-Formular', task.description)
    
    def test_submit_invalid_item(self):
        """Test task submission with invalid item ID"""
        result = self.submit_service.submit(
            item_id=NON_EXISTENT_UUID,
            title='Test Request',
            description='Test description',
            task_type='support'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class SupportAPITest(TestCase):
    """Test Support API Endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create settings
        self.settings = Settings.objects.create(
            openai_api_enabled=True,
            openai_api_key='test_key',
            kigate_api_enabled=True,
            kigate_api_token='test_token',
            weaviate_cloud_enabled=False
        )
        
        self.client = Client()
        self.auth_service = SupportAuthService()
        
        # Generate valid token
        self.token = self.auth_service.generate_jwt(str(self.item.id))
        
        # Clear cache
        cache.clear()
    
    def tearDown(self):
        """Clean up after test"""
        cache.clear()
    
    def test_submit_endpoint_without_auth(self):
        """Test submit endpoint without authentication"""
        response = self.client.post(
            f'/api/support/submit/{self.item.id}',
            data=json.dumps({
                'title': 'Test Request',
                'description': 'Test description',
                'type': 'support'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_submit_endpoint_with_jwt(self):
        """Test submit endpoint with JWT authentication"""
        response = self.client.post(
            f'/api/support/submit/{self.item.id}',
            data=json.dumps({
                'title': 'Test Request',
                'description': 'Test description',
                'type': 'support'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('taskId', data)
    
    def test_submit_endpoint_missing_title(self):
        """Test submit endpoint with missing title"""
        response = self.client.post(
            f'/api/support/submit/{self.item.id}',
            data=json.dumps({
                'description': 'Test description',
                'type': 'support'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_precheck_endpoint_with_jwt(self):
        """Test precheck endpoint with JWT authentication"""
        with patch('core.services.support_precheck_service.SupportPrecheckService.precheck') as mock_precheck:
            mock_precheck.return_value = {
                'auto_answer': {
                    'summary': 'Test answer',
                    'confidence': 0.8,
                    'sources': []
                },
                'duplicates': [],
                'recommendation': 'submit'
            }
            
            response = self.client.post(
                f'/api/support/precheck/{self.item.id}',
                data=json.dumps({
                    'title': 'Test Question',
                    'description': 'Test description',
                    'type': 'support'
                }),
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {self.token}'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            self.assertIn('autoAnswer', data)
            self.assertIn('duplicates', data)
            self.assertIn('recommendation', data)
    
    def test_rate_limit_enforced(self):
        """Test that rate limiting is enforced"""
        # Make requests until rate limit is hit
        for i in range(60):  # Default limit is 60
            self.client.post(
                f'/api/support/submit/{self.item.id}',
                data=json.dumps({
                    'title': f'Test Request {i}',
                    'description': 'Test description',
                    'type': 'support'
                }),
                content_type='application/json',
                HTTP_AUTHORIZATION=f'Bearer {self.token}',
                HTTP_REFERER='https://test.example.com'
            )
        
        # Next request should be rate limited
        response = self.client.post(
            f'/api/support/submit/{self.item.id}',
            data=json.dumps({
                'title': 'Test Request',
                'description': 'Test description',
                'type': 'support'
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
            HTTP_REFERER='https://test.example.com'
        )
        
        self.assertEqual(response.status_code, 429)


class SupportEmbedViewTest(TestCase):
    """Test Support Embed View"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        
        self.section = Section.objects.create(name='Test Section')
        
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        self.client = Client()
        self.auth_service = SupportAuthService()
        self.token = self.auth_service.generate_jwt(str(self.item.id))
    
    def test_embed_view_renders(self):
        """Test embed view renders successfully"""
        response = self.client.get(
            f'/embed/support?itemId={self.item.id}&t={self.token}'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chat')
        self.assertContains(response, 'Frage stellen')
    
    def test_embed_view_missing_item_id(self):
        """Test embed view with missing itemId"""
        response = self.client.get(
            f'/embed/support?t={self.token}'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_embed_view_missing_auth(self):
        """Test embed view with missing authentication"""
        response = self.client.get(
            f'/embed/support?itemId={self.item.id}'
        )
        
        self.assertEqual(response.status_code, 401)
    
    def test_embed_view_theme_support(self):
        """Test embed view with theme parameter"""
        response = self.client.get(
            f'/embed/support?itemId={self.item.id}&t={self.token}&theme=dark'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-theme="dark"')
    
    def test_token_refresh_endpoint_success(self):
        """Test token refresh endpoint with valid refresh token"""
        # Generate refresh token
        refresh_token = self.auth_service.generate_refresh_token(str(self.item.id))
        
        # Call refresh endpoint
        response = self.client.post(
            '/api/support/token/refresh',
            data=json.dumps({
                'refresh_token': refresh_token
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('access_token', data)
        self.assertEqual(data['expires_in'], 1800)
        
        # Verify the new access token works
        verify_result = self.auth_service.verify_jwt(data['access_token'])
        self.assertTrue(verify_result['valid'])
    
    def test_token_refresh_endpoint_expired_token(self):
        """Test token refresh endpoint with expired refresh token"""
        # Generate expired refresh token
        refresh_token = self.auth_service.generate_refresh_token(str(self.item.id), expires_in=-1)
        
        # Call refresh endpoint
        response = self.client.post(
            '/api/support/token/refresh',
            data=json.dumps({
                'refresh_token': refresh_token
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_token_refresh_endpoint_invalid_token(self):
        """Test token refresh endpoint with invalid token"""
        response = self.client.post(
            '/api/support/token/refresh',
            data=json.dumps({
                'refresh_token': 'invalid_token'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_token_refresh_endpoint_missing_token(self):
        """Test token refresh endpoint without token"""
        response = self.client.post(
            '/api/support/token/refresh',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_embed_view_with_refresh_token(self):
        """Test embed view accepts refresh token parameter"""
        refresh_token = self.auth_service.generate_refresh_token(str(self.item.id))
        
        response = self.client.get(
            f'/embed/support?itemId={self.item.id}&t={self.token}&r={refresh_token}'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, refresh_token)
