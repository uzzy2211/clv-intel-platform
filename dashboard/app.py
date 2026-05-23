"""
app.py — Streamlit Dashboard for CLV Segmentation

An interactive, premium dashboard presenting customer segments,
predicted CLV insights, customer exploration, and model diagnostics.
"""

from __future__ import annotations

import os
import sys
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Append root to path to resolve src imports
sys.path.append(os.getcwd())

from src.config import load_config
from src.clv_model import predict_expected_profit
from lifetimes import BetaGeoFitter, GammaGammaFitter

# Set page config
st.set_page_config(
    page_title="Customer Lifetime Value (CLV) Portal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load config and data
cfg = load_config()
segments_path = os.path.join(cfg.data.processed_path, "04_customer_segments.csv")
raw_data_path = cfg.data.synthetic_path if not os.path.exists(cfg.data.raw_path) else cfg.data.raw_path

@st.cache_data
def load_dashboard_data():
    if not os.path.exists(segments_path):
        st.error(f"Customer segments data not found at {segments_path}. Please run the pipeline first.")
        return None, None
    df_segmented = pd.read_csv(segments_path, index_col="CustomerID")
    df_transactions = pd.read_csv(raw_data_path)
    df_transactions["InvoiceDate"] = pd.to_datetime(df_transactions["InvoiceDate"])
    df_transactions["TotalPrice"] = df_transactions["Quantity"] * df_transactions["UnitPrice"]
    return df_segmented, df_transactions

df_seg, df_trans = load_dashboard_data()

# Inject Premium HSL CSS styling
st.markdown(
    """
    <style>
    /* Styling headers */
    h1, h2, h3 {
        font-family: 'Outfit', 'Inter', sans-serif !important;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    /* Sleek card containers */
    div.metric-card {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        backdrop-filter: blur(10px);
        text-align: center;
        margin-bottom: 1rem;
    }
    div.metric-label {
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.6);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.5rem;
    }
    div.metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1DD1A1;
        font-family: 'Outfit', sans-serif;
    }
    div.metric-sub {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.4);
        margin-top: 0.3rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar layout
st.sidebar.title("💎 CLV Analytics Portal")
st.sidebar.markdown("Navigate through the ML lifecycle outcomes.")

page = st.sidebar.radio(
    "Select Tab",
    ["Overview", "Customer Segments", "Customer Explorer", "Model Insights", "Report Export"],
)

st.sidebar.info(
    "Built for Online Retail Analytics. Predicts future purchases and values "
    "using BG/NBD + Gamma-Gamma fitters."
)

if df_seg is None:
    st.warning("Data is missing. Run features, models, and clustering pipelines first.")
else:
    # -----------------------------------------------------------------------
    # PAGE 1: Overview
    # -----------------------------------------------------------------------
    if page == "Overview":
        st.title("🎯 E-Commerce Customer Value Dashboard")
        st.markdown("Top-level KPIs and behavioral summaries.")

        # Compute KPI numbers
        total_customers = len(df_seg)
        total_revenue = df_seg["monetary"].sum() * df_seg["frequency"].mean() # Estimate
        if df_trans is not None:
            total_revenue = df_trans["TotalPrice"].sum()
        
        avg_clv = df_seg["clv"].mean() if "clv" in df_seg.columns else 0.0
        avg_churn = df_seg["churn_probability"].mean() if "churn_probability" in df_seg.columns else 0.0

        # KPI Cards HTML layout
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Total Customers</div>'
                f'<div class="metric-value">{total_customers:,}</div>'
                f'<div class="metric-sub">Unique active buyers</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Historical Revenue</div>'
                f'<div class="metric-value">${total_revenue:,.2f}</div>'
                f'<div class="metric-sub">Sum of all invoices</div></div>',
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Average Projected CLV</div>'
                f'<div class="metric-value">${avg_clv:,.2f}</div>'
                f'<div class="metric-sub">Next {cfg.data.prediction_days} days projection</div></div>',
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Average Churn Risk</div>'
                f'<div class="metric-value">{avg_churn*100:.1f}%</div>'
                f'<div class="metric-sub">Probability of inactivity</div></div>',
                unsafe_allow_html=True,
            )

        st.write("---")

        # Overview charts
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("Customer Count by Segment")
            seg_counts = df_seg["segment"].value_counts().reset_index()
            seg_counts.columns = ["Segment", "Count"]
            fig1 = px.pie(
                seg_counts,
                values="Count",
                names="Segment",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig1.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig1, use_container_width=True)

        with col_c2:
            st.subheader("Future Expected Value (CLV) Contribution")
            clv_totals = df_seg.groupby("segment", observed=False)["clv"].sum().reset_index()
            clv_totals.columns = ["Segment", "Total CLV ($)"]
            fig2 = px.bar(
                clv_totals,
                x="Segment",
                y="Total CLV ($)",
                color="Segment",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    # -----------------------------------------------------------------------
    # PAGE 2: Customer Segments
    # -----------------------------------------------------------------------
    elif page == "Customer Segments":
        st.title("👥 Customer Cohort Analysis")
        st.markdown("Detailed breakdown of behaviors across the segments.")

        # Show table of segments averages
        st.subheader("Average Metrics per Customer Segment")
        segment_averages = (
            df_seg.groupby("segment", observed=False)
            .agg(
                customer_count=("frequency", "count"),
                avg_recency=("recency", "mean"),
                avg_frequency=("frequency", "mean"),
                avg_monetary=("monetary", "mean"),
                avg_clv=("clv", "mean"),
                avg_churn_risk=("churn_probability", "mean"),
            )
            .reset_index()
        )
        st.dataframe(segment_averages.style.format({
            "avg_recency": "{:.1f} days",
            "avg_frequency": "{:.1f} orders",
            "avg_monetary": "${:,.2f}",
            "avg_clv": "${:,.2f}",
            "avg_churn_risk": "{:.1%}",
        }), use_container_width=True)

        st.write("---")

        # PCA visualization
        st.subheader("2D PCA Customer Projection Map")
        st.markdown("Visualization of customer groupings projected in 2D space based on scaled RFM + CLV features.")
        if "pca_1" in df_seg.columns and "pca_2" in df_seg.columns:
            fig_pca = px.scatter(
                df_seg.reset_index(),
                x="pca_1",
                y="pca_2",
                color="segment",
                hover_data=["CustomerID", "recency", "frequency", "monetary", "clv"],
                color_discrete_sequence=px.colors.qualitative.Pastel,
                labels={"pca_1": "PCA Component 1", "pca_2": "PCA Component 2"},
            )
            fig_pca.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=500)
            st.plotly_chart(fig_pca, use_container_width=True)
        else:
            st.info("PCA components not found. Ensure clustering script is updated and ran.")

    # -----------------------------------------------------------------------
    # PAGE 3: Customer Explorer
    # -----------------------------------------------------------------------
    elif page == "Customer Explorer":
        st.title("🔍 Individual Customer Search")
        st.markdown("Inspect profiles and forecast details for specific customers.")

        # Customer selection
        segment_filter = st.selectbox("Filter list by Segment", ["All"] + list(df_seg["segment"].unique()))
        
        filtered_df = df_seg
        if segment_filter != "All":
            filtered_df = df_seg[df_seg["segment"] == segment_filter]
        
        cust_list = filtered_df.index.tolist()
        selected_cust_id = st.selectbox("Select Customer ID", cust_list)

        if selected_cust_id:
            profile = df_seg.loc[selected_cust_id]
            
            st.subheader(f"Profile: Customer {int(selected_cust_id)}")
            
            # Show summary stats
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                st.markdown(f"**Segment**: `{profile['segment']}`")
                st.markdown(f"**Tenure (Age)**: `{int(profile['tenure'])}` days")
                st.markdown(f"**Recency**: `{int(profile['recency'])}` days since last invoice")
            with col_p2:
                st.markdown(f"**Purchase Frequency**: `{int(profile['frequency'])}` dates")
                st.markdown(f"**Avg Order Value (Monetary)**: `${profile['monetary']:.2f}`")
                st.markdown(f"**Expected Order Profit**: `${profile['expected_avg_profit']:.2f}`")
            with col_p3:
                st.markdown(f"**Predicted Purchases (90d)**: `{profile['predicted_purchases']:.2f}`")
                st.markdown(f"**Churn Risk Score**: `{profile['churn_probability']*100:.1f}%`")
                st.markdown(f"**Calculated CLV (90d)**: **`${profile['clv']:.2f}`**")

            # Show historical transactions
            if df_trans is not None:
                st.write("---")
                st.subheader("Invoice History")
                cust_tx = df_trans[df_trans["CustomerID"] == selected_cust_id].sort_values("InvoiceDate", ascending=False)
                st.dataframe(cust_tx[["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "TotalPrice"]], use_container_width=True)

    # -----------------------------------------------------------------------
    # PAGE 4: Model Insights
    # -----------------------------------------------------------------------
    elif page == "Model Insights":
        st.title("🧠 ML Model Diagnostics")
        st.markdown("Evaluate fitters and view recency-frequency correlations.")

        # Load models
        if os.path.exists("models/bgf_model.pkl"):
            bgf = BetaGeoFitter()
            bgf.load_model("models/bgf_model.pkl")

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.subheader("Probability Alive Matrix")
                st.markdown("Visualizes probability of a customer being active based on purchase count and recency.")
                
                # Plotly Heatmap
                freq_range = np.arange(0, 30, 1)
                rec_range = np.arange(0, 365, 5)
                ff, rr = np.meshgrid(freq_range, rec_range)
                
                # Assume max T for matrix visualization
                max_t = int(df_seg["tenure"].max())
                probs_matrix = bgf.conditional_probability_alive(ff, rr, max_t)

                fig_heat = go.Figure(data=go.Heatmap(
                    z=probs_matrix,
                    x=freq_range,
                    y=rec_range,
                    colorscale="Plasma",
                    colorbar=dict(title="Prob Alive"),
                ))
                fig_heat.update_layout(
                    xaxis_title="Historical Purchases (Frequency)",
                    yaxis_title="Recency (Days)",
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=350,
                )
                st.plotly_chart(fig_heat, use_container_width=True)

            with col_m2:
                st.subheader("CLV Distribution Curve")
                st.markdown("Shows how predicted customer lifetime value is distributed across the cohort.")
                fig_dist = px.histogram(
                    df_seg,
                    x="clv",
                    nbins=50,
                    log_y=True,
                    color_discrete_sequence=["#1DD1A1"],
                    labels={"clv": "Customer Lifetime Value ($)", "count": "Customer Count (Log Scale)"},
                )
                fig_dist.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=350)
                st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info("Pickled models not found. Make sure clv_model.py was executed.")

    # -----------------------------------------------------------------------
    # PAGE 5: Report Export
    # -----------------------------------------------------------------------
    elif page == "Report Export":
        st.title("📥 Export Data and Reports")
        st.markdown("Download segment spreadsheets or generate official PDF files.")

        # Download CSV
        st.subheader("Download Customer Segment CSV")
        csv_data = df_seg.to_csv(index=True)
        st.download_button(
            label="💾 Download spreadsheet (CSV)",
            data=csv_data,
            file_name="clv_customer_segments.csv",
            mime="text/csv",
        )

        st.write("---")

        # PDF Report triggers
        st.subheader("Generate Executive PDF Report")
        st.markdown("Compiles model outcomes and clustering validation scores into a structured report.")
        if st.button("📄 Generate PDF Executive Summary"):
            st.info("Triggering report generation...")
            # We can invoke the pdf generation command or call python report generator
            try:
                import subprocess
                res = subprocess.run([sys.executable, "reports/generate_report.py"], capture_output=True, text=True)
                if res.returncode == 0:
                    st.success("Report generated successfully! Check reports/output/clv_segmentation_report.pdf")
                else:
                    st.error(f"Failed to generate report: {res.stderr}")
            except Exception as e:
                st.error(f"Error executing report script: {e}")
