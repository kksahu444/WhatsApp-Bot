"""
Conversations Page
View conversation history and analytics
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from components import metric_row, line_chart, pie_chart
from utils import get_api_client


def show():
    """Render the conversations page."""
    st.title("💬 Conversations")
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now() - timedelta(days=7), datetime.now())
        )
    
    with col2:
        intent_filter = st.selectbox(
            "Intent",
            options=["All", "Product Search", "Cart", "Checkout", "Support", "Other"]
        )
    
    with col3:
        search = st.text_input("Search", placeholder="Phone number...")
    
    # Metrics
    metrics = [
        {"title": "Total Messages", "value": "2,345"},
        {"title": "Unique Users", "value": "456"},
        {"title": "Avg Response Time", "value": "1.2s"},
        {"title": "Resolution Rate", "value": "94%"},
    ]
    metric_row(metrics)
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Messages Over Time")
        
        dates = pd.date_range(start=datetime.now() - timedelta(days=7), 
                             end=datetime.now(), freq='D')
        msg_data = pd.DataFrame({
            'date': dates,
            'messages': [320, 410, 380, 450, 520, 480, 390, 420][:len(dates)]
        })
        
        line_chart(msg_data, x='date', y='messages')
    
    with col2:
        st.subheader("Messages by Intent")
        
        intent_data = pd.DataFrame({
            'intent': ['Product Search', 'Cart', 'Checkout', 'Support', 'Other'],
            'count': [450, 320, 180, 150, 245]
        })
        
        pie_chart(intent_data, values='count', names='intent')
    
    # Recent Conversations
    st.markdown("---")
    st.subheader("Recent Conversations")
    
    conversations_data = pd.DataFrame({
        'Phone': ['+62812***4567', '+62813***8901', '+62814***2345',
                 '+62815***6789', '+62816***0123'],
        'Last Message': ['2 min ago', '5 min ago', '15 min ago', '30 min ago', '1 hour ago'],
        'Messages': [12, 5, 8, 3, 15],
        'Intent': ['Product Search', 'Checkout', 'Support', 'Cart', 'Product Search'],
        'Status': ['Active', 'Completed', 'Active', 'Active', 'Completed']
    })
    
    st.dataframe(conversations_data, use_container_width=True, hide_index=True)
    
    # Conversation Detail
    st.markdown("---")
    st.subheader("Conversation Detail")
    
    selected_phone = st.selectbox(
        "Select Conversation",
        options=conversations_data['Phone'].tolist()
    )
    
    if selected_phone:
        st.markdown(f"**Conversation with {selected_phone}**")
        
        # Mock conversation messages
        messages = [
            {"role": "user", "content": "Halo, ada sepatu olahraga?", "time": "14:30"},
            {"role": "bot", "content": "Halo! Tentu, kami punya beberapa pilihan sepatu olahraga. Ini rekomendasinya:", "time": "14:30"},
            {"role": "user", "content": "Yang Nike ada?", "time": "14:31"},
            {"role": "bot", "content": "Ada! Berikut sepatu Nike yang tersedia:\n1. Nike Air Max - Rp 1,200,000\n2. Nike Pegasus - Rp 950,000", "time": "14:31"},
            {"role": "user", "content": "Tambahin Nike Pegasus ke keranjang", "time": "14:32"},
            {"role": "bot", "content": "✅ Nike Pegasus sudah ditambahkan ke keranjang Anda. Total keranjang: Rp 950,000", "time": "14:32"},
        ]
        
        for msg in messages:
            if msg["role"] == "user":
                st.markdown(
                    f"""
                    <div style="background-color: #dcf8c6; padding: 10px; border-radius: 10px; 
                    margin: 5px 0; max-width: 70%; margin-left: auto;">
                        <small>{msg['time']}</small><br>
                        {msg['content']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style="background-color: #f1f0f0; padding: 10px; border-radius: 10px; 
                    margin: 5px 0; max-width: 70%;">
                        <small>🤖 Bot - {msg['time']}</small><br>
                        {msg['content']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )


if __name__ == "__main__":
    show()
