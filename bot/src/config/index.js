/**
 * Bot Configuration
 * Centralized configuration management
 */

require('dotenv').config();

const config = {
  // Environment
  nodeEnv: process.env.NODE_ENV || 'development',
  botMode: process.env.BOT_MODE || 'dev', // 'dev' or 'prod'
  
  // Server
  port: parseInt(process.env.PORT || '3000', 10),
  host: process.env.HOST || '0.0.0.0',
  
  // Backend API
  backend: {
    url: process.env.BACKEND_URL || 'http://localhost:8000',
    apiKey: process.env.BACKEND_API_KEY || '',
    timeout: parseInt(process.env.BACKEND_TIMEOUT || '30000', 10),
  },
  
  // Redis
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379',
  },
  
  // Meta WhatsApp Cloud API (Production)
  whatsapp: {
    phoneNumberId: process.env.WHATSAPP_PHONE_NUMBER_ID || '',
    accessToken: process.env.WHATSAPP_ACCESS_TOKEN || '',
    webhookVerifyToken: process.env.WHATSAPP_WEBHOOK_VERIFY_TOKEN || '',
    webhookSecret: process.env.WHATSAPP_WEBHOOK_SECRET || '',
    apiVersion: process.env.WHATSAPP_API_VERSION || 'v18.0',
  },
  
  // Session
  session: {
    path: process.env.SESSION_PATH || './sessions',
  },
  
  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
  },
  
  // Health Check
  healthCheck: {
    interval: parseInt(process.env.HEALTH_CHECK_INTERVAL || '30000', 10),
  },
};

// Validation
function validateConfig() {
  const errors = [];
  
  if (config.botMode === 'prod') {
    if (!config.whatsapp.phoneNumberId) {
      errors.push('WHATSAPP_PHONE_NUMBER_ID is required in production mode');
    }
    if (!config.whatsapp.accessToken) {
      errors.push('WHATSAPP_ACCESS_TOKEN is required in production mode');
    }
  }
  
  if (!config.backend.url) {
    errors.push('BACKEND_URL is required');
  }
  
  if (errors.length > 0) {
    console.error('Configuration errors:');
    errors.forEach(err => console.error(`  - ${err}`));
    process.exit(1);
  }
}

// Validate on load
validateConfig();

module.exports = config;
