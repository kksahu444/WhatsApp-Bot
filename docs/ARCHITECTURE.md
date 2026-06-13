# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           WhatsApp Users                             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Meta WhatsApp Cloud API                          │
│                     (Production) / whatsapp-web.js (Dev)             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Reverse Proxy (Caddy)                         │
│                     SSL Termination, Routing                         │
└─────────────────────────────────────────────────────────────────────┘
                          │         │         │
              ┌───────────┘         │         └───────────┐
              ▼                     ▼                     ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│    Node.js Bot      │ │   FastAPI Backend   │ │ Streamlit Dashboard │
│  (WhatsApp Client)  │ │   (Business Logic)  │ │   (Admin Panel)     │
│     Port 3000       │ │     Port 8000       │ │     Port 8501       │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
              │                     │                     │
              └──────────┬──────────┘                     │
                         │                                │
                         ▼                                │
              ┌─────────────────────┐                     │
              │       Redis         │◄────────────────────┘
              │   Cache & Sessions  │
              │     Port 6379       │
              └─────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Supabase (PostgreSQL)                        │
│                    Products, Orders, Conversations                   │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │       LanceDB       │
              │   Vector Database   │
              │   (Local Storage)   │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   Google Gemini     │
              │   LLM API           │
              └─────────────────────┘
```

## Components

### 1. Node.js Bot (`bot/`)

**Purpose:** WhatsApp client interface

**Responsibilities:**
- Connect to WhatsApp (dev: whatsapp-web.js, prod: Meta Cloud API)
- Receive incoming messages
- Forward messages to Backend API
- Send responses back to users

**Key Files:**
- `src/index.js` - Entry point
- `src/adapters/` - WhatsApp client adapters
- `src/handlers/` - Message handling

### 2. FastAPI Backend (`backend/`)

**Purpose:** Core business logic

**Responsibilities:**
- Message routing and intent classification
- Product search (RAG pipeline)
- Cart and order management
- LLM response generation
- Analytics and metrics

**Key Modules:**
- `handlers/` - Request handlers by feature
- `services/` - Business logic services
- `rag/` - RAG pipeline (search, embeddings, LLM)
- `database/` - Database clients
- `middleware/` - Request middleware

### 3. Streamlit Dashboard (`dashboard/`)

**Purpose:** Admin interface

**Responsibilities:**
- View analytics and metrics
- Manage products and orders
- Configure bot settings
- Monitor conversations

### 4. Redis

**Purpose:** Caching and session storage

**Usage:**
- Conversation context caching
- Rate limiting counters
- Idempotency keys
- Session storage

### 5. Supabase (PostgreSQL)

**Purpose:** Primary data store

**Tables:**
- `products` - Product catalog
- `carts` / `cart_items` - Shopping carts
- `orders` / `order_items` - Orders
- `conversations` / `conversation_messages` - Chat history
- `analytics_events` - Event tracking

### 6. LanceDB

**Purpose:** Vector similarity search

**Usage:**
- Product embeddings storage
- Hybrid search (vector + BM25)
- Fast nearest neighbor lookup

### 7. Google Gemini

**Purpose:** Natural language understanding

**Usage:**
- Intent classification
- Response generation
- Query understanding

## Data Flow

### Message Processing Flow

```
1. User sends WhatsApp message
              │
              ▼
2. Meta Cloud API receives message
              │
              ▼
3. Webhook POST to Bot (Node.js)
              │
              ▼
4. Bot forwards to Backend API
              │
              ▼
5. Backend processes:
   a. Rate limit check (Redis)
   b. Load conversation context (Redis/Supabase)
   c. Route to appropriate handler
   d. Execute business logic
   e. Generate response (Gemini LLM)
   f. Save conversation (Supabase)
              │
              ▼
6. Response returned to Bot
              │
              ▼
7. Bot sends message via WhatsApp API
              │
              ▼
8. User receives response
```

### Product Search Flow

```
1. User: "cari sepatu nike"
              │
              ▼
2. Message Router → ProductHandler
              │
              ▼
3. SearchEngine:
   a. Generate query embedding
   b. Vector search in LanceDB
   c. BM25 keyword search
   d. Hybrid ranking (RRF)
              │
              ▼
4. LLM Handler:
   a. Format product results
   b. Generate natural response
              │
              ▼
5. Return formatted response
```

### Order Flow

```
1. User: "checkout"
              │
              ▼
2. CheckoutHandler:
   a. Load cart from Supabase
   b. Validate cart items
   c. Check inventory
              │
              ▼
3. Prompt for shipping info
              │
              ▼
4. OrderManager:
   a. Create order (with idempotency)
   b. Clear cart
   c. Send confirmation
              │
              ▼
5. Analytics: Record order event
```

## Security Architecture

### Authentication

- **API:** API key in header (`X-API-Key`)
- **Dashboard:** Session-based with streamlit-authenticator
- **Webhooks:** HMAC signature verification

### Rate Limiting

```
User (phone) → Rate Limiter → Backend
     │
     └── Redis counters per phone/endpoint
```

### Data Protection

- Phone numbers hashed for logging
- PII redaction in logs
- RLS policies in Supabase
- Encrypted connections (TLS)

## Scalability Considerations

### Horizontal Scaling

- **Backend:** Stateless, scale with replicas
- **Bot:** Single instance (WhatsApp limitation)
- **Dashboard:** Scale as needed

### Caching Strategy

```
Request → Check Redis Cache → Cache Hit? → Return
                 │                 │
                 ▼                 ▼
              Cache Miss      Get from DB
                 │                 │
                 └────── Update Cache
```

### Database Optimization

- Connection pooling
- Query optimization
- Indexing on frequently queried columns
- Partitioning for analytics tables

## Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Prometheus                                   │
│                    Metrics Collection                                │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Grafana                                     │
│                    Dashboards & Alerts                               │
└─────────────────────────────────────────────────────────────────────┘

Metrics:
- HTTP request rate & latency
- Message processing rate
- Order creation rate
- LLM token usage
- Cache hit/miss ratio
- Error rates
```

## Technology Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Backend | FastAPI | Async, fast, modern Python |
| Bot | Node.js | whatsapp-web.js ecosystem |
| Dashboard | Streamlit | Rapid development, Python |
| Database | Supabase | Managed Postgres, RLS, realtime |
| Vector DB | LanceDB | Local, fast, no server needed |
| Cache | Redis | Industry standard, reliable |
| LLM | Gemini | Cost-effective, good for Indonesian |
| Proxy | Caddy | Auto HTTPS, simple config |
