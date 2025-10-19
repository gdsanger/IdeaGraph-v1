# Send Item via Email - Feature Documentation

## Overview
This feature allows users to send item details along with all open tasks via email using the Microsoft Graph API integration.

## Components

### 1. Email Template
**File:** `main/templates/main/mailtemplates/send_item.html`

A professionally designed HTML email template that includes:
- Item title and description
- Item metadata (status, section, GitHub repo, creator, dates)
- Tags with colored badges
- List of all open tasks (excluding completed tasks)
- Task details including title, status, and assigned user
- Clean, structured layout with responsive design
- No Markdown - pure HTML as required

### 2. Mail Utility Function
**File:** `main/mail_utils.py`
**Function:** `send_item_email(item_id, recipient_email)`

This function:
- Retrieves the item with all related data (section, creator, tags, tasks)
- Filters tasks to include only open tasks (status != 'done')
- Renders the HTML email template with the item data
- Sends the email via Microsoft Graph API using the item title as the subject
- Returns a tuple of (success: bool, message: str)

### 3. API Endpoint
**File:** `main/api_views.py`
**Function:** `api_send_item_email(request, item_id)`
**URL:** `POST /api/items/{item_id}/send-email`

Request body:
```json
{
  "email": "recipient@example.com"
}
```

Success response (200):
```json
{
  "success": true,
  "message": "Item email sent successfully"
}
```

Error responses:
- 401: Authentication required
- 403: Access denied (only owner or admin can send)
- 400: Missing or invalid email address
- 404: Item not found
- 500: Email service error

### 4. URL Routing
**File:** `main/urls.py`

Added route:
```python
path('api/items/<uuid:item_id>/send-email', api_views.api_send_item_email, name='api_send_item_email')
```

## Security & Access Control

- **Authentication Required**: Users must be authenticated to use this feature
- **Authorization**: Only the item owner or admin users can send the item via email
- **Email Validation**: Basic email format validation is performed
- **Graph API**: Uses existing Microsoft Graph API integration with proper authentication

## Email Content

The email includes:

1. **Header**: Blue gradient header with lightbulb icon and "Item Details" title
2. **Item Title**: Prominently displayed as H2
3. **Metadata Section**: 
   - Status (with colored badge)
   - Section/Category
   - GitHub Repository (if set)
   - Creator
   - Created and Updated timestamps
   - Tags (with colored badges)
4. **Description**: Item description in a formatted box
5. **Open Tasks Section**:
   - Shows count of open tasks
   - Lists each open task with:
     - Task title
     - Status badge
     - Assigned user (if any)
   - Shows "no tasks" message if there are no open tasks
6. **Info Box**: Note about the automated email
7. **Footer**: IdeaGraph branding and contact information

## Testing

Comprehensive test suite in `main/test_send_item_email.py`:

**Test Cases:**
1. ✓ Send email successfully
2. ✓ Send email with no tasks
3. ✓ Handle non-existent item
4. ✓ Handle GraphService errors
5. ✓ API endpoint as owner
6. ✓ API endpoint as admin
7. ✓ Reject non-owner access
8. ✓ Reject unauthenticated requests
9. ✓ Validate missing email
10. ✓ Validate invalid email format
11. ✓ Handle non-existent item in API

All tests pass successfully!

## Usage Example

### Via API:
```bash
curl -X POST https://your-domain.com/api/items/{item-id}/send-email \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=YOUR_SESSION_ID" \
  -d '{"email": "recipient@example.com"}'
```

### Via Django Session:
```python
from main.mail_utils import send_item_email

# Send item email
success, message = send_item_email(
    item_id='123e4567-e89b-12d3-a456-426614174000',
    recipient_email='user@example.com'
)

if success:
    print("Email sent successfully!")
else:
    print(f"Failed to send email: {message}")
```

## Requirements Met

✅ Function to send item via email  
✅ Email contains all relevant item information  
✅ Email contains list of all open tasks with title and status  
✅ Email is in HTML format (no Markdown)  
✅ Email is cleanly structured and well-formatted  
✅ Uses Graph API for sending  
✅ Uses item title as email subject  

## Configuration

Ensure the following settings are configured in the Settings model:
- `graph_api_enabled`: True
- `tenant_id`: Microsoft tenant ID
- `client_id`: Microsoft application client ID
- `client_secret`: Microsoft application client secret
- `default_mail_sender`: Default sender email address

## Notes

- Completed tasks (status='done') are excluded from the email to focus on actionable items
- The email template is in German (de) as per the original requirement
- HTML email is fully styled with inline CSS for maximum email client compatibility
- The feature integrates seamlessly with the existing GraphService infrastructure
