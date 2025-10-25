# Mail Processing Job - Documentation

## Overview

This implementation provides an AI-powered job for processing incoming emails and automatically creating tasks in IdeaGraph. The system uses multiple AI services to analyze emails, match them to appropriate Items, generate normalized task descriptions, and send confirmation emails.

## Components

### 1. Mail Processing Service (`core/services/mail_processing_service.py`)

The main service that orchestrates the entire workflow:

- **Mail Retrieval**: Fetches unread emails from a mailbox via Microsoft Graph API
- **HTML to Markdown Conversion**: Converts HTML email bodies to Markdown using KiGate agent
- **Item Matching**: Uses RAG (Retrieval Augmented Generation) with Weaviate to find the most relevant Item
- **AI Normalization**: Generates normalized task descriptions using KiGate's 'teams-support-analysis-agent'
- **Task Creation**: Creates new tasks in the database linked to matched Items
- **Confirmation Emails**: Sends professional confirmation emails to senders
- **Markdown to HTML Conversion**: Converts confirmation email content to HTML using KiGate agent

### Graph Service Extensions (`core/services/graph_service.py`)

Added new methods to GraphService:

- `get_mailbox_messages()`: Retrieve messages from a mailbox
- `mark_message_as_read()`: Mark a message as read after processing
- `move_message()`: Move a message to a specified folder (e.g., Archive)

### 3. OpenAI Service Extension (`core/services/openai_service.py`)

Added new method:

- `chat_completion()`: Execute chat completions for AI-powered text processing

### 4. Django Management Command (`main/management/commands/process_mails.py`)

Command-line interface for manual execution or cron jobs:

```bash
python manage.py process_mails [options]
```

**Options:**
- `--mailbox EMAIL`: Specify mailbox address (uses default from settings if not provided)
- `--folder FOLDER`: Mail folder to process (default: 'inbox')
- `--max-messages N`: Maximum number of messages to process (default: 10)

## Configuration

### Required Settings

The following settings must be configured in the Django admin panel:

1. **Graph API Settings:**
   - `graph_api_enabled`: Must be True
   - `tenant_id`: Microsoft Azure tenant ID
   - `client_id`: Azure app client ID
   - `client_secret`: Azure app client secret
   - `default_mail_sender`: Default mailbox to process (e.g., idea@angermeier.net)

2. **KiGate API Settings (Required):**
   - `kigate_api_enabled`: Must be True
   - `kigate_api_base_url`: KiGate API endpoint
   - `kigate_api_token`: KiGate authentication token

3. **OpenAI API Settings (Optional - only used for multi-item selection):**
   - `openai_api_enabled`: Can be True for enhanced item matching
   - `openai_api_key`: OpenAI API key
   - `openai_default_model`: Model to use (e.g., 'gpt-4')

4. **Weaviate Settings:**
   - `weaviate_cloud_enabled`: True for cloud, False for local
   - `weaviate_url`: Weaviate instance URL (if using cloud)
   - `weaviate_api_key`: API key (if using cloud)

### Required KiGate Agents

The following KiGate agents must be available and configured:

1. `html-to-markdown-converter`: Converts HTML email content to Markdown
2. `markdown-to-html-converter`: Converts Markdown content to HTML for emails
3. `teams-support-analysis-agent`: Analyzes emails and generates normalized task descriptions in Markdown format

### Email Archiving

Processed emails are automatically moved to the Archive folder:

1. **Archive Folder**: Should exist in the mailbox (e.g., "Archive" or "Archiv")
2. **Automatic Creation**: If the Archive folder doesn't exist, create it manually in Outlook/Exchange
3. **Folder Name**: The default folder name is "archive" (case-insensitive in Graph API)
4. **Custom Folder**: To use a different folder, modify the `destination_folder` parameter in the `move_message()` call in `mail_processing_service.py`
5. **Failure Handling**: If archiving fails, the task is still created successfully - archiving is non-critical

