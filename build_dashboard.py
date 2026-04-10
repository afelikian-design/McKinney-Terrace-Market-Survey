"""Generate the HTML market-survey dashboard.

Reads ``market_data.json`` (produced by ``scrape_market.py``) and writes
``market_survey_dashboard.html``. The dashboard contains one section per
bedroom type (Studios, One-Bedrooms, Two-Bedrooms, Three-Bedrooms) where
each section is a Chart.js scatter chart followed immediately by a data
table. Property colors are loaded from ``config.PROPERTY_COLORS`` so the
HTML dashboard and the Excel report share the same palette.
"""

from __future__ import annotations

import html
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from config import (
    BEDROOM_SECTIONS,
    MARKET_PROPERTIES,
    PROPERTY_COLORS,
    SUBJECT_PROPERTY,
)

INPUT_JSON = Path("market_data.json")
OUTPUT_HTML = Path("market_survey_dashboard.html")


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def load_data() -> list[dict[str, Any]]:
    if not INPUT_JSON.exists():
        print(f"[error] {INPUT_JSON} not found. Run scrape_market.py first.")
        sys.exit(1)
    return json.loads(INPUT_JSON.read_text())


def live_units(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in records if not r.get("no_data")]


def sort_property_order(names: list[str]) -> list[str]:
    """Subject first, then alphabetical."""
    rest = sorted(n for n in names if n != SUBJECT_PROPERTY)
    if SUBJECT_PROPERTY in names:
        return [SUBJECT_PROPERTY, *rest]
    return rest


def properties_with_live_data(records: list[dict[str, Any]]) -> set[str]:
    return {r["property_name"] for r in live_units(records)}


def units_for_bedroom(
    records: list[dict[str, Any]], bedrooms: int
) -> list[dict[str, Any]]:
    return [r for r in live_units(records) if r.get("bedrooms") == bedrooms]


# ---------------------------------------------------------------------------
# HTML building blocks
# ---------------------------------------------------------------------------


def fmt_rent(value: Any) -> str:
    try:
        return f"$ {int(value):,}"
    except (TypeError, ValueError):
        return "—"


