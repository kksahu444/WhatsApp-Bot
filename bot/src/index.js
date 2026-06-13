/**
 * WhatsApp Seller Bot
 * Main Entry Point
 */

const express = require('express');
const helmet = require('helmet');
const morgan = require('morgan');
const config = require('./config');
const logger = require('./utils/logger');
const { createAdapter } = require('./adapters');
const { MessageHandler, createWebhookRouter } = require('./handlers');

// Express app
const app = express();

// Security middleware
app.use(helmet());

// Request logging
app.use(morgan('combined', {
  stream: { write: message => logger.info(message.trim()) },
}));

// Parse JSON (for non-webhook routes)
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  const status = adapter ? adapter.getStatus() : { isReady: false };
  
  res.json({
    status: status.isReady ? 'healthy' : 'unhealthy',
    mode: config.botMode,
    timestamp: new Date().toISOString(),
    ...status,
  });
});

// Ready endpoint
app.get('/ready', (req, res) => {
  const status = adapter ? adapter.getStatus() : { isReady: false };
  
  if (status.isReady) {
    res.status(200).json({ ready: true });
  } else {
    res.status(503).json({ ready: false });
  }
});

// Global variables
let adapter = null;
let messageHandler = null;

/**
 * Initialize the bot
 */
async function initialize() {
  logger.info('Starting WhatsApp Seller Bot...');
  logger.info(`Mode: ${config.botMode}`);
  logger.info(`Backend: ${config.backend.url}`);
  
  try {
    // Create WhatsApp adapter
    adapter = createAdapter();
    
    // Create message handler
    messageHandler = new MessageHandler(adapter);
    
    // Set up webhook routes (for production mode)
    if (config.botMode === 'prod') {
      app.use('/webhook', createWebhookRouter(adapter, messageHandler));
    }
    
    // Initialize adapter
    await adapter.initialize();
    
    // Initialize message handler
    messageHandler.initialize();
    
    // Start Express server
    app.listen(config.port, config.host, () => {
      logger.info(`Server listening on ${config.host}:${config.port}`);
    });
    
    // Set up graceful shutdown
    setupGracefulShutdown();
    
    logger.info('Bot initialized successfully');
    
  } catch (error) {
    logger.error('Failed to initialize bot:', error);
    process.exit(1);
  }
}

/**
 * Set up graceful shutdown
 */
function setupGracefulShutdown() {
  const shutdown = async (signal) => {
    logger.info(`Received ${signal}, shutting down gracefully...`);
    
    try {
      // Shutdown adapter
      if (adapter) {
        await adapter.shutdown();
      }
      
      // Close Redis
      const redis = require('./utils/redis');
      await redis.close();
      
      logger.info('Shutdown complete');
      process.exit(0);
      
    } catch (error) {
      logger.error('Error during shutdown:', error);
      process.exit(1);
    }
  };
  
  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));
  
  // Handle uncaught exceptions
  process.on('uncaughtException', (error) => {
    logger.error('Uncaught exception:', error);
    shutdown('uncaughtException');
  });
  
  process.on('unhandledRejection', (reason, promise) => {
    logger.error('Unhandled rejection at:', promise, 'reason:', reason);
  });
}

// Start the bot
initialize();
