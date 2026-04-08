"""Generate a standalone HTML dashboard that opens in any browser.

Run:  python generate_html_dashboard.py
Then open: output/dashboard.html
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from scrapers.sample_data import generate_sample_data
from models import Unit

# Load data
units = generate_sample_data()
df = pd.DataFrame([u.to_dict() for u in units])

# Color palette
COLORS = {
    "Davis at the Square": "#C00000",
    "Magnolia on the Green": "#0070C0",
    "The Link at Twin Creeks": "#00B050",
    "The Bridge at McKinney": "#7030A0",
    "Kinstead": "#FF6600",
    "Collin Square": "#00B0F0",
    "McKinney Terrace": "#FFC000",
}

UNIT_TYPES = ["Studios", "1BR", "2BR", "3BR"]


def build_chart_data(unit_type):
    """Build Plotly-compatible trace data for a unit type."""
    tdf = df[df["Unit Type"] == unit_type].copy()
    tdf = tdf.dropna(subset=["Sq Ft", "Asking Rent"])
    tdf = tdf[tdf["Sq Ft"] > 0]
    tdf = tdf[tdf["Asking Rent"] > 0]

    traces = []
    for prop in sorted(tdf["Property Name"].unique()):
        pdf = tdf[tdf["Property Name"] == prop]
        traces.append({
            "x": pdf["Sq Ft"].tolist(),
            "y": pdf["Asking Rent"].tolist(),
            "text": [f"Unit {r['Unit']}<br>{r['Floorplan']}<br>${r['Asking Rent']:,.0f}<br>{r['Sq Ft']} SF<br>${r['PSF']:.2f}/SF"
                     for _, r in pdf.iterrows()],
            "name": prop,
            "mode": "markers",
            "type": "scatter",
            "marker": {"color": COLORS.get(prop, "#999"), "size": 9},
            "hovertemplate": "%{text}<extra></extra>",
        })

    # Trendline
    if len(tdf) >= 2:
        import numpy as np
        x = tdf["Sq Ft"].values
        y = tdf["Asking Rent"].values
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        x_range = np.linspace(x.min(), x.max(), 50)
        traces.append({
            "x": x_range.tolist(),
            "y": p(x_range).tolist(),
            "name": "Market Trendline",
            "mode": "lines",
            "type": "scatter",
            "line": {"color": "#333", "width": 2, "dash": "dash"},
        })

    return traces


def build_table_html(unit_type):
    """Build HTML table for a unit type."""
    tdf = df[df["Unit Type"] == unit_type].sort_values(["Property Name", "Sq Ft"])
    if len(tdf) == 0:
        return "<p>No units available.</p>"

    rows = []
    for _, r in tdf.iterrows():
        color = COLORS.get(r["Property Name"], "#333")
        rows.append(f"""<tr>
            <td style="color:{color};font-weight:500">{r['Property Name']}</td>
            <td class="center">{r['Unit']}</td>
            <td class="center">{r['Floorplan']}</td>
            <td class="right">{int(r['Sq Ft']):,}</td>
            <td class="right">${r['Asking Rent']:,.0f}</td>
            <td class="right">${r['PSF']:.2f}</td>
            <td class="center">{r['Move-In Date'] or ''}</td>
            <td>{r['Concessions'] or ''}</td>
        </tr>""")

    return f"""<table class="data-table">
        <thead><tr>
            <th>Property Name</th><th>Unit</th><th>Floorplan</th>
            <th>Sq Ft</th><th>Asking Rent</th><th>PSF</th>
            <th>Move-In Date</th><th>Concessions</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
    </table>"""


def build_summary_html():
    """Build summary table HTML."""
    rows = []
    for prop in sorted(df["Property Name"].unique()):
        pdf = df[df["Property Name"] == prop]
        counts = {ut: len(pdf[pdf["Unit Type"] == ut]) for ut in UNIT_TYPES}
        total = len(pdf)
        avg_rent = pdf["Asking Rent"].mean()
        avg_psf = pdf["PSF"].mean()
        avg_sqft = pdf["Sq Ft"].mean()
        color = COLORS.get(prop, "#333")

        cells = f'<td style="color:{color};font-weight:600">{prop}</td>'
        for ut in UNIT_TYPES:
            cells += f'<td class="center">{counts[ut] if counts[ut] > 0 else "-"}</td>'
        cells += f'<td class="center"><b>{total}</b></td>'
        cells += f'<td class="right">${avg_rent:,.0f}</td>'
        cells += f'<td class="right">${avg_psf:.2f}</td>'
        cells += f'<td class="right">{avg_sqft:,.0f}</td>'
        rows.append(f"<tr>{cells}</tr>")

    # Totals row
    total_cells = '<td style="font-weight:700">Wtd Avg / Total</td>'
    for ut in UNIT_TYPES:
        c = len(df[df["Unit Type"] == ut])
        total_cells += f'<td class="center"><b>{c}</b></td>'
    total_cells += f'<td class="center"><b>{len(df)}</b></td>'
    total_cells += f'<td class="right"><b>${df["Asking Rent"].mean():,.0f}</b></td>'
    total_cells += f'<td class="right"><b>${df["PSF"].mean():.2f}</b></td>'
    total_cells += f'<td class="right"><b>{df["Sq Ft"].mean():,.0f}</b></td>'
    rows.append(f'<tr style="background:#D6E4F0">{total_cells}</tr>')

    return f"""<table class="data-table">
        <thead><tr>
            <th>Property</th><th>Studios</th><th>1BR</th><th>2BR</th><th>3BR</th>
            <th>Total</th><th>Avg Rent</th><th>Avg PSF</th><th>Avg Sq Ft</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
    </table>"""


# Build chart data for all unit types
chart_data = {}
for ut in UNIT_TYPES:
    chart_data[ut] = build_chart_data(ut)

# Concessions
conc_html = ""
conc_df = df[df["Concessions"].notna() & (df["Concessions"] != "")]
if len(conc_df) > 0:
    conc_items = []
    for prop in conc_df["Property Name"].unique():
        c = conc_df[conc_df["Property Name"] == prop]["Concessions"].iloc[0]
        color = COLORS.get(prop, "#333")
        conc_items.append(f'<li><span style="color:{color};font-weight:600">{prop}:</span> {c}</li>')
    conc_html = f'<div class="conc-box"><h3>Active Concessions</h3><ul>{"".join(conc_items)}</ul></div>'

# Generate HTML
date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DFW Market Survey Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; color: #333; }}
.header {{ background: linear-gradient(135deg, #1F4E79, #2980b9); color: white; padding: 24px 40px; }}
.header h1 {{ font-size: 28px; margin-bottom: 4px; }}
.header p {{ opacity: 0.85; font-size: 14px; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
.metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }}
.metric-card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
.metric-card .value {{ font-size: 28px; font-weight: 700; color: #1F4E79; }}
.metric-card .label {{ font-size: 12px; color: #666; text-transform: uppercase; margin-top: 4px; }}
.section {{ background: white; border-radius: 8px; padding: 24px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.section h2 {{ font-size: 20px; color: #1F4E79; margin-bottom: 16px; border-bottom: 2px solid #1F4E79; padding-bottom: 8px; }}
.sub-metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0; }}
.sub-metric {{ background: #f8f9fa; border-radius: 6px; padding: 12px; text-align: center; }}
.sub-metric .val {{ font-size: 18px; font-weight: 600; color: #1F4E79; }}
.sub-metric .lbl {{ font-size: 11px; color: #888; }}
.data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 16px; }}
.data-table th {{ background: #1F4E79; color: white; padding: 10px 12px; text-align: left; font-weight: 600; position: sticky; top: 0; }}
.data-table td {{ padding: 8px 12px; border-bottom: 1px solid #e8e8e8; }}
.data-table tr:hover {{ background: #f0f4f8; }}
.data-table .center {{ text-align: center; }}
.data-table .right {{ text-align: right; }}
.chart-container {{ width: 100%; height: 420px; }}
.conc-box {{ background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 16px; margin: 20px 0; }}
.conc-box h3 {{ color: #856404; margin-bottom: 8px; }}
.conc-box ul {{ margin-left: 20px; }}
.conc-box li {{ margin: 4px 0; }}
.footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
.table-scroll {{ max-height: 500px; overflow-y: auto; }}
@media (max-width: 768px) {{
    .metrics, .sub-metrics {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>

<div class="header">
    <h1>DFW Multifamily Market Survey</h1>
    <p>{len(df)} units across {df['Property Name'].nunique()} properties &mdash; Generated {date_str}</p>
</div>

<div class="container">

<div class="metrics">
    <div class="metric-card">
        <div class="value">${df['Asking Rent'].mean():,.0f}</div>
        <div class="label">Avg Asking Rent</div>
    </div>
    <div class="metric-card">
        <div class="value">${df['PSF'].mean():.2f}</div>
        <div class="label">Avg PSF</div>
    </div>
    <div class="metric-card">
        <div class="value">{df['Sq Ft'].mean():,.0f}</div>
        <div class="label">Avg Sq Ft</div>
    </div>
    <div class="metric-card">
        <div class="value">{len(df)}</div>
        <div class="label">Total Units</div>
    </div>
</div>

{conc_html}

<div class="section">
    <h2>Summary by Property</h2>
    {build_summary_html()}
</div>
"""

