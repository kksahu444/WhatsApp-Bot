"""
WhatsApp Seller Bot Dashboard
Main Application Entry Point
"""

import streamlit as st
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="WhatsApp Seller Bot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application."""
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50?text=Logo", width=150)
        st.markdown("---")
        
        st.markdown("### 🤖 WhatsApp Seller Bot")
        st.markdown("Admin Dashboard")
        
        st.markdown("---")
        
        # System Status
        st.markdown("### System Status")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("🟢 **Bot**")
            st.markdown("🟢 **API**")
        with col2:
            st.markdown("Online")
            st.markdown("Healthy")
        
        st.markdown("---")
        
        # Quick Stats
        st.markdown("### Today's Stats")
        st.metric("Messages", "234", "+12%")
        st.metric("Orders", "15", "+3")
        st.metric("Revenue", "Rp 2.5M")
        
        st.markdown("---")
        
        # Footer
        st.markdown(
            """
            <div style="text-align: center; color: #888; font-size: 0.8rem;">
                v1.0.0 | © 2024
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Main content
    st.markdown('<p class="main-header">Welcome to WhatsApp Seller Bot</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Manage your WhatsApp commerce bot from one place</p>', unsafe_allow_html=True)
    
    # Quick Actions
    st.markdown("### Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 View Analytics", use_container_width=True):
            st.switch_page("pages/1_📊_Overview.py")
    
    with col2:
        if st.button("📦 Manage Orders", use_container_width=True):
            st.switch_page("pages/2_📦_Orders.py")
    
    with col3:
        if st.button("🛍️ Products", use_container_width=True):
            st.switch_page("pages/3_🛍️_Products.py")
    
    with col4:
        if st.button("💬 Conversations", use_container_width=True):
            st.switch_page("pages/4_💬_Conversations.py")
    
    st.markdown("---")
    
    # Recent Activity Feed
    st.markdown("### Recent Activity")
    
    activities = [
        {"icon": "🛒", "text": "New order #ORD-12345 from +62812***4567", "time": "2 min ago"},
        {"icon": "💬", "text": "Product inquiry from +62813***8901", "time": "5 min ago"},
        {"icon": "📦", "text": "Order #ORD-12344 shipped", "time": "15 min ago"},
        {"icon": "🛍️", "text": "Product 'Premium Headphones' running low (5 left)", "time": "30 min ago"},
        {"icon": "✅", "text": "Order #ORD-12343 delivered", "time": "1 hour ago"},
    ]
    
    for activity in activities:
        st.markdown(
            f"""
            <div style="padding: 10px; border-left: 3px solid #1f77b4; margin: 10px 0; background: #f8f9fa;">
                {activity['icon']} {activity['text']}
                <span style="float: right; color: #888; font-size: 0.9rem;">{activity['time']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Getting Started Guide
    with st.expander("📖 Getting Started Guide"):
        st.markdown("""
        ### Welcome to your WhatsApp Seller Bot Dashboard!
        
        Here's how to get started:
        
        1. **Configure your products** - Go to Products page and add your inventory
        2. **Set up the bot** - Configure bot settings including welcome message and response style
        3. **Connect WhatsApp** - Scan the QR code to connect your WhatsApp Business account
        4. **Monitor conversations** - Watch real-time conversations and analytics
        
        Need help? Check out the [documentation](https://docs.example.com) or contact support.
        """)


if __name__ == "__main__":
    main()
