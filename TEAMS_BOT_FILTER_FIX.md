# Teams Bot Message Filtering Fix

## Problem
The `poll_teams_messages --once` command was creating an infinite loop by fetching the bot's own messages and processing them repeatedly.

## Root Cause
The code was filtering messages only by display name "IdeaGraph Bot", but the actual bot's display name is "ISARtec IdeaGraph Bot". This mismatch meant the bot's messages were not being filtered out.

## Solution
Changed the filtering logic to use **userPrincipalName (UPN)** instead of display name:
- Primary filter: Compare sender's UPN with `settings.default_mail_sender` (case-insensitive)
- Fallback filter: Keep display name check for backwards compatibility

## Implementation Details

### Changes in `teams_listener_service.py`
1. Store bot UPN during initialization:
   ```python
   self.bot_upn = self.settings.default_mail_sender if self.settings.default_mail_sender else None
   ```

2. Filter messages by UPN (primary) and display name (fallback):
   ```python
   # Check by UPN (userPrincipalName) which is more reliable than display name
   sender_upn = message.get('from', {}).get('user', {}).get('userPrincipalName', '')
   if self.bot_upn and sender_upn and sender_upn.lower() == self.bot_upn.lower():
       logger.debug(f"Skipping message from IdeaGraph Bot (UPN: {sender_upn}): {message.get('id')}")
       continue
   
   # Fallback: also check display name for backwards compatibility
   sender_name = message.get('from', {}).get('user', {}).get('displayName', '')
   if sender_name == self.IDEAGRAPH_BOT_NAME:
       logger.debug(f"Skipping message from IdeaGraph Bot (display name): {message.get('id')}")
       continue
   ```

### Test Coverage
Added two new test cases in `test_teams_message_integration.py`:
1. **`test_get_new_messages_filters_bot_by_upn`**: Tests UPN-based filtering with case-insensitive matching
2. **`test_get_new_messages_filters_bot_isartec_scenario`**: Tests the exact scenario from the issue with ISARtec bot (UPN: idea@isartec.de)

All 25 tests pass successfully.

## Configuration Required
Ensure `default_mail_sender` is set in the Settings model to match the bot's UPN:
- For the ISARtec scenario: `idea@isartec.de`
- This value should match the userPrincipalName of the bot account

## Benefits
1. **More reliable**: UPN is a unique identifier, less likely to change than display name
2. **Case-insensitive**: Works regardless of email case
3. **Backwards compatible**: Display name check still exists as fallback
4. **No database changes**: Uses existing `default_mail_sender` field from Settings

## Security
- No vulnerabilities introduced (CodeQL scan: 0 alerts)
- No sensitive data exposed
- No breaking changes to existing functionality
