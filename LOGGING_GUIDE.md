# IdeaGraph Centralized Logging System

## Overview

IdeaGraph uses a centralized logging system that provides:
- **Local file logging** with automatic rotation
- **Console output** for development
- **Sentry integration** for error tracking in production
- **Configurable log levels** via environment variables

## Quick Start

### 1. Configuration

Copy the example environment file and configure logging settings:

```bash
cp .env.example .env
```

Edit `.env` to set your logging preferences:

```bash
# Logging Configuration
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=logs                    # Directory for log files
LOG_FILE_NAME=ideagraph.log     # Main log file name
LOG_MAX_BYTES=5000000           # 5 MB before rotation
LOG_BACKUP_COUNT=5              # Keep 5 backup files

# Sentry Configuration (optional)
ENABLE_SENTRY=False             # Set to True to enable Sentry
SENTRY_DSN=                     # Your Sentry DSN
APP_ENVIRONMENT=development     # development, staging, production
```

### 2. Using the Logger

Import and use the logger in your code:

```python
from core.logger_config import get_logger

# Get a logger for your module
logger = get_logger('my_module')

# Log messages at different levels
logger.debug("Detailed debug information")
logger.info("General information about application flow")
logger.warning("Warning: something unexpected happened")
logger.error("Error: operation failed", exc_info=True)
logger.critical("Critical: system in unstable state!")
```

### 3. Service-Specific Loggers

Pre-configured loggers for services:

```python
# KiGate Service
from core.logger_config import get_logger
logger = get_logger('kigate_service')

# OpenAI Service
logger = get_logger('openai_service')

# Authentication Service
logger = get_logger('auth_service')

# Graph Service
logger = get_logger('graph_service')
```

## Log Levels

| Level    | When to Use | Where Logged |
|----------|-------------|--------------|
| **DEBUG** | Detailed diagnostic information for development | File only |
| **INFO** | General informational messages about application flow | File + Console |
| **WARNING** | Warnings about potential issues (e.g., API timeout) | File + Console |
| **ERROR** | Errors that need attention but don't crash the app | File + Console + Sentry |
| **CRITICAL** | Critical errors that may cause system failure | File + Console + Sentry |

## Log Format

All log messages follow this format:

```
YYYY-MM-DD HH:MM:SS [LEVEL] [module_name] - message
```

Example:
```
2025-10-19 11:34:02 [INFO] [kigate_service] - KI-Agent erfolgreich ausgeführt
```

## File Structure

```
IdeaGraph-v1/
├── logs/                       # Log files directory
│   ├── ideagraph.log          # Main application log
│   ├── ideagraph.log.1        # Rotated backup 1
│   ├── ideagraph.log.2        # Rotated backup 2
│   ├── ...
│   └── auth_service.log       # Authentication-specific log
├── core/
│   └── logger_config.py       # Centralized logging configuration
└── .env                       # Environment configuration
```

## Log Rotation

Logs are automatically rotated when they reach the configured size (default: 5 MB):
- Old logs are renamed with numeric suffixes (`.1`, `.2`, etc.)
- Up to 5 backup files are kept by default
- Oldest backups are automatically deleted

## Sentry Integration

### Setup

1. Create a Sentry account at [sentry.io](https://sentry.io)
2. Create a new project for IdeaGraph
3. Copy your DSN from the project settings
4. Configure in `.env`:

```bash
ENABLE_SENTRY=True
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
APP_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=1.0
```

### What Gets Sent to Sentry

When Sentry is enabled, the following are automatically captured:
- ✅ All ERROR and CRITICAL level logs
- ✅ Unhandled exceptions with full stack traces
- ✅ Django HTTP request context
- ✅ User information (if authenticated)
- ✅ Server environment details

### Privacy Considerations

- Sensitive data should **never** be logged
- Use environment variables for secrets
- Sentry automatically filters common sensitive patterns
- Review logs before enabling Sentry in production

## Best Practices

### 1. Use Appropriate Log Levels

```python
# ✅ Good
logger.debug(f"Processing item: {item_id}")
logger.info("User authenticated successfully")
logger.warning("API rate limit approaching: 90% used")
logger.error("Failed to save to database", exc_info=True)

# ❌ Bad
logger.info("x=5")  # Too verbose for INFO
logger.error("User logged in")  # Wrong level
```

### 2. Include Context

```python
# ✅ Good - includes context
logger.error(f"Failed to process task {task_id}: {str(e)}", exc_info=True)

# ❌ Bad - lacks context
logger.error("Error occurred")
```

### 3. Don't Log Sensitive Data

```python
# ❌ Never log passwords, tokens, or API keys
logger.info(f"User logged in with password: {password}")
logger.debug(f"API key: {api_key}")

# ✅ Log safely
logger.info(f"User logged in: {username}")
logger.debug(f"API key configured: {api_key[:8]}...")
```

### 4. Use Exception Info

```python
# ✅ Include full traceback for errors
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {str(e)}", exc_info=True)

# ❌ Missing valuable debugging information
except Exception as e:
    logger.error(f"Error: {str(e)}")
```

## Testing Logging

Run the demo script to test logging:

```bash
python test_logging_demo.py
```

Run the test suite:

```bash
python manage.py test main.test_logger
```

## Troubleshooting

### Logs Not Appearing

1. Check log level configuration in `.env`
2. Verify logs directory has write permissions
3. Check Django settings are loading correctly

### Log File Growing Too Large

Adjust rotation settings in `.env`:

```bash
LOG_MAX_BYTES=1000000    # Rotate at 1 MB instead of 5 MB
LOG_BACKUP_COUNT=3       # Keep fewer backups
```

### Sentry Not Working

1. Verify `ENABLE_SENTRY=True` in `.env`
2. Check SENTRY_DSN is correct
3. Look for Sentry initialization message in logs:
   ```
   INFO [IdeaGraph] - Sentry initialized for environment: production
   ```
4. Test with: `logger.error("Test Sentry integration")`

## Migration from Old Logging

If you have existing logging code:

```python
# Old way (still works!)
import logging
logger = logging.getLogger('my_module')

# New way (recommended)
from core.logger_config import get_logger
logger = get_logger('my_module')
```

Both approaches work! The Django settings now handle all loggers automatically.

## Additional Resources

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [Django Logging Documentation](https://docs.djangoproject.com/en/stable/topics/logging/)
- [Sentry Python SDK Documentation](https://docs.sentry.io/platforms/python/)

## Support

For issues or questions about logging:
1. Check this guide first
2. Review test cases in `main/test_logger.py`
3. Run the demo script: `python test_logging_demo.py`
4. Open an issue on GitHub with log samples
