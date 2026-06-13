"""
💬 Live Logs - Real-time Conversation Viewer
============================================
Debug active conversations with filtering and chat-style display.
"""

import streamlit as st
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import fetch_conversations, fetch_unique_phones


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Live Logs - WhatsApp Bot",
    page_icon="💬",
    layout="wide"
)

st.title("💬 Live Conversation Logs")
st.markdown("Debug and monitor active WhatsApp conversations in real-time.")

st.divider()


# ============================================================================
# SIDEBAR FILTERS
# ============================================================================

with st.sidebar:
    st.header("🔍 Filters")
    
    # Refresh button at top
    if st.button("🔄 Refresh Logs", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    # Phone filter
    try:
        phones = fetch_unique_phones()
        phone_options = ["All"] + phones
    except Exception as e:
        st.error(f"Error loading phones: {e}")
        phone_options = ["All"]
    
    selected_phone = st.selectbox(
        "Filter by Phone",
        options=phone_options,
        index=0,
        help="Select a phone number to filter conversations"
    )
    
    # Limit
    limit = st.slider(
        "Messages to Load",
        min_value=10,
        max_value=200,
        value=50,
        step=10
    )
    
    st.divider()
    
    # Auto-refresh toggle (informational only - no actual auto-refresh to avoid UI freeze)
    st.info(
        "💡 **Tip:** Click 'Refresh Logs' to see new messages. "
        "Auto-refresh is disabled to prevent UI freezing."
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str


def redact_phone(phone: str) -> str:
    """Partially redact phone number for privacy."""
    if not phone or len(phone) < 6:
        return phone
    return phone[:4] + "***" + phone[-3:]


def get_message_role(message_type: str) -> str:
    """Map message type to chat role."""
    if message_type in ["user", "incoming", "received"]:
        return "user"
    elif message_type in ["bot", "assistant", "outgoing", "sent"]:
        return "assistant"
    return "user"


# ============================================================================
# MAIN CONTENT
# ============================================================================

try:
    # Fetch conversations
    conversations = fetch_conversations(
        limit=limit,
        phone_filter=selected_phone if selected_phone != "All" else None
    )
    
    if not conversations:
        # Friendly empty state
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; background: #f0f2f6; border-radius: 10px; margin: 20px 0;">
            <h2>📭 No Conversations Yet</h2>
            <p style="color: #666; font-size: 1.1em;">
                Conversations will appear here once users start chatting with the bot.
            </p>
            <p style="color: #888; font-size: 0.9em;">
                Send a test message to your WhatsApp bot to see it here!
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show setup tips
        with st.expander("💡 Getting Started Tips"):
            st.markdown("""
            **To see conversations here:**
            
            1. **Start the WhatsApp bot** - Make sure the bot container is running
            2. **Send a test message** - Open WhatsApp and send "hi" to the bot
            3. **Check the database** - Verify the `conversations` table exists in Supabase
            4. **Refresh this page** - Click the "🔄 Refresh Logs" button
            
            **Troubleshooting:**
            - Check that `SUPABASE_URL` and `SUPABASE_KEY` are set correctly
            - Verify the `conversations` table schema matches expected format
            """)
    
    else:
        # Show stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Messages Loaded", len(conversations))
        with col2:
            unique_phones = len(set(c.get("user_phone", "") for c in conversations))
            st.metric("Unique Users", unique_phones)
        with col3:
            if conversations:
                latest = conversations[0].get("created_at", "N/A")
                st.metric("Latest Message", format_timestamp(latest)[:10])
        
        st.divider()
        
        # Group by phone for cleaner display
        if selected_phone == "All":
            # Show grouped view
            phones_in_view = list(set(c.get("user_phone", "Unknown") for c in conversations))
            
            selected_view_phone = st.selectbox(
                "Select conversation to view:",
                options=phones_in_view,
                format_func=redact_phone
            )
            
            # Filter to selected phone
            phone_conversations = [
                c for c in conversations 
                if c.get("user_phone") == selected_view_phone
            ]
        else:
            phone_conversations = conversations
        
        # Reverse for chronological order (oldest first)
        phone_conversations = list(reversed(phone_conversations))
        
        # Display as chat
        st.subheader(f"Conversation with {redact_phone(phone_conversations[0].get('user_phone', 'Unknown') if phone_conversations else 'N/A')}")
        
        for conv in phone_conversations:
            message = conv.get("message", "")
            message_type = conv.get("message_type", "user")
            timestamp = conv.get("created_at", "")
            
            role = get_message_role(message_type)
            
            with st.chat_message(role):
                st.markdown(message)
                st.caption(f"_{format_timestamp(timestamp)}_")
        
        # Raw data expander
        with st.expander("📊 View Raw Data"):
            import pandas as pd
            
            df = pd.DataFrame(conversations)
            
            # Redact phone numbers in display
            if "user_phone" in df.columns:
                df["user_phone_display"] = df["user_phone"].apply(redact_phone)
            
            # Select columns to display
            display_cols = ["user_phone_display", "message_type", "message", "created_at"]
            display_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(
                df[display_cols],
                use_container_width=True,
                hide_index=True
            )

except Exception as e:
    st.error(f"❌ Error loading conversations: {e}")
    
    with st.expander("🔧 Troubleshooting"):
        st.markdown(f"""
        **Error Details:**
        ```
        {str(e)}
        ```
        
        **Common Fixes:**
        1. Check that Supabase credentials are set in environment
        2. Verify the `conversations` table exists
        3. Check the table schema matches expected format
        
        **Expected Table Schema:**
        ```sql
        CREATE TABLE conversations (
            id UUID PRIMARY KEY,
            user_phone TEXT,
            message TEXT,
            message_type TEXT,  -- 'user' or 'bot'
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        ```
        """)


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption("💡 Messages are fetched from Supabase `conversations` table. Click Refresh to update.")
