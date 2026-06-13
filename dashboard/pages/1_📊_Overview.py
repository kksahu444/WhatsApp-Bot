"""
Overview Dashboard Page
Main dashboard with key metrics and charts
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from components import metric_row, line_chart, bar_chart, pie_chart
from utils import get_api_client


def show():
    """Render the overview page."""
    st.title("📊 Dashboard Overview")
    st.markdown("---")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=7)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now()
        )
    
    # Key Metrics Row
    st.subheader("Key Metrics")
    
    # Mock data - replace with API calls
    metrics = [
        {"title": "Total Orders", "value": "156", "delta": "+12%"},
        {"title": "Revenue", "value": "Rp 45.2M", "delta": "+8%"},
        {"title": "Messages", "value": "2,345", "delta": "+23%"},
        {"title": "Conversion Rate", "value": "3.2%", "delta": "-0.5%", "delta_color": "inverse"},
    ]
    
    metric_row(metrics)
    
    st.markdown("---")
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Orders Over Time")
        
        # Mock data
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        orders_data = pd.DataFrame({
            'date': dates,
            'orders': [12, 19, 15, 22, 18, 25, 20, 28][:len(dates)]
        })
        
        line_chart(orders_data, x='date', y='orders')
    
    with col2:
        st.subheader("💬 Messages by Intent")
        
        intent_data = pd.DataFrame({
            'intent': ['Product Search', 'Cart', 'Checkout', 'Support', 'Other'],
            'count': [450, 320, 180, 150, 245]
        })
        
        pie_chart(intent_data, values='count', names='intent')
    
    # Second Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top Products")
        
        products_data = pd.DataFrame({
            'product': ['Product A', 'Product B', 'Product C', 'Product D', 'Product E'],
            'sales': [45, 38, 32, 28, 22]
        })
        
        bar_chart(products_data, x='product', y='sales')
    
    with col2:
        st.subheader("📊 Revenue by Category")
        
        category_data = pd.DataFrame({
            'category': ['Electronics', 'Fashion', 'Food', 'Home', 'Beauty'],
            'revenue': [15.2, 12.5, 8.3, 5.8, 3.4]
        })
        
        bar_chart(category_data, x='category', y='revenue')
    
    # Recent Activity
    st.markdown("---")
    st.subheader("🕒 Recent Activity")
    
    activity_data = pd.DataFrame({
        'Time': ['2 min ago', '5 min ago', '12 min ago', '25 min ago', '1 hour ago'],
        'Type': ['Order', 'Message', 'Order', 'Cart', 'Message'],
        'Phone': ['+62812***4567', '+62813***8901', '+62814***2345', '+62815***6789', '+62816***0123'],
        'Details': [
            'New order #ORD-12345 (Rp 250,000)',
            'Product inquiry - "sepatu"',
            'New order #ORD-12344 (Rp 150,000)',
            'Added 2 items to cart',
            'Support request - shipping status'
        ]
    })
    
    st.dataframe(activity_data, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    show()
