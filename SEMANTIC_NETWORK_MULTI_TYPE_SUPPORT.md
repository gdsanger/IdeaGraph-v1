# Semantic Network Multi-Type Support

## Overview

This document describes the enhancement to the semantic network feature that allows including multiple object types in semantic searches. This addresses the issue where the Item view semantic network only displayed Items and didn't show semantically similar Tasks from the Weaviate database.

## Problem Statement

Previously, the semantic network service filtered search results to only include objects of the same type as the source object. When viewing an Item's semantic network:
- Only similar Items were shown
- Tasks and other related objects were excluded
- Users had no visibility into semantically related Tasks

This limitation made it difficult to discover related content across different object types.

## Solution

The semantic network service has been enhanced to support searching across multiple object types simultaneously.

### Key Changes

1. **Multi-Type Search Support**
   - `_find_similar_objects()` now accepts a list of object types instead of a single type
   - Uses Weaviate's `Filter.any_of()` to create OR filters for multiple types
   - Properly handles the actual object type from response properties

2. **Default Behavior for Items**
   - Item semantic networks now include both Items and Tasks by default
   - Other object types continue to search only their own type (backward compatible)
   - Customizable via the `include_types` parameter

3. **Visual Distinction**
   - Different color schemes for Items vs Tasks in the graph visualization
   - Updated legend to clearly show both Item and Task colors
   - Tooltips display the object type

## Usage

### Backend API

The `generate_network()` method now accepts an optional `include_types` parameter:

```python
from core.services.semantic_network_service import SemanticNetworkService

service = SemanticNetworkService()

# Default behavior for Items (includes both Items and Tasks)
result = service.generate_network(
    object_type='item',
    object_id='item-uuid',
    depth=3
)

# Custom types
result = service.generate_network(
    object_type='item',
    object_id='item-uuid',
    depth=3,
    include_types=['item', 'task', 'github_issue']
)

# Only Items (override default)
result = service.generate_network(
    object_type='item',
    object_id='item-uuid',
    depth=3,
    include_types=['item']
)
```

### API Response

The response now includes a `search_types` field indicating which types were searched:

```json
{
    "success": true,
    "source_id": "item-uuid",
    "source_type": "item",
    "depth": 3,
    "nodes": [...],
    "edges": [...],
    "levels": {...},
    "total_nodes": 42,
    "total_edges": 68,
    "search_types": ["item", "task"]
}
```

### Frontend Visualization

The semantic network graph now displays:

**Items:**
- Level 1: Amber (#f59e0b)
- Level 2: Blue (#3b82f6)
- Level 3: Violet (#8b5cf6)

**Tasks:**
- Level 1: Pink (#ec4899)
- Level 2: Purple (#a855f7)
- Level 3: Indigo (#6366f1)

The legend clearly shows both color schemes for easy identification.

## Implementation Details

### Backend Changes

**File:** `core/services/semantic_network_service.py`

1. **`_find_similar_objects()` Method**
   ```python
   def _find_similar_objects(
       self,
       object_types: List[str],  # Changed from single string
       source_uuid: str,
       similarity_threshold: float,
       limit: int = 10,
       exclude_ids: Optional[Set[str]] = None
   ) -> List[Dict[str, Any]]:
   ```

   - Builds OR filter for multiple types using `Filter.any_of()`
   - Extracts actual type from object properties
   - Returns mixed list of different object types

2. **`generate_network()` Method**
   ```python
   def generate_network(
       self,
       object_type: str,
       object_id: str,
       depth: int = 3,
       user_id: str = 'system',
       thresholds: Optional[Dict[int, float]] = None,
       generate_summaries: bool = True,
       include_hierarchy: bool = False,
       include_types: Optional[List[str]] = None  # New parameter
   ) -> Dict[str, Any]:
   ```

   - Determines search types based on `include_types` or defaults
   - For Items, defaults to `['Item', 'Task']`
   - Other types default to their own type only
   - Includes `search_types` in response

### Frontend Changes

**File:** `main/static/main/js/semantic-network.js`

1. **`getNodeColor()` Method**
   - Implements type-specific color schemes
   - Maps object types to different color palettes
   - Maintains backward compatibility for unknown types

2. **Legend**
   - Shows separate entries for Item and Task colors
   - Clearly labeled by object type and level
   - Maintains existing legend items (source, hierarchy)

## Testing

Comprehensive tests verify the implementation:

1. **Single Type Search**
   - Filters work correctly for single type
   - Results match expected type

2. **Multiple Type Search**
   - OR filter includes multiple types
   - Results contain mixed types
   - Each object has correct type property

3. **Item Default Behavior**
   - Item networks include both Items and Tasks
   - Response includes correct search_types

4. **Backward Compatibility**
   - Task networks only include Tasks
   - Other object types unaffected
   - Existing functionality preserved

## Benefits

1. **Better Content Discovery**
   - Users can see related Tasks when viewing Items
   - Semantic connections across object types are visible
   - More comprehensive view of related content

2. **Flexible Configuration**
   - Default behavior is sensible (Items + Tasks for Items)
   - Can be customized via API parameter
   - Other object types maintain existing behavior

3. **Clear Visualization**
   - Different colors help distinguish object types
   - Legend provides clear identification
   - Tooltips show object type

4. **Backward Compatible**
   - Existing functionality unchanged
   - Optional parameter doesn't break existing code
   - Task and other object types behave as before

## Future Enhancements

Potential future improvements:

1. **User Preferences** (Priority: P2, Effort: Medium)
   - Allow users to configure which types to include
   - Save preferences per user or per object type
   - Estimated: 3-5 days

2. **Dynamic Type Selection** (Priority: P1, Effort: Low)
   - UI controls to filter by object type
   - Toggle visibility of specific types
   - Estimated: 1-2 days

3. **Type-Specific Thresholds** (Priority: P3, Effort: Medium)
   - Different similarity thresholds per object type
   - Fine-tune relevance by type
   - Estimated: 2-3 days

4. **Extended Type Support** (Priority: P2, Effort: Low-Medium)
   - Include more object types (GitHub Issues, Files, etc.)
   - Configurable type combinations
   - Estimated: 2-4 days

## Migration Notes

This is a backward-compatible change:
- No database migrations required
- Existing API calls work unchanged
- Default behavior for Items has changed (now includes Tasks)
- Other object types maintain existing behavior

If you want Items to only search for Items (old behavior), explicitly set:
```python
include_types=['item']
```

## Related Documentation

- [SEMANTIC_NETWORK_FIX.md](./SEMANTIC_NETWORK_FIX.md)
- [SEMANTIC_NETWORK_IMPLEMENTATION.md](./SEMANTIC_NETWORK_IMPLEMENTATION.md)
- [SEMANTIC_NETWORK_KNOWLEDGEOBJECT_FIX.md](./SEMANTIC_NETWORK_KNOWLEDGEOBJECT_FIX.md)
