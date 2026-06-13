/**
 * Message Handler
 * Routes incoming messages to the backend API
 */

const axios = require('axios');
const config = require('../config');
const logger = require('../utils/logger');

class MessageHandler {
  constructor(whatsappAdapter) {
    this.adapter = whatsappAdapter;
    
    this.httpClient = axios.create({
      baseURL: config.backend.url,
      timeout: config.backend.timeout,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': config.backend.apiKey,
      },
    });
  }
  
  /**
   * Initialize message handling
   */
  initialize() {
    this.adapter.onMessage(this.handleMessage.bind(this));
    logger.info('Message handler initialized');
  }
  
  /**
   * Handle incoming message
   */
  async handleMessage(message) {
    const { phone, text, messageId, type } = message;
    
    try {
      // Send to backend API
      const response = await this.httpClient.post('/api/v1/webhook/whatsapp', {
        phone,
        message: text,
        message_id: messageId,
        message_type: type,
        timestamp: message.timestamp,
      });
      
      const data = response.data;
      
      // Send response back to user
      await this.sendResponse(phone, data);
      
    } catch (error) {
      logger.error('Failed to process message:', error.message);
      
      // Send error message to user
      await this.sendErrorResponse(phone);
    }
  }
  
  /**
   * Send response based on backend response
   */
  async sendResponse(phone, data) {
    // Check if response contains structured message
    if (data.message_type === 'buttons' && data.buttons) {
      await this.adapter.sendButtons(
        phone,
        data.message,
        data.buttons
      );
    } else if (data.message_type === 'list' && data.list) {
      await this.adapter.sendList(
        phone,
        data.list.header || 'Menu',
        data.message,
        data.list.button_text || 'Pilih',
        data.list.sections
      );
    } else if (data.message_type === 'image' && data.image_url) {
      await this.adapter.sendImage(
        phone,
        data.image_url,
        data.message
      );
    } else {
      // Default text message
      await this.adapter.sendText(phone, data.message || data.response);
    }
  }
  
  /**
   * Send error response
   */
  async sendErrorResponse(phone) {
    const errorMessage = 
      'Maaf, terjadi kesalahan. Silakan coba lagi nanti atau hubungi customer service kami.';
    
    try {
      await this.adapter.sendText(phone, errorMessage);
    } catch (error) {
      logger.error('Failed to send error response:', error.message);
    }
  }
}

module.exports = MessageHandler;
