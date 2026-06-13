/**
 * Meta Cloud API Adapter
 * For production mode using Meta's WhatsApp Business Cloud API
 */

const axios = require('axios');
const crypto = require('crypto');
const config = require('../config');
const logger = require('../utils/logger');

class MetaCloudAdapter {
  constructor() {
    this.isReady = false;
    this.messageHandler = null;
    this.apiUrl = `https://graph.facebook.com/${config.whatsapp.apiVersion}/${config.whatsapp.phoneNumberId}`;
    
    this.httpClient = axios.create({
      baseURL: this.apiUrl,
      timeout: 30000,
      headers: {
        'Authorization': `Bearer ${config.whatsapp.accessToken}`,
        'Content-Type': 'application/json',
      },
    });
  }
  
  /**
   * Initialize the adapter
   */
  async initialize() {
    logger.info('Initializing Meta Cloud API adapter...');
    
    // Verify credentials by getting phone number info
    try {
      const response = await this.httpClient.get('/');
      logger.info(`Connected to WhatsApp Business API: ${response.data.verified_name || 'OK'}`);
      this.isReady = true;
    } catch (error) {
      logger.error('Failed to connect to Meta Cloud API:', error.message);
      throw error;
    }
  }
  
  /**
   * Set message handler callback
   */
  onMessage(handler) {
    this.messageHandler = handler;
  }
  
  /**
   * Process incoming webhook
   */
  async processWebhook(body, signature) {
    // Verify signature
    if (!this._verifySignature(body, signature)) {
      logger.warn('Invalid webhook signature');
      return false;
    }
    
    try {
      const data = JSON.parse(body);
      
      // Process each entry
      for (const entry of data.entry || []) {
        for (const change of entry.changes || []) {
          if (change.field === 'messages') {
            await this._processMessages(change.value);
          }
        }
      }
      
      return true;
    } catch (error) {
      logger.error('Error processing webhook:', error);
      return false;
    }
  }
  
  /**
   * Process messages from webhook
   */
  async _processMessages(value) {
    const messages = value.messages || [];
    const contacts = value.contacts || [];
    
    for (const message of messages) {
      // Get contact info
      const contact = contacts.find(c => c.wa_id === message.from) || {};
      
      // Build message object
      const messageData = {
        phone: message.from,
        messageId: message.id,
        text: message.text?.body || '',
        type: message.type,
        timestamp: parseInt(message.timestamp, 10),
        contactName: contact.profile?.name || '',
      };
      
      // Handle different message types
      if (message.type === 'interactive') {
        if (message.interactive.type === 'button_reply') {
          messageData.text = message.interactive.button_reply.id;
          messageData.buttonPayload = message.interactive.button_reply;
        } else if (message.interactive.type === 'list_reply') {
          messageData.text = message.interactive.list_reply.id;
          messageData.listPayload = message.interactive.list_reply;
        }
      }
      
      logger.info(`Received message from ${message.from}: ${messageData.text.substring(0, 50)}...`);
      
      // Call message handler
      if (this.messageHandler) {
        await this.messageHandler(messageData);
      }
    }
  }
  
  /**
   * Verify webhook signature
   */
  _verifySignature(body, signature) {
    if (!config.whatsapp.webhookSecret) {
      return true; // Skip verification if no secret configured
    }
    
    if (!signature) {
      return false;
    }
    
    const [, receivedHash] = signature.split('=');
    const expectedHash = crypto
      .createHmac('sha256', config.whatsapp.webhookSecret)
      .update(body)
      .digest('hex');
    
    return crypto.timingSafeEqual(
      Buffer.from(receivedHash),
      Buffer.from(expectedHash)
    );
  }
  
  /**
   * Send a text message
   */
  async sendText(phone, text) {
    const payload = {
      messaging_product: 'whatsapp',
      to: phone,
      type: 'text',
      text: { body: text },
    };
    
    await this._sendMessage(payload);
  }
  
  /**
   * Send an interactive button message
   */
  async sendButtons(phone, text, buttons) {
    // Meta API supports max 3 buttons
    const limitedButtons = buttons.slice(0, 3).map(btn => ({
      type: 'reply',
      reply: {
        id: btn.id || btn.title.toLowerCase().replace(/\s+/g, '_'),
        title: btn.title.substring(0, 20), // Max 20 chars
      },
    }));
    
    const payload = {
      messaging_product: 'whatsapp',
      to: phone,
      type: 'interactive',
      interactive: {
        type: 'button',
        body: { text },
        action: {
          buttons: limitedButtons,
        },
      },
    };
    
    await this._sendMessage(payload);
  }
  
  /**
   * Send an interactive list message
   */
  async sendList(phone, header, body, buttonText, sections) {
    const formattedSections = sections.map(section => ({
      title: section.title.substring(0, 24), // Max 24 chars
      rows: section.rows.slice(0, 10).map(row => ({
        id: row.id || row.title.toLowerCase().replace(/\s+/g, '_'),
        title: row.title.substring(0, 24), // Max 24 chars
        description: row.description?.substring(0, 72) || '', // Max 72 chars
      })),
    }));
    
    const payload = {
      messaging_product: 'whatsapp',
      to: phone,
      type: 'interactive',
      interactive: {
        type: 'list',
        header: {
          type: 'text',
          text: header.substring(0, 60), // Max 60 chars
        },
        body: { text: body },
        action: {
          button: buttonText.substring(0, 20), // Max 20 chars
          sections: formattedSections,
        },
      },
    };
    
    await this._sendMessage(payload);
  }
  
  /**
   * Send an image message
   */
  async sendImage(phone, imageUrl, caption = '') {
    const payload = {
      messaging_product: 'whatsapp',
      to: phone,
      type: 'image',
      image: {
        link: imageUrl,
        caption: caption.substring(0, 1024), // Max 1024 chars
      },
    };
    
    await this._sendMessage(payload);
  }
  
  /**
   * Send a template message
   */
  async sendTemplate(phone, templateName, languageCode = 'id', components = []) {
    const payload = {
      messaging_product: 'whatsapp',
      to: phone,
      type: 'template',
      template: {
        name: templateName,
        language: { code: languageCode },
        components,
      },
    };
    
    await this._sendMessage(payload);
  }
  
  /**
   * Mark message as read
   */
  async markAsRead(messageId) {
    try {
      await this.httpClient.post('/messages', {
        messaging_product: 'whatsapp',
        status: 'read',
        message_id: messageId,
      });
    } catch (error) {
      logger.error('Failed to mark message as read:', error.message);
    }
  }
  
  /**
   * Send message via API
   */
  async _sendMessage(payload) {
    try {
      const response = await this.httpClient.post('/messages', payload);
      logger.info(`Sent message to ${payload.to}, ID: ${response.data.messages[0].id}`);
      return response.data;
    } catch (error) {
      logger.error('Failed to send message:', error.response?.data || error.message);
      throw error;
    }
  }
  
  /**
   * Get client status
   */
  getStatus() {
    return {
      isReady: this.isReady,
      mode: 'prod',
    };
  }
  
  /**
   * Graceful shutdown
   */
  async shutdown() {
    logger.info('Shutting down Meta Cloud API adapter');
    this.isReady = false;
  }
}

module.exports = MetaCloudAdapter;
