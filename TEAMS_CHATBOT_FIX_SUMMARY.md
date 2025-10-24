# Teams Chatbot Fix Summary

## Problem Statement (Issue #)

**German Issue Title:** Teams Chatbot Fehler über Fehler

The Teams chatbot was experiencing critical issues:
1. Fetching messages it had already processed (duplicates)
2. Fetching and responding to its own messages (infinite loops)
3. Processing old messages repeatedly
4. System clogging due to endless loops

## Required Fixes

1. ✅ **Don't fetch bot's own messages** - Check sender against default_mail_sender in GraphAPI Configuration
2. ✅ **Store message identifiers** - Use Task.message_id field to track processed messages
3. ✅ **Only fetch recent messages** - Limit to messages from the last 30 minutes
4. ✅ **Prevent self-replies** - Ensure bot doesn't respond to itself

## Implementation Details

### 1. Time-Based Message Filtering (30 Minutes)

**File:** `core/services/graph_service.py`

**Changes:**
- Modified `get_channel_messages()` method to filter messages by creation time
- Only includes messages created within the last 30 minutes
- Uses `createdDateTime` field from Microsoft Graph API
- Defensive handling of missing or malformed timestamps

**Code:**
```python
# Filter messages to only include those from the last 30 minutes
cutoff_time = datetime.utcnow() - timedelta(minutes=30)
messages = []

for message in all_messages:
    created_at_str = message.get('createdDateTime')
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            created_at_naive = created_at.replace(tzinfo=None)
            
            if created_at_naive >= cutoff_time:
                messages.append(message)
```

### 2. Enhanced Sender Filtering

**File:** `core/services/teams_listener_service.py`

**Changes:**
- Reordered checks to verify message ID and sender first
- Improved logging with "SKIPPED:" prefix for better visibility
- Case-insensitive UPN comparison
- Checks both UPN and display name for backwards compatibility

**Code:**
```python
# Check message ID first
message_id = message.get('id')
if not message_id:
    logger.warning(f"Message has no ID, skipping")
    continue

# CRITICAL: Skip messages from IdeaGraph Bot
sender_upn = message.get('from', {}).get('user', {}).get('userPrincipalName', '')

if self.bot_upn and sender_upn:
    if sender_upn.lower() == self.bot_upn.lower():
        logger.info(f"SKIPPED: Message {message_id} from bot itself (UPN: {sender_upn})")
        continue
```

### 3. Defensive Self-Reply Prevention

**File:** `core/services/message_processing_service.py`

**Changes:**
- Added defensive check at the start of `analyze_message()` method
- Prevents bot from analyzing its own messages even if they slip through earlier filters
- Logs critical error if this happens

**Code:**
```python
# CRITICAL: Double-check we're not analyzing our own messages
bot_upn = self.settings.default_mail_sender
if bot_upn and sender_upn.lower() == bot_upn.lower():
    logger.error(f"CRITICAL: Attempted to analyze message from bot itself! Message ID: {message.get('id')}, Sender: {sender_upn}")
    return {
        'success': False,
        'error': 'Cannot analyze message from bot itself (infinite loop prevention)'
    }
```

### 4. Database Index for Performance

**File:** `main/models.py`

**Changes:**
- Added database index on `Task.message_id` field
- Improves query performance for duplicate checking
- Generated migration: `0041_add_task_message_id_index.py`

**Code:**
```python
class Task(models.Model):
    # ... fields ...
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        indexes = [
            models.Index(fields=['message_id'], name='task_message_id_idx'),
        ]
```

### 5. Bot UPN Storage

**File:** `core/services/graph_response_service.py`

**Changes:**
- Store bot UPN in `__init__` for potential future use
- Maintains consistency across services

## Test Coverage

### New Test Cases Added

1. **GraphServiceTimeFilteringTestCase**
   - `test_filters_old_messages` - Verifies messages > 30 minutes old are filtered
   - `test_includes_messages_within_30_minutes` - Verifies recent messages are included

2. **MessageProcessingSelfReplyPreventionTestCase**
   - `test_rejects_bot_own_messages` - Verifies bot messages are rejected
   - `test_accepts_user_messages` - Verifies normal messages are processed

### Existing Tests Enhanced

- Enhanced bot filtering tests with better scenarios
- Added ISARtec-specific test case matching the real-world scenario
- All 31 tests passing

## Testing Results

```bash
$ python manage.py test main.test_teams_message_integration
Ran 31 tests in 2.510s
OK
```

### Test Breakdown:
- TeamsListenerServiceTestCase: 7 tests ✓
- MessageProcessingServiceTestCase: 6 tests ✓
- TeamsIntegrationAPITestCase: 4 tests ✓
- TeamsManagementCommandTestCase: 1 test ✓
- MessageProcessingServiceRAGTestCase: 7 tests ✓
- TeamsMessageDeduplicationTestCase: 2 tests ✓
- GraphServiceTimeFilteringTestCase: 2 tests ✓
- MessageProcessingSelfReplyPreventionTestCase: 2 tests ✓

## Security Review

✅ **Code Review:** No issues found
✅ **CodeQL Security Scan:** 0 alerts found

## Multi-Layer Defense Strategy

The fix implements multiple layers of protection against infinite loops:

1. **Layer 1 (Graph API):** Time-based filtering at the source
2. **Layer 2 (Listener):** Sender UPN filtering when fetching messages
3. **Layer 3 (Listener):** Message ID deduplication check
4. **Layer 4 (Processing):** Defensive check before AI analysis
5. **Layer 5 (Database):** Indexed message_id for fast lookups

This ensures that even if one layer fails, others will catch the issue.

## Migration Steps

1. Apply the database migration:
   ```bash
   python manage.py migrate main
   ```

2. Ensure `default_mail_sender` is configured in Settings with the bot's UPN (e.g., `idea@isartec.de`)

3. Restart the Teams polling service:
   ```bash
   python manage.py poll_teams_messages --once
   ```

## Verification

To verify the fix is working:

1. Check logs for "SKIPPED:" messages showing bot messages are filtered
2. Verify no duplicate tasks are created for the same message_id
3. Monitor that only recent messages (< 30 min) are processed
4. Confirm no infinite loops occur when bot posts responses

## Files Modified

- ✅ `core/services/graph_service.py`
- ✅ `core/services/teams_listener_service.py`
- ✅ `core/services/message_processing_service.py`
- ✅ `core/services/graph_response_service.py`
- ✅ `main/models.py`
- ✅ `main/test_teams_message_integration.py`
- ✅ `main/migrations/0041_add_task_message_id_index.py`

## Performance Impact

- **Positive:** Database index improves message_id lookup speed
- **Positive:** 30-minute filter reduces number of messages to process
- **Neutral:** Additional checks have negligible performance impact
- **Overall:** Improved performance and reduced system load

## Backward Compatibility

- ✅ All existing tests pass
- ✅ Display name check preserved for backwards compatibility
- ✅ Defensive timestamp parsing (includes messages with missing timestamps)
- ✅ Migration is additive (only adds index, no data changes)

## Conclusion

This fix comprehensively addresses all four requirements from the issue:
1. ✅ Bot messages are filtered by UPN
2. ✅ Message IDs are stored and checked to prevent duplicates
3. ✅ Only messages from last 30 minutes are processed
4. ✅ Multiple layers prevent bot from replying to itself

The implementation is surgical, minimal, well-tested, and includes proper defensive programming practices.
