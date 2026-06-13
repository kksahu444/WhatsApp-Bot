/**
 * Adapter Index
 * Factory for selecting the appropriate WhatsApp adapter
 */

const config = require('../config');
const WhatsAppWebAdapter = require('./whatsapp-web');
const MetaCloudAdapter = require('./meta-cloud');

/**
 * Create WhatsApp adapter based on configuration
 */
function createAdapter() {
  if (config.botMode === 'prod') {
    return new MetaCloudAdapter();
  }
  return new WhatsAppWebAdapter();
}

module.exports = {
  createAdapter,
  WhatsAppWebAdapter,
  MetaCloudAdapter,
};
