#!/bin/bash
set -e

#############################################
# AWS Infrastructure Setup for WhatsApp Bot
# Region: ap-south-1 (Mumbai)
# Instance: t2.micro (Free Tier)
#############################################

echo "============================================"
echo "  WhatsApp Bot - AWS Infrastructure Setup"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

#############################################
# STEP 0: Prerequisites Check
#############################################
echo -e "\n${YELLOW}[Step 0] Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI not installed${NC}"
    echo "Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check rsync
if ! command -v rsync &> /dev/null; then
    echo -e "${RED}ERROR: rsync not installed${NC}"
    echo "Install: sudo apt install rsync (Linux) or brew install rsync (Mac)"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

echo -e "${GREEN}All prerequisites met${NC}"

# Set region
export AWS_DEFAULT_REGION=ap-south-1
echo "Using region: $AWS_DEFAULT_REGION"

#############################################
# STEP 1: Create SSH Key Pair
#############################################
echo -e "\n${YELLOW}[Step 1] Setting up SSH Key Pair...${NC}"

KEY_NAME="whatsapp-bot-key"
KEY_FILE="${KEY_NAME}.pem"

if [ -f "$KEY_FILE" ]; then
    echo "Key file $KEY_FILE already exists locally"
else
    # Check if key exists in AWS
    if aws ec2 describe-key-pairs --key-names "$KEY_NAME" &> /dev/null; then
        echo -e "${RED}Key exists in AWS but not locally. Delete it first:${NC}"
        echo "aws ec2 delete-key-pair --key-name $KEY_NAME"
        exit 1
    fi
    
    # Create new key pair
    echo "Creating new key pair: $KEY_NAME"
    aws ec2 create-key-pair \
        --key-name "$KEY_NAME" \
        --query 'KeyMaterial' \
        --output text > "$KEY_FILE"
    
    # CRITICAL: Set permissions immediately
    chmod 400 "$KEY_FILE"
    echo -e "${GREEN}Key pair created and permissions set (chmod 400)${NC}"
fi

#############################################
# STEP 2: Network Setup (VPC & Security Group)
#############################################
echo -e "\n${YELLOW}[Step 2] Setting up network...${NC}"

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' \
    --output text)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo "Creating default VPC..."
    VPC_ID=$(aws ec2 create-default-vpc --query 'Vpc.VpcId' --output text)
fi
echo "Using VPC: $VPC_ID"

# Create or get Security Group
SG_NAME="whatsapp-bot-sg"
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

if [ "$SG_ID" == "None" ] || [ -z "$SG_ID" ]; then
    echo "Creating security group: $SG_NAME"
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SG_NAME" \
        --description "WhatsApp Bot - SSH, HTTP, HTTPS" \
        --vpc-id "$VPC_ID" \
        --query 'GroupId' \
        --output text)
    
    # Add inbound rules
    echo "Adding firewall rules..."
    
    # SSH (port 22)
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 2>/dev/null || true
    
    # HTTP (port 80)
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0 2>/dev/null || true
    
    # HTTPS (port 443)
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 2>/dev/null || true
    
    echo -e "${GREEN}Security group created with ports 22, 80, 443${NC}"
else
    echo "Using existing security group: $SG_ID"
fi

#############################################
# STEP 3: IAM Role for CloudWatch
#############################################
echo -e "\n${YELLOW}[Step 3] Setting up IAM Role...${NC}"

ROLE_NAME="EC2-CloudWatch-Role"
INSTANCE_PROFILE_NAME="EC2-CloudWatch-Profile"

# Check if role exists
if ! aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
    echo "Creating IAM role: $ROLE_NAME"
    
    # Trust policy for EC2
    cat > /tmp/trust-policy.json << 'TRUSTPOLICY'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
TRUSTPOLICY

    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "EC2 role for CloudWatch monitoring" > /dev/null
    
    # Attach CloudWatch policy
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
    
    rm /tmp/trust-policy.json
    echo -e "${GREEN}IAM role created${NC}"
else
    echo "IAM role already exists"
fi

# Create instance profile if needed
if ! aws iam get-instance-profile --instance-profile-name "$INSTANCE_PROFILE_NAME" &> /dev/null; then
    echo "Creating instance profile..."
    aws iam create-instance-profile \
        --instance-profile-name "$INSTANCE_PROFILE_NAME" > /dev/null
    
    aws iam add-role-to-instance-profile \
        --instance-profile-name "$INSTANCE_PROFILE_NAME" \
        --role-name "$ROLE_NAME"
    
    # Wait for propagation
    echo "Waiting for IAM propagation..."
    sleep 10
fi

#############################################
# STEP 4: User Data Script (Bootstrap)
#############################################
echo -e "\n${YELLOW}[Step 4] Preparing user data script...${NC}"

# Create user data script (CRITICAL: 2GB SWAP for t2.micro)
cat > /tmp/user-data.sh << 'USERDATA'
#!/bin/bash
set -e

# Log everything
exec > /var/log/user-data.log 2>&1

echo "=== Starting bootstrap ==="
date

# Update system
dnf update -y

# Install required packages
dnf install -y docker git curl

#############################################
# CRITICAL: Create 2GB SWAP (Prevents OOM)
#############################################
echo "Creating 2GB swap file..."
dd if=/dev/zero of=/swapfile bs=128M count=16
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Make swap permanent
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab

