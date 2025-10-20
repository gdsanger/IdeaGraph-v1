"""
Tests for tag management enhancements: usage counting, deletion protection, pagination and search
"""
from django.test import TestCase, Client
from django.urls import reverse
from main.models import User, Item, Task, Tag


class TagUsageCountTest(TestCase):
    """Test tag usage count functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.user.set_password('testpass123')
        self.user.save()
        
        # Set session to simulate logged-in user
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session['user_role'] = self.user.role
        session.save()
        
    def test_tag_usage_count_initial_value(self):
        """Test that new tags have usage_count of 0"""
        tag = Tag.objects.create(name='Python')
        self.assertEqual(tag.usage_count, 0)
    
    def test_tag_calculate_usage_with_items(self):
        """Test usage count calculation with items"""
        tag = Tag.objects.create(name='Django')
        
        # Create items with the tag
        item1 = Item.objects.create(title='Test Item 1', created_by=self.user)
        item1.tags.add(tag)
        
        item2 = Item.objects.create(title='Test Item 2', created_by=self.user)
        item2.tags.add(tag)
        
        # Calculate usage
        count = tag.calculate_usage_count()
        
        self.assertEqual(count, 2)
        self.assertEqual(tag.usage_count, 2)
    
    def test_tag_calculate_usage_with_tasks(self):
        """Test usage count calculation with tasks"""
        tag = Tag.objects.create(name='Backend')
        item = Item.objects.create(title='Test Item', created_by=self.user)
        
        # Create tasks with the tag
        task1 = Task.objects.create(title='Task 1', item=item, created_by=self.user)
        task1.tags.add(tag)
        
        task2 = Task.objects.create(title='Task 2', item=item, created_by=self.user)
        task2.tags.add(tag)
        
        # Calculate usage
        count = tag.calculate_usage_count()
        
        self.assertEqual(count, 2)
        self.assertEqual(tag.usage_count, 2)
    
    def test_tag_calculate_usage_with_items_and_tasks(self):
        """Test usage count calculation with both items and tasks"""
        tag = Tag.objects.create(name='API')
        
        # Create items with the tag
        item1 = Item.objects.create(title='Test Item 1', created_by=self.user)
        item1.tags.add(tag)
        
        # Create tasks with the tag
        task1 = Task.objects.create(title='Task 1', item=item1, created_by=self.user)
        task1.tags.add(tag)
        
        # Calculate usage
        count = tag.calculate_usage_count()
        
        self.assertEqual(count, 2)  # 1 item + 1 task
        self.assertEqual(tag.usage_count, 2)


class TagDeletionProtectionTest(TestCase):
    """Test tag deletion protection based on usage count"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.user.set_password('testpass123')
        self.user.save()
        
        # Set session to simulate logged-in user
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session['user_role'] = self.user.role
        session.save()
    
    def test_delete_unused_tag(self):
        """Test that unused tags can be deleted"""
        tag = Tag.objects.create(name='Unused Tag')
        tag_id = tag.id
        
        # Try to delete with POST
        response = self.client.post(reverse('main:tag_delete', args=[tag_id]))
        
        # Should redirect and tag should be deleted
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Tag.objects.filter(id=tag_id).exists())
    
    def test_cannot_delete_tag_in_use(self):
        """Test that tags in use cannot be deleted"""
        tag = Tag.objects.create(name='Used Tag')
        item = Item.objects.create(title='Test Item', created_by=self.user)
        item.tags.add(tag)
        
        tag_id = tag.id
        
        # Try to delete with POST
        response = self.client.post(reverse('main:tag_delete', args=[tag_id]))
        
        # Should redirect but tag should still exist
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tag.objects.filter(id=tag_id).exists())
    
    def test_delete_protection_message(self):
        """Test that appropriate error message is shown for tags in use"""
        tag = Tag.objects.create(name='Protected Tag')
        item = Item.objects.create(title='Test Item', created_by=self.user)
        item.tags.add(tag)
        
        # Try to delete with POST
        response = self.client.post(reverse('main:tag_delete', args=[tag.id]), follow=True)
        
        # Check for error message
        messages = list(response.context['messages'])
        self.assertTrue(any('Cannot delete' in str(m) for m in messages))
    
    def test_get_request_redirects(self):
        """Test that GET requests to delete endpoint redirect with warning"""
        tag = Tag.objects.create(name='Test Tag')
        
        # Try to delete with GET request
        response = self.client.get(reverse('main:tag_delete', args=[tag.id]), follow=True)
        
        # Should redirect and tag should still exist
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Tag.objects.filter(id=tag.id).exists())
        
        # Check for warning message
        messages = list(response.context['messages'])
        self.assertTrue(any('Invalid delete request' in str(m) for m in messages))


class TagPaginationTest(TestCase):
    """Test tag list pagination"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.user.set_password('testpass123')
        self.user.save()
        
        # Set session to simulate logged-in user
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session['user_role'] = self.user.role
        session.save()
        
        # Create multiple tags
        for i in range(25):
            Tag.objects.create(name=f'Tag {i:02d}')
    
    def test_tag_list_pagination(self):
        """Test that tag list is paginated"""
        response = self.client.get(reverse('main:tag_list'))
        
        self.assertEqual(response.status_code, 200)
        # Should have 10 tags per page (as per views.py)
        self.assertEqual(len(response.context['tags']), 10)
    
    def test_tag_list_page_2(self):
        """Test accessing second page of tags"""
        response = self.client.get(reverse('main:tag_list') + '?page=2')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tags']), 10)
    
    def test_tag_list_last_page(self):
        """Test accessing last page of tags"""
        response = self.client.get(reverse('main:tag_list') + '?page=3')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['tags']), 5)  # 25 total, 10 per page


class TagSearchTest(TestCase):
    """Test tag search functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(username='testuser', email='test@example.com')
        self.user.set_password('testpass123')
        self.user.save()
        
        # Set session to simulate logged-in user
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session['username'] = self.user.username
        session['user_role'] = self.user.role
        session.save()
        
        # Create tags with different names
        Tag.objects.create(name='Python')
        Tag.objects.create(name='Django')
        Tag.objects.create(name='JavaScript')
        Tag.objects.create(name='React')
        Tag.objects.create(name='Database')
    
    def test_tag_search_finds_results(self):
        """Test that search finds matching tags"""
        response = self.client.get(reverse('main:tag_list') + '?search=Python')
        
        self.assertEqual(response.status_code, 200)
        tags = list(response.context['tags'])
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].name, 'Python')
    
    def test_tag_search_case_insensitive(self):
        """Test that search is case-insensitive"""
        response = self.client.get(reverse('main:tag_list') + '?search=python')
        
        self.assertEqual(response.status_code, 200)
        tags = list(response.context['tags'])
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].name, 'Python')
    
    def test_tag_search_partial_match(self):
        """Test that search finds partial matches"""
        response = self.client.get(reverse('main:tag_list') + '?search=Script')
        
        self.assertEqual(response.status_code, 200)
        tags = list(response.context['tags'])
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0].name, 'JavaScript')
    
    def test_tag_search_no_results(self):
        """Test search with no matching tags"""
        response = self.client.get(reverse('main:tag_list') + '?search=NoMatch')
        
        self.assertEqual(response.status_code, 200)
        tags = list(response.context['tags'])
        self.assertEqual(len(tags), 0)
    
    def test_tag_search_empty_query(self):
        """Test that empty search returns all tags"""
        response = self.client.get(reverse('main:tag_list') + '?search=')
        
        self.assertEqual(response.status_code, 200)
        tags = list(response.context['tags'])
        self.assertEqual(len(tags), 5)