# Add sections for each unit type
for ut in UNIT_TYPES:
    tdf = df[df["Unit Type"] == ut]
    if len(tdf) == 0:
        continue

    chart_id = ut.replace(" ", "_").lower()
    traces_json = json.dumps(chart_data[ut])

    html += f"""
<div class="section">
    <h2>{ut}</h2>
    <div class="sub-metrics">
        <div class="sub-metric"><div class="val">{len(tdf)}</div><div class="lbl">Units</div></div>
        <div class="sub-metric"><div class="val">${tdf['Asking Rent'].mean():,.0f}</div><div class="lbl">Avg Rent</div></div>
        <div class="sub-metric"><div class="val">${tdf['PSF'].mean():.2f}</div><div class="lbl">Avg PSF</div></div>
        <div class="sub-metric"><div class="val">{tdf['Sq Ft'].mean():,.0f}</div><div class="lbl">Avg Sq Ft</div></div>
    </div>
    <div id="chart_{chart_id}" class="chart-container"></div>
    <script>
    Plotly.newPlot('chart_{chart_id}', {traces_json}, {{
        xaxis: {{title: 'Square Feet', gridcolor: '#E8E8E8'}},
        yaxis: {{title: 'Rental Rates ($)', gridcolor: '#E8E8E8', tickprefix: '$'}},
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        legend: {{orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center'}},
        margin: {{l: 70, r: 30, t: 20, b: 80}},
        hovermode: 'closest',
    }}, {{responsive: true}});
    </script>
    <div class="table-scroll">
        {build_table_html(ut)}
    </div>
</div>
"""

html += f"""
<div class="footer">
    DFW Multifamily Market Survey &mdash; McKinney / Allen Area Comps &mdash; {date_str}
</div>

</div>
</body>
</html>"""

# Save
os.makedirs("output", exist_ok=True)
output_path = os.path.join("output", "dashboard.html")
with open(output_path, "w") as f:
    f.write(html)

print(f"Dashboard saved to: {output_path}")
print(f"File size: {len(html):,} bytes")
print(f"Open in browser: file://{os.path.abspath(output_path)}")
