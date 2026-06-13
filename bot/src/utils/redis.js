/**
 * Redis Client Utility
 * For session and cache management
 */

const { createClient } = require('redis');
const config = require('../config');
const logger = require('./logger');

let client = null;

/**
 * Get Redis client (singleton)
 */
async function getRedisClient() {
  if (client && client.isOpen) {
    return client;
  }
  
  client = createClient({
    url: config.redis.url,
  });
  
  client.on('error', (err) => {
    logger.error('Redis Client Error:', err);
  });
  
  client.on('connect', () => {
    logger.info('Redis client connected');
  });
  
  await client.connect();
  
  return client;
}

/**
 * Set a value with optional TTL
 */
async function set(key, value, ttlSeconds = null) {
  const redis = await getRedisClient();
  
  if (ttlSeconds) {
    await redis.setEx(key, ttlSeconds, JSON.stringify(value));
  } else {
    await redis.set(key, JSON.stringify(value));
  }
}

/**
 * Get a value
 */
async function get(key) {
  const redis = await getRedisClient();
  const value = await redis.get(key);
  
  if (value) {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }
  
  return null;
}

/**
 * Delete a key
 */
async function del(key) {
  const redis = await getRedisClient();
  await redis.del(key);
}

/**
 * Check if key exists
 */
async function exists(key) {
  const redis = await getRedisClient();
  return await redis.exists(key);
}

/**
 * Close Redis connection
 */
async function close() {
  if (client && client.isOpen) {
    await client.quit();
    client = null;
    logger.info('Redis client disconnected');
  }
}

module.exports = {
  getRedisClient,
  set,
  get,
  del,
  exists,
  close,
};
