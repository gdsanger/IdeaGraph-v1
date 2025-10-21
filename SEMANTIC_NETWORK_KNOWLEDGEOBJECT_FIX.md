# Semantic Network HTTP 400 Error Fix - KnowledgeObject Collection

## Problem
Users were experiencing HTTP 400 (Bad Request) errors when trying to access the semantic network feature:

```
GET /api/semantic-network/item/{uuid}?depth=3&summaries=true
```

Error message:
```
{"success": false, "error": "Source object not found: 38fd5eb9-8563-4771-b648-795db95ce0d2", "details": "Object not found in Item"}
```

Weaviate error in logs:
```
Query call with protocol GRPC search failed with message could not find class Item in schema.
```

## Root Cause
The `SemanticNetworkService` was trying to query separate Weaviate collections named `Item`, `Task`, `GitHubIssue`, etc. However, the actual Weaviate schema stores all objects in a single `KnowledgeObject` collection, with objects differentiated by a `type` property.

**Before:**
- Service expected: `Item` collection, `Task` collection, `GitHubIssue` collection
- Actual schema: All stored in `KnowledgeObject` collection with `type` property

## Solution
Updated `SemanticNetworkService` to:
1. Query the unified `KnowledgeObject` collection
2. Filter results by the `type` property (e.g., `type='Item'`, `type='Task'`)
3. Verify object types when fetching by ID

### Changes Made

**File: `core/services/semantic_network_service.py`**

1. **Replaced `COLLECTIONS` with `TYPE_MAPPING`:**
   - Changed from: `COLLECTIONS = {'item': 'Item', 'task': 'Task', ...}`
   - To: `COLLECTION_NAME = 'KnowledgeObject'` and `TYPE_MAPPING = {'item': 'Item', ...}`

2. **Updated `_get_object_by_id` method:**
   - Now queries `KnowledgeObject` collection
   - Verifies the object's `type` property matches expected type
   - Returns `None` if type mismatch

3. **Updated `_find_similar_objects` method:**
   - Queries `KnowledgeObject` collection with type filter
   - Uses `Filter.by_property("type").equal(object_type)` to filter results
   - Ensures only objects of the correct type are returned

4. **Updated `generate_network` method:**
   - Uses `TYPE_MAPPING` instead of `COLLECTIONS`
   - Passes type value (e.g., `'Item'`) instead of collection name

5. **Added Filter import:**
   - Added `Filter` to imports from `weaviate.classes.query`

**File: `main/test_semantic_network.py`**
- Updated test to use `TYPE_MAPPING` instead of `COLLECTIONS`
- Added test for `COLLECTION_NAME` constant

### Code Example

**Before:**
```python
collection_name = self.COLLECTIONS[object_type]  # e.g., 'Item'
collection = self._client.collections.get(collection_name)  # Fails - no 'Item' collection
response = collection.query.near_object(near_object=source_uuid, ...)
```

**After:**
```python
type_value = self.TYPE_MAPPING[object_type]  # e.g., 'Item'
collection = self._client.collections.get(self.COLLECTION_NAME)  # Use 'KnowledgeObject'
response = collection.query.near_object(
    near_object=source_uuid,
    filters=Filter.by_property("type").equal(type_value)  # Filter by type='Item'
)
```

## Testing
- Ran existing unit tests: 7 out of 8 tests passing
  - 1 pre-existing test failure unrelated to this fix (invalid UUID format in test)
  - Key test `test_type_mapping` passes successfully
- CodeQL security analysis: No vulnerabilities detected
- Changes are backward compatible with existing functionality

## Impact
This fix ensures that:
1. Semantic network queries work with the actual Weaviate schema (`KnowledgeObject`)
2. Objects are correctly filtered by their `type` property
3. No false matches between different object types (e.g., Items vs Tasks)
4. Error messages are more accurate (mentions `KnowledgeObject` and type mismatch)
5. The service aligns with how other sync services (Item, Task, GitHubIssue) store data

## Technical Details

### Weaviate Schema
All objects in the system are stored in a single collection:
- **Collection:** `KnowledgeObject`
- **Type property values:** `'Item'`, `'Task'`, `'GitHubIssue'`, `'Mail'`, `'File'`

This is consistent with:
- `WeaviateItemSyncService` (stores items with `type='Item'`)
- `WeaviateTaskSyncService` (stores tasks with `type='Task'`)
- `WeaviateGitHubIssueSyncService` (stores issues with `type='GitHubIssue'`)

### API Endpoint
The API endpoint remains unchanged:
```
GET /api/semantic-network/<object_type>/<object_id>?depth=3&summaries=true
```

Where `object_type` can be: `item`, `task`, `github_issue`, `mail`, or `file`

## Notes
- This fix aligns the semantic network service with the actual Weaviate schema
- The change is surgical - only updating the collection query logic
- No changes needed to the API, frontend, or other components
- The fix maintains all existing functionality while correcting the schema mismatch