def fmt_psf(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def fmt_sqft(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


def esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


# ---------------------------------------------------------------------------
# Per-section rendering
# ---------------------------------------------------------------------------


def build_chart_datasets(
    section_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return one Chart.js dataset per property, sorted by sqft asc."""
    by_property: dict[str, list[dict[str, Any]]] = {}
    for u in section_units:
        by_property.setdefault(u["property_name"], []).append(u)

    ordered = sort_property_order(list(by_property.keys()))
    datasets: list[dict[str, Any]] = []
    for name in ordered:
        points = sorted(by_property[name], key=lambda u: u.get("sqft") or 0)
        color = PROPERTY_COLORS.get(name, "#777777")
        is_subject = name == SUBJECT_PROPERTY
        datasets.append(
            {
                "label": name,
                "data": [
                    {"x": u["sqft"], "y": u["asking_rent"]}
                    for u in points
                    if u.get("sqft") and u.get("asking_rent")
                ],
                "borderColor": color,
                "backgroundColor": color,
                "pointBackgroundColor": color,
                "pointBorderColor": color,
                "pointRadius": 6 if is_subject else 5,
                "pointHoverRadius": 8,
                "borderWidth": 4 if is_subject else 2,
                "showLine": True,
                "tension": 0.15,
                "fill": False,
                "isSubject": is_subject,
            }
        )
    return datasets


def compute_axes(section_units: list[dict[str, Any]]) -> tuple[int, int, int, int]:
    if not section_units:
        return 0, 1000, 0, 3000
    sqfts = [u["sqft"] for u in section_units if u.get("sqft")]
    rents = [u["asking_rent"] for u in section_units if u.get("asking_rent")]
    x_min = min(sqfts) - 50
    x_max = max(sqfts) + 50
    y_min = max(0, min(rents) - 100)
    y_max = max(rents) + 100
    return x_min, x_max, y_min, y_max


def render_section_header(title: str) -> str:
    return f"""
<div class="section-header">
  <div class="section-title">{esc(title)}</div>
  <div class="section-subtitle">Market Survey Comparison</div>
</div>
""".strip()


def render_chart(
    section_id: str,
    section_units: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    datasets = build_chart_datasets(section_units)
    x_min, x_max, y_min, y_max = compute_axes(section_units)
    chart_config = {
        "type": "scatter",
        "data": {"datasets": datasets},
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "position": "bottom",
                    "labels": {
                        "usePointStyle": True,
                        "padding": 16,
                        "font": {"size": 13},
                    },
                },
                "tooltip": {
                    "callbacks": {},
                },
            },
            "scales": {
                "x": {
                    "title": {
                        "display": True,
                        "text": "Square Feet",
                        "font": {"weight": "bold", "size": 13},
                    },
                    "min": x_min,
                    "max": x_max,
                },
                "y": {
                    "title": {
                        "display": True,
                        "text": "Rental Rates",
                        "font": {"weight": "bold", "size": 13},
                    },
                    "min": y_min,
                    "max": y_max,
                    "ticks": {},
                },
            },
        },
    }
    chart_html = (
        f'<div class="chart-wrap">'
        f'<canvas id="{section_id}" height="600"></canvas>'
        f"</div>"
    )
    return chart_html, chart_config


def render_table(
    section_label: str,
    section_units: list[dict[str, Any]],
    properties_with_data: set[str],
    property_url_map: dict[str, str],
) -> str:
    columns = [
        "Property Name",
        "Unit",
        "Date Available",
        "Concession",
        "Floorplan",
        "Sq Ft",
        "Asking Rent",
        "PSF",
    ]

    # Group units by property, subject first then alphabetical; within
    # each property sort by sqft ascending.
    by_property: dict[str, list[dict[str, Any]]] = {}
    for u in section_units:
        by_property.setdefault(u["property_name"], []).append(u)

    all_property_names = [p["name"] for p in MARKET_PROPERTIES]
    ordered = sort_property_order(all_property_names)

    rows_html: list[str] = []
    row_index = 0
    for prop_name in ordered:
        color = PROPERTY_COLORS.get(prop_name, "#777777")
        url = property_url_map.get(prop_name, "#")
        is_subject = prop_name == SUBJECT_PROPERTY
        prop_units = sorted(
            by_property.get(prop_name, []),
            key=lambda u: u.get("sqft") or 0,
        )

        name_classes = "prop-name" + (" subject" if is_subject else "")
        prop_link = (
            f'<a href="{esc(url)}" target="_blank" rel="noopener" '
            f'class="{name_classes}">{esc(prop_name)}</a>'
        )

        if not prop_units:
            row_class = "data-row no-data-row" + (
                " alt" if row_index % 2 else ""
            )
            row_index += 1
            rows_html.append(
                f'<tr class="{row_class}" style="border-left: 6px solid {color};">'
                f'<td class="prop-cell">{prop_link}</td>'
                f'<td colspan="{len(columns) - 1}" class="no-data-cell">'
                f"No data available</td></tr>"
            )
            continue

        for u in prop_units:
            row_class = "data-row" + (" alt" if row_index % 2 else "")
            row_index += 1
            unit_display = esc(u.get("unit_number")) or "—"
            date_display = esc(u.get("date_available")) or "—"
            conc_display = esc(u.get("concession")) if u.get("concession") else "None"
            fp_display = esc(u.get("floorplan_name")) or "—"
            rows_html.append(
                f'<tr class="{row_class}" style="border-left: 6px solid {color};">'
                f'<td class="prop-cell">{prop_link}</td>'
                f"<td>{unit_display}</td>"
                f"<td>{date_display}</td>"
                f"<td>{conc_display}</td>"
                f"<td>{fp_display}</td>"
                f'<td class="num">{fmt_sqft(u.get("sqft"))}</td>'
                f'<td class="num">{fmt_rent(u.get("asking_rent"))}</td>'
                f'<td class="num">{fmt_psf(u.get("psf"))}</td>'
                f"</tr>"
            )

    header_cells = "".join(f"<th>{esc(c)}</th>" for c in columns)

    return f"""
<table class="market-table">
  <thead>
    <tr class="table-title-row">
      <th colspan="{len(columns)}">{esc(section_label.upper())}</th>
    </tr>
    <tr class="table-header-row">{header_cells}</tr>
  </thead>
  <tbody>
    {''.join(rows_html)}
  </tbody>
</table>
""".strip()


# ---------------------------------------------------------------------------
# Full-page rendering
# ---------------------------------------------------------------------------


STYLE = """
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #ffffff;
  color: #222;
}
.page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px 64px;
}
.page-header {
  text-align: center;
  margin-bottom: 24px;
}
.page-header h1 {
  font-size: 34px;
  margin: 0 0 6px;
  color: #1B2A4A;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.page-header .subtitle {
  color: #555;
  font-size: 14px;
  letter-spacing: 0.4px;
}
.freshness-banner {
  margin: 24px 0;
  padding: 14px 18px;
  border: 1px solid #E0E3EC;
  border-radius: 8px;
  background: #FAFBFD;
  font-size: 13px;
  color: #333;
}
.freshness-banner strong { color: #1B2A4A; }
.freshness-banner .status-live { color: #1e7a3c; font-weight: 600; }
.freshness-banner .status-missing { color: #9a3030; font-weight: 600; }
.section {
  margin-top: 40px;
}
.section + .section {
  border-top: 1px solid #E0E3EC;
  padding-top: 40px;
}
.section-header {
  background: #1B2A4A;
  color: #fff;
  padding: 18px 24px;
  border-radius: 8px 8px 0 0;
}
.section-header .section-title {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.3px;
}
.section-header .section-subtitle {
  font-size: 13px;
  opacity: 0.85;
  margin-top: 2px;
}
.chart-wrap {
  background: #fff;
  border: 1px solid #E0E3EC;
  border-top: none;
  padding: 20px;
  height: 600px;
}
.market-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 0;
  font-size: 13px;
  border: 1px solid #E0E3EC;
  border-top: none;
}
.market-table th,
.market-table td {
  padding: 10px 12px;
  text-align: left;
}
.market-table .table-title-row th {
  background: #1B2A4A;
  color: #fff;
  font-weight: 700;
  text-align: center;
  font-size: 14px;
  letter-spacing: 0.4px;
  padding: 12px;
}
.market-table .table-header-row th {
  background: #1B2A4A;
  color: #fff;
  font-weight: 700;
  text-align: center;
  font-size: 12px;
  letter-spacing: 0.3px;
  border-top: 1px solid #2e3f63;
}
.market-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.market-table tr.data-row { background: #ffffff; }
.market-table tr.data-row.alt { background: #F6F7FA; }
.market-table tr.no-data-row .no-data-cell {
  color: #888;
  font-style: italic;
  text-align: center;
}
.market-table a.prop-name {
  color: #2C3E50;
  text-decoration: none;
}
.market-table a.prop-name:hover { text-decoration: underline; }
.market-table a.prop-name.subject {
  color: #1B2A4A;
  font-weight: 700;
}
.market-table td.prop-cell { padding-left: 14px; }
"""


def build_html(records: list[dict[str, Any]]) -> str:
    prop_url_map = {p["name"]: p["url"] for p in MARKET_PROPERTIES}
    with_data = properties_with_live_data(records)

    # Build each section
    sections_html: list[str] = []
    chart_configs: list[dict[str, Any]] = []
    section_canvases: list[str] = []

    for cfg in BEDROOM_SECTIONS:
        section_units = units_for_bedroom(records, cfg["bedrooms"])
        if not section_units:
            continue  # skip empty sections

        canvas_id = f"chart-bed-{cfg['bedrooms']}"
        section_canvases.append(canvas_id)

        header_html = render_section_header(cfg["section_title"])
        chart_html, chart_cfg = render_chart(canvas_id, section_units)
        chart_configs.append({"id": canvas_id, "config": chart_cfg})
        table_html = render_table(
            cfg["label"],
            section_units,
            with_data,
            prop_url_map,
        )
        sections_html.append(
            f'<div class="section">{header_html}{chart_html}{table_html}</div>'
        )

    # Data freshness banner — list live vs missing
    live_list = sorted(with_data)
    missing_list = sorted(
        p["name"] for p in MARKET_PROPERTIES if p["name"] not in with_data
    )
    live_html = (
        ", ".join(f'<span class="status-live">{esc(n)}</span>' for n in live_list)
        or "<em>none</em>"
    )
    missing_html = (
        ", ".join(
            f'<span class="status-missing">{esc(n)}</span>' for n in missing_list
        )
        or "<em>none</em>"
    )
    freshness_html = (
        '<div class="freshness-banner">'
        "<strong>Live data:</strong> "
        f"{live_html}"
        "<br/>"
        "<strong>Unavailable:</strong> "
        f"{missing_html}"
        "</div>"
    )

    today = date.today().strftime("%B %d, %Y")
    page_header = f"""
<div class="page-header">
  <h1>Market Survey Dashboard</h1>
  <div class="subtitle">{esc(today)} &middot; McKinney / Allen &middot; DFW</div>
</div>
""".strip()

    # Chart.js bootstrap (with a tiny y-axis formatter for $1,000 style)
    chart_js_snippets: list[str] = []
    for item in chart_configs:
        cfg_json = json.dumps(item["config"])
        chart_js_snippets.append(
            f"""
(function() {{
  var cfg = {cfg_json};
  cfg.options.scales.y.ticks.callback = function(value) {{
    return '$' + value.toLocaleString();
  }};
  cfg.options.plugins.tooltip.callbacks.label = function(ctx) {{
    var p = ctx.raw || {{}};
    return ctx.dataset.label + ': ' + (p.x||0).toLocaleString() + ' SF, $' + (p.y||0).toLocaleString();
  }};
  var ctx = document.getElementById('{item["id"]}');
  if (ctx) new Chart(ctx, cfg);
}})();
""".strip()
        )

    chart_bootstrap = "\n".join(chart_js_snippets)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Market Survey Dashboard — McKinney / Allen</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>{STYLE}</style>
</head>
<body>
<div class="page">
  {page_header}
  {freshness_html}
  {''.join(sections_html)}
</div>
<script>
{chart_bootstrap}
</script>
</body>
</html>
"""


def main() -> int:
    records = load_data()
    html_doc = build_html(records)
    OUTPUT_HTML.write_text(html_doc)
    print(f"Wrote {OUTPUT_HTML}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
