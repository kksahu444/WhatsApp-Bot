#!/bin/bash
set -e

#############################################
# Deploy WhatsApp Bot to AWS EC2
#############################################

echo "============================================"
echo "  WhatsApp Bot - Application Deployment"
echo "============================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

#############################################
# Argument Validation
#############################################
if [ $# -ne 3 ]; then
    echo -e "${RED}Usage: $0 <ELASTIC_IP> <KEY_PEM> <DOMAIN_NAME>${NC}"
    echo ""
    echo "Example:"
    echo "  $0 13.232.xx.xx whatsapp-bot-key.pem my-bot.duckdns.org"
    echo ""
    exit 1
fi

ELASTIC_IP=$1
KEY_FILE=$2
DOMAIN_NAME=$3

echo "Elastic IP:  $ELASTIC_IP"
echo "Key File:    $KEY_FILE"
echo "Domain:      $DOMAIN_NAME"

#############################################
# Pre-flight Checks
#############################################
echo -e "\n${YELLOW}[Step 1] Running pre-flight checks...${NC}"

# Check key file exists
if [ ! -f "$KEY_FILE" ]; then
    echo -e "${RED}ERROR: Key file not found: $KEY_FILE${NC}"
    exit 1
fi

# Check .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found in current directory${NC}"
    echo "Copy .env.example to .env and fill in your values"
    exit 1
fi

# Check key permissions
KEY_PERMS=$(stat -c %a "$KEY_FILE" 2>/dev/null || stat -f %Lp "$KEY_FILE" 2>/dev/null)
if [ "$KEY_PERMS" != "400" ]; then
    echo "Fixing key file permissions..."
    chmod 400 "$KEY_FILE"
fi

echo -e "${GREEN}All checks passed${NC}"

#############################################
# Wait for Instance Bootstrap
#############################################
echo -e "\n${YELLOW}[Step 2] Checking instance readiness...${NC}"

SSH_CMD="ssh -i $KEY_FILE -o StrictHostKeyChecking=no -o ConnectTimeout=10 ec2-user@$ELASTIC_IP"

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if $SSH_CMD "echo 'SSH OK'" 2>/dev/null; then
        echo -e "${GREEN}Instance is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for instance... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 10
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}ERROR: Could not connect to instance${NC}"
    exit 1
fi

# Check if Docker is ready
echo "Checking Docker..."
MAX_RETRIES=12
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if $SSH_CMD "docker --version" 2>/dev/null; then
        echo -e "${GREEN}Docker is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for Docker... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 10
done

#############################################
# Sync Application Files
#############################################
echo -e "\n${YELLOW}[Step 3] Syncing application files...${NC}"

REMOTE_DIR="/home/ec2-user/whatsapp-bot"

# Create deploy directory structure
mkdir -p deploy/temp

# Copy necessary files to temp
cp -r backend deploy/temp/
cp deploy/docker-compose.yml deploy/temp/
cp deploy/Dockerfile deploy/temp/
cp .env deploy/temp/
cp requirements.txt deploy/temp/ 2>/dev/null || echo "requirements.txt will be created"

# Create requirements.txt if missing
if [ ! -f "deploy/temp/requirements.txt" ]; then
    cat > deploy/temp/requirements.txt << 'REQUIREMENTS'
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-dotenv>=1.0.0
httpx>=0.25.0
loguru>=0.7.0
redis>=5.0.0
supabase>=2.0.0
google-generativeai>=0.3.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
lancedb>=0.3.0
sentence-transformers>=2.2.0
slowapi>=0.1.9
REQUIREMENTS
fi

# Rsync to EC2
echo "Uploading files..."
rsync -avz --progress \
    -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
    deploy/temp/ \
    ec2-user@$ELASTIC_IP:$REMOTE_DIR/

# Cleanup temp
rm -rf deploy/temp

echo -e "${GREEN}Files synced successfully${NC}"

#############################################
# Generate Caddyfile
#############################################
echo -e "\n${YELLOW}[Step 4] Generating Caddyfile for HTTPS...${NC}"

$SSH_CMD << CADDYFILE
cat > $REMOTE_DIR/Caddyfile << 'EOF'
$DOMAIN_NAME {
    reverse_proxy app:8000
    
    log {
        output file /var/log/caddy/access.log
        format json
    }
    
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
    }
}
EOF
echo "Caddyfile created for $DOMAIN_NAME"
CADDYFILE

