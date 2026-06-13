"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Products table
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('sku', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('price', sa.Numeric(12, 2), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('stock_quantity', sa.Integer, nullable=False, server_default='0'),
        sa.Column('image_url', sa.Text),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.CheckConstraint('price >= 0', name='products_price_positive'),
        sa.CheckConstraint('stock_quantity >= 0', name='products_stock_positive'),
    )
    
    op.create_index('idx_products_category', 'products', ['category'])
    op.create_index('idx_products_is_active', 'products', ['is_active'])
    op.create_index('idx_products_sku', 'products', ['sku'])
    
    # Carts table
    op.create_table(
        'carts',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
    )
    
    op.create_index('idx_carts_phone', 'carts', ['phone'])
    op.create_index('idx_carts_updated_at', 'carts', ['updated_at'])
    
    # Cart items table
    op.create_table(
        'cart_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('cart_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('price', sa.Numeric(12, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.CheckConstraint('quantity > 0', name='cart_items_quantity_positive'),
    )
    
    op.create_index('idx_cart_items_cart_id', 'cart_items', ['cart_id'])
    
    # Orders table
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('order_number', sa.String(50), nullable=False, unique=True),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('shipping_address', sa.Text),
        sa.Column('shipping_method', sa.String(50)),
        sa.Column('payment_method', sa.String(50)),
        sa.Column('payment_status', sa.String(20), server_default='pending'),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
    )
    
    op.create_index('idx_orders_phone', 'orders', ['phone'])
    op.create_index('idx_orders_status', 'orders', ['status'])
    op.create_index('idx_orders_created_at', 'orders', ['created_at'])
    op.create_index('idx_orders_order_number', 'orders', ['order_number'])
    
    # Order items table
    op.create_table(
        'order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=False),
        sa.Column('product_sku', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id']),
        sa.CheckConstraint('quantity > 0', name='order_items_quantity_positive'),
    )
    
    op.create_index('idx_order_items_order_id', 'order_items', ['order_id'])
    
    # Conversations table
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.Column('message_count', sa.Integer, server_default='0'),
        sa.Column('current_intent', sa.String(50)),
        sa.Column('context', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
    )
    
    op.create_index('idx_conversations_phone', 'conversations', ['phone'])
    op.create_index('idx_conversations_last_message_at', 'conversations', ['last_message_at'])
    
    # Conversation messages table
    op.create_table(
        'conversation_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], 
                                ondelete='CASCADE'),
    )
    
    op.create_index('idx_conversation_messages_conversation_id', 
                    'conversation_messages', ['conversation_id'])
    op.create_index('idx_conversation_messages_created_at', 
                    'conversation_messages', ['created_at'])
    
    # Cart reminders table
    op.create_table(
        'cart_reminders',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('cart_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reminder_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['cart_id'], ['carts.id'], ondelete='CASCADE'),
    )
    
    # Idempotency keys table
    op.create_table(
        'idempotency_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('key', sa.String(255), nullable=False, unique=True),
        sa.Column('response', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    op.create_index('idx_idempotency_keys_expires_at', 'idempotency_keys', ['expires_at'])
    
    # Cost tracking table
    op.create_table(
        'cost_tracking',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('date', sa.Date, nullable=False, 
                  server_default=sa.func.current_date()),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('input_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_cost', sa.Numeric(10, 6), nullable=False, server_default='0'),
        sa.Column('request_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
        sa.UniqueConstraint('date', 'model', name='cost_tracking_date_model_unique'),
    )
    
    # Analytics events table
    op.create_table(
        'analytics_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), 
                  server_default=sa.text('uuid_generate_v4()'), 
                  primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('data', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.func.now()),
    )
    
    op.create_index('idx_analytics_events_event_type', 'analytics_events', ['event_type'])
    op.create_index('idx_analytics_events_created_at', 'analytics_events', ['created_at'])
    
    # Create updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create triggers for updated_at
    for table in ['products', 'carts', 'orders', 'conversations']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    # Drop triggers
    for table in ['products', 'carts', 'orders', 'conversations']:
        op.execute(f'DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}')
    
    # Drop trigger function
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    
    # Drop tables in reverse order
    op.drop_table('analytics_events')
    op.drop_table('cost_tracking')
    op.drop_table('idempotency_keys')
    op.drop_table('cart_reminders')
    op.drop_table('conversation_messages')
    op.drop_table('conversations')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('cart_items')
    op.drop_table('carts')
    op.drop_table('products')
