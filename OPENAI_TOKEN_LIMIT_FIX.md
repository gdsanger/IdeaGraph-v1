# OpenAI Token Limit Fix for Mail Processing

## Problem
The `process_mails` command was failing when processing emails with large content that exceeded the OpenAI API's context length limit (e.g., 8192 tokens for GPT-4). This resulted in errors like:

```
OpenAI API error: Error code: 400 - {'error': {'message': "This model's maximum context length is 8192 tokens. However, your messages resulted in 10153 tokens. Please reduce the length of the messages.", 'type': 'invalid_request_error', 'param': 'messages', 'code': 'context_length_exceeded'}}
```

## Solution
Implemented token limit enforcement in the mail processing service to respect the `openai_max_tokens` setting from the IdeaGraph configuration:

### Changes Made

1. **Added Token Estimation Utilities** (`core/services/mail_processing_service.py`)
   - `estimate_token_count(text)`: Estimates token count using a 4 characters per token heuristic
   - `truncate_text_to_tokens(text, max_tokens, suffix)`: Intelligently truncates text to fit within token limit, attempting to break at sentence boundaries

2. **Updated `find_matching_item` Method**
   - Calculates available tokens based on prompt template overhead
   - Truncates mail content if it exceeds available token budget
   - Logs when truncation occurs
   - Falls back to reducing the number of similar items if needed

3. **Updated `generate_normalized_description` Method**
   - Calculates available tokens for mail body based on template overhead
   - Truncates mail body content when necessary before sending to KiGate/OpenAI
   - Preserves at least 1000 tokens for mail body to ensure meaningful content

### How It Works

#### Token Budget Calculation
For each AI API call, the service calculates:
- **Template overhead**: Tokens used by the prompt template structure
- **Context tokens**: Tokens used by item descriptions, subjects, etc.
- **Response tokens**: Reserved tokens for the AI response
- **Available tokens**: Remaining tokens for the actual mail content

Formula: `available_tokens = max_tokens - template_overhead - context_tokens - response_tokens`

#### Intelligent Truncation
When content exceeds the available tokens:
1. Converts token limit to approximate character count (4 chars per token)
2. Truncates content at that point
3. Attempts to find a sentence boundary within the last 500 characters
4. Adds a clear suffix indicating truncation (e.g., "[...E-Mail-Inhalt wurde gekürzt...]")

### Configuration
The token limit is controlled by the `openai_max_tokens` field in the Settings model:
- Default value: 10,000 tokens
- Configurable via Django admin or settings API
- Used for both direct OpenAI calls and KiGate agent calls (which may use OpenAI internally)

### Testing
Created comprehensive test suite (`main/test_mail_token_limits.py`) covering:
- Token count estimation accuracy
- Text truncation with various content sizes
- Sentence boundary detection
- Integration with `find_matching_item` method
- Integration with `generate_normalized_description` method
- Verification that normal-sized content is not truncated

All tests pass successfully.

### Backward Compatibility
- Normal-sized emails (< token limit) are processed exactly as before
- No changes to the API or command-line interface
- Existing tests continue to pass (except one pre-existing unrelated failure)

## Usage Example

### Before Fix
```bash
python manage.py process_mails --mailbox idea@angermeier.net
# Would fail with: "This model's maximum context length is 8192 tokens..."
```

### After Fix
```bash
python manage.py process_mails --mailbox idea@angermeier.net
# Processes successfully, truncating large emails as needed
# Logs show: "Mail content truncated from 10153 to 7500 tokens"
```

## Technical Details

### Token Estimation
Uses a simple but effective heuristic: `tokens ≈ characters / 4`

This works well for English and German text (the languages used in IdeaGraph). More sophisticated tokenization (e.g., using tiktoken) could be added in the future if needed.

### Truncation Strategy
1. **Prefer sentence boundaries**: Attempts to break at `. `, `.\n`, `! `, etc.
2. **Fallback to character boundary**: If no sentence boundary is found nearby
3. **Clear indication**: Adds a suffix to show content was truncated
4. **Minimum content**: Ensures at least 500-1000 tokens of actual content

### Error Handling
- If items context is too large, reduces the number of items returned
- If content still can't fit, uses the fallback strategy (best match by distance)
- All failures are logged with appropriate detail level

## Related Files
- `core/services/mail_processing_service.py` - Main service implementation
- `main/test_mail_token_limits.py` - Test suite
- `main/models.py` - Settings model with `openai_max_tokens` field
- `core/services/milestone_knowledge_service.py` - Similar pattern used as reference

## Future Enhancements
Possible improvements for the future:
1. Use tiktoken library for exact token counting
2. Implement chunking strategy (process in multiple API calls) for extremely large emails
3. Add token usage statistics/monitoring
4. Make suffix text configurable
5. Add support for different models with different token limits
