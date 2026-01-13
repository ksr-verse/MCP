# Logging Documentation

## Overview

Comprehensive logging has been added to help debug the SailPoint Support Bot.

## Log Locations

1. **Console Output** - Real-time logs in terminal
2. **Log File** - `sailpoint_bot.log` in backend directory

## Log Levels

- **INFO** - Normal operations, API calls, tool executions
- **WARNING** - Warnings (e.g., missing config, using placeholders)
- **ERROR** - Errors with full traceback
- **DEBUG** - Detailed information (payloads, responses)

## Log Rotation

For production, consider log rotation:

```python
# Add to main.py
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'sailpoint_bot.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

## Adjusting Log Level

Edit `backend/main.py`:

