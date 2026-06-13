"""
Settings Page
Bot configuration and system settings
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import get_user_role


def show():
    """Render the settings page."""
    st.title("⚙️ Settings")
    st.markdown("---")
    
    # Tabs for different settings categories
    tab1, tab2, tab3, tab4 = st.tabs([
        "🤖 Bot Settings", 
        "💰 Cost Management",
        "🔔 Notifications", 
        "🔐 Security"
    ])
    
    with tab1:
        st.subheader("Bot Configuration")
        
        with st.form("bot_settings"):
            st.markdown("**General Settings**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                bot_name = st.text_input("Bot Name", value="WhatsApp Seller Bot")
                welcome_message = st.text_area(
                    "Welcome Message",
                    value="Halo! Selamat datang di toko kami. Ada yang bisa saya bantu?"
                )
            
            with col2:
                language = st.selectbox("Language", options=["Indonesian", "English"])
                response_delay = st.slider("Response Delay (seconds)", 0.0, 5.0, 1.0)
            
            st.markdown("**RAG Settings**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                max_products = st.number_input(
                    "Max Products in Search Results", 
                    min_value=1, max_value=10, value=5
                )
                similarity_threshold = st.slider(
                    "Similarity Threshold", 
                    0.0, 1.0, 0.7
                )
            
            with col2:
                use_hybrid_search = st.checkbox("Enable Hybrid Search", value=True)
                rerank_results = st.checkbox("Enable Reranking", value=False)
            
            st.markdown("**LLM Settings**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                model = st.selectbox(
                    "LLM Model",
                    options=["gemini-1.5-flash", "gemini-1.5-pro", "gpt-3.5-turbo"]
                )
                temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
            
            with col2:
                max_input_tokens = st.number_input(
                    "Max Input Tokens", 
                    min_value=100, max_value=8000, value=1000
                )
                max_output_tokens = st.number_input(
                    "Max Output Tokens", 
                    min_value=100, max_value=2000, value=500
                )
            
            if st.form_submit_button("💾 Save Bot Settings"):
                st.success("Bot settings saved successfully!")
    
    with tab2:
        st.subheader("Cost Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Today's Cost", "Rp 12,500", "+15%")
            st.metric("This Month", "Rp 285,000", "+8%")
        
        with col2:
            st.metric("Daily Budget", "Rp 50,000")
            st.metric("Monthly Budget", "Rp 1,000,000")
        
        st.markdown("---")
        
        with st.form("budget_settings"):
            st.markdown("**Budget Limits**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                daily_budget = st.number_input(
                    "Daily Budget (Rp)", 
                    min_value=0, value=50000, step=10000
                )
            
            with col2:
                monthly_budget = st.number_input(
                    "Monthly Budget (Rp)", 
                    min_value=0, value=1000000, step=100000
                )
            
            enable_budget_alerts = st.checkbox("Enable Budget Alerts", value=True)
            budget_alert_threshold = st.slider(
                "Alert at % of Budget",
                50, 100, 80
            )
            
            if st.form_submit_button("💾 Save Budget Settings"):
                st.success("Budget settings saved successfully!")
    
    with tab3:
        st.subheader("Notification Settings")
        
        with st.form("notification_settings"):
            st.markdown("**Email Notifications**")
            
            notify_new_order = st.checkbox("New Order", value=True)
            notify_low_stock = st.checkbox("Low Stock Alert", value=True)
            notify_daily_report = st.checkbox("Daily Report", value=False)
            
            email = st.text_input("Notification Email", value="admin@example.com")
            
            st.markdown("**WhatsApp Notifications**")
            
            notify_wa_new_order = st.checkbox("Send Order Updates via WhatsApp", value=True)
            admin_phone = st.text_input("Admin WhatsApp Number", value="+6281234567890")
            
            if st.form_submit_button("💾 Save Notification Settings"):
                st.success("Notification settings saved successfully!")
    
    with tab4:
        st.subheader("Security Settings")
        
        st.markdown("**Safe Mode**")
        
        safe_mode = st.checkbox(
            "Enable Safe Mode (Stops all bot responses)",
            value=False,
            help="Use this to immediately stop the bot in case of issues"
        )
        
        if safe_mode:
            st.warning("⚠️ Safe Mode is enabled. Bot will not respond to any messages.")
        
        st.markdown("---")
        
        st.markdown("**API Keys**")
        
        st.text_input("Backend API Key", value="••••••••••••••••", type="password")
        
        if st.button("🔄 Regenerate API Key"):
            st.info("New API key generated. Please update your bot configuration.")
        
        st.markdown("---")
        
        st.markdown("**Rate Limiting**")
        
        with st.form("rate_limit_settings"):
            col1, col2 = st.columns(2)
            
            with col1:
                rate_limit_messages = st.number_input(
                    "Max Messages per Minute",
                    min_value=1, max_value=60, value=10
                )
            
            with col2:
                rate_limit_orders = st.number_input(
                    "Max Orders per Hour",
                    min_value=1, max_value=100, value=5
                )
            
            if st.form_submit_button("💾 Save Rate Limits"):
                st.success("Rate limit settings saved successfully!")


if __name__ == "__main__":
    show()
