# Weaviate GitHub Issue Sync - Upsert Fix Summary

## Problem

The `sync_github_issues.py` script was failing with HTTP 422 errors when synchronizing GitHub issues to Weaviate:

```
HTTP Request: POST http://localhost:8081/v1/objects "HTTP/1.1 422 Unprocessable Entity"
Failed to sync issue to Weaviate: Object was not added! Unexpected status code: 422, 
with response body: {'error': [{'message': "id '73cf2cb9-d2c8-5500-8b04-b0b0823d77e9' already exists"}]}
```

The issue occurred because the code always tried to **INSERT** new objects, even when objects with the same UUID already existed in Weaviate.

## Solution

Modified the synchronization logic to implement proper **upsert** behavior:

1. **Check for existence first**: Use `collection.data.exists(uuid)` to check if an object already exists
2. **Update existing objects**: Use `collection.data.update()` (PATCH operation) for existing objects
3. **Insert new objects**: Use `collection.data.insert()` (POST operation) for new objects
4. **Proper cleanup**: Ensure Weaviate client connection is closed in finally block

## Changes Made

### 1. Modified `sync_issue_to_weaviate()` method
**File**: `core/services/weaviate_github_issue_sync_service.py`

```python
# Check if object already exists
exists = collection.data.exists(uuid)

if exists:
    # Update existing object (PATCH operation)
    logger.info(f"Issue #{issue_number} already exists in Weaviate, updating...")
    collection.data.update(
        uuid=uuid,
        properties=properties
    )
else:
    # Insert new object (POST operation)
    logger.info(f"Issue #{issue_number} is new, inserting into Weaviate...")
    collection.data.insert(
        properties=properties,
        uuid=uuid
    )
```

### 2. Modified `sync_pull_request_to_weaviate()` method
Applied the same upsert logic to pull request synchronization.

### 3. Added proper connection cleanup
**File**: `sync_github_issues.py`

```python
finally:
    # Ensure Weaviate client connection is properly closed
    if sync_service:
        sync_service.close()
    logger.info(f"Finished at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
```

This addresses the warning: "The connection to Weaviate was not closed properly"

## Testing

Created comprehensive test suite in `main/test_weaviate_github_issue_sync_upsert.py` with 8 test cases:

1. ✅ `test_sync_issue_inserts_when_not_exists` - Verify INSERT for new objects
2. ✅ `test_sync_issue_updates_when_exists` - Verify UPDATE for existing objects
3. ✅ `test_sync_pr_inserts_when_not_exists` - Verify INSERT for new PRs
4. ✅ `test_sync_pr_updates_when_exists` - Verify UPDATE for existing PRs
5. ✅ `test_sync_issue_uses_deterministic_uuid` - Verify UUID consistency
6. ✅ `test_sync_issue_with_custom_uuid` - Verify custom UUID handling
7. ✅ `test_sync_issue_handles_references` - Verify task/item references
8. ✅ `test_sync_continues_on_reference_error` - Verify error recovery

All tests pass successfully!

## Benefits

1. **No more 422 errors**: Objects can be synced multiple times without errors
2. **Idempotent operations**: Running sync multiple times produces consistent results
3. **Data updates**: Changes to GitHub issues are now properly synchronized
4. **Better logging**: Clear indication of whether an object was inserted or updated
5. **Resource cleanup**: Proper connection closure prevents resource leaks
6. **Test coverage**: Comprehensive tests ensure reliability

## Verification

To verify the fix works:

1. Run the sync script: `python sync_github_issues.py`
2. Check logs for messages like:
   - "Issue #221 is new, inserting into Weaviate..." (first run)
   - "Issue #221 already exists in Weaviate, updating..." (subsequent runs)
3. No more 422 errors should appear
4. The "ResourceWarning: unclosed" warning should be gone

## Security

CodeQL analysis performed - **0 security issues found** ✓
