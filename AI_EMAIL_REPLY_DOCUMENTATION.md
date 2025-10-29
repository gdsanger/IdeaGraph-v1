# AI-Powered Email Reply Feature

## Overview

The AI-powered email reply feature enables semi-automated responses to incoming email comments in IdeaGraph. When an email arrives as a comment, users can generate an AI-powered draft reply that uses context from the task, item, and related content to provide informed responses.

## Features

### 1. 3-Tier Context Retrieval (RAG)

The system retrieves context from three tiers:

- **Tier A (Thread Context)**: Recent comments from the same task, with email comments weighted higher
- **Tier B (Item Context)**: Content from the related item, including description, tasks, and files
- **Tier C (Global Context)**: Similar items across the system, filtered by tags and relevance

### 2. AI Draft Generation

- Uses KiGate's `answers-draft-agent` with OpenAI GPT-4o-mini
- Generates subject and body based on incoming email and retrieved context
- Provides confidence scoring and source references
- Typical latency: < 3 seconds (warm cache < 1 second)

### 3. Security & Privacy

- **PII Masking**: Automatically masks emails, phone numbers, and sensitive data in context
- **Secret Filtering**: Removes API keys, tokens, and internal URLs from drafts
- **Domain Allowlist**: Optional email domain restrictions for sending
- **Redis Caching**: Cached context with 600-second TTL to improve performance

### 4. Email Threading

- Maintains proper email conversation threading
- Sets `In-Reply-To` and `References` headers automatically
- Creates outbound email comment records for tracking

## User Interface

### AI Reply Button

The "Mit AI beantworten" button appears **only** on inbound email comments (`email_direction = 'inbound'`). 

Location: Task detail page → Comments section → Inbound email comment actions

### AI Reply Modal

