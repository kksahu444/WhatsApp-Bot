#!/bin/bash
#
# Health Check Monitor
# ====================
# Monitors the WhatsApp Bot health endpoint and auto-restarts on failures.
#
# Usage:
#   ./monitor.sh                    # Run in foreground
#   ./monitor.sh --daemon           # Run as background daemon
#   ./monitor.sh --stop             # Stop the daemon
#
# Systemd service example:
#   See deploy/monitor.service for systemd integration
#

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Directory paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${PROJECT_ROOT}/logs/monitor.log"
PID_FILE="${PROJECT_ROOT}/logs/monitor.pid"

# Health check configuration
HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"          # Seconds between checks
TIMEOUT="${TIMEOUT:-5}"                          # Request timeout in seconds
MAX_FAILURES="${MAX_FAILURES:-3}"                # Failures before restart

# Docker configuration
DOCKER_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
APP_SERVICE_NAME="${APP_SERVICE_NAME:-backend}"

# WhatsApp alert configuration (optional)
ADMIN_PHONE="${ADMIN_PHONE:-}"
WHATSAPP_API_URL="${WHATSAPP_API_URL:-http://localhost:3000/send}"

# ============================================================================
# GLOBAL STATE
# ============================================================================

FAILURE_COUNT=0
RUNNING=true

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

log_warn() {
    log "WARN" "$1"
}

log_error() {
    log "ERROR" "$1"
}

log_critical() {
    log "CRITICAL" "$1"
}

ensure_directories() {
    mkdir -p "$(dirname "${LOG_FILE}")"
}

send_whatsapp_alert() {
    local message="$1"
    
    if [ -z "${ADMIN_PHONE}" ]; then
        log_info "WhatsApp alert skipped (ADMIN_PHONE not set)"
        return 0
    fi
    
    log_info "Sending WhatsApp alert to ${ADMIN_PHONE}..."
    
    # Try to send via WhatsApp API
    local response
    response=$(curl -s -X POST "${WHATSAPP_API_URL}" \
        -H "Content-Type: application/json" \
        -d "{\"phone\": \"${ADMIN_PHONE}\", \"message\": \"${message}\"}" \
        --max-time 10 2>/dev/null || echo "FAILED")
    
    if [ "${response}" = "FAILED" ]; then
        log_warn "WhatsApp alert failed to send"
    else
        log_info "WhatsApp alert sent successfully"
    fi
}

check_health() {
    local response
    local http_code
    
    # Make health check request
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time "${TIMEOUT}" \
        "${HEALTH_URL}" 2>/dev/null || echo "000")
    
    if [ "${response}" = "200" ]; then
        return 0
    else
        return 1
    fi
}

restart_service() {
    log_warn "Initiating service restart..."
    
    cd "${PROJECT_ROOT}"
    
    # Try docker-compose restart first
    if [ -f "${DOCKER_COMPOSE_FILE}" ]; then
        log_info "Running: docker-compose restart ${APP_SERVICE_NAME}"
        
        if docker-compose restart "${APP_SERVICE_NAME}" >> "${LOG_FILE}" 2>&1; then
            log_info "Service restarted successfully via docker-compose"
            return 0
        else
            log_error "docker-compose restart failed"
        fi
    fi
    
    # Fallback: try docker restart directly
    local container_name
    container_name=$(docker ps --filter "name=${APP_SERVICE_NAME}" --format "{{.Names}}" | head -1)
    
    if [ -n "${container_name}" ]; then
        log_info "Running: docker restart ${container_name}"
        
        if docker restart "${container_name}" >> "${LOG_FILE}" 2>&1; then
            log_info "Service restarted successfully via docker"
            return 0
        else
            log_error "docker restart failed"
        fi
    fi
    
    log_error "Could not restart service - no matching container found"
    return 1
}

