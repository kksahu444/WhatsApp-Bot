"""
Orders Management Page
View and manage orders
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from components import metric_row
from utils import get_api_client


def show():
    """Render the orders page."""
    st.title("📦 Orders Management")
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            options=["All", "Pending", "Confirmed", "Processing", "Shipped", "Delivered", "Cancelled"]
        )
    
    with col2:
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now().replace(day=1), datetime.now())
        )
    
    with col3:
        search = st.text_input("Search", placeholder="Order number or phone...")
    
    # Metrics
    metrics = [
        {"title": "Total Orders", "value": "156"},
        {"title": "Pending", "value": "12"},
        {"title": "Processing", "value": "8"},
        {"title": "Completed", "value": "136"},
    ]
    metric_row(metrics)
    
    st.markdown("---")
    
    # Orders Table
    orders_data = pd.DataFrame({
        'Order #': ['ORD-20240115-A1B2', 'ORD-20240115-C3D4', 'ORD-20240114-E5F6', 
                   'ORD-20240114-G7H8', 'ORD-20240113-I9J0'],
        'Date': ['2024-01-15 14:30', '2024-01-15 12:15', '2024-01-14 16:45',
                '2024-01-14 09:20', '2024-01-13 11:30'],
        'Customer': ['+62812***4567', '+62813***8901', '+62814***2345',
                    '+62815***6789', '+62816***0123'],
        'Items': [3, 1, 2, 4, 1],
        'Total': ['Rp 450,000', 'Rp 150,000', 'Rp 280,000', 'Rp 520,000', 'Rp 75,000'],
        'Status': ['Processing', 'Pending', 'Shipped', 'Delivered', 'Pending'],
        'Payment': ['Paid', 'Pending', 'Paid', 'Paid', 'Pending']
    })
    
    # Add status color coding
    def color_status(val):
        colors = {
            'Pending': 'background-color: #fff3cd',
            'Processing': 'background-color: #cce5ff',
            'Shipped': 'background-color: #d4edda',
            'Delivered': 'background-color: #d1ecf1',
            'Cancelled': 'background-color: #f8d7da'
        }
        return colors.get(val, '')
    
    st.dataframe(
        orders_data.style.applymap(color_status, subset=['Status']),
        use_container_width=True,
        hide_index=True
    )
    
    # Order Details Modal (using expander)
    st.markdown("---")
    st.subheader("Order Details")
    
    selected_order = st.selectbox(
        "Select Order",
        options=orders_data['Order #'].tolist()
    )
    
    if selected_order:
        with st.expander("View Order Details", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Order Information**")
                st.write(f"Order Number: {selected_order}")
                st.write("Date: 2024-01-15 14:30")
                st.write("Status: Processing")
                st.write("Payment: Paid via Bank Transfer")
            
            with col2:
                st.markdown("**Customer Information**")
                st.write("Phone: +62812***4567")
                st.write("Address: Jl. Sudirman No. 123")
                st.write("City: Jakarta")
            
            st.markdown("**Order Items**")
            items_data = pd.DataFrame({
                'Product': ['Product A', 'Product B', 'Product C'],
                'SKU': ['SKU-001', 'SKU-002', 'SKU-003'],
                'Qty': [1, 2, 1],
                'Price': ['Rp 150,000', 'Rp 100,000', 'Rp 100,000'],
                'Subtotal': ['Rp 150,000', 'Rp 200,000', 'Rp 100,000']
            })
            st.dataframe(items_data, use_container_width=True, hide_index=True)
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Confirm Order"):
                    st.success("Order confirmed!")
            with col2:
                if st.button("📦 Mark as Shipped"):
                    st.success("Order marked as shipped!")
            with col3:
                if st.button("❌ Cancel Order"):
                    st.error("Order cancelled!")


if __name__ == "__main__":
    show()
