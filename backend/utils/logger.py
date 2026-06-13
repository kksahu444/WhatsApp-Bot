"""
Structured Logging Configuration
================================
Production-ready logging with loguru.

Features:
- Console output: Human-readable colored format
- File output: JSON format for log aggregation
- Automatic rotation: 10MB per file, keep 5 files
- Context injection: Request ID, phone (redacted), etc.
- Exception handling: Full tracebacks in structured format

Usage:
    from backend.utils.logger import logger
    
    logger.info("Processing message", phone="1234567890", intent="add_to_cart")
    logger.error("Database error", exc_info=True)
    
    # With context
    with logger.contextualize(request_id="abc123"):
        logger.info("Handling webhook")
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from loguru import logger

# Remove default handler
logger.remove()

# ============================================================================
# CONFIGURATION
# ============================================================================

# Get settings from config (imported here to avoid circular imports)
try:
    from backend.config.logging_config import LoggingSettings
    settings = LoggingSettings()
except ImportError:
    # Fallback defaults if config not available
    class LoggingSettings:
        LOG_LEVEL: str = "INFO"
        LOG_DIR: str = "logs"
        LOG_FILE_NAME: str = "app.json"
        LOG_ROTATION: str = "10 MB"
        LOG_RETENTION: int = 5
        LOG_FORMAT_CONSOLE: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ENABLE_JSON_LOGS: bool = True
        ENABLE_CONSOLE_LOGS: bool = True
        REDACT_PII: bool = True
    settings = LoggingSettings()

# Ensure log directory exists
LOG_DIR = Path(settings.LOG_DIR)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# PII REDACTION
# ============================================================================

PII_PATTERNS = [
    # Phone numbers (various formats)
    (re.compile(r'\+?\d{10,15}'), lambda m: redact_phone(m.group())),
    # Email addresses
    (re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'), '[EMAIL_REDACTED]'),
    # Credit card numbers (basic pattern)
    (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), '[CARD_REDACTED]'),
    # UPI IDs
    (re.compile(r'[a-zA-Z0-9._-]+@[a-zA-Z]+'), lambda m: redact_upi(m.group())),
]


def redact_phone(phone: str) -> str:
    """Redact phone number keeping first 4 and last 2 digits."""
    clean = re.sub(r'[^\d+]', '', phone)
    if len(clean) >= 10:
        return clean[:4] + '*' * (len(clean) - 6) + clean[-2:]
    return '[PHONE_REDACTED]'


def redact_upi(upi_id: str) -> str:
    """Redact UPI ID keeping domain."""
    parts = upi_id.split('@')
    if len(parts) == 2:
        return parts[0][:2] + '***@' + parts[1]
    return '[UPI_REDACTED]'


def redact_pii(message: str) -> str:
    """Redact all PII from a message."""
    if not settings.REDACT_PII:
        return message
    
    for pattern, replacement in PII_PATTERNS:
        if callable(replacement):
            message = pattern.sub(replacement, message)
        else:
            message = pattern.sub(replacement, message)
    
    return message


# ============================================================================
# FORMATTERS
# ============================================================================

def format_record_for_json(record: Dict[str, Any]) -> str:
    """Format a log record as JSON."""
    # Extract exception info if present
    exception_info = None
    if record.get("exception"):
        exception_info = {
            "type": record["exception"].type.__name__ if record["exception"].type else None,
            "value": str(record["exception"].value) if record["exception"].value else None,
            "traceback": record["exception"].traceback.format() if record["exception"].traceback else None,
        }
    
    # Build structured log entry
    log_entry = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "level": record["level"].name,
        "logger": record["name"],
        "message": redact_pii(record["message"]),
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    
    # Add extra context
    if record.get("extra"):
        extra = {}
        for key, value in record["extra"].items():
            # Redact known PII fields
            if key in ("phone", "phone_number", "email", "address"):
                if isinstance(value, str):
                    extra[key] = redact_pii(value)
                else:
                    extra[key] = "[REDACTED]"
            else:
                extra[key] = value
        log_entry["extra"] = extra
    
    # Add exception info
    if exception_info:
        log_entry["exception"] = exception_info
    
    return json.dumps(log_entry, default=str) + "\n"


def console_formatter(record: Dict[str, Any]) -> str:
    """Format for human-readable console output."""
    # Redact message
    record["message"] = redact_pii(record["message"])
    
    # Add extra context to message if present
    extra = record.get("extra", {})
    if extra:
        # Filter out internal loguru extras
        user_extra = {k: v for k, v in extra.items() 
                      if not k.startswith("_") and k not in ("name",)}
        if user_extra:
            # Redact PII in extra
            for key in ("phone", "phone_number", "email", "address"):
                if key in user_extra and isinstance(user_extra[key], str):
                    user_extra[key] = redact_pii(user_extra[key])
            
            extra_str = " | " + " ".join(f"{k}={v}" for k, v in user_extra.items())
            record["message"] = record["message"] + extra_str
    
    return settings.LOG_FORMAT_CONSOLE + "\n"


# ============================================================================
# CONFIGURE HANDLERS
# ============================================================================

# Console handler (human-readable)
if settings.ENABLE_CONSOLE_LOGS:
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=console_formatter,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

# JSON file handler (structured)
if settings.ENABLE_JSON_LOGS:
    logger.add(
        LOG_DIR / settings.LOG_FILE_NAME,
        level=settings.LOG_LEVEL,
        format=format_record_for_json,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="gz",
        serialize=False,  # We handle serialization ourselves
        backtrace=True,
        diagnose=True,
    )

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_logger(name: str = None):
    """Get a logger instance with optional name binding."""
    if name:
        return logger.bind(name=name)
    return logger


def log_request(request_id: str, phone: str = None, **kwargs):
    """Log an incoming request with context."""
    return logger.bind(
        request_id=request_id,
        phone=phone,
        **kwargs
    )


# ============================================================================
# EXCEPTION HANDLER
# ============================================================================

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler that logs uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupts
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger.opt(exception=(exc_type, exc_value, exc_traceback)).critical(
        "Uncaught exception"
    )


# Install global exception handler
sys.excepthook = handle_exception


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "logger",
    "get_logger",
    "log_request",
    "redact_pii",
]
