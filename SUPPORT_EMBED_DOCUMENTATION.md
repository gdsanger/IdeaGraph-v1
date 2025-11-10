# Support Embed Feature - Documentation

## Overview

The Support Embed feature allows you to integrate an embeddable support chat and form into any web application via `<iframe>`. This enables users to:

- **Chat**: Ask questions and get AI-powered answers using the same Q&A pipeline as the internal system
- **Submit Support Requests**: Submit support tickets with automatic duplicate detection and auto-answer suggestions

## Features

### Core Capabilities

1. **Embeddable Widget**: Integrate via simple `<iframe>` tag
2. **Dual Interface**: 
   - Chat tab for real-time Q&A
   - Form tab for structured support requests
3. **Smart Precheck**:
   - Automatic answer generation before submission
   - Duplicate detection across existing tasks
   - User confirmation flow ("Does this help? Yes/No")
4. **Security**:
   - JWT or HMAC authentication
   - Referrer allowlist
   - Rate limiting per domain+item
5. **Theme Support**: Automatic dark/light mode based on system preferences
6. **Telemetry**: Built-in tracking of usage metrics

## Quick Start

### 1. Generate Authentication Token

You need to generate a JWT token for the item you want to provide support for:

```python
from core.services.support_auth_service import SupportAuthService

auth_service = SupportAuthService()
item_id = "12345678-1234-1234-1234-123456789012"  # Your item UUID

# Generate token (valid for 30 minutes)
token = auth_service.generate_jwt(item_id)
print(f"Token: {token}")
```

### 2. Embed the Widget

Add this HTML to your web page:

```html
<iframe 
    src="https://your-ideagraph-instance.com/embed/support?itemId=12345678-1234-1234-1234-123456789012&t=YOUR_JWT_TOKEN"
    width="420"
    height="650"
    frameborder="0"
    style="border: 1px solid #ddd; border-radius: 8px;"
></iframe>
```

### 3. Optional Parameters

You can customize the embed with URL parameters:

```
?itemId=<uuid>          # Required: Item UUID
&t=<token>              # Required: JWT token
&locale=de|en           # Optional: Language (default: de)
&theme=auto|light|dark  # Optional: Theme (default: auto)
```

## Authentication

### Option A: JWT (Recommended)

JWT tokens are short-lived and secure. They contain the item_id and expire after 30 minutes.

**Generate Token:**
```python
from core.services.support_auth_service import SupportAuthService

auth_service = SupportAuthService()
token = auth_service.generate_jwt(
    item_id="your-item-uuid",
    expires_in=1800  # 30 minutes
)
```

**Use Token:**
```html
<iframe src="https://your-instance.com/embed/support?itemId=<uuid>&t=<token>"></iframe>
```

### Option B: HMAC Signature

For scenarios where you can't generate JWT tokens, use HMAC signatures:

**Generate Signature:**
```python
from core.services.support_auth_service import SupportAuthService

auth_service = SupportAuthService()
secret = "your-shared-secret"  # Must be same as SUPPORT_EMBED_SECRET

hmac_data = auth_service.generate_hmac(
    item_id="your-item-uuid",
    secret=secret
)

# Use: sig=<signature>&ts=<timestamp>
print(f"sig={hmac_data['signature']}&ts={hmac_data['timestamp']}")
```

**Use Signature:**
```html
<iframe src="https://your-instance.com/embed/support?itemId=<uuid>&sig=<signature>&ts=<timestamp>"></iframe>
```

## API Endpoints

The embed widget uses three API endpoints:

### 1. Chat Send

**Endpoint:** `POST /api/support/chat/send/<item_id>`

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request:**
```json
{
  "message": "How do I configure X?",
  "conversation_history": [
    {"role": "user", "content": "Previous message"},
    {"role": "assistant", "content": "Previous answer"}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "answer": "To configure X, you need to...",
  "sources": [
    {
      "type": "KnowledgeObject",
      "title": "Configuration Guide",
      "relevance": 0.92
    }
  ],
  "meta": {
    "relevance_score": 0.85,
    "qa_id": "uuid"
  }
}
```

### 2. Precheck

**Endpoint:** `POST /api/support/precheck/<item_id>`

**Request:**
```json
{
  "type": "support",
  "title": "Login not working",
  "description": "I can't login to the system"
}
```

**Response:**
```json
{
  "success": true,
  "autoAnswer": {
    "summary": "To fix login issues, try clearing your browser cache...",
    "confidence": 0.78,
    "sources": [...]
  },
  "duplicates": [
    {
      "task_id": "uuid",
      "title": "Login Problems",
      "similarity": 0.92,
      "status": "new"
    }
  ],
  "recommendation": "ask_user"
}
```

