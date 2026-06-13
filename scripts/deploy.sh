#!/bin/bash
# Deploy script for WhatsApp Seller Bot
# Usage: ./deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "WhatsApp Seller Bot Deployment"
echo "Environment: $ENVIRONMENT"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Check environment file
check_env() {
    log_info "Checking environment configuration..."
    
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log_error ".env file not found"
        log_info "Copy .env.example to .env and configure it"
        exit 1
    fi
    
    # Check required variables
    source "$PROJECT_DIR/.env"
    
    if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
        log_error "Supabase credentials not configured"
        exit 1
    fi
    
    log_info "Environment check passed"
}

# Pull latest images
pull_images() {
    log_info "Pulling latest images..."
    cd "$PROJECT_DIR"
    docker compose pull
}

# Build services
build_services() {
    log_info "Building services..."
    cd "$PROJECT_DIR"
    docker compose build --no-cache
}

# Deploy services
deploy() {
    log_info "Deploying services..."
    cd "$PROJECT_DIR"
    
    # Stop existing services
    docker compose down --remove-orphans
    
    # Start services
    docker compose up -d
    
    log_info "Waiting for services to start..."
    sleep 10
}

# Health check
health_check() {
    log_info "Running health checks..."
    
    # Check backend
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        log_info "Backend: Healthy ✓"
    else
        log_warn "Backend: Not responding"
    fi
    
    # Check bot
    if curl -s http://localhost:3000/health | grep -q "healthy"; then
        log_info "Bot: Healthy ✓"
    else
        log_warn "Bot: Not responding"
    fi
    
    # Check dashboard
    if curl -s http://localhost:8501/_stcore/health | grep -q "ok"; then
        log_info "Dashboard: Healthy ✓"
    else
        log_warn "Dashboard: Not responding"
    fi
}

# Show status
show_status() {
    log_info "Service Status:"
    docker compose ps
}

# Main
main() {
    check_prerequisites
    check_env
    
    if [ "$ENVIRONMENT" == "production" ]; then
        pull_images
    fi
    
    build_services
    deploy
    health_check
    show_status
    
    echo ""
    log_info "Deployment complete!"
    echo ""
    echo "Access points:"
    echo "  - Dashboard: http://localhost:8501"
    echo "  - API: http://localhost:8000"
    echo "  - Bot: http://localhost:3000"
    echo ""
}

main
