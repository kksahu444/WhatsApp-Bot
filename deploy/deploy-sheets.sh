#!/bin/bash
# ============================================
# Google Sheets Deployment Script
# Uploads service_account.json and restarts app
# ============================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default values
EC2_USER="ec2-user"
REMOTE_PATH="/home/ec2-user/whatsapp-bot"

# Check arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    echo -e "${RED}Usage: ./deploy-sheets.sh <EC2_IP> <path-to-service_account.json>${NC}"
    echo ""
    echo "Example:"
    echo "  ./deploy-sheets.sh 3.14.159.26 ~/Downloads/service_account.json"
    echo ""
    echo "Prerequisites:"
    echo "  1. Download service_account.json from Google Cloud Console"
    echo "  2. Share your Google Sheet with the service account email"
    echo ""
    exit 1
fi

EC2_IP="$1"
SERVICE_ACCOUNT_FILE="$2"

# Validate file exists
if [ ! -f "$SERVICE_ACCOUNT_FILE" ]; then
    echo -e "${RED}❌ File not found: $SERVICE_ACCOUNT_FILE${NC}"
    exit 1
fi

# Validate JSON
if ! python3 -c "import json; json.load(open('$SERVICE_ACCOUNT_FILE'))" 2>/dev/null; then
    echo -e "${RED}❌ Invalid JSON file: $SERVICE_ACCOUNT_FILE${NC}"
    exit 1
fi

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Google Sheets Deployment${NC}"
echo -e "${GREEN}============================================${NC}"

# Extract service account email for display
SERVICE_EMAIL=$(python3 -c "import json; print(json.load(open('$SERVICE_ACCOUNT_FILE'))['client_email'])")
echo -e "${YELLOW}📧 Service Account: ${SERVICE_EMAIL}${NC}"
echo ""

# Upload service_account.json
echo -e "${YELLOW}📤 Uploading service_account.json to EC2...${NC}"
scp -o StrictHostKeyChecking=no "$SERVICE_ACCOUNT_FILE" "${EC2_USER}@${EC2_IP}:${REMOTE_PATH}/service_account.json"

# Set permissions
echo -e "${YELLOW}🔒 Setting secure permissions...${NC}"
ssh -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" "chmod 600 ${REMOTE_PATH}/service_account.json"

# Restart application to pick up new mount
echo -e "${YELLOW}🔄 Restarting application...${NC}"
ssh -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" "cd ${REMOTE_PATH} && docker compose restart app"

# Wait for app to be healthy
echo -e "${YELLOW}⏳ Waiting for app to be healthy...${NC}"
sleep 10

# Check health
HEALTH_STATUS=$(ssh -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" "curl -s http://localhost:8000/health | grep -o 'healthy' || echo 'unhealthy'")

if [ "$HEALTH_STATUS" == "healthy" ]; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
else
    echo -e "${RED}❌ Health check failed. Checking logs...${NC}"
    ssh -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" "docker logs whatsapp-bot-app --tail 50"
    exit 1
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Google Sheets Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Make sure your Google Sheet is shared with:${NC}"
echo -e "${GREEN}  ${SERVICE_EMAIL}${NC}"
echo ""
echo "Sheet Requirements:"
echo "  • Spreadsheet Name: SmartShop_Data"
echo "  • Worksheet Name: Orders"
echo "  • Headers Row: Order ID | Date | Customer | Items | Amount | Status | Timestamp"
echo ""
