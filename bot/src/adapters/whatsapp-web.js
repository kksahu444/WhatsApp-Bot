/**
 * WhatsApp Web.js Adapter
 * For development mode using whatsapp-web.js
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const config = require('../config');
const logger = require('../utils/logger');

class WhatsAppWebAdapter {
  constructor() {
    this.client = null;
    this.isReady = false;
    this.messageHandler = null;
  }
  
  /**
   * Initialize the WhatsApp Web client
   */
  async initialize() {
    logger.info('Initializing WhatsApp Web.js client...');
    
    this.client = new Client({
      authStrategy: new LocalAuth({
        dataPath: config.session.path,
      }),
      puppeteer: {
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--single-process',
          '--disable-gpu',
        ],
      },
    });
    
    this._setupEventListeners();
    
    await this.client.initialize();
  }
  
  /**
   * Set up event listeners
   */
  _setupEventListeners() {
    // QR Code for authentication
    this.client.on('qr', (qr) => {
      logger.info('QR Code received, scan with WhatsApp:');
      qrcode.generate(qr, { small: true });
    });
    
    // Client is ready
    this.client.on('ready', () => {
      this.isReady = true;
      logger.info('WhatsApp Web client is ready!');
    });
    
    // Authentication successful
    this.client.on('authenticated', () => {
      logger.info('WhatsApp Web client authenticated');
    });
    
    // Authentication failure
    this.client.on('auth_failure', (error) => {
      logger.error('WhatsApp authentication failed:', error);
      this.isReady = false;
    });
    
    // Disconnection
    this.client.on('disconnected', (reason) => {
      logger.warn('WhatsApp client disconnected:', reason);
      this.isReady = false;
    });
    
    // Incoming message
    this.client.on('message', async (message) => {
      try {
        await this._handleMessage(message);
      } catch (error) {
        logger.error('Error handling message:', error);
      }
    });
    
    // Message acknowledgment
    this.client.on('message_ack', (message, ack) => {
      logger.debug(`Message ${message.id.id} ack: ${ack}`);
    });
  }
  
  /**
   * Handle incoming message
   */
  async _handleMessage(message) {
    // Skip group messages and status updates
    if (message.isGroupMsg || message.isStatus) {
      return;
    }
    
    // Get sender phone number
    const phone = message.from.replace('@c.us', '');
    
    // Build message object
    const messageData = {
      phone,
      messageId: message.id.id,
      text: message.body,
      type: message.type,
      timestamp: message.timestamp,
      hasMedia: message.hasMedia,
    };
    
    logger.info(`Received message from ${phone}: ${message.body.substring(0, 50)}...`);
    
    // Call message handler if set
    if (this.messageHandler) {
      await this.messageHandler(messageData);
    }
  }
  
  /**
   * Set message handler callback
   */
  onMessage(handler) {
    this.messageHandler = handler;
  }
  
  /**
   * Send a text message
   */
  async sendText(phone, text) {
    if (!this.isReady) {
      throw new Error('WhatsApp client not ready');
    }
    
    const chatId = `${phone}@c.us`;
    await this.client.sendMessage(chatId, text);
    logger.info(`Sent message to ${phone}`);
  }
  
  /**
   * Send a message with buttons (simulated as text)
   */
  async sendButtons(phone, text, buttons) {
    // whatsapp-web.js has limited button support
    // Format as text with numbered options
    let message = text + '\n\n';
    buttons.forEach((btn, idx) => {
      message += `${idx + 1}. ${btn.title}\n`;
    });
    message += '\nBalas dengan nomor pilihan Anda.';
    
    await this.sendText(phone, message);
  }
  
  /**
   * Send a list message (simulated as text)
   */
  async sendList(phone, header, body, buttonText, sections) {
    let message = `*${header}*\n\n${body}\n\n`;
    
    sections.forEach(section => {
      if (section.title) {
        message += `*${section.title}*\n`;
      }
      section.rows.forEach((row, idx) => {
        message += `${idx + 1}. ${row.title}`;
        if (row.description) {
          message += ` - ${row.description}`;
        }
        message += '\n';
      });
      message += '\n';
    });
    
    message += 'Balas dengan nomor pilihan Anda.';
    
    await this.sendText(phone, message);
  }
  
  /**
   * Send an image message
   */
  async sendImage(phone, imageUrl, caption = '') {
    if (!this.isReady) {
      throw new Error('WhatsApp client not ready');
    }
    
    const { MessageMedia } = require('whatsapp-web.js');
    const media = await MessageMedia.fromUrl(imageUrl);
    
    const chatId = `${phone}@c.us`;
    await this.client.sendMessage(chatId, media, { caption });
    logger.info(`Sent image to ${phone}`);
  }
  
  /**
   * Get client status
   */
  getStatus() {
    return {
      isReady: this.isReady,
      mode: 'dev',
    };
  }
  
  /**
   * Graceful shutdown
   */
  async shutdown() {
    if (this.client) {
      logger.info('Shutting down WhatsApp Web client...');
      await this.client.destroy();
    }
  }
}

module.exports = WhatsAppWebAdapter;
