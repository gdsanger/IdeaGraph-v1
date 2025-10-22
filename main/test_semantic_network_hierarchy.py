"""
Tests for Semantic Network Service with Hierarchical Support

This module tests the semantic network generation with parent-child relationships.
"""
from django.test import TestCase
from unittest.mock import Mock, MagicMock, patch
from core.services.semantic_network_service import SemanticNetworkService, SemanticNetworkServiceError
from main.models import User, Item, Section


class SemanticNetworkHierarchyTest(TestCase):
    """Test cases for semantic network with hierarchical relationships"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock settings
        self.settings = Mock()
        self.settings.weaviate_cloud_enabled = False
        self.settings.weaviate_url = None
        self.settings.weaviate_api_key = None
        
        # Create test user
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='admin'
        )
        
        # Create test items
        self.parent_item = Item.objects.create(
            title='Parent Item',
            description='Parent description',
            created_by=self.user
        )
        
        self.child_item = Item.objects.create(
            title='Child Item',
            description='Child description',
            parent=self.parent_item,
            inherit_context=True,
            created_by=self.user
        )
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_find_hierarchical_relations_with_parent(self, mock_weaviate):
        """Test finding hierarchical relations when item has parent"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        
        # Mock parent object
        mock_parent_obj = MagicMock()
        mock_parent_obj.uuid = str(self.parent_item.id)
        mock_parent_obj.properties = {
            'title': 'Parent Item',
            'description': 'Parent description',
            'type': 'Item'
        }
        
        # Mock collection response for parent
        def mock_fetch_by_id(obj_id):
            if obj_id == str(self.parent_item.id):
                return mock_parent_obj
            return None
        
        mock_collection.query.fetch_object_by_id = mock_fetch_by_id
        
        service = SemanticNetworkService(settings=self.settings)
        
        # Test finding relations for child item
        relations = service._find_hierarchical_relations('Item', str(self.child_item.id))
        
        self.assertEqual(len(relations['parent']), 1)
        self.assertEqual(relations['parent'][0]['id'], str(self.parent_item.id))
        self.assertEqual(relations['parent'][0]['relationship'], 'parent')
        
        service.close()
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_find_hierarchical_relations_with_children(self, mock_weaviate):
        """Test finding hierarchical relations when item has children"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        
        # Mock child object
        mock_child_obj = MagicMock()
        mock_child_obj.uuid = str(self.child_item.id)
        mock_child_obj.properties = {
            'title': 'Child Item',
            'description': 'Child description',
            'type': 'Item'
        }
        
        # Mock collection response
        def mock_fetch_by_id(obj_id):
            if obj_id == str(self.child_item.id):
                return mock_child_obj
            return None
        
        mock_collection.query.fetch_object_by_id = mock_fetch_by_id
        
        service = SemanticNetworkService(settings=self.settings)
        
        # Test finding relations for parent item
        relations = service._find_hierarchical_relations('Item', str(self.parent_item.id))
        
        self.assertEqual(len(relations['children']), 1)
        self.assertEqual(relations['children'][0]['id'], str(self.child_item.id))
        self.assertEqual(relations['children'][0]['relationship'], 'child')
        self.assertTrue(relations['children'][0]['inherits_context'])
        
        service.close()
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_find_hierarchical_relations_for_non_item(self, mock_weaviate):
        """Test that hierarchical relations return empty for non-Item types"""
        mock_client = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        
        service = SemanticNetworkService(settings=self.settings)
        
        # Test with Task type (should return empty relations)
        relations = service._find_hierarchical_relations('Task', 'some-uuid')
        
        self.assertEqual(len(relations['parent']), 0)
        self.assertEqual(len(relations['children']), 0)
        
        service.close()
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_generate_network_includes_hierarchy_parameter(self, mock_weaviate):
        """Test that generate_network accepts include_hierarchy parameter"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        
        # Mock source object
        mock_obj = MagicMock()
        mock_obj.uuid = str(self.child_item.id)
        mock_obj.properties = {
            'title': 'Child Item',
            'type': 'Item'
        }
        
        mock_collection.query.fetch_object_by_id.return_value = mock_obj
        mock_collection.query.near_object.return_value = Mock(objects=[])
        
        service = SemanticNetworkService(settings=self.settings)
        
        # Test with include_hierarchy=False
        result = service.generate_network(
            object_type='item',
            object_id=str(self.child_item.id),
            depth=1,
            include_hierarchy=False,
            generate_summaries=False
        )
        
        self.assertTrue(result['success'])
        self.assertFalse(result['include_hierarchy'])
        self.assertNotIn('hierarchy', result)
        
        # Test with include_hierarchy=True
        result = service.generate_network(
            object_type='item',
            object_id=str(self.child_item.id),
            depth=1,
            include_hierarchy=True,
            generate_summaries=False
        )
        
        self.assertTrue(result['success'])
        self.assertTrue(result['include_hierarchy'])
        self.assertIn('hierarchy', result)
        
        service.close()
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_hierarchy_edges_have_correct_type(self, mock_weaviate):
        """Test that hierarchical edges have type='hierarchy'"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        
        # Mock objects
        mock_child_obj = MagicMock()
        mock_child_obj.uuid = str(self.child_item.id)
        mock_child_obj.properties = {
            'title': 'Child Item',
            'type': 'Item'
        }
        
        mock_parent_obj = MagicMock()
        mock_parent_obj.uuid = str(self.parent_item.id)
        mock_parent_obj.properties = {
            'title': 'Parent Item',
            'type': 'Item'
        }
        
        def mock_fetch_by_id(obj_id):
            if obj_id == str(self.child_item.id):
                return mock_child_obj
            elif obj_id == str(self.parent_item.id):
                return mock_parent_obj
            return None
        
        mock_collection.query.fetch_object_by_id = mock_fetch_by_id
        mock_collection.query.near_object.return_value = Mock(objects=[])
        
        service = SemanticNetworkService(settings=self.settings)
        
        result = service.generate_network(
            object_type='item',
            object_id=str(self.child_item.id),
            depth=1,
            include_hierarchy=True,
            generate_summaries=False
        )
        
        # Check that hierarchy edges exist and have correct type
        hierarchy_edges = [e for e in result['edges'] if e.get('type') == 'hierarchy']
        self.assertGreater(len(hierarchy_edges), 0)
        
        # Check that hierarchy edge has weight 1.0
        for edge in hierarchy_edges:
            self.assertEqual(edge['weight'], 1.0)
            self.assertIn('relationship', edge)
            self.assertIn(edge['relationship'], ['parent', 'child'])
        
        service.close()
    
    @patch('core.services.semantic_network_service.weaviate')
    def test_hierarchy_nodes_have_correct_flags(self, mock_weaviate):
        """Test that parent/child nodes have correct flags"""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_weaviate.connect_to_local.return_value = mock_client
        mock_client.collections.get.return_value = mock_collection
        
        # Mock objects
        mock_child_obj = MagicMock()
        mock_child_obj.uuid = str(self.child_item.id)
        mock_child_obj.properties = {
            'title': 'Child Item',
            'type': 'Item'
        }
        
        mock_parent_obj = MagicMock()
        mock_parent_obj.uuid = str(self.parent_item.id)
        mock_parent_obj.properties = {
            'title': 'Parent Item',
            'type': 'Item'
        }
        
        def mock_fetch_by_id(obj_id):
            if obj_id == str(self.child_item.id):
                return mock_child_obj
            elif obj_id == str(self.parent_item.id):
                return mock_parent_obj
            return None
        
        mock_collection.query.fetch_object_by_id = mock_fetch_by_id
        mock_collection.query.near_object.return_value = Mock(objects=[])
        
        service = SemanticNetworkService(settings=self.settings)
        
        result = service.generate_network(
            object_type='item',
            object_id=str(self.child_item.id),
            depth=1,
            include_hierarchy=True,
            generate_summaries=False
        )
        
        # Find parent node
        parent_nodes = [n for n in result['nodes'] if n.get('isParent', False)]
        self.assertEqual(len(parent_nodes), 1)
        self.assertEqual(parent_nodes[0]['id'], str(self.parent_item.id))
        
        service.close()
