"""
Chart Components
Reusable chart components using Plotly
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st


def line_chart(data: pd.DataFrame, x: str, y: str, title: str = "", color: str = None):
    """Create a line chart."""
    fig = px.line(
        data,
        x=x,
        y=y,
        color=color,
        title=title,
        template="plotly_white"
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def bar_chart(data: pd.DataFrame, x: str, y: str, title: str = "", color: str = None, orientation: str = "v"):
    """Create a bar chart."""
    fig = px.bar(
        data,
        x=x,
        y=y,
        color=color,
        title=title,
        template="plotly_white",
        orientation=orientation
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def pie_chart(data: pd.DataFrame, values: str, names: str, title: str = ""):
    """Create a pie chart."""
    fig = px.pie(
        data,
        values=values,
        names=names,
        title=title,
        template="plotly_white",
        hole=0.4
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def funnel_chart(data: pd.DataFrame, x: str, y: str, title: str = ""):
    """Create a funnel chart."""
    fig = go.Figure(go.Funnel(
        y=data[y],
        x=data[x],
        textinfo="value+percent initial"
    ))
    
    fig.update_layout(
        title=title,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)


def heatmap(data: pd.DataFrame, x: str, y: str, z: str, title: str = ""):
    """Create a heatmap."""
    pivot = data.pivot(index=y, columns=x, values=z)
    
    fig = px.imshow(
        pivot,
        title=title,
        template="plotly_white",
        color_continuous_scale="Blues"
    )
    
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    st.plotly_chart(fig, use_container_width=True)
