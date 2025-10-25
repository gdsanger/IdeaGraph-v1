"""
Test suite for the new modular Semantic Graph Component

This test verifies that the component structure is correctly set up.
"""

from django.test import TestCase
import os
from django.conf import settings


class SemanticGraphComponentTest(TestCase):
    """Test the new modular semantic graph component"""
    
    @classmethod
    def setUpClass(cls):
        """Set up class-level fixtures"""
        super().setUpClass()
        cls.base_path = os.path.join(settings.BASE_DIR, 'main', 'static', 'main', 'js', 'semantic-graph')
    
    def test_component_structure_exists(self):
        """Test that component files exist in the correct locations"""
        # Check that all component files exist
        self.assertTrue(os.path.exists(os.path.join(self.base_path, 'SemanticGraph.js')))
        self.assertTrue(os.path.exists(os.path.join(self.base_path, 'useSemanticGraphData.js')))
        self.assertTrue(os.path.exists(os.path.join(self.base_path, 'GraphNodeTooltip.js')))
        self.assertTrue(os.path.exists(os.path.join(self.base_path, 'GraphToolbar.js')))
        self.assertTrue(os.path.exists(os.path.join(self.base_path, 'README.md')))
    
    def test_semantic_graph_js_has_correct_class_name(self):
        """Test that SemanticGraph.js defines the SemanticGraph class"""
        file_path = os.path.join(self.base_path, 'SemanticGraph.js')
        
        with open(file_path, 'r') as f:
            content = f.read()
            self.assertIn('class SemanticGraph', content)
            self.assertIn('constructor(containerId, options = {})', content)
    
    def test_data_manager_has_load_method(self):
        """Test that useSemanticGraphData.js defines SemanticGraphDataManager with load method"""
        file_path = os.path.join(self.base_path, 'useSemanticGraphData.js')
        
        with open(file_path, 'r') as f:
            content = f.read()
            self.assertIn('class SemanticGraphDataManager', content)
            self.assertIn('async load(objectType, objectId)', content)
    
    def test_tooltip_has_show_hide_methods(self):
        """Test that GraphNodeTooltip.js has show and hide methods"""
        file_path = os.path.join(self.base_path, 'GraphNodeTooltip.js')
        
        with open(file_path, 'r') as f:
            content = f.read()
            self.assertIn('class GraphNodeTooltip', content)
            self.assertIn('show(event, nodeData)', content)
            self.assertIn('hide()', content)
    
    def test_toolbar_has_event_handlers(self):
        """Test that GraphToolbar.js has event handling methods"""
        file_path = os.path.join(self.base_path, 'GraphToolbar.js')
        
        with open(file_path, 'r') as f:
            content = f.read()
            self.assertIn('class GraphToolbar', content)
            self.assertIn('bindEvents()', content)
            self.assertIn('onReset', content)
            self.assertIn('onToggleLabels', content)
            self.assertIn('onToggleHierarchy', content)
    
    def test_readme_exists_and_has_content(self):
        """Test that README.md exists and has documentation"""
        file_path = os.path.join(self.base_path, 'README.md')
        
        with open(file_path, 'r') as f:
            content = f.read()
            self.assertIn('# Semantic Graph Component', content)
            self.assertIn('## Usage', content)
            self.assertIn('## Architecture', content)