## Usage

### Manual Execution

Process emails from the default mailbox:
```bash
python manage.py process_mails
```

Process emails from a specific mailbox:
```bash
python manage.py process_mails --mailbox custom@example.com
```

Process up to 20 emails:
```bash
python manage.py process_mails --max-messages 20
```

### Automated Execution (Cron Job)

Add to crontab for periodic execution:

```bash
# Process emails every 15 minutes
*/15 * * * * cd /path/to/IdeaGraph-v1 && python manage.py process_mails >> /var/log/ideagraph/mail_processing.log 2>&1

# Process emails every hour
0 * * * * cd /path/to/IdeaGraph-v1 && python manage.py process_mails --max-messages 20 >> /var/log/ideagraph/mail_processing.log 2>&1
```

### Systemd Timer (Alternative to Cron)

Create a systemd service and timer for better management:

**`/etc/systemd/system/ideagraph-mail-processing.service`:**
```ini
[Unit]
Description=IdeaGraph Mail Processing Service
After=network.target

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/path/to/IdeaGraph-v1
ExecStart=/usr/bin/python3 manage.py process_mails
StandardOutput=journal
StandardError=journal
```

**`/etc/systemd/system/ideagraph-mail-processing.timer`:**
```ini
[Unit]
Description=IdeaGraph Mail Processing Timer
Requires=ideagraph-mail-processing.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=15min
Unit=ideagraph-mail-processing.service

[Install]
WantedBy=timers.target
```

Enable and start the timer:
```bash
sudo systemctl enable ideagraph-mail-processing.timer
sudo systemctl start ideagraph-mail-processing.timer
```

## Workflow

1. **Email Reception**: User sends email to configured mailbox (e.g., idea@angermeier.net)

2. **Retrieval**: Job fetches unread messages from mailbox via Graph API

3. **HTML to Markdown**: Email body is converted from HTML to Markdown format

4. **Item Matching via RAG**:
   - Email content (subject + body) is used as query
   - Weaviate searches for similar Items using vector similarity
   - OpenAI analyzes top matches and selects the best one
   - If only one result, uses distance-based selection

5. **Description Normalization**:
   - KiGate's 'teams-support-analysis-agent' analyzes the email
   - Generates a clear, actionable task description in Markdown format
   - Maintains context from the email
   - Uses Item context to add relevant details
   - Lists unclear points as "ggf. noch zu klären:"
   - Preserves original email at the end

6. **Task Creation**:
   - New task created with:
     - Title: Email subject
     - Description: Normalized description + original email
     - Status: 'new'
     - Item: Matched Item
     - Requester: Sender (if user exists in system)

6a. **Original Mail Comment**:
   - Comment added to task with original email content
   - Includes sender's name, subject, and email body in Markdown
   - Author: User who sent the email (identified by email address)
   - Source: 'user'

7. **Confirmation Email**:
   - Professional HTML email sent to sender
   - Confirms receipt of their request
   - Shows which Item it was assigned to
   - Displays the normalized description

7a. **Confirmation Email Comment**:
   - Comment added to task with confirmation email content
   - Includes German greeting, Item assignment, and normalized description
   - Author: "AI Agent Bot"
   - Source: 'agent'

8. **Email Archiving**:
   - After successful processing, email is moved to Archive folder
   - Uses Microsoft Graph API move operation
   - Failures in archiving don't prevent task creation
   - Archive status is logged and displayed in command output

9. **Cleanup**: Email marked as read

## Error Handling

The service includes comprehensive error handling:

- **No Matching Item**: Email processing skipped with warning log
- **AI Service Failures**: Fallback to formatted original content
- **KiGate Unavailable**: Fallback to basic HTML-to-Markdown conversion and original email content
- **Graph API Errors**: Logged with detailed error messages
- **Task Creation Failures**: Logged but doesn't stop processing other emails
- **Archiving Failures**: Non-critical, task creation still succeeds

