# DFW Multifamily Market Survey

Production-grade scraper + dashboard + Excel export tool for Dallas-Fort Worth apartment comps.

## Target Properties

| # | Property | Location | Platform |
|---|----------|----------|----------|
| 1 | Davis at the Square | McKinney, TX | Custom / Willow Bridge |
| 2 | Magnolia on the Green | Allen, TX | RENTCafe / Yardi |
| 3 | The Link at Twin Creeks | Allen, TX | Greystar |
| 4 | The Bridge at McKinney | McKinney, TX | RENTCafe |
| 5 | Kinstead | McKinney, TX | RENTCafe / CBRE |
| 6 | Collin Square | McKinney, TX | ZRS Management |
| 7 | McKinney Terrace | McKinney, TX | Greystar |

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Generate Excel report (sample data)

```bash
python main.py
```

### 3. Generate Excel report (live scraping)

```bash
python main.py --live
```

### 4. Launch dashboard

```bash
python main.py --dashboard
# or directly:
streamlit run app.py
```

## Output

### Excel Workbook (5 tabs)

| Tab | Content |
|-----|---------|
| **Summary** | Property-level stats, unit counts, avg rents, avg PSF by unit type |
| **Studios** | Scatter chart (SqFt vs Rent) + full unit list |
| **1BR** | Scatter chart + full unit list |
| **2BR** | Scatter chart + full unit list |
| **3BR** | Scatter chart + full unit list |

### Streamlit Dashboard

- **Refresh Live Data** button — triggers Playwright scrapers
- **Download to Excel** button — generates workbook matching reference format
- Filterable data view by property, unit type, and rent range
- 4 scatter charts (Studios / 1BR / 2BR / 3BR) with market trendlines
- Unit list below each chart (1:1 match with chart points)
- Last Updated timestamp
- Active concessions display

## Project Structure

```
├── app.py                  # Streamlit dashboard
├── main.py                 # CLI entry point
├── config.py               # Property configs & constants
├── models.py               # Unit data model
├── excel_export.py         # Excel workbook generator
├── requirements.txt        # Python dependencies
├── scrapers/
│   ├── __init__.py
│   ├── base.py             # Shared utilities (parsing, HTTP)
│   ├── playwright_scraper.py  # Playwright browser automation
│   ├── all_properties.py   # Individual scrapers for all 7 properties
│   └── sample_data.py      # Demo data for testing
└── output/                 # Generated Excel files
```

## Scraping Architecture

Each property scraper:

1. **Launches Playwright** with a headless Chromium browser
2. **Intercepts XHR/API responses** for RENTCafe, Entrata, or custom endpoints
3. **Navigates to the floor plans page** and waits for dynamic content
4. **Clicks through UI controls** (tabs, "View All" buttons) to load all units
5. **Parses API data** if intercepted, otherwise falls back to HTML parsing
6. **Validates unit count** against what's visible on the page

### Data Sources per Property

| Property | Primary Source | Fallback |
|----------|---------------|----------|
| Davis at the Square | API interception | HTML floor plan cards |
| Magnolia on the Green | RENTCafe API | RENTCafe listing page |
| The Link at Twin Creeks | API interception | HTML parsing |
| The Bridge at McKinney | RENTCafe API | RENTCafe listing page |
| Kinstead | RENTCafe API | RENTCafe listing page |
| Collin Square | API interception | HTML parsing |
| McKinney Terrace | API interception | HTML parsing |

## Normalization Rules

- **Unit Types:** Studio → "Studios", 1 Bed → "1BR", 2 Bed → "2BR", 3 Bed → "3BR"
- **Rent:** Exact rent used when available; minimum of range used when only range shown
- **PSF:** Calculated as Rent / Sq Ft
- **Concessions:** Raw text preserved; estimated value derived when possible

## Assumptions & Limitations

- Sample data is based on publicly listed information from apartments.com, rentcafe.com, and property websites
- Live scraping requires local Playwright installation with Chromium
- Some properties may only expose floor-plan-level data (flagged in output)
- Rent ranges use minimum value for normalized rent calculations
- Concession values are estimates based on stated terms
