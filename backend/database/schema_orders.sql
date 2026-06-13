-- ============================================
-- DAY 7: ORDER MANAGEMENT SCHEMA
-- Run this in Supabase SQL Editor
-- ============================================

-- ============================================
-- ATOMIC STOCK UPDATE FUNCTION
-- ============================================
CREATE OR REPLACE FUNCTION update_stock_atomic(
    p_product_id INT,
    p_quantity_change INT
)
RETURNS INT AS $$
DECLARE
    v_new_stock INT;
BEGIN
    UPDATE products
    SET stock = stock + p_quantity_change
    WHERE id = p_product_id
    AND stock + p_quantity_change >= 0
    RETURNING stock INTO v_new_stock;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Insufficient stock (Product ID: %)', p_product_id;
    END IF;

    RETURN v_new_stock;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- DROP EXISTING TABLES (if any)
-- ============================================
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;

-- ============================================
-- ORDERS TABLE (create first)
-- ============================================
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(20) UNIQUE NOT NULL,
    user_phone VARCHAR(20) NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    delivery_address TEXT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    idempotency_key VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- ORDER ITEMS TABLE (references orders.order_id)
-- ============================================
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(20) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_name VARCHAR(200) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX IF NOT EXISTS idx_orders_user_phone ON orders(user_phone);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_idempotency ON orders(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- ============================================
-- AUTO-UPDATE TRIGGER
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_orders_updated_at ON orders;
CREATE TRIGGER trigger_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- RLS POLICIES (Optional - for security)
-- ============================================
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;

-- Allow service role to access all orders
CREATE POLICY "Service role can access all orders" ON orders
    FOR ALL USING (true);

CREATE POLICY "Service role can access all order items" ON order_items
    FOR ALL USING (true);