echo -e "${GREEN}Caddyfile generated${NC}"

#############################################
# Deploy with Docker Compose
#############################################
echo -e "\n${YELLOW}[Step 5] Deploying application...${NC}"

$SSH_CMD << 'DEPLOY'
cd /home/ec2-user/whatsapp-bot

# Show swap status
echo "=== Memory Status ==="
free -h
swapon --show

# Stop existing containers
echo "=== Stopping existing containers ==="
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true

# Remove old images to free space
echo "=== Cleaning up old images ==="
docker system prune -f

# Build and start
echo "=== Building and starting containers ==="
docker compose up -d --build 2>/dev/null || docker-compose up -d --build

# Wait for containers to start
echo "=== Waiting for containers to start ==="
sleep 10

# Show status
echo "=== Container Status ==="
docker compose ps 2>/dev/null || docker-compose ps

echo "=== Container Logs (last 50 lines) ==="
docker compose logs --tail=50 2>/dev/null || docker-compose logs --tail=50
DEPLOY

echo -e "${GREEN}Application deployed${NC}"

#############################################
# Create Monitor Script
#############################################
echo -e "\n${YELLOW}[Step 6] Creating health monitor script...${NC}"

$SSH_CMD << 'MONITOR'
cat > /home/ec2-user/whatsapp-bot/monitor.sh << 'SCRIPT'
#!/bin/bash
#############################################
# Health Monitor for WhatsApp Bot
# Restarts containers if unhealthy
#############################################

LOG_FILE="/home/ec2-user/whatsapp-bot/monitor.log"
FAIL_COUNT=0
MAX_FAILS=3

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

check_health() {
    # Try localhost first (Caddy handles HTTPS)
    if curl -sf -k https://localhost/health > /dev/null 2>&1; then
        return 0
    fi
    
    # Try the app container directly
    APP_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' whatsapp-bot-app-1 2>/dev/null)
    if [ -n "$APP_IP" ]; then
        if curl -sf "http://$APP_IP:8000/health" > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    return 1
}

# Main loop
while true; do
    if check_health; then
        if [ $FAIL_COUNT -gt 0 ]; then
            log "Health check recovered after $FAIL_COUNT failures"
        fi
        FAIL_COUNT=0
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        log "Health check failed ($FAIL_COUNT/$MAX_FAILS)"
        
        if [ $FAIL_COUNT -ge $MAX_FAILS ]; then
            log "Max failures reached, restarting containers..."
            cd /home/ec2-user/whatsapp-bot
            docker compose restart 2>/dev/null || docker-compose restart
            FAIL_COUNT=0
            log "Containers restarted"
            sleep 30
        fi
    fi
    
    sleep 60
done
SCRIPT

chmod +x /home/ec2-user/whatsapp-bot/monitor.sh

# Create systemd service for monitor
sudo tee /etc/systemd/system/whatsapp-monitor.service > /dev/null << 'SERVICE'
[Unit]
Description=WhatsApp Bot Health Monitor
After=docker.service

[Service]
Type=simple
User=ec2-user
ExecStart=/home/ec2-user/whatsapp-bot/monitor.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable whatsapp-monitor
sudo systemctl start whatsapp-monitor

echo "Monitor service installed and started"
MONITOR

echo -e "${GREEN}Health monitor installed${NC}"

#############################################
# Final Status
#############################################
echo ""
echo "============================================"
echo -e "${GREEN}  DEPLOYMENT COMPLETE${NC}"
echo "============================================"
echo ""
echo "Domain:      https://$DOMAIN_NAME"
echo "Webhook:     https://$DOMAIN_NAME/whatsapp/webhook"
echo "Health:      https://$DOMAIN_NAME/health"
echo ""
echo "============================================"
echo "  NEXT STEPS"
echo "============================================"
echo ""
echo "1. Point your domain to: $ELASTIC_IP"
echo "   (DuckDNS: Update the IP in your account)"
echo ""
echo "2. Wait 1-2 minutes for Caddy to get SSL certificate"
echo ""
echo "3. Configure Meta Webhook:"
echo "   Callback URL: https://$DOMAIN_NAME/whatsapp/webhook"
echo "   Verify Token: (from your .env WHATSAPP_VERIFY_TOKEN)"
echo ""
echo "4. Check logs:"
echo "   ssh -i $KEY_FILE ec2-user@$ELASTIC_IP"
echo "   cd whatsapp-bot && docker compose logs -f"
echo ""
echo "============================================"
