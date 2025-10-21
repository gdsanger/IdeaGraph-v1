# Weaviate Cloud Configuration Implementation

## Overview
This document describes the implementation of Weaviate Cloud configuration support in IdeaGraph v1.0, allowing users to switch between local and cloud-based Weaviate instances.

## Issue Requirements
The implementation addresses the following requirements from issue #204:

1. ✅ **Settings Entity Extension**: Add `WEAVIATE_URL`, `WEAVIATE_API_KEY`, and a `Cloud` toggle (yes/no) to the Settings model
2. ✅ **Client Adaptation**: Modify the Weaviate client to use cloud credentials when Cloud=yes, or local configuration when Cloud=no
3. ✅ **Admin View Extension**: Add the configuration fields to the `/admin/settings` view

## Implementation Details

### 1. Database Model (Already Existed)
**File**: `main/models.py` (lines 454-473)
```python
# Weaviate Configuration
weaviate_cloud_enabled = models.BooleanField(
    default=False,
    verbose_name='Cloud',
    help_text='Enable Weaviate Cloud (if disabled, local configuration is used)'
)
weaviate_url = models.CharField(
    max_length=255,
    blank=True,
    default='',
    verbose_name='WEAVIATE_URL',
    help_text='Weaviate Cloud URL'
)
weaviate_api_key = models.CharField(
    max_length=255,
    blank=True,
    default='',
    verbose_name='WEAVIATE_API_KEY',
    help_text='Weaviate Cloud API Key'
)
```

**Migration**: `main/migrations/0015_add_weaviate_cloud_settings.py`

### 2. Service Layer (Already Existed)
All Weaviate sync services were already updated to support cloud configuration:

- `core/services/weaviate_sync_service.py` (Items)
- `core/services/weaviate_task_sync_service.py` (Tasks)
- `core/services/weaviate_tag_sync_service.py` (Tags)
- `core/services/weaviate_github_issue_sync_service.py` (GitHub Issues)

**Logic** (example from `weaviate_sync_service.py`):
```python
def _initialize_client(self):
    if self.settings.weaviate_cloud_enabled:
        # Use cloud configuration
        if not self.settings.weaviate_url or not self.settings.weaviate_api_key:
            raise WeaviateItemSyncServiceError(
                "Weaviate Cloud enabled but URL or API key not configured"
            )
        self._client = weaviate.connect_to_weaviate_cloud(
            cluster_url=self.settings.weaviate_url,
            auth_credentials=Auth.api_key(self.settings.weaviate_api_key)
        )
    else:
        # Use local Weaviate instance at localhost:8081
        self._client = weaviate.connect_to_local(
            host="localhost",
            port=8081
        )
```

### 3. Views (NEW - This PR)
**File**: `main/views.py`

**Changes in `settings_create`** (lines 336-338):
```python
weaviate_cloud_enabled=request.POST.get('weaviate_cloud_enabled') == 'on',
weaviate_url=request.POST.get('weaviate_url', ''),
weaviate_api_key=request.POST.get('weaviate_api_key', ''),
```

**Changes in `settings_update`** (lines 378-380):
```python
settings.weaviate_cloud_enabled = request.POST.get('weaviate_cloud_enabled') == 'on'
settings.weaviate_url = request.POST.get('weaviate_url', '')
settings.weaviate_api_key = request.POST.get('weaviate_api_key', '')
```

### 4. Template (NEW - This PR)
**File**: `main/templates/main/settings_form.html`

Added new section between KiGate Configuration and Additional Settings:

```html
<!-- Weaviate Configuration -->
<div class="mb-4">
    <h5 class="mb-3" style="color: var(--autumn-accent);">
        <i class="bi bi-cloud-fill"></i> Weaviate Configuration
    </h5>
    <div class="row">
        <div class="col-md-12 mb-3">
            <div class="form-check form-switch">
                <input 
                    class="form-check-input" 
                    type="checkbox" 
                    id="weaviate_cloud_enabled" 
                    name="weaviate_cloud_enabled"
                    {% if settings.weaviate_cloud_enabled %}checked{% endif %}>
                <label class="form-check-label" for="weaviate_cloud_enabled">
                    Cloud
                </label>
                <div class="form-text">Enable Weaviate Cloud (if disabled, local configuration is used)</div>
            </div>
        </div>
    </div>
    <div class="row">
        <div class="col-md-6 mb-3">
            <label for="weaviate_url" class="form-label">WEAVIATE_URL</label>
            <input 
                type="url" 
                class="form-control" 
                id="weaviate_url" 
                name="weaviate_url" 
                value="{{ settings.weaviate_url|default:'' }}"
                placeholder="https://your-cluster.weaviate.network">
            <div class="form-text">Weaviate Cloud URL</div>
        </div>
        <div class="col-md-6 mb-3">
            <label for="weaviate_api_key" class="form-label">WEAVIATE_API_KEY</label>
            <input 
                type="password" 
                class="form-control" 
                id="weaviate_api_key" 
                name="weaviate_api_key" 
                value="{{ settings.weaviate_api_key|default:'' }}"
                placeholder="Your Weaviate API Key">
            <div class="form-text">Weaviate Cloud API Key</div>
        </div>
    </div>
</div>
```

### 5. Tests (Already Existed)
**File**: `main/test_settings_weaviate_cloud.py`

Comprehensive test suite with 16 tests covering:
- Model CRUD operations
- Service initialization with cloud/local configuration
- Error handling for missing credentials
- View integration tests
- Toggle switching between cloud and local modes

**Test Results**: All 16 tests pass ✅

## Usage

### Configuring Weaviate Cloud

1. Navigate to `/admin/settings/` in the application
2. Click "Create" or "Update" on an existing settings entry
3. Scroll to the "Weaviate Configuration" section
4. Toggle "Cloud" to enable cloud mode
5. Enter your Weaviate Cloud URL (e.g., `https://my-cluster.weaviate.network`)
6. Enter your Weaviate API Key
7. Save the settings

### Using Local Weaviate

1. Navigate to `/admin/settings/`
2. Ensure the "Cloud" toggle is disabled (unchecked)
3. The system will automatically use `localhost:8081` for Weaviate connections
4. No URL or API Key needed for local mode

## Security Considerations

- API keys are stored as password fields (type="password") in the UI
- API keys are stored in the database (consider encryption for production)
- Local configuration credentials are not stored in the database
- The cloud toggle provides a clear switch between modes

## Backward Compatibility

- Default value for `weaviate_cloud_enabled` is `False`, maintaining local behavior
- Existing local configurations continue to work without changes
- No breaking changes to existing code

## Files Modified in This PR

1. `main/views.py` - Added Weaviate fields to create/update views
2. `main/templates/main/settings_form.html` - Added Weaviate configuration UI section

## Related Documentation

- See `WEAVIATE_CLOUD_CONFIGURATION.md` for additional context
- Migration: `main/migrations/0015_add_weaviate_cloud_settings.py`
- Tests: `main/test_settings_weaviate_cloud.py`