The modal displays:
1. **Metadata**: Confidence score, source count, latency
2. **Email Form**: Subject, body (editable), CC field
3. **Sources**: Expandable section showing all sources with tier markers [#A-1], [#B-2], etc.

Users can:
- Edit the generated subject and body
- Add CC recipients
- Review source references
- Send the reply or cancel

## API Endpoints

### GET /api/comments/{comment_id}/ai-reply/draft

Generates an AI draft reply for an inbound email comment.

**Authentication**: Required (JWT or session)

**Response**:
```json
{
  "success": true,
  "subject": "Re: Question about task",
  "body": "Thank you for your question...",
  "sources": [
    {
      "tier": "A",
      "marker": "#A-1",
      "type": "comment",
      "excerpt": "Previous discussion...",
      "author": "username",
      "created_at": "2025-10-29T10:00:00Z"
    }
  ],
  "confidence": "high",
  "language": "de",
  "latency_ms": 1234,
  "tier_a_count": 3,
  "tier_b_count": 2,
  "tier_c_count": 1,
  "total_sources": 6
}
```

### POST /api/comments/{comment_id}/ai-reply/send

Sends the AI-generated (and optionally edited) reply.

**Authentication**: Required (JWT or session)

**Request Body**:
```json
{
  "subject": "Re: Question about task",
  "body": "Thank you for your question...",
  "cc": "optional@example.com"
}
```

**Note**: The `cc` field is optional and can be omitted.

**Response**:
```json
{
  "success": true,
  "message": "Email sent successfully",
  "comment_id": "uuid-of-new-outbound-comment",
  "recipient": "sender@example.com"
}
```

## Service Architecture

### EmailReplyRAGService

Located: `core/services/email_reply_rag_service.py`

**Key Methods**:
- `retrieve_context(comment)`: Retrieves full 3-tier context
- `retrieve_tier_a(task, comment)`: Thread context
- `retrieve_tier_b(item, task)`: Item context
- `retrieve_tier_c(item, task)`: Global context
- `format_context_for_kigate(context)`: Formats for AI agent

**Configuration**:
```python
TIER_A_MAX_COMMENTS = 10  # Recent comments
TIER_B_TOP_N = 5          # Item-related content
TIER_C_TOP_N = 3          # Similar cases
MAX_SNIPPET_LENGTH = 500  # Characters per snippet
CACHE_TTL = 600           # Seconds
```

### AIEmailReplyService

Located: `core/services/ai_email_reply_service.py`

**Key Methods**:
- `generate_draft(comment, user)`: Generates AI draft
- `send_reply(comment, subject, body, user, cc)`: Sends email
- `_filter_secrets(text)`: Security filtering
- `_validate_email_domain(email)`: Domain validation

**Security Configuration**:
```python
DOMAIN_ALLOWLIST = []  # Empty = allow all
SECRET_PATTERNS = [...]  # Regex patterns for filtering
```

## Configuration Requirements

### Settings Model

Required fields in `Settings` model:
- `kigate_api_enabled = True`
- `kigate_api_base_url`: KiGate server URL
- `kigate_api_token`: Authentication token

### KiGate Agent

The feature requires the `answers-draft-agent` to be configured in KiGate with:
- Provider: `openai`
- Model: `gpt-4o-mini`
- Role: Email response generation specialist

### Email Adapter

Requires configured email sending via:
- Microsoft Graph API (primary)
- SMTP (fallback)
- Zammad integration (optional)

## Logging & Observability

All operations are logged with structured data:

```python
logger.info(
    f"Draft generated successfully | "
    f"comment_id={comment_id} | "
    f"task_id={task_id} | "
    f"item_id={item_id} | "
    f"latency_ms={latency} | "
    f"sources_n={source_count} | "
    f"confidence={confidence}"
)
```

Key metrics tracked:
- Latency (ms)
- Source counts (per tier)
- Confidence scores
- Send success/failure
- Cache hits

## Testing

Test suite location: `main/test_ai_email_reply.py`

**Test Coverage**:
- RAG service (7 tests):
  - Tier A/B/C retrieval
  - PII masking
  - Snippet truncation
  - Context formatting
  - Full retrieval pipeline

- AI service (3 tests):
  - Domain validation
  - Secret filtering
  - Draft generation (mocked)

- API endpoints (8 tests):
  - Authentication
  - Draft generation
  - Email sending
  - Error handling

Run tests:
```bash
python manage.py test main.test_ai_email_reply
```

## Performance Considerations

### Caching Strategy

- Redis cache with 600-second TTL
- Cache key: `rag:email_reply:{hash(comment_id:item_id)}`
- Warm cache: < 1 second response time
- Cold cache: < 3 seconds response time

### Optimization Tips

1. **Adjust tier limits** based on typical conversation size
2. **Tune snippet length** to balance context vs. token usage
3. **Monitor cache hit rate** and adjust TTL if needed
4. **Use semantic search** for Tier C (Weaviate integration available)

## Limitations & Future Enhancements

### Current Limitations

1. Tier C uses tag-based similarity (not semantic)
2. No multi-language detection (assumes German)
3. Single reply per action (no follow-up suggestions)
4. No attachment support in drafts

### Planned Enhancements

1. Weaviate semantic search for Tier C
2. Automatic language detection
3. Conversation history analysis
4. Sentiment analysis
5. Automated follow-up reminders
6. A/B testing for draft quality

## Troubleshooting

### Draft Generation Fails

**Symptom**: Error in modal, "Fehler beim Laden des Entwurfs"

**Possible Causes**:
1. KiGate API not enabled (`kigate_api_enabled = False`)
2. Invalid KiGate credentials
3. `answers-draft-agent` not configured
4. Network connectivity to KiGate server

**Resolution**:
- Check Settings → KiGate API configuration
- Verify KiGate server is accessible
- Check logs for detailed error messages

### Email Not Sending

**Symptom**: Draft generates but send fails

**Possible Causes**:
1. Email adapter not configured (Graph API/SMTP)
2. Domain not in allowlist (if configured)
3. Invalid recipient email
4. Missing Microsoft Graph permissions

**Resolution**:
- Check Settings → Email configuration
- Verify Graph API credentials
- Review domain allowlist configuration
- Check logs for SMTP/Graph errors

### Poor Context Quality

**Symptom**: Irrelevant or incomplete AI responses

**Possible Causes**:
1. Insufficient thread history
2. Missing item description
3. No similar cases in Tier C

**Resolution**:
- Increase `TIER_A_MAX_COMMENTS` value
- Ensure items have descriptive content
- Add more tags to improve Tier C matching
- Consider enabling Weaviate semantic search

## Security Considerations

### Data Privacy

- PII is masked before sending to AI
- Context is cached with short TTL (600 seconds)
- No persistent storage of AI interactions
- Email content follows existing access controls

### Access Control

- Only authenticated users can generate drafts
- Comments inherit task/item permissions
- Email sending requires valid sender permissions
- Domain allowlist prevents unauthorized recipients

### Audit Trail

- All draft generations logged with user ID
- Email sends create comment records
- Full threading maintains conversation history
- Structured logs enable security audits

## Integration Points

### With Existing Features

1. **Email Conversation Service**: Uses existing threading logic
2. **Mail Utils**: Leverages `send_task_email` function
3. **Task Comments**: Creates outbound comment records
4. **Weaviate**: Optional semantic search for Tier C

### External Services

1. **KiGate**: AI agent execution platform
2. **Microsoft Graph**: Email sending (primary)
3. **Redis**: Context caching
4. **OpenAI**: LLM via KiGate

## Example Workflow

1. **Email arrives** → Creates `TaskComment` with `source='email'`, `email_direction='inbound'`
2. **User opens task** → Sees email comment with AI reply button
3. **User clicks "Mit AI beantworten"** → Modal opens, loading spinner shows
4. **System retrieves context**:
   - Last 10 comments from task (Tier A)
   - Item description and related tasks (Tier B)
   - Similar items by tags (Tier C)
5. **System calls KiGate** → `answers-draft-agent` generates reply
6. **Modal shows draft** → User reviews/edits subject, body, sources
7. **User clicks "Senden"** → Email sent via Graph API
8. **System creates outbound comment** → Thread maintained with proper headers
9. **Modal closes** → Comments list refreshes automatically

## Code Examples

### Using RAG Service

```python
from core.services.email_reply_rag_service import EmailReplyRAGService

# Get comment
comment = TaskComment.objects.get(id=comment_id)

# Initialize service
rag_service = EmailReplyRAGService()

# Retrieve context
context = rag_service.retrieve_context(comment)

# Format for AI
formatted = rag_service.format_context_for_kigate(context)
```

### Using AI Reply Service

```python
from core.services.ai_email_reply_service import AIEmailReplyService

# Initialize service
ai_service = AIEmailReplyService()

# Generate draft
result = ai_service.generate_draft(comment, user)

if result['success']:
    # Edit if needed
    subject = result['subject']
    body = result['body']
    
    # Send reply
    send_result = ai_service.send_reply(
        comment=comment,
        subject=subject,
        body=body,
        user=user
    )
```

## Configuration Example

```python
# In Settings admin or environment
{
    "kigate_api_enabled": true,
    "kigate_api_base_url": "https://kigate.example.com",
    "kigate_api_token": "your_token_here",
    "client_id": "your_ms_client_id",
    "client_secret": "your_ms_secret",
    "tenant_id": "your_ms_tenant"
}
```

## Support

For issues or questions:
1. Check logs in `logs/ideagraph.log`
2. Review structured log entries with relevant IDs
3. Verify KiGate and email service connectivity
4. Ensure all required settings are configured
