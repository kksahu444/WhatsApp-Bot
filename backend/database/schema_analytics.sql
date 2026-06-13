-- ============================================
-- Analytics Events Table
-- Tracks user actions for funnel analysis
-- ============================================

CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_phone TEXT NOT NULL,
    event_type TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying by event type
CREATE INDEX IF NOT EXISTS idx_analytics_event_type 
ON analytics_events(event_type);

-- Index for querying by user
CREATE INDEX IF NOT EXISTS idx_analytics_user_phone 
ON analytics_events(user_phone);

-- Index for time-based queries (dashboard)
CREATE INDEX IF NOT EXISTS idx_analytics_created_at 
ON analytics_events(created_at DESC);

-- Composite index for funnel analysis
CREATE INDEX IF NOT EXISTS idx_analytics_user_event 
ON analytics_events(user_phone, event_type, created_at DESC);

-- ============================================
-- Event Types Reference (for documentation)
-- ============================================
-- message          - User sent a message
-- search           - Product search query
-- product_view     - Product viewed
-- add_to_cart      - Item added to cart
-- remove_from_cart - Item removed from cart
-- cart_view        - Cart viewed
-- checkout_start   - Checkout initiated
-- checkout         - Order placed (checkout complete)
-- order_placed     - Order confirmed
-- payment          - Payment received
-- abandoned_cart_reminder - Reminder sent
-- support_request  - Human support requested
-- error            - Error occurred

-- ============================================
-- Sample Queries for Dashboard
-- ============================================

-- Daily event counts
-- SELECT 
--     DATE(created_at) as date,
--     event_type,
--     COUNT(*) as count
-- FROM analytics_events
-- WHERE created_at >= NOW() - INTERVAL '7 days'
-- GROUP BY DATE(created_at), event_type
-- ORDER BY date DESC, count DESC;

-- Conversion funnel
-- SELECT 
--     event_type,
--     COUNT(DISTINCT user_phone) as users
-- FROM analytics_events
-- WHERE created_at >= NOW() - INTERVAL '24 hours'
--     AND event_type IN ('search', 'add_to_cart', 'checkout_start', 'checkout')
-- GROUP BY event_type;

-- Top search queries
-- SELECT 
--     metadata->>'query' as query,
--     COUNT(*) as count
-- FROM analytics_events
-- WHERE event_type = 'search'
--     AND created_at >= NOW() - INTERVAL '7 days'
-- GROUP BY metadata->>'query'
-- ORDER BY count DESC
-- LIMIT 10;

-- ============================================
-- Row Level Security (RLS)
-- ============================================
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role has full access to analytics"
ON analytics_events
FOR ALL
USING (auth.role() = 'service_role');

-- Allow authenticated users to insert events
CREATE POLICY "Allow insert for authenticated"
ON analytics_events
FOR INSERT
WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'anon');