**Recommendations:**
- `resolve`: High confidence answer or high similarity duplicate → suggest user accepts answer
- `ask_user`: Medium confidence → show answer and ask user
- `submit`: Low confidence → proceed with submission

### 3. Submit

**Endpoint:** `POST /api/support/submit/<item_id>`

**Request:**
```json
{
  "type": "support",
  "title": "Login not working",
  "description": "I can't login to the system after password reset",
  "reporter": {
    "email": "user@example.com"
  },
  "autoAnswer": {
    "offered": true,
    "accepted": false,
    "summary": "Auto-generated answer text"
  },
  "duplicateOfTaskId": "uuid-of-similar-task",
  "chatHistory": [
    {"role": "user", "content": "Previous chat message"}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "taskId": "new-task-uuid",
  "url": "/items/<item_id>/tasks/"
}
```

## Rate Limiting

Rate limits are applied per `referrer + itemId`:

- **Default Limit**: 60 requests per 10 minutes
- **Applies to**: All support API endpoints
- **Response on Limit**: HTTP 429 with `retry_after` seconds

**Rate Limit Headers** (in response):
```json
{
  "limit": 60,
  "remaining": 45,
  "reset_in": 582
}
```

## Configuration

### Django Settings

Add to your `settings.py` or `.env`:

```python
# Support Embed Configuration
SUPPORT_EMBED_ALLOWLIST = "example.com,app.example.com,staging.example.com"
SUPPORT_EMBED_SECRET = "your-secret-key-for-hmac"
```

### Referrer Allowlist

To restrict which domains can embed your widget, configure the allowlist:

```python
# In settings.py
SUPPORT_EMBED_ALLOWLIST = os.getenv('SUPPORT_EMBED_ALLOWLIST', '').split(',')
```

**Format**: Comma-separated list of allowed domains (without protocol)

**Example**: `example.com,app.example.com,*.example.com`

## Telemetry & Metrics

The system tracks the following metrics:

| Metric | Description |
|--------|-------------|
| `support_chat_send_total` | Total chat messages sent |
| `support_chat_send_success` | Successful chat responses |
| `support_chat_send_error` | Failed chat responses |
| `support_precheck_total` | Total precheck requests |
| `support_precheck_resolved_total` | Issues resolved by precheck (user accepted auto-answer) |
| `support_submit_total` | Total support submissions |
| `support_submit_success` | Successful submissions |
| `support_submit_despite_duplicate_total` | Submissions despite duplicate warning |
| `support_auth_failure_total` | Authentication failures |
| `support_rate_limit_exceeded_total` | Rate limit violations |

Metrics are logged every 10 events and can be exported to Prometheus/StatsD.

## Task Data Model

Support tasks are created with extended metadata:

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Always "support" for embed submissions |
| `reporter_email` | string | Email provided by user (optional) |
| `reporter_referrer` | string | Referrer URL from HTTP header |
| `auto_answer_offered` | boolean | Whether auto-answer was shown |
| `auto_answer_accepted` | boolean | Whether user accepted auto-answer |
| `auto_answer_text` | text | Text of the auto-answer |
| `duplicate_of_task_id` | UUID | Reference to potential duplicate task |
| `client_fingerprint` | string | Hash of referrer+UA for rate limiting |

**Enriched Description**:

Tasks created via the embed form have enriched markdown descriptions:

```markdown
## Beschreibung

User's original description text

## Chat-Verlauf

**User:** Previous chat message 1
**Assistant:** Previous chat answer 1
**User:** Previous chat message 2

## Automatische Antwort

**Status:** ✗ Abgelehnt

Auto-generated answer text that was offered

## Ähnliche Tasks

Möglicherweise Duplikat von: `/tasks/<uuid>/`

---
*Erstellt via Support-Formular*
```

## Integration Examples

### Example 1: Simple Embed

```html
<!DOCTYPE html>
<html>
<head>
    <title>Help Center</title>
</head>
<body>
    <h1>Need Help?</h1>
    <iframe 
        src="https://idea.example.com/embed/support?itemId=12345678-1234-1234-1234-123456789012&t=eyJ0eXAiOiJKV1QiLCJhbGc..."
        width="420"
        height="650"
        frameborder="0"
    ></iframe>
</body>
</html>
```

### Example 2: Dynamic Token Generation

