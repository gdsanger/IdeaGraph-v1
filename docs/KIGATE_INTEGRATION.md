# KiGate API Integration

This document describes the integration of KiGate API in IdeaGraph for agent-based AI workflows.

## Overview

The KiGate integration enables IdeaGraph to communicate with AI agents through a unified API. This allows tasks to be automatically processed by appropriate AI agents with specific capabilities.

## Configuration

### Settings Model

The KiGate API is configured through the Settings model with the following fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `kigate_api_enabled` | Boolean | `false` | Enable/disable KiGate API integration |
| `kigate_api_base_url` | String | `http://localhost:8000` | KiGate API base URL |
| `kigate_api_token` | String | `''` | API token (format: `client_id:client_secret`) |
| `kigate_api_timeout` | Integer | `30` | Request timeout in seconds |

### Enabling KiGate API

1. Access the Django Admin or Settings UI
2. Navigate to Settings
3. Set the following values:
   - Enable KiGate API: `true`
   - Base URL: Your KiGate API URL (e.g., `https://kigate.isarlabs.de`)
   - API Token: Your authentication token
   - Timeout: Request timeout (default: 30 seconds)

## Core Service

### KiGateService

The `KiGateService` class provides methods for interacting with the KiGate API:

```python
from core.services.kigate_service import KiGateService

kigate = KiGateService()
```

### Methods

#### get_agents()

Lists all available agents from the KiGate API.

```python
agents = kigate.get_agents()
# Returns: {'success': True, 'agents': [...]}
```

#### execute_agent()

Executes a specific agent with given parameters.

```python
result = kigate.execute_agent(
    agent_name="translation-agent",
    provider="openai",
    model="gpt-4",
    message="Translate this text to German",
    user_id="user@example.com",
    parameters={"language": "German"}  # Optional
)
# Returns: {
#     'success': True,
#     'job_id': 'job-123-abc',
#     'status': 'completed',
#     'result': '...'
# }
```

**Required Parameters:**
- `agent_name`: Name of the agent to execute
- `provider`: AI provider (e.g., "openai", "claude", "gemini")
- `model`: AI model (e.g., "gpt-4", "claude-3-sonnet")
- `message`: User message/prompt for the agent
- `user_id`: User identifier

**Optional Parameters:**
- `parameters`: Dictionary of additional agent-specific parameters

#### get_agent_details()

Retrieves detailed configuration of a specific agent.

```python
details = kigate.get_agent_details("translation-agent")
# Returns: {
#     'success': True,
#     'agent': {
#         'name': 'translation-agent',
#         'description': '...',
#         'provider': 'openai',
#         'model': 'gpt-4',
#         ...
#     }
# }
```

## REST API Endpoints

All endpoints require authentication via JWT token in the Authorization header.

### List Agents

```
GET /api/kigate/agents
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
    "success": true,
    "agents": [
        {
            "name": "translation-agent",
            "description": "Translates text",
            "provider": "openai",
            "model": "gpt-4"
        }
    ]
}
```

### Execute Agent

```
POST /api/kigate/execute
Authorization: Bearer <jwt-token>
Content-Type: application/json

{
    "agent_name": "translation-agent",
    "provider": "openai",
    "model": "gpt-4",
    "message": "Hello world",
    "user_id": "user@example.com",
    "parameters": {
        "language": "German"
    }
}
```

**Response:**
```json
{
    "success": true,
    "job_id": "job-123-abc",
    "agent": "translation-agent",
    "provider": "openai",
    "model": "gpt-4",
    "status": "completed",
    "result": "Hallo Welt"
}
```

### Get Agent Details

```
GET /api/kigate/agent/{agent_name}
Authorization: Bearer <jwt-token>
```

**Response:**
```json
{
    "success": true,
    "agent": {
        "name": "translation-agent",
        "description": "An agent that translates text",
        "role": "You are a translation agent",
        "provider": "openai",
        "model": "gpt-4",
        "parameters": ["language"]
    }
}
```

## Error Handling

The service uses structured error handling through `KiGateServiceError`:

```python
try:
    result = kigate.execute_agent(...)
except KiGateServiceError as e:
    print(f"Error: {e.message}")
    print(f"Status Code: {e.status_code}")
    print(f"Details: {e.details}")
    
    # Get structured error dict
    error_dict = e.to_dict()
    # Returns: {'success': False, 'error': '...', 'details': '...'}
```

### Common Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing token |
| 404 | Not Found - Agent does not exist |
| 408 | Timeout - Request exceeded timeout limit |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Cannot connect to KiGate |

## Logging

All KiGate API interactions are logged to the `kigate_service` logger:

```python
import logging
logger = logging.getLogger('kigate_service')
```

Logs include:
- Request information (method, URL, parameters)
- Response status codes
- Error details
- Agent execution results

## Testing

The integration includes comprehensive unit tests:

```bash
# Run KiGate service tests
python manage.py test main.test_kigate_service

# Run all tests
python manage.py test
```

Test coverage includes:
- Service initialization and configuration
- Agent listing
- Agent execution (with and without parameters)
- Error handling (timeout, connection errors, API errors)
- API endpoint authentication and authorization
- Missing required fields validation

## Example Usage

See `examples/kigate_usage.py` for detailed examples of:
- Listing available agents
- Executing agents
- Using custom parameters
- Error handling
- Working with agent details

## Integration with IdeaGraph Workflows

The KiGate integration enables the following workflows:

1. **Task → KI-Agent**: When a task is created, IdeaGraph can automatically identify and execute the appropriate agent
2. **KI-Agent → Result**: Agent results are processed and stored in tasks
3. **Result → GitHub**: Validated results can be forwarded to GitHub integration for issue creation

## Security Considerations

- API token is stored securely in the database
- All endpoints require authentication
- Token is transmitted via Bearer authentication header
- Sensitive information is logged carefully
- Input validation on all parameters

## Troubleshooting

### KiGate API is disabled

**Error:** `KiGate API is not enabled in settings`

**Solution:** Enable the API in Settings with `kigate_api_enabled = true`

### Missing API token

**Error:** `KiGate API configuration incomplete`

**Solution:** Set the `kigate_api_token` in Settings

### Connection refused

**Error:** `Failed to connect to KiGate API`

**Solution:** 
- Check that the KiGate API URL is correct
- Ensure KiGate service is running
- Verify network connectivity

### Request timeout

**Error:** `Request to KiGate API timed out after X seconds`

**Solution:**
- Increase `kigate_api_timeout` in Settings
- Check KiGate service performance
- Verify network latency

## Documentation References

For more information about KiGate agents and API:
- [KiGate Documentation](../docs/KIGate_Documentation.md)
- [Quick Start Agents](../docs/QUICK_START_AGENTS.md)
- [Agents README](../docs/README_AGENTS.md)

## Support

For questions or issues:
- Author: Christian Angermeier
- Email: ca@angermeier.net
- Date: 2025-10-17
