# API Reference

## Overview

The WhatsApp Seller Bot API provides endpoints for managing products, orders, carts, and conversations.

**Base URL:** `http://localhost:8000/api/v1`

## Authentication

All API requests require an API key in the header:

```
X-API-Key: your-api-key
```

## Endpoints

### Health Check

#### GET /health
Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### Products

#### GET /products
List all products with optional filtering.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| category | string | Filter by category |
| search | string | Search in name/description |
| is_active | boolean | Filter by active status |
| limit | integer | Max results (default: 50) |
| offset | integer | Pagination offset |

**Response:**
```json
{
  "products": [
    {
      "id": "uuid",
      "sku": "SKU-001",
      "name": "Product Name",
      "description": "Description",
      "price": 150000,
      "category": "Electronics",
      "stock_quantity": 25,
      "image_url": "https://...",
      "is_active": true,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

#### GET /products/{product_id}
Get a single product by ID.

#### POST /products
Create a new product.

**Request Body:**
```json
{
  "sku": "SKU-001",
  "name": "Product Name",
  "description": "Description",
  "price": 150000,
  "category": "Electronics",
  "stock_quantity": 25,
  "image_url": "https://...",
  "is_active": true
}
```

#### PUT /products/{product_id}
Update a product.

#### DELETE /products/{product_id}
Delete a product.

---

### Search

#### POST /products/search
Search products using natural language.

**Request Body:**
```json
{
  "query": "sepatu olahraga nike",
  "limit": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "product": { ... },
      "score": 0.95,
      "relevance": "high"
    }
  ],
  "query_info": {
    "original_query": "sepatu olahraga nike",
    "tokens": ["sepatu", "olahraga", "nike"]
  }
}
```

---

### Cart

#### GET /cart/{phone}
Get cart for a phone number.

**Response:**
```json
{
  "id": "uuid",
  "phone": "+6281234567890",
  "items": [
    {
      "product_id": "uuid",
      "product": { ... },
      "quantity": 2,
      "price": 150000
    }
  ],
  "total": 300000,
  "item_count": 2
}
```

#### POST /cart/{phone}/add
Add item to cart.

**Request Body:**
```json
{
  "product_id": "uuid",
  "quantity": 1
}
```

#### PUT /cart/{phone}/update
Update item quantity.

**Request Body:**
```json
{
  "product_id": "uuid",
  "quantity": 3
}
```

#### DELETE /cart/{phone}/remove/{product_id}
Remove item from cart.

#### DELETE /cart/{phone}/clear
Clear entire cart.

---

### Orders

#### GET /orders
List orders with filtering.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| phone | string | Filter by phone |
| status | string | Filter by status |
| start_date | date | Start date |
| end_date | date | End date |

#### GET /orders/{order_id}
Get order details.

#### POST /orders
Create order from cart.

**Request Body:**
```json
{
  "phone": "+6281234567890",
  "shipping_address": "Jl. Sudirman No. 123, Jakarta",
  "shipping_method": "regular",
  "payment_method": "bank_transfer",
  "notes": "Handle with care"
}
```

**Headers:**
```
X-Idempotency-Key: unique-key-123
```

#### PUT /orders/{order_id}/status
Update order status.

**Request Body:**
```json
{
  "status": "shipped",
  "tracking_number": "JNE123456789"
}
```

---

### Webhook

#### POST /webhook/whatsapp
WhatsApp message webhook.

**Request Body:**
```json
{
  "phone": "+6281234567890",
  "message": "User message",
  "message_id": "msg-123",
  "timestamp": 1705312200
}
```

**Response:**
```json
{
  "response": "Bot response text",
  "message_type": "text",
  "intent": "product_search"
}
```

---

### Analytics

#### GET /analytics/overview
Get analytics overview.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| start_date | date | Start date |
| end_date | date | End date |

**Response:**
```json
{
  "period": {
    "start": "2024-01-01",
    "end": "2024-01-15"
  },
  "messages": {
    "total": 2345,
    "by_intent": {
      "product_search": 450,
      "cart": 320,
      "checkout": 180
    }
  },
  "orders": {
    "total": 156,
    "revenue": 45200000,
    "average_value": 289743
  },
  "conversion_rate": 3.2
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Invalid request data |
| UNAUTHORIZED | 401 | Missing or invalid API key |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| API (general) | 100 requests/minute |
| Search | 30 requests/minute |
| Webhook | 500 requests/minute |

---

## Webhooks

### Order Status Updates

Configure webhook URL in settings to receive order updates:

```json
{
  "event": "order.status_changed",
  "order_id": "uuid",
  "old_status": "pending",
  "new_status": "confirmed",
  "timestamp": "2024-01-15T10:30:00Z"
}
```
