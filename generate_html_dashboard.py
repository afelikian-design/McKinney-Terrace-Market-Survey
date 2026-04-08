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
import numpy as np
from scrapers.sample_data import generate_sample_data
from models import Unit

# Load data
units = generate_sample_data()
df = pd.DataFrame([u.to_dict() for u in units])

SUBJECT_PROPERTY = "McKinney Terrace"

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
COMP_PROPERTIES = [p for p in sorted(df["Property Name"].unique()) if p != SUBJECT_PROPERTY]


def fmt_money(val):
    if pd.isna(val) or val == 0:
        return ""
    return f"${val:,.0f}"

def fmt_psf(val):
    if pd.isna(val) or val == 0:
        return ""
    return f"${val:.2f}"


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
        is_subject = r["Property Name"] == SUBJECT_PROPERTY
        weight = "700" if is_subject else "500"
        rows.append(f"""<tr{"" if not is_subject else ' class="subject-row"'}>
            <td style="color:{color};font-weight:{weight}">{r['Property Name']}</td>
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


def _summary_row(prop, pdf, is_total=False, is_subject=False):
    """Build one row of the summary table matching the reference format."""
    concession_text = ""
    conc_df = pdf[pdf["Concessions"].notna() & (pdf["Concessions"] != "")]
    if len(conc_df) > 0:
        concession_text = conc_df["Concessions"].iloc[0]

    counts = {}
    for ut in UNIT_TYPES:
        counts[ut] = len(pdf[pdf["Unit Type"] == ut])

    total = len(pdf)
    avg_sqft = int(pdf["Sq Ft"].mean()) if len(pdf) > 0 else 0

    # Style
    if is_total:
        row_style = 'style="background:#D6E4F0;font-weight:700"'
        name_style = 'style="font-weight:700;color:#1F4E79"'
    elif is_subject:
        row_style = 'style="background:#FFF8E1;font-weight:600;border-top:3px solid #1F4E79"'
        name_style = f'style="font-weight:700;color:{COLORS.get(prop, "#333")}"'
    else:
        row_style = ''
        name_style = f'style="color:{COLORS.get(prop, "#0070C0")};font-weight:500"'

    # Left section cells
    cells = f'<td {name_style}>{prop}</td>'
    cells += f'<td class="center">{concession_text}</td>'
    for ut in UNIT_TYPES:
        cells += f'<td class="center">{counts[ut] if counts[ut] > 0 else 0}</td>'
    cells += f'<td class="center"><b>{total}</b></td>'
    cells += f'<td class="right">{avg_sqft:,}</td>'

    # Spacer
    cells += '<td class="spacer"></td>'

    # Right section: avg rent and PSF per unit type
    for ut in UNIT_TYPES:
        type_df = pdf[pdf["Unit Type"] == ut]
        if len(type_df) > 0:
            avg_rent = type_df["Asking Rent"].mean()
            avg_psf = type_df["PSF"].mean()
            cells += f'<td class="right">{fmt_money(avg_rent)}</td>'
            cells += f'<td class="right">{fmt_psf(avg_psf)}</td>'
        else:
            cells += '<td class="right"></td><td class="right"></td>'

    return f'<tr {row_style}>{cells}</tr>'


def build_summary_html():
    """Build the institutional-format summary table matching the reference."""
    date_str = datetime.now().strftime("%m/%d/%Y")

    # Comp properties (exclude subject)
    comp_df = df[df["Property Name"] != SUBJECT_PROPERTY]
    subject_df = df[df["Property Name"] == SUBJECT_PROPERTY]

    rows = []
    for prop in COMP_PROPERTIES:
        pdf = df[df["Property Name"] == prop]
        rows.append(_summary_row(prop, pdf))

    # Wtd Avg / Total row (comps only)
    rows.append(_summary_row("Wtd Avg / Total", comp_df, is_total=True))

    # Blank spacer row
    spacer_cols = '<td colspan="19" style="height:12px;border:none"></td>'
    rows.append(f'<tr>{spacer_cols}</tr>')

    # Subject property row
    rows.append(_summary_row(SUBJECT_PROPERTY, subject_df, is_subject=True))

    # Build header spanning two sections
    header_left = """
        <th class="summary-hdr">PROPERTY</th>
        <th class="summary-hdr">Concessions</th>
        <th class="summary-hdr">Studio</th>
        <th class="summary-hdr">1BR</th>
        <th class="summary-hdr">2BR</th>
        <th class="summary-hdr">3BR</th>
        <th class="summary-hdr">TOTAL</th>
        <th class="summary-hdr">AVG SQ FT</th>
    """
    header_right = """
        <th class="summary-hdr-r">Studio MKT</th><th class="summary-hdr-r">Studio PSF</th>
        <th class="summary-hdr-r">1BR MKT</th><th class="summary-hdr-r">1BR PSF</th>
        <th class="summary-hdr-r">2BR MKT</th><th class="summary-hdr-r">2BR PSF</th>
        <th class="summary-hdr-r">3BR MKT</th><th class="summary-hdr-r">3BR PSF</th>
    """

    return f"""
    <table class="summary-table">
        <thead>
            <tr>
                <th colspan="8" class="section-title-left">SUMMARY</th>
                <th class="spacer-hdr"></th>
                <th colspan="8" class="section-title-right">AVERAGE MARKET RENTS AS OF {date_str}</th>
            </tr>
            <tr>
                {header_left}
                <th class="spacer-hdr"></th>
                {header_right}
            </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
    </table>"""


# Build chart data for all unit types
chart_data = {}
for ut in UNIT_TYPES:
    chart_data[ut] = build_chart_data(ut)

# Generate HTML
date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>McKinney Terrace Market Survey | Buchanan Street Partners</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; color: #333; }}

/* ---- HEADER / BRANDING ---- */
.top-bar {{
    background: #FFFFFF;
    border-bottom: 3px solid #1F4E79;
    padding: 16px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.brand {{
    display: flex;
    align-items: center;
    gap: 16px;
}}
.brand-logo {{
    width: 48px;
    height: 48px;
    background: #1F4E79;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 900;
    font-size: 20px;
    letter-spacing: -1px;
}}
.brand-text {{
    line-height: 1.2;
}}
.brand-name {{
    font-size: 18px;
    font-weight: 700;
    color: #1F4E79;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
.brand-sub {{
    font-size: 11px;
    color: #888;
    letter-spacing: 2px;
    text-transform: uppercase;
}}
.top-actions {{
    display: flex;
    gap: 12px;
    align-items: center;
}}
.btn {{
    padding: 10px 22px;
    border: none;
    border-radius: 5px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: all 0.2s;
}}
.btn-primary {{
    background: #1F4E79;
    color: white;
}}
.btn-primary:hover {{ background: #163a5c; }}
.btn-export {{
    background: #FFFFFF;
    color: #1F4E79;
    border: 2px solid #1F4E79;
}}
.btn-export:hover {{ background: #EBF0F5; }}
.btn-icon {{ font-size: 16px; }}

/* ---- TITLE BAR ---- */
.title-bar {{
    background: linear-gradient(135deg, #1F4E79 0%, #2C6FAC 100%);
    color: white;
    padding: 20px 40px;
}}
.title-bar h1 {{
    font-size: 24px;
    font-weight: 300;
    letter-spacing: 1px;
}}
.title-bar h1 strong {{ font-weight: 700; }}
.title-bar .subtitle {{
    font-size: 13px;
    opacity: 0.8;
    margin-top: 4px;
    letter-spacing: 0.5px;
}}

/* ---- LAYOUT ---- */
.container {{ max-width: 1500px; margin: 0 auto; padding: 24px; }}
.metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
.metric-card {{
    background: white;
    border-radius: 6px;
    padding: 20px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    text-align: center;
    border-top: 3px solid #1F4E79;
}}
.metric-card .value {{ font-size: 26px; font-weight: 700; color: #1F4E79; }}
.metric-card .label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }}

.section {{
    background: white;
    border-radius: 6px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}}
.section h2 {{
    font-size: 16px;
    color: #1F4E79;
    margin-bottom: 16px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 700;
    border-bottom: 2px solid #1F4E79;
    padding-bottom: 8px;
}}

/* ---- SUMMARY TABLE ---- */
.summary-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}}
.section-title-left {{
    background: #1F4E79;
    color: white;
    padding: 8px 12px;
    text-align: left;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}}
.section-title-right {{
    background: #1F4E79;
    color: white;
    padding: 8px 12px;
    text-align: center;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}}
.spacer-hdr {{
    background: #f0f2f5;
    width: 8px;
    border: none;
}}
.summary-hdr {{
    background: #2C6FAC;
    color: white;
    padding: 8px 10px;
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
}}
.summary-hdr:first-child {{ text-align: left; }}
.summary-hdr-r {{
    background: #2C6FAC;
    color: white;
    padding: 8px 10px;
    text-align: right;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
}}
.summary-table td {{
    padding: 7px 10px;
    border-bottom: 1px solid #e0e0e0;
    white-space: nowrap;
}}
.summary-table td.spacer {{
    background: #f0f2f5;
    width: 8px;
    border: none;
}}
.summary-table td.center {{ text-align: center; }}
.summary-table td.right {{ text-align: right; }}
.subject-row td {{ background: #FFF8E1 !important; }}

/* ---- UNIT TYPE TABLES ---- */
.data-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
.data-table th {{
    background: #1F4E79;
    color: white;
    padding: 9px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    position: sticky;
    top: 0;
}}
.data-table td {{ padding: 7px 12px; border-bottom: 1px solid #e8e8e8; }}
.data-table tr:hover {{ background: #f0f4f8; }}
.data-table tr.subject-row {{ background: #FFF8E1; }}
.data-table tr.subject-row:hover {{ background: #FFF3CD; }}
.data-table .center {{ text-align: center; }}
.data-table .right {{ text-align: right; }}

.chart-container {{ width: 100%; height: 420px; }}

.sub-metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 12px 0 16px; }}
.sub-metric {{ background: #f8f9fa; border-radius: 4px; padding: 10px; text-align: center; }}
.sub-metric .val {{ font-size: 16px; font-weight: 700; color: #1F4E79; }}
.sub-metric .lbl {{ font-size: 10px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; }}

.table-scroll {{ max-height: 500px; overflow-y: auto; }}

.footer {{
    text-align: center;
    padding: 24px;
    color: #aaa;
    font-size: 11px;
    letter-spacing: 0.5px;
    border-top: 1px solid #ddd;
    margin-top: 20px;
}}
.footer strong {{ color: #1F4E79; }}

@media (max-width: 768px) {{
    .metrics, .sub-metrics {{ grid-template-columns: repeat(2, 1fr); }}
    .top-bar {{ flex-direction: column; gap: 12px; }}
}}
</style>
</head>
<body>

<!-- TOP BAR WITH BRANDING AND BUTTONS -->
<div class="top-bar">
    <div class="brand">
        <div class="brand-logo">BSP</div>
        <div class="brand-text">
            <div class="brand-name">Buchanan Street Partners</div>
            <div class="brand-sub">Real Estate Investment Management</div>
        </div>
    </div>
    <div class="top-actions">
        <button class="btn btn-primary" onclick="alert('Update Now will scrape all 7 property websites for live data.\\n\\nTo enable live scraping, run this locally:\\n  python main.py --live\\n\\nThis static dashboard uses data captured at generation time.')">
            <span class="btn-icon">&#8635;</span> Update Now
        </button>
        <button class="btn btn-export" onclick="alert('To export to Excel, run locally:\\n  python main.py\\n\\nThis generates a formatted .xlsx file matching the institutional reference format.')">
            <span class="btn-icon">&#8681;</span> Export
        </button>
    </div>
</div>

<!-- TITLE BAR -->
<div class="title-bar">
    <h1><strong>McKinney Terrace</strong> &mdash; Market Survey Comparison</h1>
    <div class="subtitle">{len(df)} available units across {df['Property Name'].nunique()} properties &nbsp;|&nbsp; McKinney &amp; Allen, TX &nbsp;|&nbsp; {date_str}</div>
</div>

<div class="container">

<!-- METRICS -->
<div class="metrics">
    <div class="metric-card">
        <div class="value">${df['Asking Rent'].mean():,.0f}</div>
        <div class="label">Market Avg Rent</div>
    </div>
    <div class="metric-card">
        <div class="value">${df['PSF'].mean():.2f}</div>
        <div class="label">Market Avg PSF</div>
    </div>
    <div class="metric-card">
        <div class="value">{df['Sq Ft'].mean():,.0f}</div>
        <div class="label">Avg Unit Size (SF)</div>
    </div>
    <div class="metric-card">
        <div class="value">{len(df)}</div>
        <div class="label">Total Available Units</div>
    </div>
</div>

<!-- SUMMARY TABLE -->
<div class="section">
    <h2>Competitive Set Summary</h2>
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
    beds_label = {"Studios": "Studios", "1BR": "1-Bedrooms", "2BR": "2-Bedrooms", "3BR": "3-Bedrooms"}

    html += f"""
<div class="section">
    <h2>{beds_label.get(ut, ut)} &mdash; Market Comparison</h2>
    <div class="sub-metrics">
        <div class="sub-metric"><div class="val">{len(tdf)}</div><div class="lbl">Available Units</div></div>
        <div class="sub-metric"><div class="val">${tdf['Asking Rent'].mean():,.0f}</div><div class="lbl">Avg Asking Rent</div></div>
        <div class="sub-metric"><div class="val">${tdf['PSF'].mean():.2f}</div><div class="lbl">Avg Price / SF</div></div>
        <div class="sub-metric"><div class="val">{tdf['Sq Ft'].mean():,.0f}</div><div class="lbl">Avg Unit Size</div></div>
    </div>
    <div id="chart_{chart_id}" class="chart-container"></div>
    <script>
    Plotly.newPlot('chart_{chart_id}', {traces_json}, {{
        xaxis: {{title: 'Square Feet', gridcolor: '#E8E8E8', zeroline: false}},
        yaxis: {{title: 'Rental Rates ($)', gridcolor: '#E8E8E8', tickprefix: '$', zeroline: false}},
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        legend: {{orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center', font: {{size: 11}}}},
        margin: {{l: 70, r: 30, t: 10, b: 80}},
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
    <strong>Buchanan Street Partners</strong> &nbsp;&mdash;&nbsp; McKinney Terrace Market Survey &nbsp;&mdash;&nbsp; {date_str}
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