# Verify swap
echo "Swap enabled:"
swapon --show
free -h

#############################################
# Install Docker Compose
#############################################
echo "Installing Docker Compose..."
DOCKER_CONFIG=/usr/local/lib/docker
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

# Also install to /usr/local/bin for direct access
ln -sf $DOCKER_CONFIG/cli-plugins/docker-compose /usr/local/bin/docker-compose

# Verify
docker-compose version || echo "Docker compose installed as plugin"

#############################################
# Start Docker
#############################################
systemctl enable docker
systemctl start docker

# Add ec2-user to docker group
usermod -aG docker ec2-user

#############################################
# Create App Directories
#############################################
APP_DIR=/home/ec2-user/whatsapp-bot
mkdir -p $APP_DIR/data
mkdir -p $APP_DIR/redis-data
mkdir -p $APP_DIR/caddy-data
mkdir -p $APP_DIR/caddy-config
chown -R ec2-user:ec2-user $APP_DIR

echo "=== Bootstrap complete ==="
date
USERDATA

echo -e "${GREEN}User data script prepared${NC}"

#############################################
# STEP 5: Get Latest Amazon Linux 2023 AMI
#############################################
echo -e "\n${YELLOW}[Step 5] Finding latest Amazon Linux 2023 AMI...${NC}"

AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters \
        "Name=name,Values=al2023-ami-2023*-x86_64" \
        "Name=state,Values=available" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --output text)

echo "Using AMI: $AMI_ID"

#############################################
# STEP 6: Launch EC2 Instance
#############################################
echo -e "\n${YELLOW}[Step 6] Launching EC2 instance...${NC}"

# Check for existing instance
EXISTING_INSTANCE=$(aws ec2 describe-instances \
    --filters \
        "Name=tag:Name,Values=whatsapp-bot" \
        "Name=instance-state-name,Values=running,pending,stopped" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text 2>/dev/null || echo "None")

if [ "$EXISTING_INSTANCE" != "None" ] && [ -n "$EXISTING_INSTANCE" ]; then
    echo "Instance already exists: $EXISTING_INSTANCE"
    INSTANCE_ID=$EXISTING_INSTANCE
else
    echo "Launching new t2.micro instance..."
    
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id "$AMI_ID" \
        --instance-type t2.micro \
        --key-name "$KEY_NAME" \
        --security-group-ids "$SG_ID" \
        --iam-instance-profile Name="$INSTANCE_PROFILE_NAME" \
        --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":30,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
        --user-data file:///tmp/user-data.sh \
        --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=whatsapp-bot}]' \
        --query 'Instances[0].InstanceId' \
        --output text)
    
    echo "Instance launched: $INSTANCE_ID"
    
    # Wait for instance to be running
    echo "Waiting for instance to start..."
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
    echo -e "${GREEN}Instance is running${NC}"
fi

rm -f /tmp/user-data.sh

#############################################
# STEP 7: Allocate Elastic IP
#############################################
echo -e "\n${YELLOW}[Step 7] Setting up Elastic IP...${NC}"

# Check if instance already has an EIP
CURRENT_EIP=$(aws ec2 describe-addresses \
    --filters "Name=instance-id,Values=$INSTANCE_ID" \
    --query 'Addresses[0].PublicIp' \
    --output text 2>/dev/null || echo "None")

if [ "$CURRENT_EIP" != "None" ] && [ -n "$CURRENT_EIP" ]; then
    ELASTIC_IP=$CURRENT_EIP
    echo "Instance already has Elastic IP: $ELASTIC_IP"
else
    # Allocate new Elastic IP
    echo "Allocating new Elastic IP..."
    ALLOCATION_ID=$(aws ec2 allocate-address \
        --domain vpc \
        --query 'AllocationId' \
        --output text)
    
    # Associate with instance
    aws ec2 associate-address \
        --instance-id "$INSTANCE_ID" \
        --allocation-id "$ALLOCATION_ID" > /dev/null
    
    ELASTIC_IP=$(aws ec2 describe-addresses \
        --allocation-ids "$ALLOCATION_ID" \
        --query 'Addresses[0].PublicIp' \
        --output text)
    
    echo -e "${GREEN}Elastic IP allocated and associated${NC}"
fi

#############################################
# DONE: Output Summary
#############################################
echo ""
echo "============================================"
echo -e "${GREEN}  AWS INFRASTRUCTURE READY${NC}"
echo "============================================"
echo ""
echo "Instance ID:    $INSTANCE_ID"
echo "Elastic IP:     $ELASTIC_IP"
echo "Key File:       $KEY_FILE"
echo "Region:         $AWS_DEFAULT_REGION"
echo ""
echo "============================================"
echo "  NEXT STEPS"
echo "============================================"
echo ""
echo "1. Wait 2-3 minutes for instance bootstrap to complete"
echo ""
echo "2. Get a free domain from DuckDNS:"
echo "   https://www.duckdns.org"
echo "   Point it to: $ELASTIC_IP"
echo ""
echo "3. Update your .env file with production values"
echo ""
echo "4. Deploy the application:"
echo "   ./deploy/deploy-app.sh $ELASTIC_IP $KEY_FILE YOUR_DOMAIN.duckdns.org"
echo ""
echo "5. SSH into the instance:"
echo "   ssh -i $KEY_FILE ec2-user@$ELASTIC_IP"
echo ""
echo "============================================"
