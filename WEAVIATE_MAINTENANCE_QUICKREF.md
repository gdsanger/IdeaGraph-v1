# Weaviate Maintenance Dashboard - Quick Reference

## Overview
Admin-only API endpoints for monitoring and maintaining the Weaviate vector database in IdeaGraph.

## Prerequisites
- Admin role required
- Valid authentication session

## API Endpoints

### 1. Check Weaviate Status
**Endpoint:** `GET /api/weaviate/status`

**Purpose:** Get system metadata, version, and collection statistics

**Example Request:**
```bash
curl http://localhost:8000/api/weaviate/status \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

**Example Response:**
```json
{
  "success": true,
  "meta": {
    "version": "1.24.0",
    "hostname": "weaviate-node-1"
  },
  "version": "1.24.0",
  "hostname": "weaviate-node-1",
  "stats": {
    "collection_name": "KnowledgeObject",
    "total_objects": 1250,
    "objects_by_type": {
      "Item": 450,
      "Task": 600,
      "File": 150,
      "Mail": 50
    },
    "timestamp": "2024-10-27T23:00:00Z"
  }
}
```

**Use Cases:**
- Health check monitoring
- Capacity planning
- Troubleshooting sync issues

---

### 2. Export Schema
**Endpoint:** `POST /api/weaviate/schema/export`

**Purpose:** Export current Weaviate schema for backup

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/weaviate/schema/export \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

**Example Response:**
```json
{
  "success": true,
  "schema": {
    "collections": ["KnowledgeObject"],
    "timestamp": "2024-10-27T23:00:00Z",
    "weaviate_version": "1.24.0"
  },
  "export_time": "2024-10-27T23:00:00Z"
}
```

**Use Cases:**
- Regular backups
- Pre-migration snapshots
- Schema documentation

---

### 3. Search Object by UUID
**Endpoint:** `GET /api/weaviate/object/<uuid>`

**Purpose:** Retrieve a specific object from Weaviate by its UUID

**Example Request:**
```bash
curl http://localhost:8000/api/weaviate/object/550e8400-e29b-41d4-a716-446655440000 \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

**Example Response (Found):**
```json
{
  "success": true,
  "found": true,
  "object": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "properties": {
      "title": "Example Item",
      "type": "Item",
      "description": "This is an example item",
      "section": "Development",
      "owner": "john.doe",
      "status": "active",
      "createdAt": "2024-10-27T23:00:00Z",
      "tags": ["feature", "backend"],
      "url": "/items/550e8400-e29b-41d4-a716-446655440000/"
    },
    "collection": "KnowledgeObject"
  }
}
```

**Example Response (Not Found):**
```json
{
  "success": true,
  "found": false,
  "object": null
}
```

**Use Cases:**
- Verify object synchronization
- Debug missing objects
- Inspect object properties

---

### 4. Rebuild Index
**Endpoint:** `POST /api/weaviate/rebuild`

**Purpose:** Trigger index rebuild (informational for Weaviate v4)

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/weaviate/rebuild \
  -H "Cookie: sessionid=YOUR_SESSION_ID"
```

**Example Response:**
```json
{
  "success": true,
  "message": "Weaviate v4 manages indices automatically. No manual rebuild needed.",
  "info": "If you are experiencing issues, consider checking cluster health and restarting nodes if necessary."
}
```

**Note:** Weaviate v4 automatically manages indices. This endpoint provides guidance rather than performing manual operations.

---

### 5. Restore Schema
**Endpoint:** `POST /api/weaviate/schema/restore`

**Purpose:** Restore schema from backup (safety stub)

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/weaviate/schema/restore \
  -H "Cookie: sessionid=YOUR_SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "schema": {
      "collections": ["KnowledgeObject"],
      "timestamp": "2024-10-27T23:00:00Z"
    },
    "confirm": true
  }'
```

**Example Response:**
```json
{
  "success": false,
  "error": "Schema restore is not fully implemented. This requires manual intervention for safety.",
  "message": "Please contact system administrator for schema restoration."
}
```

**Note:** Schema restoration requires manual intervention for safety. Contact system administrator for assistance.

---

## Error Responses

### Unauthorized (401)
```json
{
  "success": false,
  "error": "Unauthorized"
}
```
**Solution:** Ensure you're logged in with a valid session.

### Forbidden (403)
```json
{
  "success": false,
  "error": "Admin permission required"
}
```
**Solution:** Contact administrator to request admin role.

### Internal Error (500)
```json
{
  "success": false,
  "error": "Failed to get Weaviate status",
  "details": "Connection refused..."
}
```
**Solution:** Check Weaviate service is running and accessible.

---

## Common Tasks

### Monitor System Health
1. Check status endpoint regularly
2. Monitor `total_objects` count
3. Review `objects_by_type` distribution
4. Verify version matches expected

### Backup Workflow
1. Export schema using `/api/weaviate/schema/export`
2. Save response to file with timestamp
3. Store securely with other backups

### Troubleshoot Missing Object
1. Get object UUID from Django database
2. Search using `/api/weaviate/object/<uuid>`
3. If not found, check sync service logs
4. Re-sync object if needed

### Verify Synchronization
1. Count objects in Django database
2. Check `total_objects` from status endpoint
3. Compare counts by type
4. Investigate discrepancies

---

## Security Notes

- All endpoints require authentication
- Only admin users can access
- All operations are logged
- Destructive operations require confirmation
- Schema restore is intentionally limited

---

## Integration Examples

### Python
```python
import requests

session = requests.Session()
session.post('http://localhost:8000/login/', data={
    'username': 'admin',
    'password': 'password'
})

# Check status
response = session.get('http://localhost:8000/api/weaviate/status')
data = response.json()
print(f"Total objects: {data['stats']['total_objects']}")

# Export schema
response = session.post('http://localhost:8000/api/weaviate/schema/export')
schema = response.json()['schema']

# Search object
object_uuid = '550e8400-e29b-41d4-a716-446655440000'
response = session.get(f'http://localhost:8000/api/weaviate/object/{object_uuid}')
if response.json()['found']:
    print(f"Object found: {response.json()['object']['properties']['title']}")
```

### JavaScript/Fetch
```javascript
// Check status
const response = await fetch('/api/weaviate/status', {
    credentials: 'include'
});
const data = await response.json();
console.log(`Total objects: ${data.stats.total_objects}`);

// Export schema
const exportResponse = await fetch('/api/weaviate/schema/export', {
    method: 'POST',
    credentials: 'include'
});
const schema = await exportResponse.json();
console.log('Schema exported:', schema.export_time);
```

---

## Troubleshooting

### "Connection refused" error
- Check Weaviate service is running
- Verify connection settings in Django settings
- Test direct connection to Weaviate

### "Object not found" despite existing in Django
- Check sync service logs
- Verify object was created after sync service started
- Manually re-sync the object

### High object count discrepancy
- Compare Django database counts with Weaviate
- Look for sync service errors in logs
- Consider full re-sync if significant drift

---

## Related Documentation
- See `WEAVIATE_MAINTENANCE_DASHBOARD_IMPLEMENTATION.md` for full implementation details
- See `core/services/weaviate_maintenance_service.py` for service documentation
- See `main/test_weaviate_maintenance.py` for usage examples
