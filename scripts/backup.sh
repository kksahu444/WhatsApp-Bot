#!/bin/bash
# Backup script for WhatsApp Seller Bot
# Usage: ./backup.sh [backup_dir]

set -e

BACKUP_DIR=${1:-./backups}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="backup_$TIMESTAMP"

echo "=========================================="
echo "WhatsApp Seller Bot Backup"
echo "Backup Directory: $BACKUP_DIR"
echo "=========================================="

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup Redis
echo "Backing up Redis..."
docker exec redis redis-cli BGSAVE
sleep 2
docker cp redis:/data/dump.rdb "$BACKUP_DIR/$BACKUP_NAME/redis_dump.rdb"

# Backup LanceDB data
echo "Backing up LanceDB..."
if [ -d "./data/lancedb" ]; then
    cp -r ./data/lancedb "$BACKUP_DIR/$BACKUP_NAME/"
fi

# Backup configuration
echo "Backing up configuration..."
cp .env "$BACKUP_DIR/$BACKUP_NAME/.env.backup" 2>/dev/null || true
cp docker-compose.yml "$BACKUP_DIR/$BACKUP_NAME/"

# Backup WhatsApp sessions
echo "Backing up WhatsApp sessions..."
if [ -d "./bot/sessions" ]; then
    cp -r ./bot/sessions "$BACKUP_DIR/$BACKUP_NAME/"
fi

# Create archive
echo "Creating archive..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

echo ""
echo "Backup complete: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
echo ""

# Cleanup old backups (keep last 7)
echo "Cleaning up old backups..."
ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm

echo "Done!"
