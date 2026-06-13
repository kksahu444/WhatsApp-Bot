# Ops Configuration: Logging
# Centralized logging configuration for the WhatsApp Seller Bot

import os
import sys
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log formats."""
    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    # Basic settings
    level: LogLevel = LogLevel(os.getenv("LOG_LEVEL", "INFO"))
    format: LogFormat = LogFormat(os.getenv("LOG_FORMAT", "json"))
    
    # Output destinations
    log_to_console: bool = True
    log_to_file: bool = os.getenv("LOG_TO_FILE", "false").lower() == "true"
    log_file_path: str = os.getenv("LOG_FILE_PATH", "/var/log/whatsapp-bot/app.log")
    log_file_max_size_mb: int = int(os.getenv("LOG_FILE_MAX_SIZE_MB", "100"))
    log_file_backup_count: int = int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))
    
    # Loki integration
    loki_enabled: bool = os.getenv("LOKI_ENABLED", "false").lower() == "true"
    loki_url: str = os.getenv("LOKI_URL", "http://loki:3100")
    
    # Log enrichment
    include_request_id: bool = True
    include_user_id: bool = True
    include_trace_id: bool = True
    redact_sensitive_fields: bool = True
    
    # Sensitive field patterns to redact
    sensitive_patterns: tuple = (
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "credit_card",
        "phone",
    )


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def __init__(self, config: LoggingConfig):
        super().__init__()
        self.config = config
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "request_id", "user_id", "trace_id", "message"
            ):
                if self.config.redact_sensitive_fields:
                    if any(pattern in key.lower() for pattern in self.config.sensitive_patterns):
                        log_data[key] = "[REDACTED]"
                    else:
                        log_data[key] = value
                else:
                    log_data[key] = value
        
        return json.dumps(log_data, default=str)


class StructuredFormatter(logging.Formatter):
    """Structured text formatter for human-readable logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Build structured message
        parts = [
            f"[{timestamp}]",
            f"[{record.levelname:8}]",
            f"[{record.name}]",
        ]
        
        if hasattr(record, "request_id"):
            parts.append(f"[req:{record.request_id[:8]}]")
        
        parts.append(record.getMessage())
        
        if record.exc_info:
            parts.append(f"\n{self.formatException(record.exc_info)}")
        
        return " ".join(parts)


class LogContext:
    """Context manager for adding context to logs."""
    
    _context: Dict[str, Any] = {}
    
    @classmethod
    def set(cls, **kwargs) -> None:
        """Set context values."""
        cls._context.update(kwargs)
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return cls._context.get(key, default)
    
    @classmethod
    def clear(cls) -> None:
        """Clear all context."""
        cls._context.clear()
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all context values."""
        return cls._context.copy()


class ContextFilter(logging.Filter):
    """Filter that adds context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in LogContext.get_all().items():
            setattr(record, key, value)
        return True


def setup_logging(config: Optional[LoggingConfig] = None) -> logging.Logger:
    """Set up logging with the given configuration."""
    if config is None:
        config = LoggingConfig()
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level.value))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create formatter based on format type
    if config.format == LogFormat.JSON:
        formatter = JSONFormatter(config)
    elif config.format == LogFormat.STRUCTURED:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # Add context filter
    context_filter = ContextFilter()
    
    # Console handler
    if config.log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(context_filter)
        root_logger.addHandler(console_handler)
    
    # File handler
    if config.log_to_file:
        from logging.handlers import RotatingFileHandler
        import os
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(config.log_file_path), exist_ok=True)
        
        file_handler = RotatingFileHandler(
            config.log_file_path,
            maxBytes=config.log_file_max_size_mb * 1024 * 1024,
            backupCount=config.log_file_backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(context_filter)
        root_logger.addHandler(file_handler)
    
    # Configure third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


# Convenience functions
def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra
) -> None:
    """Log an HTTP request."""
    logger = get_logger("http.request")
    logger.info(
        f"{method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra={"method": method, "path": path, "status_code": status_code, "duration_ms": duration_ms, **extra}
    )


def log_event(
    event: str,
    user_id: Optional[str] = None,
    **data
) -> None:
    """Log a business event."""
    logger = get_logger("events")
    logger.info(
        f"Event: {event}",
        extra={"event": event, "user_id": user_id, **data}
    )


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    **extra
) -> None:
    """Log an error with context."""
    logger = get_logger("errors")
    logger.error(
        f"Error: {type(error).__name__}: {str(error)}",
        exc_info=error,
        extra={"error_type": type(error).__name__, "context": context, **extra}
    )
