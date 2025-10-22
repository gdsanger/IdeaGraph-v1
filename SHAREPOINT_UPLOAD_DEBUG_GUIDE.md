# SharePoint Upload Debug Guide

## Overview

This guide explains how to use the enhanced debug logging to troubleshoot SharePoint file upload issues in IdeaGraph.

## Recent Changes

Comprehensive debug logging has been added to help diagnose SharePoint file upload problems. The logging now provides detailed information at every step of the upload process.

## What Information is Now Logged

### 1. Configuration Information (DEBUG level)
- SharePoint site ID
- Graph API base URL
- Tenant ID
- Folder paths
- Item details (ID, title)
- Normalized folder names

### 2. Authentication Details (INFO/DEBUG level)
- Token acquisition attempts
- Token endpoint URLs
- Authentication scopes
- Token expiration times
- Client ID (in case of errors)

### 3. Upload Process Details (INFO/DEBUG level)
- File name and size
- Complete API endpoint URLs
- HTTP request details
- Upload response status codes
- Successful upload metadata

### 4. Error Details (ERROR level)
- HTTP status codes
- Full error response bodies
- Request URLs that failed
- All relevant configuration values
- Context about the file and item

## How to Enable Debug Logging

To see the detailed debug output, ensure your Django logging configuration includes DEBUG level for the relevant loggers:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} [{levelname}] [{name}] - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'graph_service': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',  # Set to DEBUG to see all details
            'propagate': False,
        },
        'item_file_service': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',  # Set to DEBUG to see all details
            'propagate': False,
        },
    },
}
```

## Common Issues and How to Diagnose Them

### Issue 1: Invalid SharePoint Site ID

**Symptoms:**
```
[ERROR] Failed to upload file (HTTP 404)
[ERROR] Response body: {"error": {"code": "itemNotFound", "message": "The resource could not be found."}}
[ERROR] SharePoint site ID: invalid-site-id
```

**Solution:**
- Check the `sharepoint_site_id` in your Settings
- Verify the site ID is correct in SharePoint
- Ensure you have access to the site

### Issue 2: Authentication Problems

**Symptoms:**
```
[ERROR] Token request failed: 401 - Invalid credentials
[ERROR] Token URL: https://login.microsoftonline.com/tenant-xyz/oauth2/v2.0/token
[ERROR] Client ID: client-abc-123
```

**Solution:**
- Verify `tenant_id`, `client_id`, and `client_secret` in Settings
- Check that the client credentials are still valid
- Ensure the app registration has the required permissions

### Issue 3: Incorrect Folder Path

**Symptoms:**
```
[ERROR] Failed to upload file (HTTP 400 or 404)
[ERROR] Folder path: IdeaGraph/Invalid:Folder*Name
```

**Solution:**
- Check for special characters in the item title
- Review the normalized folder name in DEBUG logs
- Ensure the folder path follows SharePoint naming conventions

### Issue 4: Configuration Issues

**Symptoms:**
```
[ERROR] Graph API configuration incomplete
[ERROR] tenant_id present: True
[ERROR] client_id present: False
[ERROR] client_secret present: True
```

**Solution:**
- Check which configuration values are missing
- Verify all required fields in Settings model
- Ensure Graph API is enabled in settings

### Issue 5: Network or Timeout Issues

**Symptoms:**
```
[ERROR] Request error: Connection timeout
[ERROR] Request URL: https://graph.microsoft.com/v1.0/...
[ERROR] Request method: PUT
```

**Solution:**
- Check network connectivity to Microsoft Graph API
- Verify firewall rules allow outbound HTTPS
- Check if proxy settings are required

## Example Debug Session

Here's what a complete debug log looks like for a successful upload:

```
2025-10-22 09:35:59 [INFO] [item_file_service] - Uploading file ideagraph_Ideagraph.txt (88 bytes) to IdeaGraph/IdeaGraph v1.0 (Item-Management)
2025-10-22 09:35:59 [DEBUG] [item_file_service] - Item ID: abc-123, Item title: IdeaGraph v1.0 (Item-Management)
2025-10-22 09:35:59 [DEBUG] [item_file_service] - Normalized folder name: IdeaGraph_v1.0_Item-Management
2025-10-22 09:35:59 [DEBUG] [item_file_service] - Content type: text/plain
2025-10-22 09:35:59 [DEBUG] [item_file_service] - Graph service initialized with base URL: https://graph.microsoft.com/v1.0
2025-10-22 09:35:59 [DEBUG] [item_file_service] - SharePoint site ID: site-xyz-789
2025-10-22 09:35:59 [INFO] [graph_service] - Uploading file: ideagraph_Ideagraph.txt (88 bytes)
2025-10-22 09:35:59 [DEBUG] [graph_service] - SharePoint site ID: site-xyz-789
2025-10-22 09:35:59 [DEBUG] [graph_service] - Folder path: IdeaGraph/IdeaGraph_v1.0_Item-Management
2025-10-22 09:35:59 [DEBUG] [graph_service] - Base URL: https://graph.microsoft.com/v1.0
2025-10-22 09:35:59 [DEBUG] [graph_service] - Upload endpoint: sites/site-xyz-789/drive/root:/IdeaGraph/IdeaGraph_v1.0_Item-Management/ideagraph_Ideagraph.txt:/content
2025-10-22 09:35:59 [INFO] [graph_service] - Requesting new access token from Microsoft (tenant_id: tenant-abc-123)
2025-10-22 09:35:59 [DEBUG] [graph_service] - Token endpoint: https://login.microsoftonline.com/tenant-abc-123/oauth2/v2.0/token
2025-10-22 09:35:59 [DEBUG] [graph_service] - Scopes: https://graph.microsoft.com/.default
2025-10-22 09:35:59 [INFO] [graph_service] - Successfully acquired access token (expires in 3600s)
2025-10-22 09:35:59 [INFO] [graph_service] - Uploading file: ideagraph_Ideagraph.txt (88 bytes)
2025-10-22 09:35:59 [DEBUG] [graph_service] - Full upload URL: https://graph.microsoft.com/v1.0/sites/site-xyz-789/drive/root:/IdeaGraph/IdeaGraph_v1.0_Item-Management/ideagraph_Ideagraph.txt:/content
2025-10-22 09:35:59 [INFO] [graph_service] - Upload response status: 201
2025-10-22 09:35:59 [INFO] [graph_service] - File uploaded successfully: ideagraph_Ideagraph.txt
2025-10-22 09:35:59 [DEBUG] [graph_service] - Response metadata: file_id=file-123-abc, size=88
```

## Comparing Working vs. Non-Working Installations

When you have one working installation and one that fails, compare these key values in the debug logs:

1. **SharePoint Site ID**: Must be exactly correct
2. **Tenant ID**: Should match your Azure AD tenant
3. **Base URL**: Usually `https://graph.microsoft.com/v1.0`
4. **Folder Path**: Check for differences in normalization
5. **Token Acquisition**: Verify both can get tokens successfully
6. **Error Response Bodies**: These provide the most specific error information

## Reporting Issues

When reporting SharePoint upload issues, please include:

1. Complete error logs with DEBUG level enabled
2. The relevant section from the logs showing:
   - Configuration values (SharePoint site ID, base URL)
   - Token acquisition attempts
   - Full error response body
3. Whether the same credentials work in another installation
4. The item title and normalized folder name

## Additional Resources

- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
- [SharePoint REST API Reference](https://docs.microsoft.com/en-us/sharepoint/dev/sp-add-ins/working-with-folders-and-files-with-rest)
- [Azure AD Authentication](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
