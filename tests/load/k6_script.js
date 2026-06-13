import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const webhookLatency = new Trend('webhook_latency');
const searchLatency = new Trend('search_latency');
const orderLatency = new Trend('order_latency');
const messagesProcessed = new Counter('messages_processed');

// Test configuration
export const options = {
  // Stages for ramping up and down
  stages: [
    { duration: '1m', target: 10 },    // Ramp up to 10 users
    { duration: '3m', target: 10 },    // Stay at 10 users
    { duration: '2m', target: 50 },    // Ramp up to 50 users
    { duration: '5m', target: 50 },    // Stay at 50 users
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 0 },     // Ramp down to 0
  ],
  
  // Thresholds for pass/fail
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'],  // 95% < 2s, 99% < 5s
    errors: ['rate<0.1'],                              // Error rate < 10%
    webhook_latency: ['p(95)<1500'],                   // Webhook 95% < 1.5s
    search_latency: ['p(95)<500'],                     // Search 95% < 500ms
  },
  
  // Tags for organization
  tags: {
    testName: 'WhatsApp Bot Load Test',
    environment: __ENV.ENVIRONMENT || 'staging',
  },
};

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-api-key';

// Sample phone numbers for testing
const PHONE_NUMBERS = [
  '628123456789', '628234567890', '628345678901',
  '628456789012', '628567890123', '628678901234',
  '628789012345', '628890123456', '628901234567',
  '628012345678',
];

// Sample messages
const MESSAGES = {
  greeting: ['halo', 'hi', 'hai', 'hello'],
  search: ['cari headphone', 'ada kaos?', 'laptop stand', 'madu asli'],
  cart: ['tambah ke keranjang', 'lihat keranjang', 'checkout'],
  help: ['bantuan', 'help', 'cara pesan'],
};

// Helper functions
function getRandomPhone() {
  return PHONE_NUMBERS[Math.floor(Math.random() * PHONE_NUMBERS.length)];
}

function getRandomMessage(type) {
  const messages = MESSAGES[type];
  return messages[Math.floor(Math.random() * messages.length)];
}

function headers() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`,
  };
}

// Setup function - runs once before tests
export function setup() {
  console.log(`Starting load test against ${BASE_URL}`);
  
  // Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check passed': (r) => r.status === 200,
  });
  
  return { startTime: Date.now() };
}

// Main test function
export default function(data) {
  // Simulate different user behaviors
  const scenario = Math.random();
  
  if (scenario < 0.3) {
    // 30% - New user greeting
    newUserGreeting();
  } else if (scenario < 0.6) {
    // 30% - Product search
    productSearch();
  } else if (scenario < 0.8) {
    // 20% - Cart operations
    cartOperations();
  } else {
    // 20% - Full checkout flow
    checkoutFlow();
  }
  
  // Small pause between requests
  sleep(Math.random() * 2 + 0.5);  // 0.5-2.5 seconds
}

// Test scenarios
function newUserGreeting() {
  group('New User Greeting', function() {
    const phone = getRandomPhone();
    const message = getRandomMessage('greeting');
    
    const payload = JSON.stringify({
      entry: [{
        id: 'test-entry',
        changes: [{
          value: {
            messaging_product: 'whatsapp',
            metadata: { phone_number_id: 'test-phone-id' },
            messages: [{
              from: phone,
              id: `msg_${Date.now()}`,
              timestamp: Math.floor(Date.now() / 1000).toString(),
              type: 'text',
              text: { body: message },
            }],
          },
        }],
      }],
    });
    
    const startTime = Date.now();
    const res = http.post(`${BASE_URL}/webhook`, payload, { headers: headers() });
    const duration = Date.now() - startTime;
    
    webhookLatency.add(duration);
    messagesProcessed.add(1);
    
    const success = check(res, {
      'webhook status 200': (r) => r.status === 200,
      'response time < 2s': (r) => r.timings.duration < 2000,
    });
    
    errorRate.add(!success);
  });
}

function productSearch() {
  group('Product Search', function() {
    const query = getRandomMessage('search');
    
    // Direct search API call
    const startTime = Date.now();
    const res = http.get(`${BASE_URL}/api/v1/products/search?q=${encodeURIComponent(query)}&limit=5`, {
      headers: headers(),
    });
    const duration = Date.now() - startTime;
    
    searchLatency.add(duration);
    
    const success = check(res, {
      'search status 200': (r) => r.status === 200,
      'search has results': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.products && body.products.length >= 0;
        } catch {
          return false;
        }
      },
      'search time < 500ms': (r) => r.timings.duration < 500,
    });
    
    errorRate.add(!success);
  });
}

function cartOperations() {
  group('Cart Operations', function() {
    const phone = getRandomPhone();
    
    // View cart
    const cartRes = http.get(`${BASE_URL}/api/v1/cart/${phone}`, {
      headers: headers(),
    });
    
    check(cartRes, {
      'get cart status 200 or 404': (r) => r.status === 200 || r.status === 404,
    });
    
    // Add to cart (if cart exists or create new)
    const addPayload = JSON.stringify({
      product_id: 'test-product-1',
      quantity: 1,
    });
    
    const addRes = http.post(`${BASE_URL}/api/v1/cart/${phone}/items`, addPayload, {
      headers: headers(),
    });
    
    const success = check(addRes, {
      'add to cart status 200/201': (r) => r.status === 200 || r.status === 201,
    });
    
    errorRate.add(!success);
  });
}

function checkoutFlow() {
  group('Checkout Flow', function() {
    const phone = getRandomPhone();
    
    // Step 1: Get or create cart
    let cartRes = http.get(`${BASE_URL}/api/v1/cart/${phone}`, {
      headers: headers(),
    });
    
    // Step 2: Add item
    const addPayload = JSON.stringify({
      product_id: 'test-product-1',
      quantity: 1,
    });
    
    http.post(`${BASE_URL}/api/v1/cart/${phone}/items`, addPayload, {
      headers: headers(),
    });
    
    // Step 3: Create order
    const orderPayload = JSON.stringify({
      phone_number: phone,
      shipping_address: 'Jl. Test No. 123, Jakarta',
      payment_method: 'bank_transfer',
    });
    
    const startTime = Date.now();
    const orderRes = http.post(`${BASE_URL}/api/v1/orders`, orderPayload, {
      headers: headers(),
    });
    const duration = Date.now() - startTime;
    
    orderLatency.add(duration);
    
    const success = check(orderRes, {
      'order created': (r) => r.status === 200 || r.status === 201 || r.status === 400,
      'order time < 3s': (r) => r.timings.duration < 3000,
    });
    
    errorRate.add(!success);
  });
}

// Teardown function - runs once after tests
export function teardown(data) {
  const duration = (Date.now() - data.startTime) / 1000;
  console.log(`Load test completed in ${duration.toFixed(2)} seconds`);
}
