"""
Metric Card Component
Reusable metric display card
"""

import streamlit as st


def metric_card(title: str, value: str, delta: str = None, delta_color: str = "normal"):
    """
    Display a metric card.
    
    Args:
        title: Card title
        value: Main value to display
        delta: Optional delta value
        delta_color: 'normal', 'inverse', or 'off'
    """
    st.metric(
        label=title,
        value=value,
        delta=delta,
        delta_color=delta_color
    )


def metric_row(metrics: list):
    """
    Display a row of metric cards.
    
    Args:
        metrics: List of dicts with keys: title, value, delta (optional), delta_color (optional)
    """
    cols = st.columns(len(metrics))
    
    for col, metric in zip(cols, metrics):
        with col:
            metric_card(
                title=metric.get('title', ''),
                value=metric.get('value', ''),
                delta=metric.get('delta'),
                delta_color=metric.get('delta_color', 'normal')
            )
