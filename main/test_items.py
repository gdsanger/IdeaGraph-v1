"""
Tests for Item views
"""
from django.test import TestCase, Client
from main.models import User, Item, Section, Tag


class ItemViewsTest(TestCase):
    """Test Item views"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create admin user
        self.admin = User.objects.create(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        self.admin.set_password('Admin@123')
        self.admin.save()
        
        # Create section
        self.section = Section.objects.create(name='Test Section')
        
        # Create tag
        self.tag = Tag.objects.create(name='Test Tag', color='#3b82f6')
        
        # Create test item
        self.item = Item.objects.create(
            title='Test Item',
            description='Test description',
            status='new',
            section=self.section,
            created_by=self.user
        )
        self.item.tags.add(self.tag)
        
        self.client = Client()
    
    def login_user(self, user):
        """Helper to log in a user"""
        self.client.post('/login/', {
            'username': user.username,
            'password': 'Test@123' if user == self.user else 'Admin@123'
        })
    
    def test_item_list_requires_login(self):
        """Test that item list requires login"""
        response = self.client.get('/items/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_item_list_view(self):
        """Test item list view"""
        self.login_user(self.user)
        response = self.client.get('/items/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Items - List View')
        self.assertContains(response, 'Test Item')
    
    def test_item_list_view_without_search_query(self):
        """Test item list view without search query (regression test for UnboundLocalError)"""
        self.login_user(self.user)
        # This should not raise UnboundLocalError even without search query
        # because Q is imported at module level
        response = self.client.get('/items/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Item')
    
    def test_item_kanban_view(self):
        """Test item tile view (converted from kanban)"""
        self.login_user(self.user)
        response = self.client.get('/items/kanban/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Items - Tile View')
        self.assertContains(response, 'Test Item')
    
    def test_item_kanban_view_without_search_query(self):
        """Test item kanban view without search query (regression test for UnboundLocalError)"""
        self.login_user(self.user)
        # This should not raise UnboundLocalError even without search query
        # because Q is imported at module level
        response = self.client.get('/items/kanban/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Item')
    
    def test_item_detail_view(self):
        """Test item detail view"""
        self.login_user(self.user)
        response = self.client.get(f'/items/{self.item.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Item')
        self.assertContains(response, 'Item Details')
    
    def test_item_create_view_get(self):
        """Test item create view GET"""
        self.login_user(self.user)
        response = self.client.get('/items/create/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create New Item')
    
    def test_item_create_view_post(self):
        """Test item create view POST"""
        self.login_user(self.user)
        response = self.client.post('/items/create/', {
            'title': 'New Test Item',
            'description': 'New description',
            'status': 'new',
            'section': self.section.id,
            'tags': [self.tag.id]
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(Item.objects.filter(title='New Test Item').exists())
    
    def test_item_edit_view_post(self):
        """Test item edit view POST"""
        self.login_user(self.user)
        response = self.client.post(f'/items/{self.item.id}/edit/', {
            'title': 'Updated Title',
            'description': 'Updated description',
            'status': 'working',
            'section': self.section.id,
            'tags': [self.tag.id]
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'Updated Title')
        self.assertEqual(self.item.status, 'working')
    
    def test_item_delete_view(self):
        """Test item delete view"""
        self.login_user(self.user)
        item_id = self.item.id
        response = self.client.post(f'/items/{item_id}/delete/')
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertFalse(Item.objects.filter(id=item_id).exists())
    
    def test_user_can_only_see_own_items(self):
        """Test that users can only see their own items"""
        # Create another user and item
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='user'
        )
        other_user.set_password('Test@123')
        other_user.save()
        
        other_item = Item.objects.create(
            title='Other User Item',
            description='Other description',
            status='new',
            created_by=other_user
        )
        
        # Login as first user
        self.login_user(self.user)
        response = self.client.get('/items/')
        
        # Should see own item but not other user's item
        self.assertContains(response, 'Test Item')
        self.assertNotContains(response, 'Other User Item')
    
    def test_admin_can_see_all_items(self):
        """Test that admin can see all items"""
        # Create another user and item
        other_user = User.objects.create(
            username='otheruser',
            email='other@example.com',
            role='user'
        )
        other_item = Item.objects.create(
            title='Other User Item',
            description='Other description',
            status='new',
            created_by=other_user
        )
        
        # Login as admin
        self.login_user(self.admin)
        response = self.client.get('/items/')
        
        # Should see all items
        self.assertContains(response, 'Test Item')
        self.assertContains(response, 'Other User Item')
    
    def test_item_status_choices(self):
        """Test that all status choices are available"""
        self.login_user(self.user)
        response = self.client.get('/items/create/')
        
        # Check all status options are present
        self.assertContains(response, 'Neu')
        self.assertContains(response, 'Spezifikation Review')
        self.assertContains(response, 'Working')
        self.assertContains(response, 'Ready')
        self.assertContains(response, 'Erledigt')
        self.assertContains(response, 'Verworfen')
    
    def test_item_detail_view_post_saves_changes(self):
        """Test that item detail view handles POST requests and saves changes"""
        self.login_user(self.user)
        
        # Update item through detail view
        response = self.client.post(f'/items/{self.item.id}/', {
            'title': 'Updated via Detail View',
            'description': 'Updated description via detail',
            'status': 'ready',
            'section': self.section.id,
            'tags': [self.tag.id]
        })
        
        # Should return 200 (stay on same page)
        self.assertEqual(response.status_code, 200)
        
        # Verify changes were saved
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, 'Updated via Detail View')
        self.assertEqual(self.item.description, 'Updated description via detail')
        self.assertEqual(self.item.status, 'ready')
        
        # Check success message
        messages_list = list(response.context['messages'])
        self.assertTrue(any('updated successfully' in str(m) for m in messages_list))
    
    def test_item_detail_milestone_badge_bar(self):
        """Test that milestone badge bar is rendered with correct styles"""
        from main.models import Milestone
        from django.utils import timezone
        from datetime import timedelta
        
        self.login_user(self.user)
        
        today = timezone.now().date()
        
        # Create milestones with different due dates
        overdue_milestone = Milestone.objects.create(
            name='Overdue Milestone',
            description='This is overdue',
            due_date=today - timedelta(days=5),
            status='planned',
            item=self.item
        )
        
        due_soon_milestone = Milestone.objects.create(
            name='Due Soon',
            description='Due within a week',
            due_date=today + timedelta(days=3),
            status='in_progress',
            item=self.item
        )
        
        future_milestone = Milestone.objects.create(
            name='Future Milestone',
            description='Due in the future',
            due_date=today + timedelta(days=30),
            status='planned',
            item=self.item
        )
        
        response = self.client.get(f'/items/{self.item.id}/')
        self.assertEqual(response.status_code, 200)
        
        # Check that milestone badge bar is rendered
        self.assertContains(response, 'milestone-badge-bar')
        self.assertContains(response, 'Milestones:')
        
        # Check that milestones are rendered with correct names
        self.assertContains(response, 'Overdue Milestone')
        self.assertContains(response, 'Due Soon')
        self.assertContains(response, 'Future Milestone')
        
        # Check that correct badge classes are applied
        self.assertContains(response, 'badge-error')  # For overdue
        self.assertContains(response, 'badge-warning')  # For due soon
        self.assertContains(response, 'badge-success')  # For future
    
    def test_item_detail_no_milestone_badge_bar(self):
        """Test that milestone badge bar is not shown when no milestones"""
        self.login_user(self.user)
        
        response = self.client.get(f'/items/{self.item.id}/')
        self.assertEqual(response.status_code, 200)
        
        # Badge bar content should not be present when no milestones
        # Check for the actual Milestones: label instead of just the CSS class
        self.assertNotContains(response, '<strong style="font-size: 0.875rem;">Milestones:</strong>')
    
    def test_item_detail_hierarchical_relationships_position(self):
        """Test that hierarchical relationships card appears after item details"""
        self.login_user(self.user)
        
        # Create parent and child items
        parent_item = Item.objects.create(
            title='Parent Item',
            description='Parent description',
            status='ready',
            created_by=self.user
        )
        
        self.item.parent = parent_item
        self.item.save()
        
        child_item = Item.objects.create(
            title='Child Item',
            description='Child description',
            status='new',
            parent=self.item,
            created_by=self.user
        )
        
        response = self.client.get(f'/items/{self.item.id}/')
        self.assertEqual(response.status_code, 200)
        
        # Check that hierarchical relationships card is rendered
        self.assertContains(response, 'Hierarchische Beziehungen')
        self.assertContains(response, 'Parent Item')
        self.assertContains(response, 'Child Item')
        
        # Verify it appears after the item details card (by checking HTML structure)
        content = response.content.decode()
        item_details_pos = content.find('Item Details')
        hierarchical_pos = content.find('Hierarchische Beziehungen')
        
        # Hierarchical relationships should appear after item details
        self.assertGreater(hierarchical_pos, item_details_pos)


class ItemTileViewFilterTest(TestCase):
    """Test TileView (Kanban) search and filter functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='user'
        )
        self.user.set_password('Test@123')
        self.user.save()
        
        # Create sections
        self.section1 = Section.objects.create(name='Section A')
        self.section2 = Section.objects.create(name='Section B')
        
        # Create tags
        self.tag1 = Tag.objects.create(name='Tag 1', color='#3b82f6')
        self.tag2 = Tag.objects.create(name='Tag 2', color='#f59e0b')
        
        # Create test items with different statuses and sections
        self.item1 = Item.objects.create(
            title='First Item',
            description='Description for first item',
            status='new',
            section=self.section1,
            created_by=self.user
        )
        self.item1.tags.add(self.tag1)
        
        self.item2 = Item.objects.create(
            title='Second Item',
            description='Description for second item',
            status='ready',
            section=self.section2,
            created_by=self.user
        )
        self.item2.tags.add(self.tag2)
        
        self.item3 = Item.objects.create(
            title='Third Item',
            description='Special keyword in description',
            status='working',
            section=self.section1,
            created_by=self.user
        )
        self.item3.tags.add(self.tag1, self.tag2)
        
        self.item4 = Item.objects.create(
            title='Fourth Item',
            description='Another description',
            status='done',
            section=self.section2,
            created_by=self.user
        )
        
        self.client = Client()
    
    def login_user(self):
        """Helper to log in the test user"""
        self.client.post('/login/', {
            'username': self.user.username,
            'password': 'Test@123'
        })
    
    def test_tile_view_search_by_title(self):
        """Test search functionality by title"""
        self.login_user()
        response = self.client.get('/items/kanban/?search=First')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Item')
        self.assertNotContains(response, 'Second Item')
        self.assertNotContains(response, 'Third Item')
    
    def test_tile_view_search_by_description(self):
        """Test search functionality by description"""
        self.login_user()
        response = self.client.get('/items/kanban/?search=Special keyword')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Third Item')
        self.assertNotContains(response, 'First Item')
    
    def test_tile_view_filter_by_status(self):
        """Test filter by status"""
        self.login_user()
        response = self.client.get('/items/kanban/?status=ready')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Second Item')
        self.assertNotContains(response, 'First Item')
        self.assertNotContains(response, 'Third Item')
    
    def test_tile_view_filter_by_section(self):
        """Test filter by section"""
        self.login_user()
        response = self.client.get(f'/items/kanban/?section={self.section1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Item')
        self.assertContains(response, 'Third Item')
        self.assertNotContains(response, 'Second Item')
    
    def test_tile_view_combined_filters(self):
        """Test combined search and filters"""
        self.login_user()
        response = self.client.get(f'/items/kanban/?search=Item&status=new&section={self.section1.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First Item')
        self.assertNotContains(response, 'Second Item')
        self.assertNotContains(response, 'Third Item')
    
    def test_tile_view_no_results(self):
        """Test when no items match the filters"""
        self.login_user()
        response = self.client.get('/items/kanban/?search=NonExistentItem')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No items found matching your search criteria')
        self.assertContains(response, 'Clear Filters')
    
    def test_tile_view_has_filter_form(self):
        """Test that tile view has filter form elements"""
        self.login_user()
        response = self.client.get('/items/kanban/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="search"')
        self.assertContains(response, 'name="status"')
        self.assertContains(response, 'name="section"')
        self.assertContains(response, '<i class="bi bi-funnel"></i> Filter')
    
    def test_tile_view_preserves_filter_values(self):
        """Test that filter values are preserved in the form"""
        self.login_user()
        response = self.client.get(f'/items/kanban/?search=test&status=ready&section={self.section1.id}')
        self.assertEqual(response.status_code, 200)
        # Check that filter values are preserved
        self.assertContains(response, 'value="test"')
        self.assertContains(response, 'value="ready" selected')
        self.assertContains(response, f'value="{self.section1.id}" selected')
    
    def test_tile_view_pagination(self):
        """Test that pagination works in tile view"""
        self.login_user()
        
        # Create more items to test pagination (need more than 24 items)
        for i in range(30):
            Item.objects.create(
                title=f'Pagination Item {i}',
                description=f'Description {i}',
                status='new',
                section=self.section1,
                created_by=self.user
            )
        
        # Get first page
        response = self.client.get('/items/kanban/')
        self.assertEqual(response.status_code, 200)
        # Should have pagination controls
        self.assertContains(response, 'pagination')
        self.assertContains(response, 'Next')
        
        # Get second page
        response = self.client.get('/items/kanban/?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Previous')
    
    def test_tile_view_shows_item_count(self):
        """Test that tile view shows total item count"""
        self.login_user()
        response = self.client.get('/items/kanban/')
        self.assertEqual(response.status_code, 200)
        # Should show item count badge (4 items in setup)
        self.assertContains(response, '4 items')
    
    def test_item_detail_shows_only_non_completed_milestones(self):
        """Test that item detail page shows only non-completed milestones in the top badge bar"""
        from main.models import Milestone
        from datetime import date, timedelta
        
        # Create test milestones with different statuses
        milestone_planned = Milestone.objects.create(
            name='Planned Milestone',
            due_date=date.today() + timedelta(days=30),
            status='planned',
            item=self.item
        )
        milestone_in_progress = Milestone.objects.create(
            name='In Progress Milestone',
            due_date=date.today() + timedelta(days=15),
            status='in_progress',
            item=self.item
        )
        milestone_completed = Milestone.objects.create(
            name='Completed Milestone',
            due_date=date.today() - timedelta(days=10),
            status='completed',
            item=self.item
        )
        
        self.login_user(self.user)
        response = self.client.get(f'/items/{self.item.id}/')
        
        # Should show non-completed milestones
        self.assertContains(response, 'Planned Milestone')
        self.assertContains(response, 'In Progress Milestone')
        
        # Should show the milestone badge bar since there are non-completed milestones
        self.assertContains(response, 'milestone-badge-bar')
        
        # Verify the context contains filtered milestones
        self.assertIn('non_completed_milestones', response.context)
        non_completed = list(response.context['non_completed_milestones'])
        self.assertEqual(len(non_completed), 2)
        self.assertIn(milestone_planned, non_completed)
        self.assertIn(milestone_in_progress, non_completed)
        self.assertNotIn(milestone_completed, non_completed)
    
    def test_item_detail_hides_milestone_bar_when_all_completed(self):
        """Test that milestone badge bar is hidden when all milestones are completed"""
        from main.models import Milestone
        from datetime import date, timedelta
        
        # Create only completed milestones
        Milestone.objects.create(
            name='Completed Milestone 1',
            due_date=date.today() - timedelta(days=10),
            status='completed',
            item=self.item
        )
        Milestone.objects.create(
            name='Completed Milestone 2',
            due_date=date.today() - timedelta(days=5),
            status='completed',
            item=self.item
        )
        
        self.login_user(self.user)
        response = self.client.get(f'/items/{self.item.id}/')
        
        # Milestone badge bar should NOT be rendered when all milestones are completed
        self.assertNotContains(response, 'milestone-badge-bar')
        
        # Verify the context contains empty filtered milestones
        self.assertIn('non_completed_milestones', response.context)
        non_completed = list(response.context['non_completed_milestones'])
        self.assertEqual(len(non_completed), 0)
