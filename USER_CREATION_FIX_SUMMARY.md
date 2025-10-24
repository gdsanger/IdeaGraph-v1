# User Creation Fix Summary

## Problem

When new messages arrived via Teams or Mail, the system was not correctly creating unique users for different senders. Instead, a generic user (e.g., `user@example.com`) was being created and all new messages were incorrectly assigned to this single user, rather than creating separate users with correct names and email addresses.

## Root Cause

The issue was in the mail processing service (`core/services/mail_processing_service.py`):

1. The `process_mail` method was only extracting the sender's email address from the message, but not the sender's name
2. The `create_task_from_mail` method was not receiving or using the sender's name when creating new users
3. When a new user was created from an email, only the email was set as username and email, but `first_name` and `last_name` fields were left empty

This meant that while each user had a unique email address, there was no way to identify them by their actual name, making it impossible to properly communicate with them.

## Solution

### Mail Processing Service Changes

**File: `core/services/mail_processing_service.py`**

#### 1. Extract sender name from message (line 720)

```python
# Before:
sender = message.get('from', {}).get('emailAddress', {})
sender_email = sender.get('address', '')

# After:
sender = message.get('from', {}).get('emailAddress', {})
sender_email = sender.get('address', '')
sender_name = sender.get('name', '')
```

#### 2. Pass sender name to task creation (line 772)

```python
# Before:
task_info = self.create_task_from_mail(
    mail_subject=subject,
    mail_body_markdown=normalized_description,
    item_id=item_id,
    sender_email=sender_email
)

# After:
task_info = self.create_task_from_mail(
    mail_subject=subject,
    mail_body_markdown=normalized_description,
    item_id=item_id,
    sender_email=sender_email,
    sender_name=sender_name
)
```

#### 3. Update method signature and user creation logic (lines 544-599)

```python
def create_task_from_mail(
    self,
    mail_subject: str,
    mail_body_markdown: str,
    item_id: str,
    sender_email: str,
    sender_name: str = ''  # NEW parameter
) -> Optional[Dict[str, Any]]:
    # ... existing code ...
    
    except User.DoesNotExist:
        # Create new user with email as username
        logger.info(f"Creating new user for email {sender_email}")
        
        # NEW: Extract first and last name from sender name
        first_name = ''
        last_name = ''
        if sender_name:
            name_parts = sender_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            elif len(name_parts) == 1:
                first_name = name_parts[0]
        
        requester = User.objects.create(
            username=sender_email,
            email=sender_email,
            first_name=first_name,      # NEW
            last_name=last_name,         # NEW
            role='user',
            is_active=True
        )
        logger.info(f"Created new user {requester.id} for email {sender_email} ({first_name} {last_name})")
```

### Teams Integration (Already Working Correctly)

The Teams integration was already working correctly. The `message_processing_service.py` has a method `get_or_create_user_from_upn` that properly extracts first and last names from the `displayName` field in Teams messages.

## Testing

Added comprehensive tests in `main/test_mail_processing_service.py`:

1. **test_create_task_from_mail_with_sender_name**: Verifies that a user with a full name "John Doe" is correctly split into first_name="John" and last_name="Doe"

2. **test_create_task_from_mail_with_single_name**: Verifies that a single name "Madonna" is correctly set as first_name="Madonna" with empty last_name

3. **test_create_task_from_mail_with_compound_last_name**: Verifies that compound last names like "Maria Garcia Lopez" are correctly split into first_name="Maria" and last_name="Garcia Lopez"

4. **test_process_mail_extracts_sender_name**: End-to-end test verifying that the complete mail processing flow correctly extracts and uses sender names

All tests pass successfully.

## Impact

- **Mail Processing**: Now correctly creates users with proper first and last names from email sender information
- **Teams Processing**: Already worked correctly, no changes needed
- **User Creation**: Each sender now gets a unique user account with their actual name, making it possible to properly identify and communicate with them
- **Backward Compatibility**: The `sender_name` parameter is optional (defaults to empty string), so existing code that doesn't pass it will continue to work

## Message Structure

For reference, the message structures from Microsoft Graph API:

### Mail Message Structure
```json
{
  "from": {
    "emailAddress": {
      "name": "John Doe",
      "address": "john.doe@example.com"
    }
  }
}
```

### Teams Message Structure
```json
{
  "from": {
    "user": {
      "displayName": "John Doe",
      "userPrincipalName": "john.doe@example.com"
    }
  }
}
```

## Files Modified

1. `core/services/mail_processing_service.py` - Main fix
2. `main/test_mail_processing_service.py` - Test additions

## Verification

Run the following tests to verify the fix:

```bash
# Test mail processing with sender names
python manage.py test main.test_mail_processing_service.MailProcessingServiceTestCase.test_create_task_from_mail_with_sender_name

# Test mail processing with single names
python manage.py test main.test_mail_processing_service.MailProcessingServiceTestCase.test_create_task_from_mail_with_single_name

# Test mail processing with compound last names
python manage.py test main.test_mail_processing_service.MailProcessingServiceTestCase.test_create_task_from_mail_with_compound_last_name

# Test complete process_mail flow
python manage.py test main.test_mail_processing_service.MailProcessingServiceTestCase.test_process_mail_extracts_sender_name

# Run all mail processing tests
python manage.py test main.test_mail_processing_service

# Verify Teams processing still works
python manage.py test main.test_teams_message_integration
```
