"""
Tests for tag cleaning and duplicate prevention in AI Enhancer
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from main.models import User, Item, Task, Tag, Settings, Section
from main.api_views import api_item_ai_enhance, api_task_ai_enhance, clean_tag_name


class TagCleaningTest(TestCase):
    """Test tag name cleaning helper function"""
    
    def test_clean_tag_name_removes_numbers(self):
        """Test that numbered tags are cleaned correctly"""
        self.assertEqual(clean_tag_name('1. Python'), 'Python')
        self.assertEqual(clean_tag_name('2) Django'), 'Django')
        self.assertEqual(clean_tag_name('3. API'), 'API')
    
    def test_clean_tag_name_removes_bullets(self):
        """Test that bulleted tags are cleaned correctly"""
        self.assertEqual(clean_tag_name('- Python'), 'Python')
        self.assertEqual(clean_tag_name('* Django'), 'Django')
        self.assertEqual(clean_tag_name('• API'), 'API')
    
    def test_clean_tag_name_removes_brackets(self):
        """Test that brackets are removed from tags"""
        self.assertEqual(clean_tag_name('[Python]'), 'Python')
        self.assertEqual(clean_tag_name('(Django)'), 'Django')
    
    def test_clean_tag_name_removes_quotes(self):
        """Test that quotes are removed from tags"""
        self.assertEqual(clean_tag_name('"Python"'), 'Python')
        self.assertEqual(clean_tag_name("'Django'"), 'Django')
    
    def test_clean_tag_name_handles_complex_formats(self):
        """Test that complex formats are cleaned correctly"""
        self.assertEqual(clean_tag_name('1. "Python"'), 'Python')
        self.assertEqual(clean_tag_name('- [Django]'), 'Django')
        self.assertEqual(clean_tag_name('* "API"'), 'API')
        self.assertEqual(clean_tag_name('1) (Testing)'), 'Testing')
    
    def test_clean_tag_name_preserves_internal_spaces(self):
        """Test that internal spaces in tags are preserved"""
        self.assertEqual(clean_tag_name('Machine Learning'), 'Machine Learning')
        self.assertEqual(clean_tag_name('1. Machine Learning'), 'Machine Learning')
    
    def test_clean_tag_name_returns_none_for_empty(self):
        """Test that empty or whitespace-only tags return None"""
        self.assertIsNone(clean_tag_name(''))
        self.assertIsNone(clean_tag_name('   '))
        self.assertIsNone(clean_tag_name('1. '))
        self.assertIsNone(clean_tag_name('- '))
    
    def test_clean_tag_name_handles_unicode(self):
        """Test that unicode characters are preserved"""
        self.assertEqual(clean_tag_name('Künstliche Intelligenz'), 'Künstliche Intelligenz')
        self.assertEqual(clean_tag_name('1. Künstliche Intelligenz'), 'Künstliche Intelligenz')


class TagDuplicatePreventionTest(TestCase):
    """Test that duplicate tags are not created"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer',
            is_active=True
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        # Create test settings
        self.settings = Settings.objects.create(
            max_tags_per_idea=5,
            kigate_api_enabled=True,
            kigate_api_token='test-token',
            kigate_api_base_url='http://localhost:8000'
        )
        
        # Create test section
        self.section = Section.objects.create(name='Test Section')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test item description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        
        # Create test task
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            status='new',
            item=self.item,
            created_by=self.user
        )
    
    @patch('main.api_views.KiGateService')
    def test_item_ai_enhance_prevents_duplicate_tags(self, mock_kigate_service):
        """Test that AI enhance does not create duplicate tags in database"""
        # Create an existing tag in database
        existing_tag = Tag.objects.create(name='Python')
        initial_tag_count = Tag.objects.count()
        
        # Mock KiGate service to return tags including the existing one
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.side_effect = [
            {'success': True, 'result': 'Enhanced description'},
            {'success': True, 'result': 'Enhanced Title'},
            {'success': True, 'result': '1. Python\n2. Django\n3. Testing'}
        ]
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        # Execute
        response = api_item_ai_enhance(request, self.item.id)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify no duplicate tag was created (should have added 2 new tags only)
        final_tag_count = Tag.objects.count()
        self.assertEqual(final_tag_count, initial_tag_count + 2)
        
        # Verify the existing tag was reused
        self.assertEqual(Tag.objects.filter(name='Python').count(), 1)
        
        # Verify item has the correct tags
        item_tags = list(self.item.tags.values_list('name', flat=True))
        self.assertIn('Python', item_tags)
        self.assertIn('Django', item_tags)
        self.assertIn('Testing', item_tags)
    
    @patch('main.api_views.KiGateService')
    def test_item_ai_enhance_case_insensitive_duplicate_prevention(self, mock_kigate_service):
        """Test that duplicate tags with different cases are not created"""
        # Create an existing tag in database
        existing_tag = Tag.objects.create(name='Python')
        initial_tag_count = Tag.objects.count()
        
        # Mock KiGate service to return same tag with different case
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.side_effect = [
            {'success': True, 'result': 'Enhanced description'},
            {'success': True, 'result': 'Enhanced Title'},
            {'success': True, 'result': 'python, PYTHON, PyThOn'}  # Same tag, different cases
        ]
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        # Execute
        response = api_item_ai_enhance(request, self.item.id)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        
        # Verify no duplicate tag was created
        final_tag_count = Tag.objects.count()
        self.assertEqual(final_tag_count, initial_tag_count)
        
        # Verify only one Python tag exists
        self.assertEqual(Tag.objects.filter(name__iexact='python').count(), 1)
    
    @patch('main.api_views.ChromaTaskSyncService')
    @patch('main.api_views.KiGateService')
    def test_task_ai_enhance_prevents_duplicate_tags(self, mock_kigate_service, mock_chroma_service):
        """Test that task AI enhance does not create duplicate tags"""
        # Mock ChromaDB service
        mock_chroma_instance = MagicMock()
        mock_chroma_instance.search_similar.return_value = {
            'success': True,
            'results': []
        }
        mock_chroma_service.return_value = mock_chroma_instance
        
        # Create an existing tag in database
        existing_tag = Tag.objects.create(name='Django')
        initial_tag_count = Tag.objects.count()
        
        # Mock KiGate service to return tags including the existing one
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.side_effect = [
            {'success': True, 'result': 'Normalized text'},
            {'success': True, 'result': 'Enhanced Title'},
            {'success': True, 'result': '"Django", [Testing], - API'}
        ]
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/tasks/{self.task.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        # Execute
        response = api_task_ai_enhance(request, self.task.id)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify no duplicate tag was created
        final_tag_count = Tag.objects.count()
        self.assertEqual(final_tag_count, initial_tag_count + 2)
        
        # Verify the existing tag was reused
        self.assertEqual(Tag.objects.filter(name='Django').count(), 1)
        
        # Verify tags were cleaned correctly
        self.assertIn('Django', data['tags'])
        self.assertIn('Testing', data['tags'])
        self.assertIn('API', data['tags'])
    
    @patch('main.api_views.KiGateService')
    def test_item_ai_enhance_handles_special_characters(self, mock_kigate_service):
        """Test that AI enhance correctly handles tags with special characters"""
        # Mock KiGate service with various special character formats
        mock_kigate_instance = MagicMock()
        mock_kigate_instance.execute_agent.side_effect = [
            {'success': True, 'result': 'Enhanced description'},
            {'success': True, 'result': 'Enhanced Title'},
            {'success': True, 'result': '1. "Machine Learning"\n2. [Deep Learning]\n- *Neural Networks*\n4) (AI Research)'}
        ]
        mock_kigate_service.return_value = mock_kigate_instance
        
        # Create request
        request = self.factory.post(
            f'/api/items/{self.item.id}/ai-enhance',
            data=json.dumps({
                'title': 'Test Title',
                'description': 'Test Description'
            }),
            content_type='application/json'
        )
        request.session = {'user_id': str(self.user.id)}
        
        # Execute
        response = api_item_ai_enhance(request, self.item.id)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify tags were cleaned correctly
        self.assertEqual(len(data['tags']), 4)
        self.assertIn('Machine Learning', data['tags'])
        self.assertIn('Deep Learning', data['tags'])
        self.assertIn('Neural Networks', data['tags'])
        self.assertIn('AI Research', data['tags'])
        
        # Verify tags in database don't have special characters
        item_tags = list(self.item.tags.values_list('name', flat=True))
        for tag_name in item_tags:
            self.assertNotIn('"', tag_name)
            self.assertNotIn('[', tag_name)
            self.assertNotIn(']', tag_name)
            self.assertNotIn('*', tag_name)
            self.assertNotIn('(', tag_name)
            self.assertNotIn(')', tag_name)
