#!/bin/bash
#
# Database Backup Script
# ======================
# Creates timestamped PostgreSQL backups with 7-day retention.
#
# Usage:
#   ./backup_db.sh                    # Backup using Docker container
#   ./backup_db.sh --direct           # Backup using local pg_dump
#
# Cron example (daily at 2 AM):
#   0 2 * * * /path/to/scripts/backup_db.sh >> /path/to/logs/backup_cron.log 2>&1
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Directory paths (relative to script location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
LOG_FILE="${PROJECT_ROOT}/logs/backup.log"

# Database configuration (can be overridden by environment variables)
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-whatsapp_bot}"
DB_USER="${POSTGRES_USER:-postgres}"

# Docker configuration
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER_NAME:-whatsapp-bot-postgres-1}"

# Retention policy
RETENTION_DAYS=7

# Timestamp for backup filename
TIMESTAMP=$(date +"%Y_%m_%d_%H%M%S")
BACKUP_FILENAME="backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"

# ============================================================================
# FUNCTIONS
# ============================================================================

log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "$1"
}

log_error() {
    log "ERROR" "$1"
}

log_success() {
    log "SUCCESS" "$1"
}

ensure_directories() {
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "$(dirname "${LOG_FILE}")"
}

backup_via_docker() {
    log_info "Running backup via Docker container: ${POSTGRES_CONTAINER}"
    
    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
        # Try common container name patterns
        POSTGRES_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E 'postgres|db' | head -1)
        if [ -z "${POSTGRES_CONTAINER}" ]; then
            log_error "PostgreSQL container not found. Available containers:"
            docker ps --format '{{.Names}}' | tee -a "${LOG_FILE}"
            return 1
        fi
        log_info "Using detected container: ${POSTGRES_CONTAINER}"
    fi
    
    # Run pg_dump inside container and pipe to gzip
    docker exec "${POSTGRES_CONTAINER}" pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        2>> "${LOG_FILE}" | gzip > "${BACKUP_PATH}"
    
    return ${PIPESTATUS[0]}
}

backup_via_docker_compose() {
    log_info "Running backup via docker-compose exec"
    
    if [ ! -f "${DOCKER_COMPOSE_FILE}" ]; then
        log_error "docker-compose.yml not found at ${DOCKER_COMPOSE_FILE}"
        return 1
    fi
    
    cd "${PROJECT_ROOT}"
    
    docker-compose exec -T postgres pg_dump \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        2>> "${LOG_FILE}" | gzip > "${BACKUP_PATH}"
    
    return ${PIPESTATUS[0]}
}

backup_direct() {
    log_info "Running backup via direct pg_dump connection"
    
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        2>> "${LOG_FILE}" | gzip > "${BACKUP_PATH}"
    
    return ${PIPESTATUS[0]}
}

verify_backup() {
    if [ ! -f "${BACKUP_PATH}" ]; then
        log_error "Backup file not created: ${BACKUP_PATH}"
        return 1
    fi
    
    local size
    size=$(stat -f%z "${BACKUP_PATH}" 2>/dev/null || stat -c%s "${BACKUP_PATH}" 2>/dev/null)
    
    if [ "${size}" -lt 100 ]; then
        log_error "Backup file too small (${size} bytes). Backup likely failed."
        rm -f "${BACKUP_PATH}"
        return 1
    fi
    
    # Test gzip integrity
    if ! gzip -t "${BACKUP_PATH}" 2>/dev/null; then
        log_error "Backup file is corrupted (gzip test failed)"
        rm -f "${BACKUP_PATH}"
        return 1
    fi
    
    log_success "Backup verified: ${BACKUP_FILENAME} (${size} bytes)"
    return 0
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    local deleted_count
    deleted_count=$(find "${BACKUP_DIR}" -name "backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -print -delete 2>/dev/null | wc -l)
    
    if [ "${deleted_count}" -gt 0 ]; then
        log_info "Deleted ${deleted_count} old backup(s)"
    else
        log_info "No old backups to delete"
    fi
    
    # Show current backup count
    local current_count
    current_count=$(find "${BACKUP_DIR}" -name "backup_*.sql.gz" -type f | wc -l)
    log_info "Current backup count: ${current_count}"
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --direct       Use direct pg_dump connection instead of Docker"
    echo "  --compose      Use docker-compose exec instead of docker exec"
    echo "  --help         Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  POSTGRES_HOST              Database host (default: localhost)"
    echo "  POSTGRES_PORT              Database port (default: 5432)"
    echo "  POSTGRES_DB                Database name (default: whatsapp_bot)"
    echo "  POSTGRES_USER              Database user (default: postgres)"
    echo "  POSTGRES_PASSWORD          Database password (for --direct mode)"
    echo "  POSTGRES_CONTAINER_NAME    Docker container name"
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    local mode="docker"
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --direct)
                mode="direct"
                shift
                ;;
            --compose)
                mode="compose"
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log_info "========================================="
    log_info "Starting database backup..."
    log_info "Mode: ${mode}"
    log_info "Target: ${BACKUP_PATH}"
    log_info "========================================="
    
    # Ensure directories exist
    ensure_directories
    
    # Run backup based on mode
    local backup_status=0
    case ${mode} in
        docker)
            backup_via_docker || backup_status=$?
            ;;
        compose)
            backup_via_docker_compose || backup_status=$?
            ;;
        direct)
            backup_direct || backup_status=$?
            ;;
    esac
    
    if [ ${backup_status} -ne 0 ]; then
        log_error "Backup command failed with exit code: ${backup_status}"
        rm -f "${BACKUP_PATH}" 2>/dev/null
        exit 1
    fi
    
    # Verify backup
    if ! verify_backup; then
        exit 1
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    log_success "========================================="
    log_success "Backup completed successfully!"
    log_success "File: ${BACKUP_FILENAME}"
    log_success "========================================="
}

main "$@"