handle_failure() {
    FAILURE_COUNT=$((FAILURE_COUNT + 1))
    log_warn "Health check failed (${FAILURE_COUNT}/${MAX_FAILURES})"
    
    if [ "${FAILURE_COUNT}" -ge "${MAX_FAILURES}" ]; then
        log_critical "========================================="
        log_critical "CRITICAL: ${MAX_FAILURES} consecutive failures detected!"
        log_critical "Restarting Bot Service..."
        log_critical "========================================="
        
        # Send alert
        send_whatsapp_alert "🚨 ALERT: WhatsApp Bot service unresponsive! Auto-restarting... (${MAX_FAILURES} failures)"
        
        # Restart service
        if restart_service; then
            # Wait for service to come up
            log_info "Waiting 30 seconds for service to initialize..."
            sleep 30
            
            # Verify restart was successful
            if check_health; then
                log_info "Service recovered successfully after restart"
                send_whatsapp_alert "✅ WhatsApp Bot service recovered and is now healthy."
            else
                log_critical "Service still unhealthy after restart!"
                send_whatsapp_alert "❌ WhatsApp Bot service failed to recover after restart. Manual intervention required!"
            fi
        else
            log_critical "Failed to restart service!"
            send_whatsapp_alert "❌ Failed to restart WhatsApp Bot service. Manual intervention required!"
        fi
        
        # Reset failure counter
        FAILURE_COUNT=0
    fi
}

handle_success() {
    if [ "${FAILURE_COUNT}" -gt 0 ]; then
        log_info "Health check passed (resetting failure count from ${FAILURE_COUNT})"
        FAILURE_COUNT=0
    fi
}

cleanup() {
    RUNNING=false
    log_info "Monitor shutting down..."
    rm -f "${PID_FILE}"
    exit 0
}

start_daemon() {
    if [ -f "${PID_FILE}" ]; then
        local existing_pid
        existing_pid=$(cat "${PID_FILE}")
        if kill -0 "${existing_pid}" 2>/dev/null; then
            echo "Monitor already running (PID: ${existing_pid})"
            exit 1
        fi
        rm -f "${PID_FILE}"
    fi
    
    echo "Starting monitor daemon..."
    nohup "$0" >> "${LOG_FILE}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${PID_FILE}"
    echo "Monitor started (PID: ${pid})"
    echo "Logs: ${LOG_FILE}"
}

stop_daemon() {
    if [ ! -f "${PID_FILE}" ]; then
        echo "Monitor not running (no PID file)"
        exit 0
    fi
    
    local pid
    pid=$(cat "${PID_FILE}")
    
    if kill -0 "${pid}" 2>/dev/null; then
        echo "Stopping monitor (PID: ${pid})..."
        kill "${pid}"
        rm -f "${PID_FILE}"
        echo "Monitor stopped"
    else
        echo "Monitor not running (stale PID file)"
        rm -f "${PID_FILE}"
    fi
}

show_status() {
    if [ -f "${PID_FILE}" ]; then
        local pid
        pid=$(cat "${PID_FILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            echo "Monitor is running (PID: ${pid})"
            echo ""
            echo "Recent logs:"
            tail -20 "${LOG_FILE}" 2>/dev/null || echo "(no logs)"
        else
            echo "Monitor not running (stale PID file)"
        fi
    else
        echo "Monitor not running"
    fi
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --daemon       Run as background daemon"
    echo "  --stop         Stop the daemon"
    echo "  --status       Show daemon status"
    echo "  --help         Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  HEALTH_URL         Health check URL (default: http://localhost:8000/health)"
    echo "  CHECK_INTERVAL     Seconds between checks (default: 60)"
    echo "  TIMEOUT            Request timeout in seconds (default: 5)"
    echo "  MAX_FAILURES       Failures before restart (default: 3)"
    echo "  APP_SERVICE_NAME   Docker service name (default: backend)"
    echo "  ADMIN_PHONE        WhatsApp number for alerts (optional)"
}

run_monitor() {
    log_info "========================================="
    log_info "Health Monitor Started"
    log_info "URL: ${HEALTH_URL}"
    log_info "Interval: ${CHECK_INTERVAL}s"
    log_info "Timeout: ${TIMEOUT}s"
    log_info "Max Failures: ${MAX_FAILURES}"
    log_info "========================================="
    
    # Set up signal handlers
    trap cleanup SIGTERM SIGINT
    
    # Main monitoring loop
    while ${RUNNING}; do
        if check_health; then
            handle_success
        else
            handle_failure
        fi
        
        # Sleep with ability to be interrupted
        sleep "${CHECK_INTERVAL}" &
        wait $! 2>/dev/null || true
    done
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    ensure_directories
    
    # Parse arguments
    case "${1:-}" in
        --daemon)
            start_daemon
            exit 0
            ;;
        --stop)
            stop_daemon
            exit 0
            ;;
        --status)
            show_status
            exit 0
            ;;
        --help)
            show_usage
            exit 0
            ;;
        "")
            # Run in foreground
            run_monitor
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
