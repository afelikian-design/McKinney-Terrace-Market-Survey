"""DFW Market Survey Dashboard — Streamlit application.

Run with:  streamlit run app.py
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PROPERTIES, UNIT_TYPES
from models import Unit
from excel_export import workbook_to_bytes, save_workbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# -- Page config --
st.set_page_config(
    page_title="DFW Market Survey",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Color palette for charts --
COLOR_PALETTE = [
    "#C00000", "#0070C0", "#00B050", "#7030A0",
    "#FF6600", "#00B0F0", "#FFC000",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(use_live: bool = False) -> pd.DataFrame:
    """Load unit data. Use live scraping or sample data."""
    if use_live:
        try:
            from scrapers.all_properties import run_all_scrapers
            units = run_all_scrapers()
        except Exception as e:
            st.error(f"Live scraping failed: {e}. Falling back to sample data.")
            from scrapers.sample_data import generate_sample_data
            units = generate_sample_data()
    else:
        from scrapers.sample_data import generate_sample_data
        units = generate_sample_data()

    records = [u.to_dict() for u in units]
    df = pd.DataFrame(records)
    return df


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def build_scatter_chart(df: pd.DataFrame, unit_type: str) -> px.scatter:
    """Build a scatter plot for a given unit type (Sq Ft vs Asking Rent)."""
    type_df = df[df["Unit Type"] == unit_type].copy()
    type_df = type_df.dropna(subset=["Sq Ft", "Asking Rent"])
    type_df = type_df[type_df["Sq Ft"] > 0]
    type_df = type_df[type_df["Asking Rent"] > 0]

    if len(type_df) == 0:
        return None

    properties = type_df["Property Name"].unique().tolist()
    color_map = {p: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, p in enumerate(
        df["Property Name"].unique().tolist()
    )}

    fig = px.scatter(
        type_df,
        x="Sq Ft",
        y="Asking Rent",
        color="Property Name",
        color_discrete_map=color_map,
        hover_data=["Unit", "Floorplan", "PSF"],
        title=f"{unit_type} — Rent vs. Square Feet",
        labels={"Sq Ft": "Square Feet", "Asking Rent": "Rental Rates ($)"},
    )

    # Add trendline
    fig.update_layout(
        plot_bgcolor="white",
        xaxis=dict(gridcolor="#E0E0E0", title_font_size=12),
        yaxis=dict(gridcolor="#E0E0E0", title_font_size=12, tickprefix="$"),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        margin=dict(l=60, r=20, t=40, b=80),
        height=450,
    )

    # Add OLS trendline
    if len(type_df) >= 2:
        import numpy as np
        x = type_df["Sq Ft"].values
        y = type_df["Asking Rent"].values
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        x_range = np.linspace(x.min(), x.max(), 100)
        fig.add_scatter(
            x=x_range, y=p(x_range),
            mode="lines",
            line=dict(color="#333333", width=2, dash="dash"),
            name="Market Trendline",
            showlegend=True,
        )

    return fig


# ---------------------------------------------------------------------------
# Dashboard layout
# ---------------------------------------------------------------------------

def main():
    # -- Sidebar --
    st.sidebar.title("DFW Market Survey")
    st.sidebar.markdown("**McKinney / Allen Area Comps**")
    st.sidebar.markdown("---")

    use_live = st.sidebar.button("🔄 Refresh Live Data", help="Scrape all 7 properties (requires Playwright)")

    if "df" not in st.session_state or use_live:
        with st.spinner("Loading data..." if not use_live else "Scraping live data from all 7 properties..."):
            st.session_state.df = load_data(use_live=use_live)
            st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df = st.session_state.df

    st.sidebar.markdown(f"**Last Updated:** {st.session_state.get('last_updated', 'N/A')}")
    st.sidebar.markdown(f"**Total Units:** {len(df)}")

    # -- Filters --
    st.sidebar.markdown("### Filters")

    all_properties = sorted(df["Property Name"].unique().tolist())
    selected_properties = st.sidebar.multiselect(
        "Properties", all_properties, default=all_properties
    )

    selected_types = st.sidebar.multiselect(
        "Unit Types", UNIT_TYPES, default=UNIT_TYPES
    )

    rent_min = int(df["Asking Rent"].min()) if df["Asking Rent"].notna().any() else 0
    rent_max = int(df["Asking Rent"].max()) if df["Asking Rent"].notna().any() else 5000
    rent_range = st.sidebar.slider(
        "Rent Range ($)", rent_min, rent_max, (rent_min, rent_max), step=50
    )

    # Apply filters
    filtered = df[
        (df["Property Name"].isin(selected_properties)) &
        (df["Unit Type"].isin(selected_types)) &
        (df["Asking Rent"].between(rent_range[0], rent_range[1]))
    ].copy()

    # -- Download button --
    st.sidebar.markdown("---")
    excel_bytes = workbook_to_bytes(filtered)
    st.sidebar.download_button(
        label="📥 Download to Excel",
        data=excel_bytes,
        file_name=f"DFW_Market_Survey_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # -- Concessions section --
    concession_df = filtered[filtered["Concessions"].notna() & (filtered["Concessions"] != "")]
    if len(concession_df) > 0:
        st.sidebar.markdown("### Active Concessions")
        for prop in concession_df["Property Name"].unique():
            conc = concession_df[concession_df["Property Name"] == prop]["Concessions"].iloc[0]
            st.sidebar.markdown(f"**{prop}:** {conc}")

    # ===== MAIN CONTENT =====

    st.title("DFW Multifamily Market Survey")
    st.markdown(f"**{len(filtered)}** units across **{filtered['Property Name'].nunique()}** properties")

    # -- Summary metrics --
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_rent = filtered["Asking Rent"].mean()
        st.metric("Avg Asking Rent", f"${avg_rent:,.0f}" if pd.notna(avg_rent) else "N/A")
    with col2:
        avg_psf = filtered["PSF"].mean()
        st.metric("Avg PSF", f"${avg_psf:.2f}" if pd.notna(avg_psf) else "N/A")
    with col3:
        avg_sqft = filtered["Sq Ft"].mean()
        st.metric("Avg Sq Ft", f"{avg_sqft:,.0f}" if pd.notna(avg_sqft) else "N/A")
    with col4:
        st.metric("Total Units", len(filtered))

    st.markdown("---")

    # -- Charts and tables for each unit type --
    for unit_type in UNIT_TYPES:
        type_df = filtered[filtered["Unit Type"] == unit_type]
        if len(type_df) == 0:
            continue

        st.header(unit_type)

        # Chart
        fig = build_scatter_chart(filtered, unit_type)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        # Stats row
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(f"{unit_type} Units", len(type_df))
        with c2:
            avg_r = type_df["Asking Rent"].mean()
            st.metric("Avg Rent", f"${avg_r:,.0f}" if pd.notna(avg_r) else "N/A")
        with c3:
            avg_p = type_df["PSF"].mean()
            st.metric("Avg PSF", f"${avg_p:.2f}" if pd.notna(avg_p) else "N/A")
        with c4:
            avg_s = type_df["Sq Ft"].mean()
            st.metric("Avg Sq Ft", f"{avg_s:,.0f}" if pd.notna(avg_s) else "N/A")

        # Data table
        display_cols = [
            "Property Name", "Unit", "Floorplan", "Sq Ft",
            "Asking Rent", "PSF", "Move-In Date", "Concessions",
        ]
        available_cols = [c for c in display_cols if c in type_df.columns]
        st.dataframe(
            type_df[available_cols].sort_values(["Property Name", "Sq Ft"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Asking Rent": st.column_config.NumberColumn(format="$%d"),
                "PSF": st.column_config.NumberColumn(format="$%.2f"),
                "Sq Ft": st.column_config.NumberColumn(format="%d"),
            },
        )

        st.markdown("---")

    # -- Summary by property --
    st.header("Summary by Property")

    summary_rows = []
    for prop in all_properties:
        prop_df = filtered[filtered["Property Name"] == prop]
        if len(prop_df) == 0:
            continue
        row = {"Property": prop, "Total Units": len(prop_df)}
        for utype in UNIT_TYPES:
            t = prop_df[prop_df["Unit Type"] == utype]
            row[f"{utype} Count"] = len(t)
            if len(t) > 0:
                row[f"{utype} Avg Rent"] = f"${t['Asking Rent'].mean():,.0f}"
                row[f"{utype} Avg PSF"] = f"${t['PSF'].mean():.2f}"
            else:
                row[f"{utype} Avg Rent"] = "-"
                row[f"{utype} Avg PSF"] = "-"
        row["Avg Sq Ft"] = f"{prop_df['Sq Ft'].mean():,.0f}"
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    # -- Data quality notes --
    floorplan_only = filtered[filtered["Data Level"] == "floorplan"]
    if len(floorplan_only) > 0:
        st.warning(
            f"**Note:** {len(floorplan_only)} entries are floor-plan level only "
            "(no unit-level data available). Properties: "
            + ", ".join(floorplan_only["Property Name"].unique())
        )


if __name__ == "__main__":
    main()
