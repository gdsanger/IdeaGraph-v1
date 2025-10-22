"""
Semantic Network Service for IdeaGraph

This module provides semantic network generation and traversal using Weaviate vector database.
It builds multi-level semantic networks from any object (Item, Task, GitHub Issue, etc.)
and generates AI summaries for each level using KiGate.
"""

import logging
from typing import Optional, Dict, Any, List, Set
from datetime import datetime
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery, Filter


logger = logging.getLogger('semantic_network_service')


class SemanticNetworkServiceError(Exception):
    """Base exception for SemanticNetworkService errors"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to structured dictionary"""
        return {
            'success': False,
            'error': self.message,
            'details': self.details or ''
        }


class SemanticNetworkService:
    """
    Semantic Network Service
    
    Generates semantic networks by traversing Weaviate vector database:
    - Finds semantically similar objects at multiple levels
    - Builds graph structure with nodes and edges
    - Generates AI summaries for each level using KiGate
    """
    
    # All objects are stored in the KnowledgeObject collection
    # and differentiated by their 'type' property
    COLLECTION_NAME = 'KnowledgeObject'
    
    # Type values in the KnowledgeObject collection
    TYPE_MAPPING = {
        'item': 'Item',
        'task': 'Task',
        'github_issue': 'GitHubIssue',
        'mail': 'Mail',
        'file': 'File'
    }
    
    # Default similarity thresholds for each level
    DEFAULT_THRESHOLDS = {
        1: 0.8,  # Level 1: Very similar (>80%)
        2: 0.7,  # Level 2: Similar (>70%)
        3: 0.6   # Level 3: Somewhat similar (>60%)
    }
    
    # Maximum results per level
    MAX_RESULTS_PER_LEVEL = 10
    
    def __init__(self, settings=None):
        """
        Initialize SemanticNetworkService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise SemanticNetworkServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise SemanticNetworkServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            SemanticNetworkServiceError: If initialization fails
        """
        try:
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise SemanticNetworkServiceError(
                        "Weaviate Cloud enabled but URL or API key not configured"
                    )
                
                logger.info(f"Initializing Weaviate client for cloud: {self.settings.weaviate_url}")
                
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
                )
            else:
                # Use local Weaviate instance at localhost:8081 with no authentication
                logger.info("Initializing Weaviate client at localhost:8081")
                
                self._client = weaviate.connect_to_local(
                    host="localhost",
                    port=8081
                )

            logger.info("Weaviate client initialized for semantic network service")

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {str(e)}")
            raise SemanticNetworkServiceError(
                "Failed to initialize Weaviate client",
                details=str(e)
            )
    
    def _get_object_by_id(self, object_type: str, object_id: str) -> Optional[Dict[str, Any]]:
        """
        Get object from Weaviate by ID and verify its type
        
        Args:
            object_type: Type value to verify (e.g., 'Item', 'Task')
            object_id: UUID of the object
        
        Returns:
            Object data or None if not found or type mismatch
        """
        try:
            collection = self._client.collections.get(self.COLLECTION_NAME)
            obj = collection.query.fetch_object_by_id(object_id)
            
            if obj:
                # Verify the object has the correct type
                obj_type = obj.properties.get('type', '')
                if obj_type == object_type:
                    return {
                        'id': str(obj.uuid),
                        'type': object_type.lower(),
                        'properties': obj.properties,
                        'vector': obj.vector if hasattr(obj, 'vector') else None
                    }
                else:
                    logger.warning(f"Object {object_id} has type '{obj_type}', expected '{object_type}'")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching object {object_id} from {self.COLLECTION_NAME}: {str(e)}")
            return None
    
    def _find_hierarchical_relations(self, object_type: str, object_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find parent and child relationships for an object
        
        Args:
            object_type: Type value (e.g., 'Item')
            object_id: UUID of the object
        
        Returns:
            Dictionary with 'parent' and 'children' lists
        """
        relations = {
            'parent': [],
            'children': []
        }
        
        # Only Items have hierarchical relationships
        if object_type != 'Item':
            return relations
        
        try:
            from main.models import Item
            
            # Get the item
            try:
                item = Item.objects.get(id=object_id)
            except Item.DoesNotExist:
                return relations
            
            # Get parent if exists
            if item.parent:
                parent_obj = self._get_object_by_id('Item', str(item.parent.id))
                if parent_obj:
                    relations['parent'].append({
                        'id': str(item.parent.id),
                        'type': 'item',
                        'properties': parent_obj['properties'],
                        'relationship': 'parent'
                    })
            
            # Get children
            for child in item.children.all():
                child_obj = self._get_object_by_id('Item', str(child.id))
                if child_obj:
                    relations['children'].append({
                        'id': str(child.id),
                        'type': 'item',
                        'properties': child_obj['properties'],
                        'relationship': 'child',
                        'inherits_context': child.inherit_context
                    })
            
            return relations
            
        except Exception as e:
            logger.error(f"Error finding hierarchical relations: {str(e)}")
            return relations
    
    def _find_similar_objects(
        self,
        object_type: str,
        source_uuid: str,
        similarity_threshold: float,
        limit: int = 10,
        exclude_ids: Optional[Set[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar objects using nearObject query, filtered by type
        
        Args:
            object_type: Type value to filter by (e.g., 'Item', 'Task')
            source_uuid: UUID of the source object
            similarity_threshold: Minimum similarity (1 - distance)
            limit: Maximum number of results
            exclude_ids: Set of IDs to exclude from results
        
        Returns:
            List of similar objects with metadata
        """
        try:
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Use nearObject to find similar items, filtered by type
            response = collection.query.near_object(
                near_object=source_uuid,
                limit=limit + 20,  # Get extra to account for filtering
                return_metadata=MetadataQuery(distance=True),
                filters=Filter.by_property("type").equal(object_type)
            )
            
            similar_objects = []
            exclude_ids = exclude_ids or set()
            
            for obj in response.objects:
                obj_id = str(obj.uuid)
                
                # Skip if this is the source object or in exclude list
                if obj_id == source_uuid or obj_id in exclude_ids:
                    continue
                
                # Calculate similarity from distance
                distance = obj.metadata.distance if obj.metadata else 1.0
                similarity = max(0, 1 - distance)
                
                # Filter by similarity threshold
                if similarity >= similarity_threshold:
                    similar_objects.append({
                        'id': obj_id,
                        'type': object_type.lower(),
                        'properties': obj.properties,
                        'similarity': similarity,
                        'distance': distance
                    })
                
                # Stop if we have enough results
                if len(similar_objects) >= limit:
                    break
            
            logger.info(f"Found {len(similar_objects)} similar objects of type {object_type} "
                       f"(threshold: {similarity_threshold})")
            
            return similar_objects
            
        except Exception as e:
            logger.error(f"Error finding similar objects of type {object_type}: {str(e)}")
            return []
    
    def _generate_level_summary(self, level: int, objects: List[Dict[str, Any]], user_id: str) -> str:
        """
        Generate AI summary for a network level using KiGate
        
        Args:
            level: Level number (1, 2, 3)
            objects: List of objects in this level
            user_id: User ID for KiGate request
        
        Returns:
            Summary text
        """
        try:
            from core.services.kigate_service import KiGateService
            
            # Build context from objects
            object_descriptions = []
            for obj in objects[:20]:  # Limit to first 20 for summary
                props = obj.get('properties', {})
                title = props.get('title', 'Untitled')
                description = props.get('description', '')[:200]  # First 200 chars
                obj_type = obj.get('type', 'unknown')
                
                object_descriptions.append(
                    f"- [{obj_type.upper()}] {title}: {description}"
                )
            
            # Create prompt for summarization
            context = "\n".join(object_descriptions)
            message = f"""Diese Ebene {level} des semantischen Netzwerks enthält {len(objects)} Objekte.
Bitte fasse die wichtigsten Themen, Gemeinsamkeiten und Schwerpunkte dieser Objekte zusammen.

Objekte:
{context}

Bitte antworte in 2-3 kurzen Sätzen auf Deutsch."""
            
            # Call KiGate summarize-text-agent
            kigate = KiGateService(self.settings)
            response = kigate.execute_agent(
                agent_name='summarize-text-agent',
                provider='openai',
                model='gpt-4',
                message=message,
                user_id=user_id
            )
            
            if response.get('success') and response.get('result'):
                return response['result']
            else:
                logger.warning(f"KiGate summarization failed for level {level}")
                return f"Ebene {level} umfasst {len(objects)} semantisch verwandte Objekte."
                
        except Exception as e:
            logger.error(f"Error generating level summary: {str(e)}")
            return f"Ebene {level} umfasst {len(objects)} semantisch verwandte Objekte."
    
    def generate_network(
        self,
        object_type: str,
        object_id: str,
        depth: int = 3,
        user_id: str = 'system',
        thresholds: Optional[Dict[int, float]] = None,
        generate_summaries: bool = True,
        include_hierarchy: bool = False
    ) -> Dict[str, Any]:
        """
        Generate semantic network from a source object
        
        Args:
            object_type: Type of object ('item', 'task', 'github_issue', etc.)
            object_id: UUID of the source object
            depth: Maximum depth of network (1-3)
            user_id: User ID for KiGate requests
            thresholds: Custom similarity thresholds per level
            generate_summaries: Whether to generate AI summaries
            include_hierarchy: Whether to include parent-child relationships
        
        Returns:
            Dictionary containing:
                - nodes: List of nodes with metadata
                - edges: List of edges with weights
                - levels: Level-by-level breakdown with summaries
                - source_id: ID of the source object
                - hierarchy: Parent and child relationships (if include_hierarchy=True)
        """
        try:
            # Validate object type
            if object_type not in self.TYPE_MAPPING:
                raise SemanticNetworkServiceError(
                    f"Invalid object type: {object_type}",
                    details=f"Must be one of: {', '.join(self.TYPE_MAPPING.keys())}"
                )
            
            type_value = self.TYPE_MAPPING[object_type]
            thresholds = thresholds or self.DEFAULT_THRESHOLDS
            depth = min(max(depth, 1), 3)  # Clamp to 1-3
            
            logger.info(f"Generating semantic network for {object_type}/{object_id}, depth={depth}, include_hierarchy={include_hierarchy}")
            
            # Get source object
            source_obj = self._get_object_by_id(type_value, object_id)
            if not source_obj:
                raise SemanticNetworkServiceError(
                    f"Source object not found: {object_id}",
                    details=f"Object not found in {self.COLLECTION_NAME} or type mismatch"
                )
            
            # Initialize graph structure
            nodes = {}
            edges = []
            levels = {}
            visited_ids = {object_id}
            
            # Add source node
            nodes[object_id] = {
                'id': object_id,
                'type': object_type,
                'level': 0,
                'properties': source_obj['properties'],
                'isSource': True
            }
            
            # Get hierarchical relationships if requested
            hierarchy = None
            if include_hierarchy:
                hierarchy = self._find_hierarchical_relations(type_value, object_id)
                
                # Add parent node and edge if exists
                if hierarchy['parent']:
                    parent = hierarchy['parent'][0]
                    parent_id = parent['id']
                    
                    if parent_id not in visited_ids:
                        nodes[parent_id] = {
                            'id': parent_id,
                            'type': parent['type'],
                            'level': -1,  # Parent is at level -1
                            'properties': parent['properties'],
                            'isSource': False,
                            'isParent': True
                        }
                        visited_ids.add(parent_id)
                    
                    # Add hierarchical edge (parent -> child)
                    edges.append({
                        'source': parent_id,
                        'target': object_id,
                        'weight': 1.0,
                        'level': 0,
                        'type': 'hierarchy',
                        'relationship': 'parent'
                    })
                
                # Add children nodes and edges
                for child in hierarchy['children']:
                    child_id = child['id']
                    
                    if child_id not in visited_ids:
                        nodes[child_id] = {
                            'id': child_id,
                            'type': child['type'],
                            'level': -1,  # Children are also at level -1 (hierarchy level)
                            'properties': child['properties'],
                            'isSource': False,
                            'isChild': True,
                            'inheritsContext': child.get('inherits_context', False)
                        }
                        visited_ids.add(child_id)
                    
                    # Add hierarchical edge (parent -> child)
                    edges.append({
                        'source': object_id,
                        'target': child_id,
                        'weight': 1.0,
                        'level': 0,
                        'type': 'hierarchy',
                        'relationship': 'child'
                    })
            
            # Build semantic network level by level
            current_level_ids = [object_id]
            
            for level in range(1, depth + 1):
                threshold = thresholds.get(level, 0.6)
                level_nodes = []
                next_level_ids = []
                
                logger.info(f"Processing level {level} (threshold: {threshold})")
                
                # Find similar objects for each node in current level
                for node_id in current_level_ids:
                    similar = self._find_similar_objects(
                        type_value,
                        node_id,
                        threshold,
                        limit=self.MAX_RESULTS_PER_LEVEL,
                        exclude_ids=visited_ids
                    )
                    
                    for sim_obj in similar:
                        sim_id = sim_obj['id']
                        
                        # Add node if not already visited
                        if sim_id not in visited_ids:
                            nodes[sim_id] = {
                                'id': sim_id,
                                'type': sim_obj['type'],
                                'level': level,
                                'properties': sim_obj['properties'],
                                'similarity': sim_obj['similarity'],
                                'isSource': False
                            }
                            level_nodes.append(sim_obj)
                            next_level_ids.append(sim_id)
                            visited_ids.add(sim_id)
                        
                        # Add semantic similarity edge
                        edges.append({
                            'source': node_id,
                            'target': sim_id,
                            'weight': sim_obj['similarity'],
                            'level': level,
                            'type': 'similarity'
                        })
                
                # Generate summary for this level
                summary = ""
                if generate_summaries and level_nodes:
                    summary = self._generate_level_summary(level, level_nodes, user_id)
                
                # Store level information
                levels[level] = {
                    'level': level,
                    'threshold': threshold,
                    'node_count': len(level_nodes),
                    'nodes': [n['id'] for n in level_nodes],
                    'summary': summary
                }
                
                # Prepare for next level
                current_level_ids = next_level_ids
                
                # Stop if no more nodes to explore
                if not current_level_ids:
                    break
            
            result = {
                'success': True,
                'source_id': object_id,
                'source_type': object_type,
                'depth': depth,
                'nodes': list(nodes.values()),
                'edges': edges,
                'levels': levels,
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'include_hierarchy': include_hierarchy
            }
            
            # Add hierarchy information if requested
            if include_hierarchy and hierarchy:
                result['hierarchy'] = {
                    'has_parent': len(hierarchy['parent']) > 0,
                    'has_children': len(hierarchy['children']) > 0,
                    'parent_count': len(hierarchy['parent']),
                    'children_count': len(hierarchy['children'])
                }
            
            logger.info(f"Generated network with {len(nodes)} nodes and {len(edges)} edges")
            
            return result
            
        except SemanticNetworkServiceError:
            raise
        except Exception as e:
            logger.error(f"Error generating semantic network: {str(e)}")
            raise SemanticNetworkServiceError(
                "Failed to generate semantic network",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate client connection closed")
