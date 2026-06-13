# Deployment Guide

## Overview

This guide covers deploying the WhatsApp Seller Bot to production environments.

## Prerequisites

- Docker and Docker Compose
- Domain name with DNS configured
- SSL certificate (auto-managed with Caddy)
- Supabase account
- Google Cloud account (for Gemini API)
- Meta Developer account (for production WhatsApp)

## Deployment Options

### Option 1: Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/whatsapp-seller-bot.git
   cd whatsapp-seller-bot
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Start services:**
   ```bash
   docker compose up -d
   ```

4. **Verify deployment:**
   ```bash
   docker compose ps
   curl http://localhost:8000/health
   ```

### Option 2: Manual Deployment

#### Backend

1. **Install dependencies:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run with Uvicorn:**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

#### Bot

1. **Install dependencies:**
   ```bash
   cd bot
   npm install
   ```

2. **Start bot:**
   ```bash
   npm start
   ```

#### Dashboard

1. **Install dependencies:**
   ```bash
   cd dashboard
   pip install -r requirements.txt
   ```

2. **Run Streamlit:**
   ```bash
   streamlit run app.py --server.port 8501
   ```

## Production Configuration

### Environment Variables

**Backend (.env):**
```env
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# Redis
REDIS_URL=redis://redis:6379

# LLM
GEMINI_API_KEY=your-gemini-key

# WhatsApp
WHATSAPP_API_URL=http://bot:3000
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
WHATSAPP_ACCESS_TOKEN=your-access-token

# Security
SECRET_KEY=your-secret-key
```

**Bot (.env):**
```env
BOT_MODE=prod
BACKEND_URL=http://backend:8000
WHATSAPP_PHONE_NUMBER_ID=your-phone-id
WHATSAPP_ACCESS_TOKEN=your-access-token
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your-verify-token
```

### Reverse Proxy Setup

#### Using Caddy (Recommended)

Update `infra/Caddyfile`:
```
yourdomain.com {
    handle /api/* {
        reverse_proxy backend:8000
    }
    
    handle /webhook/* {
        reverse_proxy bot:3000
    }
    
    handle {
        reverse_proxy dashboard:8501
    }
}
```

#### Using Nginx

Use the configuration in `infra/nginx/nginx.conf`.

### SSL Certificates

**Caddy:** Automatic via Let's Encrypt.

**Nginx:** Use Certbot:
```bash
certbot --nginx -d yourdomain.com
```

### Systemd Service

1. **Copy service file:**
   ```bash
   sudo cp infra/systemd/whatsapp-bot.service /etc/systemd/system/
   ```

2. **Enable and start:**
   ```bash
   sudo systemctl enable whatsapp-bot
   sudo systemctl start whatsapp-bot
   ```

## Database Setup

1. **Create Supabase project** at [supabase.com](https://supabase.com)

2. **Run schema:**
   - Open SQL Editor in Supabase Dashboard
   - Run `backend/database/schema.sql`

3. **Seed data (optional):**
   ```bash
   python backend/scripts/seed_data.py
   ```

## Meta WhatsApp Setup

1. **Create Meta Developer account**

2. **Create WhatsApp Business App**

3. **Configure webhook:**
   - URL: `https://yourdomain.com/webhook`
   - Verify Token: Your configured token
   - Subscribe to: `messages`

4. **Get credentials:**
   - Phone Number ID
   - Access Token

## Monitoring

### Prometheus + Grafana

1. **Access Grafana:** `http://yourdomain.com:3001`
2. **Default credentials:** admin/admin
3. **Import dashboard:** `infra/grafana/dashboards/bot-dashboard.json`

### Health Checks

- Backend: `GET /health`
- Bot: `GET /health`
- Dashboard: `GET /_stcore/health`

## Scaling

### Horizontal Scaling

1. **Update docker-compose.yml:**
   ```yaml
   backend:
     deploy:
       replicas: 3
   ```

2. **Add load balancer** in Caddy/Nginx config.

### Database Scaling

- Enable connection pooling in Supabase
- Consider read replicas for analytics queries

## Backup Strategy

### Database

Supabase provides automatic backups. For manual backups:
```bash
pg_dump -h your-supabase-host -U postgres -d postgres > backup.sql
```

### Redis

```bash
docker exec redis redis-cli BGSAVE
```

## Security Checklist

- [ ] Change all default passwords
- [ ] Enable HTTPS only
- [ ] Configure firewall rules
- [ ] Set up rate limiting
- [ ] Enable RLS in Supabase
- [ ] Rotate API keys regularly
- [ ] Monitor for unusual activity
- [ ] Set up alerts for errors

## Troubleshooting

### Bot not connecting

1. Check WhatsApp credentials
2. Verify webhook URL is accessible
3. Check bot logs: `docker compose logs bot`

### High latency

1. Check Redis connection
2. Monitor LLM API response times
3. Review database query performance

### Messages not processing

1. Verify webhook is receiving requests
2. Check backend logs for errors
3. Ensure rate limits not exceeded
