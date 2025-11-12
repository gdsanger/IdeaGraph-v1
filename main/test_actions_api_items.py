"""
Tests for Actions API Items endpoints
"""
import json
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from main.models import User, ApiKey, Item, Section, Tag, ItemFile


@override_settings(
    ACTIONS_API_ENABLED=True,
    ACTIONS_API_KEY_HEADER='X-IG-API-Key'
)
class ItemsAPITest(TestCase):
    """Test Items API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            is_active=True
        )
        
        # Create API key
        self.api_key = ApiKey.generate_key(
            user=self.user,
            name='Test API Key'
        )
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create tags
        self.tag1 = Tag.objects.create(name='python')
        self.tag2 = Tag.objects.create(name='django')
        
        # Create test items
        self.item1 = Item.objects.create(
            title='Test Item 1',
            description='Description for item 1',
            status='new',
            section=self.section,
            created_by=self.user
        )
        self.item1.tags.add(self.tag1)
        
        self.item2 = Item.objects.create(
            title='Test Item 2',
            description='Description for item 2',
            status='working',
            created_by=self.user
        )
        self.item2.tags.add(self.tag1, self.tag2)
        
        # Add files to item1
        self.file1 = ItemFile.objects.create(
            item=self.item1,
            filename='test.pdf',
            file_size=1024,
            content_type='application/pdf',
            uploaded_by=self.user
        )
    
    def _set_api_key(self):
        """Set API key header for requests"""
        self.client.credentials(HTTP_X_IG_API_KEY=self.api_key.key)
    
    def test_list_items_requires_auth(self):
        """Test that listing items requires authentication"""
        response = self.client.get('/api/ideagraph/items/')
        
        self.assertEqual(response.status_code, 403)
    
    def test_list_items_success(self):
        """Test listing items with valid API key"""
        self._set_api_key()
        
        response = self.client.get('/api/ideagraph/items/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('items', data)
        self.assertEqual(data['count'], 2)
        self.assertEqual(len(data['items']), 2)
    
    def test_list_items_with_limit(self):
        """Test listing items with limit parameter"""
        self._set_api_key()
        
        response = self.client.get('/api/ideagraph/items/?limit=1')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['items']), 1)
    
    def test_list_items_with_query(self):
        """Test listing items with query filter"""
        self._set_api_key()
        
        response = self.client.get('/api/ideagraph/items/?query=Item 1')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['title'], 'Test Item 1')
    
    def test_list_items_with_tag(self):
        """Test listing items with tag filter"""
        self._set_api_key()
        
        response = self.client.get('/api/ideagraph/items/?tag=django')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['title'], 'Test Item 2')
    
    def test_get_item_detail(self):
        """Test getting item detail"""
        self._set_api_key()
        
        response = self.client.get(f'/api/ideagraph/items/{self.item1.id}/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('item', data)
        
        item = data['item']
        self.assertEqual(item['title'], 'Test Item 1')
        self.assertEqual(item['status'], 'new')
        self.assertEqual(item['section_name'], 'Test Section')
        self.assertIn('file_count', item)
        self.assertEqual(item['file_count'], 1)
        self.assertIn('task_count', item)
        self.assertIn('milestone_count', item)
    
    def test_get_item_not_found(self):
        """Test getting non-existent item returns 404"""
        self._set_api_key()
        
        response = self.client.get('/api/ideagraph/items/00000000-0000-0000-0000-000000000000/')
        
        self.assertEqual(response.status_code, 404)
    
    def test_get_item_files(self):
        """Test getting item files"""
        self._set_api_key()
        
        response = self.client.get(f'/api/ideagraph/items/{self.item1.id}/files/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('files', data)
        self.assertEqual(len(data['files']), 1)
        
        file_data = data['files'][0]
        self.assertEqual(file_data['filename'], 'test.pdf')
        self.assertEqual(file_data['content_type'], 'application/pdf')
        self.assertIn('file_id', file_data)
    
    def test_get_item_files_empty(self):
        """Test getting files for item with no files"""
        self._set_api_key()
        
        response = self.client.get(f'/api/ideagraph/items/{self.item2.id}/files/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['files']), 0)
    
    def test_items_include_tags(self):
        """Test that items include tag information"""
        self._set_api_key()
        
        response = self.client.get(f'/api/ideagraph/items/{self.item1.id}/')
        
        data = response.json()
        item = data['item']
        self.assertIn('tags', item)
        self.assertEqual(len(item['tags']), 1)
        self.assertEqual(item['tags'][0]['name'], 'python')
    
    def test_items_include_created_by(self):
        """Test that items include creator information"""
        self._set_api_key()
        
        response = self.client.get(f'/api/ideagraph/items/{self.item1.id}/')
        
        data = response.json()
        item = data['item']
        self.assertIn('created_by', item)
        self.assertEqual(item['created_by']['username'], 'testuser')


@override_settings(ACTIONS_API_ENABLED=False)
class ItemsAPIDisabledTest(TestCase):
    """Test Items API when disabled"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com'
        )
        
        self.api_key = ApiKey.generate_key(
            user=self.user,
            name='Test Key'
        )
    
    def test_api_disabled(self):
        """Test that API returns error when disabled"""
        self.client.credentials(HTTP_X_IG_API_KEY=self.api_key.key)
        
        response = self.client.get('/api/ideagraph/items/')
        
        self.assertEqual(response.status_code, 403)
