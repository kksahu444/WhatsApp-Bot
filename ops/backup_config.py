# Ops Configuration: Backup
# Centralized backup configuration for the WhatsApp Seller Bot

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
from enum import Enum


class BackupType(str, Enum):
    """Backup types."""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class StorageBackend(str, Enum):
    """Backup storage backends."""
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"


@dataclass
class RetentionPolicy:
    """Backup retention policy."""
    daily_backups: int = 7  # Keep last 7 daily backups
    weekly_backups: int = 4  # Keep last 4 weekly backups
    monthly_backups: int = 6  # Keep last 6 monthly backups
    
    def should_delete(self, backup_date: datetime) -> bool:
        """Check if a backup should be deleted based on retention policy."""
        now = datetime.utcnow()
        age_days = (now - backup_date).days
        
        # Keep all backups less than daily_backups days old
        if age_days < self.daily_backups:
            return False
        
        # Keep weekly backups for weekly_backups weeks
        if age_days < self.weekly_backups * 7 and backup_date.weekday() == 0:
            return False
        
        # Keep monthly backups for monthly_backups months
        if age_days < self.monthly_backups * 30 and backup_date.day == 1:
            return False
        
        return True


@dataclass
class BackupTarget:
    """Backup target configuration."""
    name: str
    source_type: str  # postgres, redis, files
    enabled: bool = True
    
    # PostgreSQL settings
    pg_host: Optional[str] = None
    pg_port: int = 5432
    pg_database: Optional[str] = None
    pg_user: Optional[str] = None
    pg_password: Optional[str] = None
    
    # Redis settings
    redis_host: Optional[str] = None
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # File backup settings
    source_paths: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class BackupConfig:
    """Main backup configuration."""
    # General settings
    enabled: bool = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
    backup_type: BackupType = BackupType(os.getenv("BACKUP_TYPE", "full"))
    
    # Schedule (cron format)
    schedule_cron: str = os.getenv("BACKUP_SCHEDULE", "0 2 * * *")  # 2 AM daily
    
    # Storage settings
    storage_backend: StorageBackend = StorageBackend(os.getenv("BACKUP_STORAGE", "local"))
    local_backup_path: str = os.getenv("BACKUP_LOCAL_PATH", "/var/backups/whatsapp-bot")
    
    # S3 settings
    s3_bucket: str = os.getenv("BACKUP_S3_BUCKET", "")
    s3_prefix: str = os.getenv("BACKUP_S3_PREFIX", "whatsapp-bot/backups")
    s3_region: str = os.getenv("BACKUP_S3_REGION", "us-east-1")
    s3_access_key: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    s3_secret_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    
    # GCS settings
    gcs_bucket: str = os.getenv("BACKUP_GCS_BUCKET", "")
    gcs_prefix: str = os.getenv("BACKUP_GCS_PREFIX", "whatsapp-bot/backups")
    gcs_credentials_path: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    # Compression
    compression_enabled: bool = True
    compression_level: int = 6  # gzip compression level (1-9)
    
    # Encryption
    encryption_enabled: bool = os.getenv("BACKUP_ENCRYPTION", "true").lower() == "true"
    encryption_key: str = os.getenv("BACKUP_ENCRYPTION_KEY", "")
    
    # Retention
    retention_policy: RetentionPolicy = field(default_factory=RetentionPolicy)
    
    # Notification
    notify_on_success: bool = True
    notify_on_failure: bool = True
    notification_email: str = os.getenv("BACKUP_NOTIFICATION_EMAIL", "")
    slack_webhook: str = os.getenv("BACKUP_SLACK_WEBHOOK", "")
    
    # Backup targets
    @property
    def targets(self) -> List[BackupTarget]:
        return [
            BackupTarget(
                name="supabase_postgres",
                source_type="postgres",
                enabled=True,
                pg_host=os.getenv("SUPABASE_DB_HOST", "db.supabase.co"),
                pg_port=int(os.getenv("SUPABASE_DB_PORT", "5432")),
                pg_database=os.getenv("SUPABASE_DB_NAME", "postgres"),
                pg_user=os.getenv("SUPABASE_DB_USER", "postgres"),
                pg_password=os.getenv("SUPABASE_DB_PASSWORD", ""),
            ),
            BackupTarget(
                name="redis_cache",
                source_type="redis",
                enabled=True,
                redis_host=os.getenv("REDIS_HOST", "localhost"),
                redis_port=int(os.getenv("REDIS_PORT", "6379")),
                redis_password=os.getenv("REDIS_PASSWORD"),
            ),
            BackupTarget(
                name="app_data",
                source_type="files",
                enabled=True,
                source_paths=[
                    "/app/data/embeddings",
                    "/app/data/products",
                    "/app/data/sessions",
                ],
                exclude_patterns=[
                    "*.tmp",
                    "*.log",
                    "__pycache__",
                    "*.pyc",
                ],
            ),
        ]


def get_backup_filename(target_name: str, backup_type: BackupType) -> str:
    """Generate a backup filename with timestamp."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{target_name}_{backup_type.value}_{timestamp}.tar.gz"


def get_backup_config() -> BackupConfig:
    """Get backup configuration instance."""
    return BackupConfig()


# Backup scripts templates
POSTGRES_BACKUP_SCRIPT = """
#!/bin/bash
# PostgreSQL backup script
set -e

BACKUP_FILE=$1
PG_HOST=$2
PG_PORT=$3
PG_DATABASE=$4
PG_USER=$5

export PGPASSWORD="${BACKUP_PG_PASSWORD}"

pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DATABASE" \
    --format=custom \
    --compress=6 \
    --no-owner \
    --no-acl \
    > "$BACKUP_FILE"

echo "PostgreSQL backup completed: $BACKUP_FILE"
"""

REDIS_BACKUP_SCRIPT = """
#!/bin/bash
# Redis backup script
set -e

BACKUP_FILE=$1
REDIS_HOST=$2
REDIS_PORT=$3

redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --rdb "$BACKUP_FILE"

echo "Redis backup completed: $BACKUP_FILE"
"""

FILES_BACKUP_SCRIPT = """
#!/bin/bash
# Files backup script
set -e

BACKUP_FILE=$1
SOURCE_PATHS=$2
EXCLUDE_PATTERNS=$3

tar -czf "$BACKUP_FILE" $SOURCE_PATHS $EXCLUDE_PATTERNS

echo "Files backup completed: $BACKUP_FILE"
"""
