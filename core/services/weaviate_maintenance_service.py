"""
Weaviate Maintenance Service for IdeaGraph

This module provides maintenance and diagnostic functionality for the Weaviate database:
- System status and metadata retrieval
- Schema export/backup and restore
- Index rebuilding
- Object search and inspection
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
import weaviate
from weaviate.classes.init import Auth

logger = logging.getLogger('weaviate_maintenance_service')


class WeaviateMaintenanceServiceError(Exception):
    """Base exception for WeaviateMaintenanceService errors"""
    
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


class WeaviateMaintenanceService:
    """
    Weaviate Maintenance Service
    
    Provides administrative functionality for Weaviate database:
    - Get system metadata, version, and uptime
    - Export and restore schema
    - Rebuild indices
    - Search and inspect individual objects
    """
    
    COLLECTION_NAME = 'KnowledgeObject'
    
    def __init__(self, settings=None):
        """
        Initialize WeaviateMaintenanceService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise WeaviateMaintenanceServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise WeaviateMaintenanceServiceError("No settings found in database")
        
        # Initialize Weaviate client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """
        Initialize Weaviate client
        
        Raises:
            WeaviateMaintenanceServiceError: If initialization fails
        """
        try:
            # Check if cloud mode is enabled
            if self.settings.weaviate_cloud_enabled:
                # Use cloud configuration
                if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
                    raise WeaviateMaintenanceServiceError(
                        "Weaviate Cloud enabled but URL or API key not configured"
                    )
                
                logger.info(f"Initializing Weaviate maintenance client for cloud: {self.settings.weaviate_url}")
                
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.settings.weaviate_url,
                    auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
                )
            else:
                # Use local Weaviate instance at localhost:8081 with no authentication
                logger.info("Initializing Weaviate maintenance client at localhost:8081")
                
                self._client = weaviate.connect_to_local(
                    host="localhost",
                    port=8081
                )

            logger.info("Weaviate maintenance client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate maintenance client: {str(e)}")
            raise WeaviateMaintenanceServiceError(
                "Failed to initialize Weaviate maintenance client",
                details=str(e)
            )
    
    def get_meta(self) -> Dict[str, Any]:
        """
        Get Weaviate system metadata including version, uptime, and node information
        
        Returns:
            Dictionary containing:
                - success: bool
                - meta: dict with system metadata
                - version: Weaviate version
                - hostname: Node hostname
        
        Raises:
            WeaviateMaintenanceServiceError: If metadata retrieval fails
        """
        try:
            logger.info("Retrieving Weaviate system metadata")
            
            # Get node metadata
            meta = self._client.get_meta()
            
            result = {
                'success': True,
                'meta': meta,
                'version': meta.get('version', 'Unknown'),
                'hostname': meta.get('hostname', 'Unknown'),
            }
            
            logger.info(f"Retrieved Weaviate metadata: version={result['version']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve Weaviate metadata: {str(e)}")
            raise WeaviateMaintenanceServiceError(
                "Failed to retrieve Weaviate metadata",
                details=str(e)
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get current Weaviate schema
        
        Returns:
            Dictionary containing:
                - success: bool
                - schema: dict with complete schema definition
                - collections: list of collection names
        
        Raises:
            WeaviateMaintenanceServiceError: If schema retrieval fails
        """
        try:
            logger.info("Retrieving Weaviate schema")
            
            # Get all collections
            collections_list = []
            try:
                # Get schema by iterating collections
                for collection_name in self._client.collections.list_all().keys():
                    collections_list.append(collection_name)
            except Exception as e:
                logger.warning(f"Could not list collections: {str(e)}")
            
            # Build schema representation
            schema = {
                'collections': collections_list,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Retrieved schema with {len(collections_list)} collections")
            
            return {
                'success': True,
                'schema': schema,
                'collections': collections_list
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve Weaviate schema: {str(e)}")
            raise WeaviateMaintenanceServiceError(
                "Failed to retrieve Weaviate schema",
                details=str(e)
            )
    
    def search_object(self, object_uuid: str) -> Dict[str, Any]:
        """
        Search for a specific object by UUID in Weaviate
        
        Args:
            object_uuid: UUID of the object to search for
        
        Returns:
            Dictionary containing:
                - success: bool
                - found: bool
                - object: dict with object data (if found)
        
        Raises:
            WeaviateMaintenanceServiceError: If search fails
        """
        try:
            logger.info(f"Searching for object with UUID: {object_uuid}")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Fetch object by ID
            obj = collection.query.fetch_object_by_id(object_uuid)
            
            if obj is None:
                logger.info(f"Object {object_uuid} not found in Weaviate")
                return {
                    'success': True,
                    'found': False,
                    'object': None
                }
            
            # Build object data
            object_data = {
                'uuid': str(obj.uuid),
                'properties': obj.properties,
                'collection': self.COLLECTION_NAME
            }
            
            logger.info(f"Found object {object_uuid} in Weaviate")
            
            return {
                'success': True,
                'found': True,
                'object': object_data
            }
            
        except Exception as e:
            logger.error(f"Failed to search for object {object_uuid}: {str(e)}")
            raise WeaviateMaintenanceServiceError(
                f"Failed to search for object {object_uuid}",
                details=str(e)
            )
    
    def export_schema(self) -> Dict[str, Any]:
        """
        Export current schema as JSON backup
        
        Returns:
            Dictionary containing:
                - success: bool
                - schema: dict with schema data
                - export_time: ISO timestamp of export
        
        Raises:
            WeaviateMaintenanceServiceError: If export fails
        """
        try:
            logger.info("Exporting Weaviate schema")
            
            # Get schema
            schema_result = self.get_schema()
            
            export_data = {
                'schema': schema_result['schema'],
                'export_time': datetime.now().isoformat(),
                'weaviate_version': self.get_meta()['version']
            }
            
            logger.info("Schema exported successfully")
            
            return {
                'success': True,
                'schema': export_data,
                'export_time': export_data['export_time']
            }
            
        except Exception as e:
            logger.error(f"Failed to export schema: {str(e)}")
            raise WeaviateMaintenanceServiceError(
                "Failed to export schema",
                details=str(e)
            )
    
    def restore_schema(self, schema_data: Dict[str, Any], confirm: bool = False) -> Dict[str, Any]:
        """
        Restore schema from backup
        
        WARNING: This operation is destructive and will delete all existing data
        
        Args:
            schema_data: Schema data from export
            confirm: Must be True to proceed with restore
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateMaintenanceServiceError: If restore fails
        """
        if not confirm:
            return {
                'success': False,
                'error': 'Schema restore requires confirmation. Set confirm=True to proceed.'
            }
        
        try:
            logger.warning("Schema restore requested - this is a destructive operation!")
            
            # Note: In Weaviate v4, schema restoration is more complex
            # This is a simplified implementation that would need enhancement
            # for production use
            
            return {
                'success': False,
                'error': 'Schema restore is not fully implemented. This requires manual intervention for safety.',
                'message': 'Please contact system administrator for schema restoration.'
            }
            
        except Exception as e:
            logger.error(f"Failed to restore schema: {str(e)}")
            raise WeaviateMaintenanceServiceError(
                "Failed to restore schema",
                details=str(e)
            )
    
    def rebuild_index(self) -> Dict[str, Any]:
        """
        Rebuild Weaviate indices
        
        Returns:
            Dictionary containing:
                - success: bool
                - message: str
        
        Raises:
            WeaviateMaintenanceServiceError: If rebuild fails
        """
        try:
            logger.info("Index rebuild requested")
            
            # Note: In Weaviate v4, index rebuilding is typically automatic
            # Manual rebuilding is generally not needed or exposed in the same way
            # This would require specific operations or cluster management
            
            return {
                'success': True,
                'message': 'Weaviate v4 manages indices automatically. No manual rebuild needed.',
                'info': 'If you are experiencing issues, consider checking cluster health and restarting nodes if necessary.'
            }
            
        except Exception as e:
            logger.error(f"Failed to rebuild index: {str(e)}")
            raise WeaviateMaintenanceServiceError(
                "Failed to rebuild index",
                details=str(e)
            )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the KnowledgeObject collection
        
        Returns:
            Dictionary containing:
                - success: bool
                - stats: dict with collection statistics
        
        Raises:
            WeaviateMaintenanceServiceError: If stats retrieval fails
        """
        try:
            logger.info("Retrieving collection statistics")
            
            # Get collection
            collection = self._client.collections.get(self.COLLECTION_NAME)
            
            # Count objects by type
            type_counts = {}
            
            # Query all objects (limited sample for counting)
            # Note: For large collections, this should be optimized
            try:
                response = collection.query.fetch_objects(limit=10000)
                
                for obj in response.objects:
                    obj_type = obj.properties.get('type', 'Unknown')
                    type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
                
                total_count = sum(type_counts.values())
            except Exception as e:
                logger.warning(f"Could not count objects: {str(e)}")
                total_count = 0
                type_counts = {}
            
            stats = {
                'collection_name': self.COLLECTION_NAME,
                'total_objects': total_count,
                'objects_by_type': type_counts,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Retrieved collection stats: {total_count} objects")
            
            return {
                'success': True,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve collection stats: {str(e)}")
            raise WeaviateMaintenanceServiceError(
                "Failed to retrieve collection stats",
                details=str(e)
            )
    
    def close(self):
        """Close the Weaviate client connection"""
        if self._client:
            self._client.close()
            logger.info("Weaviate maintenance client connection closed")
