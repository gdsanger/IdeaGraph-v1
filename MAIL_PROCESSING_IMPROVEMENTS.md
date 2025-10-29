# Mail Processing Improvements - IG-TASK Email Threading

## Overview

This document describes the improvements made to the `process_mails` command to support email conversation threading with task references.

## Requirements Implemented

Based on issue requirements, the following changes have been implemented:

### 1. Email Comments Marked as Email (Not Note)
**Requirement:** Comments must be marked as "Mail" (email) and not as "Note", with sender information stored.

**Implementation:**
- All incoming email comments are now created with `source='email'` and `email_direction='inbound'`
- Sender information is stored in `email_from`, `author`, and `author_name` fields
- Original email subject is stored in `email_subject` field

### 2. Task Reference in Reply Subject
**Requirement:** Reply emails must include the task reference `[IG-TASK:#XXXXXX]` in the subject.

**Implementation:**
- Confirmation emails now use `EmailConversationService.format_subject_with_short_id()` to add the task reference
- Example: `Re: Support Request [IG-TASK:#A1B2C3]`

### 3. Outgoing Email Marked Correctly
**Requirement:** Outgoing mail must be marked as email outbound with System as sender.

**Implementation:**
- Confirmation emails are now created with `source='email'` and `email_direction='outbound'`
- `email_from` is set to `settings.default_mail_sender`
- `author_name` is set to 'System'

### 4. Process Replies to Existing Tasks
**Requirement:** When emails come in via `process_mails`, check if IG-TASK is in the subject.
- If yes: Add message to task comments, send notification to assigned user
- If no or task not found: Create new task as before

**Implementation:**
- `process_mail()` method now checks for IG-TASK reference first using `EmailConversationService.extract_short_id_from_subject()`
- If found and task exists:
  - Email is added as a comment to the existing task
  - Comment is marked with `source='email'` and `email_direction='inbound'`
  - Notification email is sent to the user in the `assigned_to` field
  - Notification subject includes the IG-TASK reference
- If not found or task doesn't exist:
  - Creates a new task following the original workflow
  - Confirmation email includes IG-TASK reference for future replies

## Technical Changes

### Modified Files

#### `core/services/mail_processing_service.py`

**New Import:**
```python
from core.services.email_conversation_service import EmailConversationService, EmailConversationServiceError
```

**Service Initialization:**
- Added `self.email_conversation_service = EmailConversationService(settings)` in `__init__`

**Updated Methods:**

1. **`add_comment_to_task()`** - Extended with email-specific parameters:
   - `email_message_id`
   - `email_in_reply_to`
   - `email_references`
   - `email_from`
   - `email_to`
   - `email_cc`
   - `email_subject`
   - `email_direction`

2. **`send_confirmation_email()`** - Enhanced to include task reference:
   - Added `task` parameter
   - Uses `EmailConversationService.format_subject_with_short_id()` to add IG-TASK reference

3. **`send_notification_to_assigned_user()`** - New method:
   - Sends notification to assigned user when new message arrives
   - Includes IG-TASK reference in subject
   - Only sends if task has an assigned user

4. **`process_mail()`** - Completely restructured:
   - First checks for IG-TASK reference in subject
   - If found and task exists: Adds comment and sends notification
   - If not found: Creates new task with original workflow
   - All email comments are properly marked with `source='email'` and `email_direction`

### Test Coverage

Added comprehensive tests in `main/test_mail_processing_service.py`:

1. **`test_process_mail_with_existing_task_reference`**
   - Tests email reply to existing task
   - Verifies comment is added with correct email fields
   - Verifies notification is sent to assigned user

2. **`test_process_mail_marks_comments_as_email`**
   - Tests new task creation
   - Verifies inbound email comment has `email_direction='inbound'`
   - Verifies outbound confirmation has `email_direction='outbound'` and IG-TASK reference

3. **`test_process_mail_with_invalid_task_reference`**
   - Tests fallback behavior when task reference is invalid
   - Verifies new task is created

## Email Flow

### New Email (No IG-TASK Reference)

```
1. Email arrives → process_mail()
2. No IG-TASK found → Create new task workflow
3. Create task with normalized description
4. Add inbound email comment (source='email', direction='inbound')
5. Send confirmation with IG-TASK reference
6. Add outbound email comment (source='email', direction='outbound')
```

### Reply Email (With IG-TASK Reference)

```
1. Email arrives → process_mail()
2. Extract Short-ID from subject [IG-TASK:#XXXXXX]
3. Find existing task by Short-ID
4. Add email as comment (source='email', direction='inbound')
5. Send notification to assigned user (with IG-TASK reference)
6. Archive message
```

## Benefits

1. **Conversation Threading**: Email conversations are now properly threaded with tasks
2. **Improved Tracking**: All emails (inbound/outbound) are tracked in task comments
3. **Better Notifications**: Assigned users are notified when new messages arrive
4. **Consistent Workflow**: Maintains backward compatibility while adding new features

## Database Schema

Uses existing `TaskComment` fields:
- `source`: 'user', 'agent', or 'email'
- `email_direction`: 'inbound' or 'outbound'
- `email_from`, `email_to`, `email_cc`: Email addresses
- `email_subject`: Email subject line
- `email_message_id`, `email_in_reply_to`, `email_references`: For threading

## Usage

The changes are automatically applied when using the management command:

```bash
python manage.py process_mails --mailbox idea@angermeier.net --max-messages 10
```

No configuration changes required - the system automatically:
- Detects IG-TASK references in email subjects
- Routes replies to existing tasks
- Sends notifications to assigned users
- Includes IG-TASK references in confirmation emails
