"""
Logging Configuration Settings
==============================
Centralized configuration for the logging system.

Environment variables:
    LOG_LEVEL          - Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_DIR            - Directory for log files
    LOG_ROTATION       - When to rotate logs (e.g., "10 MB", "1 day")
    LOG_RETENTION      - Number of rotated files to keep
    ENABLE_JSON_LOGS   - Enable JSON file logging (true/false)
    ENABLE_CONSOLE_LOGS - Enable console logging (true/false)
    REDACT_PII         - Redact phone numbers, emails, etc. (true/false)
"""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class LoggingSettings(BaseSettings):
    """Logging configuration with sensible defaults."""
    
    # Log level
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # File paths
    LOG_DIR: str = Field(
        default="logs",
        description="Directory for log files (relative to project root)"
    )
    
    LOG_FILE_NAME: str = Field(
        default="app.json",
        description="Name of the JSON log file"
    )
    
    # Rotation settings
    LOG_ROTATION: str = Field(
        default="10 MB",
        description="When to rotate log files (e.g., '10 MB', '1 day', '100 KB')"
    )
    
    LOG_RETENTION: int = Field(
        default=5,
        description="Number of rotated log files to keep"
    )
    
    # Format settings
    LOG_FORMAT_CONSOLE: str = Field(
        default=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        description="Console log format (loguru format string)"
    )
    
    # Feature toggles
    ENABLE_JSON_LOGS: bool = Field(
        default=True,
        description="Enable JSON file logging for log aggregation"
    )
    
    ENABLE_CONSOLE_LOGS: bool = Field(
        default=True,
        description="Enable console/stderr logging"
    )
    
    REDACT_PII: bool = Field(
        default=True,
        description="Redact phone numbers, emails, and other PII from logs"
    )
    
    # Advanced settings
    BACKTRACE: bool = Field(
        default=True,
        description="Include full traceback in exception logs"
    )
    
    DIAGNOSE: bool = Field(
        default=True,
        description="Include variable values in exception tracebacks (disable in production for security)"
    )
    
    COMPRESSION: str = Field(
        default="gz",
        description="Compression format for rotated logs (gz, bz2, xz, or empty for none)"
    )
    
    class Config:
        env_prefix = ""
        case_sensitive = True
        extra = "ignore"


# Singleton instance
_settings: Optional[LoggingSettings] = None


def get_logging_settings() -> LoggingSettings:
    """Get the logging settings singleton."""
    global _settings
    if _settings is None:
        _settings = LoggingSettings()
    return _settings


# Export settings for direct import
settings = get_logging_settings()


__all__ = [
    "LoggingSettings",
    "get_logging_settings",
    "settings",
]