```python
# Django view
from django.shortcuts import render
from core.services.support_auth_service import SupportAuthService

def help_page(request, item_id):
    auth_service = SupportAuthService()
    token = auth_service.generate_jwt(str(item_id))
    
    return render(request, 'help.html', {
        'item_id': item_id,
        'embed_token': token
    })
```

```html
<!-- help.html -->
<iframe 
    src="{% url 'main:embed_support' %}?itemId={{ item_id }}&t={{ embed_token }}"
    width="420"
    height="650"
    frameborder="0"
></iframe>
```

### Example 3: With Custom Styling

```html
<div style="max-width: 420px; margin: 0 auto; padding: 20px;">
    <h2>Get Support</h2>
    <p>Ask questions or submit a support request below.</p>
    <iframe 
        src="https://idea.example.com/embed/support?itemId=<uuid>&t=<token>&theme=light"
        width="100%"
        height="650"
        frameborder="0"
        style="border: 2px solid #e59a28; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"
    ></iframe>
</div>
```

## Security Best Practices

1. **Token Expiry**: Use short-lived JWT tokens (30 minutes recommended)
2. **HTTPS Only**: Always serve the embed over HTTPS
3. **Referrer Validation**: Configure allowlist to prevent unauthorized usage
4. **Rate Limiting**: Monitor and adjust limits based on usage patterns
5. **PII Handling**: Consider implementing PII sanitization in form submissions
6. **Secret Rotation**: Regularly rotate HMAC secrets

## Troubleshooting

### Issue: 401 Unauthorized

**Causes:**
- Expired JWT token
- Invalid HMAC signature
- Missing authentication parameters

**Solution:**
- Regenerate JWT token
- Verify HMAC secret matches between client and server
- Check URL includes `t=<token>` or `sig=<sig>&ts=<ts>` parameters

### Issue: 403 Forbidden

**Causes:**
- Referrer not in allowlist
- Token item_id mismatch

**Solution:**
- Add domain to `SUPPORT_EMBED_ALLOWLIST`
- Verify token was generated for correct item_id

### Issue: 429 Rate Limit Exceeded

**Causes:**
- Too many requests from same domain+item combination

**Solution:**
- Wait for rate limit to reset (check `reset_in` seconds)
- Increase rate limits in `SupportRateLimiter` if needed
- Implement client-side request throttling

### Issue: Chat Not Working

**Causes:**
- Weaviate not configured
- Item has no knowledge objects
- Q&A service error

**Solution:**
- Verify Weaviate connection in settings
- Ensure item has synced knowledge objects
- Check server logs for Q&A service errors

## Testing

Run the comprehensive test suite:

```bash
python manage.py test main.test_support_embed
```

**Test Coverage:**
- JWT and HMAC authentication
- Rate limiting
- Task submission with metadata
- Precheck with auto-answer and duplicates
- API endpoint security
- Embed view rendering

## Monitoring

**Key Metrics to Monitor:**

1. **Conversion Rate**: `(support_precheck_resolved_total / support_precheck_total) * 100`
2. **Submission Rate**: `(support_submit_success / support_submit_total) * 100`
3. **Duplicate Prevention**: `(support_submit_despite_duplicate_total / support_submit_success) * 100`
4. **Error Rate**: `(support_chat_send_error / support_chat_send_total) * 100`

**Logging:**

All support embed activity is logged to `ideagraph.log` with the following loggers:
- `support_api_views`
- `support_auth_service`
- `support_rate_limiter`
- `support_precheck_service`
- `support_submit_service`
- `support_duplicate_finder_service`

## Roadmap / Future Enhancements

**Not in MVP but could be added:**

1. **Attachments**: Allow file uploads in support form
2. **Web Component**: Standalone widget without iframe
3. **Admin UI**: Configure allowlist and settings via UI
4. **i18n**: Full internationalization support
5. **SLA Integration**: Automatic priority/routing based on issue type
6. **Real-time Updates**: WebSocket support for live chat
7. **Analytics Dashboard**: Visual metrics and reporting
8. **Custom Branding**: Configurable colors and logos
9. **Canned Responses**: Predefined response templates
10. **Feedback Loop**: User satisfaction ratings

## Support

For issues or questions about the Support Embed feature:

1. Check the logs: `logs/ideagraph.log`
2. Run tests: `python manage.py test main.test_support_embed`
3. Review telemetry metrics
4. Contact the platform team

---

**Version**: 1.0 (MVP)  
**Last Updated**: 2025-11-10  
**Maintainer**: Platform Team (IdeaGraph)
