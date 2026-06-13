/**
 * Webhook Handler
 * Express routes for handling Meta webhook callbacks
 */

const express = require('express');
const config = require('../config');
const logger = require('../utils/logger');

/**
 * Create webhook router
 */
function createWebhookRouter(adapter, messageHandler) {
  const router = express.Router();
  
  /**
   * Webhook verification (GET)
   * Meta sends this to verify the webhook URL
   */
  router.get('/', (req, res) => {
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];
    
    logger.info('Webhook verification request received');
    
    if (mode === 'subscribe' && token === config.whatsapp.webhookVerifyToken) {
      logger.info('Webhook verified successfully');
      res.status(200).send(challenge);
    } else {
      logger.warn('Webhook verification failed');
      res.sendStatus(403);
    }
  });
  
  /**
   * Webhook callback (POST)
   * Receives incoming messages and status updates
   */
  router.post('/', express.raw({ type: 'application/json' }), async (req, res) => {
    const signature = req.headers['x-hub-signature-256'];
    
    // Immediately respond to webhook
    res.sendStatus(200);
    
    try {
      // Process webhook asynchronously
      if (config.botMode === 'prod') {
        await adapter.processWebhook(req.body.toString(), signature);
      }
    } catch (error) {
      logger.error('Error processing webhook:', error);
    }
  });
  
  return router;
}

module.exports = { createWebhookRouter };