## Security

The implementation has been validated with CodeQL security scanner:

- ✅ No SQL injection vulnerabilities
- ✅ No code injection risks
- ✅ Proper input validation
- ✅ Secure API communication
- ✅ No credential exposure

## Monitoring and Logging

All operations are logged using Python's logging framework:

```python
logger = logging.getLogger('mail_processing_service')
```

Log levels used:
- **INFO**: Normal operations (email processed, task created, etc.)
- **WARNING**: Recoverable issues (no matching item, AI service unavailable)
- **ERROR**: Failures requiring attention (API errors, task creation failures)

## Testing

Comprehensive test suite included in `main/test_mail_processing_service.py`:

Run tests:
```bash
python manage.py test main.test_mail_processing_service
```

Tests cover:
- Service initialization
- HTML/Markdown conversion
- Item matching with RAG
- AI description generation
- Task creation
- Confirmation emails
- Complete mail processing workflow
- Mailbox processing

**Note**: Tests require proper mocking of external services (Weaviate, OpenAI, Graph API, KiGate).

## Troubleshooting

### Common Issues

1. **"Graph API is not enabled"**
   - Solution: Enable Graph API in Settings and configure credentials

2. **"No matching item found"**
   - Solution: Ensure Items are synced to Weaviate
   - Run: `python manage.py sync_tags_to_weaviate` (if applicable)
   - Verify Weaviate is running and accessible

3. **"Failed to send confirmation email"**
   - Solution: Check Graph API credentials and permissions
   - Verify sender email has send permissions

4. **"KiGate agent not available"**
   - Solution: Verify KiGate is running and agents are configured
   - System will fallback to using HTML/Markdown as-is

5. **"OpenAI API error"**
   - Solution: Check API key and quota
   - Verify model name is correct

6. **"Failed to archive message"** (Warning)
   - Solution: Verify Archive folder exists in the mailbox
   - Check that Mail.ReadWrite permission is granted
   - Note: This is a warning only - task creation still succeeds

### Debug Mode

Enable debug logging in Django settings:

```python
LOGGING = {
    'loggers': {
        'mail_processing_service': {
            'level': 'DEBUG',
        },
    },
}
```

## Future Enhancements

Potential improvements:

1. **Attachment Handling**: Process email attachments
2. **Thread Support**: Handle email threads and replies
3. **Priority Detection**: Auto-assign priority based on content
4. **Multi-language Support**: Process emails in multiple languages
5. **Custom Rules**: User-defined routing rules for specific senders/subjects
6. **Web Interface**: Monitor processing status via Django admin
7. **Metrics Dashboard**: Track processing statistics and success rates
8. **Configurable Archive Folder**: Make archive folder name configurable via settings
9. **Archive Retention Policy**: Automatically delete old archived emails after a configured period

## API Integration Reference

### Microsoft Graph API

- **Endpoint**: `https://graph.microsoft.com/v1.0`
- **Authentication**: OAuth 2.0 Client Credentials Flow
- **Required Permissions**:
  - `Mail.Read` - Read emails
  - `Mail.ReadWrite` - Mark emails as read and move to folders
  - `Mail.Send` - Send confirmation emails

### Weaviate

- **Collection**: `Item`
- **Query Type**: `near_text` (semantic search)
- **Vectorization**: Automatic via text2vec-transformers

### OpenAI

- **API**: Chat Completions
- **Models**: gpt-4, gpt-4-turbo, or gpt-3.5-turbo
- **Temperature**: 0.7 (configurable)

### KiGate

- **Agents Used**:
  - `html-to-markdown-converter`
  - `markdown-to-html-converter`
- **Provider**: OpenAI
- **Model**: gpt-4o-mini

## License

This implementation is part of the IdeaGraph project and follows the same license.

## Support

For issues or questions:
- Check logs for detailed error messages
- Review configuration settings
- Verify all required services are running
- Contact: idea@angermeier.net
