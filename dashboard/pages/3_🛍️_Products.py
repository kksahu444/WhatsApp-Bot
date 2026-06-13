"""
Products Management Page
View and manage products
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from components import metric_row
from utils import get_api_client


def show():
    """Render the products page."""
    st.title("🛍️ Products Management")
    st.markdown("---")
    
    # Tabs
    tab1, tab2 = st.tabs(["📋 Product List", "➕ Add Product"])
    
    with tab1:
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            category_filter = st.selectbox(
                "Category",
                options=["All", "Electronics", "Fashion", "Food", "Home", "Beauty"]
            )
        
        with col2:
            status_filter = st.selectbox(
                "Status",
                options=["All", "Active", "Inactive", "Low Stock"]
            )
        
        with col3:
            search = st.text_input("Search", placeholder="Product name or SKU...")
        
        # Metrics
        metrics = [
            {"title": "Total Products", "value": "245"},
            {"title": "Active", "value": "220"},
            {"title": "Low Stock", "value": "15"},
            {"title": "Out of Stock", "value": "10"},
        ]
        metric_row(metrics)
        
        st.markdown("---")
        
        # Products Table
        products_data = pd.DataFrame({
            'SKU': ['SKU-001', 'SKU-002', 'SKU-003', 'SKU-004', 'SKU-005'],
            'Product Name': ['Premium Headphones', 'Wireless Mouse', 'USB-C Hub', 
                           'Mechanical Keyboard', 'Laptop Stand'],
            'Category': ['Electronics', 'Electronics', 'Electronics', 'Electronics', 'Home'],
            'Price': ['Rp 350,000', 'Rp 150,000', 'Rp 250,000', 'Rp 450,000', 'Rp 200,000'],
            'Stock': [25, 50, 15, 8, 30],
            'Status': ['Active', 'Active', 'Active', 'Low Stock', 'Active'],
        })
        
        st.dataframe(products_data, use_container_width=True, hide_index=True)
        
        # Edit Product
        st.markdown("---")
        st.subheader("Edit Product")
        
        selected_product = st.selectbox(
            "Select Product",
            options=products_data['SKU'].tolist()
        )
        
        if selected_product:
            with st.form("edit_product"):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("Product Name", value="Premium Headphones")
                    category = st.selectbox(
                        "Category",
                        options=["Electronics", "Fashion", "Food", "Home", "Beauty"],
                        index=0
                    )
                    price = st.number_input("Price (Rp)", value=350000, step=1000)
                
                with col2:
                    stock = st.number_input("Stock Quantity", value=25, step=1)
                    is_active = st.checkbox("Active", value=True)
                    image_url = st.text_input("Image URL", value="https://example.com/image.jpg")
                
                description = st.text_area(
                    "Description",
                    value="High-quality premium headphones with noise cancellation."
                )
                
                if st.form_submit_button("💾 Save Changes"):
                    st.success("Product updated successfully!")
    
    with tab2:
        st.subheader("Add New Product")
        
        with st.form("add_product"):
            col1, col2 = st.columns(2)
            
            with col1:
                sku = st.text_input("SKU", placeholder="SKU-XXX")
                name = st.text_input("Product Name", placeholder="Product name...")
                category = st.selectbox(
                    "Category",
                    options=["Electronics", "Fashion", "Food", "Home", "Beauty"]
                )
            
            with col2:
                price = st.number_input("Price (Rp)", min_value=0, step=1000)
                stock = st.number_input("Stock Quantity", min_value=0, step=1)
                image_url = st.text_input("Image URL", placeholder="https://...")
            
            description = st.text_area("Description", placeholder="Product description...")
            
            if st.form_submit_button("➕ Add Product"):
                if sku and name and price > 0:
                    st.success(f"Product {name} added successfully!")
                else:
                    st.error("Please fill in all required fields.")


if __name__ == "__main__":
    show()
