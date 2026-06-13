"""
🧠 Brain Manager - RAG Knowledge Base Manager
==============================================
Upload documents to expand the bot's knowledge without coding.
"""

import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.rag_ops import ingest_document, get_knowledge_base_stats, search_knowledge_base


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Brain Manager - WhatsApp Bot",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Brain Manager")
st.markdown("Add product knowledge to the bot's brain without writing code.")

st.divider()


# ============================================================================
# SIDEBAR - KNOWLEDGE BASE STATS
# ============================================================================

with st.sidebar:
    st.header("📊 Knowledge Base Stats")
    
    if st.button("🔄 Refresh Stats", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    try:
        stats = get_knowledge_base_stats()
        
        st.metric("Total Documents", stats.get("total_records", 0))
        
        sources = stats.get("sources", [])
        st.metric("Unique Sources", len(sources))
        
        if sources:
            st.markdown("**Indexed Files:**")
            for source in sources[:10]:  # Show max 10
                st.caption(f"📄 {source}")
            if len(sources) > 10:
                st.caption(f"... and {len(sources) - 10} more")
        
        source_types = stats.get("source_types", {})
        if source_types:
            st.markdown("**By Type:**")
            for stype, count in source_types.items():
                st.caption(f"• {stype}: {count}")
        
        if stats.get("error"):
            st.warning(f"⚠️ {stats['error']}")
            
    except Exception as e:
        st.error(f"Error loading stats: {e}")


# ============================================================================
# MAIN CONTENT - TABS
# ============================================================================

tab1, tab2, tab3 = st.tabs(["📤 Upload Documents", "🔍 Test Search", "⚙️ Settings"])


# ----------------------------------------------------------------------------
# TAB 1: UPLOAD DOCUMENTS
# ----------------------------------------------------------------------------

with tab1:
    st.header("Upload New Documents")
    st.markdown("""
    Upload PDF or TXT files to add to the bot's knowledge base. 
    The content will be chunked, embedded, and stored for RAG search.
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt"],
            help="Supported formats: PDF, TXT"
        )
    
    with col2:
        source_type = st.selectbox(
            "Document Type",
            options=["product_catalog", "faq", "policy", "general", "other"],
            help="Categorize the document for better organization"
        )
    
    if uploaded_file:
        st.info(f"📄 **File:** {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            ingest_button = st.button(
                "🧠 Ingest to Brain",
                type="primary",
                use_container_width=True
            )
        
        if ingest_button:
            with st.spinner("Processing document... This may take a moment."):
                try:
                    success, num_chunks, message = ingest_document(
                        file_obj=uploaded_file,
                        filename=uploaded_file.name,
                        source_type=source_type
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                        
                        # Show details
                        with st.expander("📊 Ingestion Details"):
                            st.markdown(f"""
                            - **File:** {uploaded_file.name}
                            - **Type:** {source_type}
                            - **Chunks Created:** {num_chunks}
                            - **Embedding Model:** `models/embedding-001`
                            - **Storage:** LanceDB
                            """)
                    else:
                        st.error(f"❌ {message}")
                        
                        # Show troubleshooting
                        with st.expander("🔧 Troubleshooting"):
                            st.markdown("""
                            **Common Issues:**
                            
                            1. **Empty PDF:** The PDF might be scanned (image-only). 
                               Try a text-based PDF or use OCR first.
                            
                            2. **Encoding Issues:** For TXT files, ensure UTF-8 encoding.
                            
                            3. **API Limits:** Gemini API might be rate-limited. 
                               Wait a minute and try again.
                            
                            4. **File Too Large:** Very large files may timeout. 
                               Try splitting into smaller files.
                            """)
                            
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")
                    st.exception(e)
    
    else:
        # Show placeholder
        st.markdown("""
        <div style="text-align: center; padding: 40px; background: #f0f2f6; border-radius: 10px; border: 2px dashed #ccc;">
            <h3>📁 Drop a file here</h3>
            <p style="color: #666;">or click "Browse files" above</p>
            <p style="color: #888; font-size: 0.9em;">Supported: PDF, TXT</p>
        </div>
        """, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# TAB 2: TEST SEARCH
# ----------------------------------------------------------------------------

with tab2:
    st.header("Test Knowledge Base Search")
    st.markdown("Test how the bot will search the knowledge base for user queries.")
    
    query = st.text_input(
        "Enter a test query",
        placeholder="e.g., 'wireless headphones under 5000'"
    )
    
    num_results = st.slider("Number of results", min_value=1, max_value=10, value=5)
    
    if query:
        with st.spinner("Searching..."):
            try:
                results = search_knowledge_base(query, limit=num_results)
                
                if results:
                    st.success(f"Found {len(results)} results")
                    
                    for i, result in enumerate(results, 1):
                        with st.expander(f"Result {i} - Score: {result.get('_distance', 'N/A'):.4f}"):
                            st.markdown(f"**Source:** {result.get('source', 'Unknown')}")
                            st.markdown(f"**Type:** {result.get('source_type', 'Unknown')}")
                            st.markdown(f"**Chunk:** {result.get('chunk_index', '?')}/{result.get('total_chunks', '?')}")
                            st.divider()
                            st.markdown(result.get('text', 'No text'))
                else:
                    st.warning("No results found. Try uploading some documents first!")
                    
            except Exception as e:
                st.error(f"Search error: {e}")


# ----------------------------------------------------------------------------
# TAB 3: SETTINGS
# ----------------------------------------------------------------------------

with tab3:
    st.header("Knowledge Base Settings")
    
    st.markdown("### Current Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        | Setting | Value |
        |---------|-------|
        | **LanceDB Path** | `/app/data/lancedb` |
        | **Table Name** | `products` |
        | **Embedding Model** | `models/embedding-001` |
        | **Chunk Size** | 500 chars |
        | **Chunk Overlap** | 50 chars |
        """)
    
    with col2:
        st.markdown("""
        **Environment Variables:**
        - `LANCEDB_PATH` - Vector DB location
        - `GEMINI_API_KEY` - For embeddings
        - `SUPABASE_URL` - Database URL
        - `SUPABASE_KEY` - Database key
        """)
    
    st.divider()
    
    st.markdown("### Danger Zone")
    
    st.warning("⚠️ These actions cannot be undone!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Clear Cache", help="Clear Streamlit cache"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Cache cleared!")
            st.rerun()
    
    with col2:
        st.button(
            "🔄 Rebuild Index",
            disabled=True,
            help="Coming soon - Rebuild vector index"
        )
    
    with col3:
        st.button(
            "💣 Delete All",
            disabled=True,
            help="Coming soon - Delete all documents"
        )


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption(
    "🧠 Knowledge is stored in LanceDB (shared with backend). "
    "Embeddings use Google Gemini `models/embedding-001`."
)
