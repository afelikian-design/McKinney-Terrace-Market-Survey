"""Configuration for the DFW Market Survey scraper."""

from dataclasses import dataclass

@dataclass
class PropertyConfig:
    name: str
    url: str
    scraper: str  # module name in scrapers/

PROPERTIES = [
    PropertyConfig(
        name="Davis at the Square",
        url="https://davisatthesquare.com/",
        scraper="davis_at_the_square",
    ),
    PropertyConfig(
        name="Magnolia on the Green",
        url="https://www.magnoliaonthegreen.com/",
        scraper="magnolia_on_the_green",
    ),
    PropertyConfig(
        name="The Link at Twin Creeks",
        url="https://livethelinkapts.com/",
        scraper="links_at_twin_creeks",
    ),
    PropertyConfig(
        name="The Bridge at McKinney",
        url="https://www.thebridgeatmckinney.com/",
        scraper="bridge_at_mckinney",
    ),
    PropertyConfig(
        name="Kinstead",
        url="https://www.kinsteadmckinney.com/",
        scraper="kinstead",
    ),
    PropertyConfig(
        name="Collin Square",
        url="https://www.collinsquareapts.com/",
        scraper="collin_square",
    ),
    PropertyConfig(
        name="McKinney Terrace",
        url="https://mckinneyterrace.com/",
        scraper="mckinney_terrace",
    ),
]

# Unit type normalization map
UNIT_TYPE_MAP = {
    "studio": "Studios",
    "studios": "Studios",
    "s": "Studios",
    "0br": "Studios",
    "0 bed": "Studios",
    "0": "Studios",
    "1br": "1BR",
    "1 br": "1BR",
    "1bed": "1BR",
    "1 bed": "1BR",
    "1 bedroom": "1BR",
    "1-bedroom": "1BR",
    "one bedroom": "1BR",
    "1": "1BR",
    "2br": "2BR",
    "2 br": "2BR",
    "2bed": "2BR",
    "2 bed": "2BR",
    "2 bedroom": "2BR",
    "2-bedroom": "2BR",
    "two bedroom": "2BR",
    "2": "2BR",
    "3br": "3BR",
    "3 br": "3BR",
    "3bed": "3BR",
    "3 bed": "3BR",
    "3 bedroom": "3BR",
    "3-bedroom": "3BR",
    "three bedroom": "3BR",
    "3": "3BR",
}

UNIT_TYPES = ["Studios", "1BR", "2BR", "3BR"]

# Excel formatting
HEADER_FILL_COLOR = "1F4E79"
HEADER_FONT_COLOR = "FFFFFF"

# -----------------------------------------------------------------------------
# Shared market-survey configuration (used by scrape_market.py, build_dashboard.py,
# and build_excel.py). These match the exact specification for the market survey
# pipeline and are independent of the legacy PropertyConfig above.
# -----------------------------------------------------------------------------

# The canonical list of properties scraped by scrape_market.py.
MARKET_PROPERTIES = [
    {
        "name": "McKinney Terrace",
        "url": "https://mckinneyterrace.com/",
        "is_subject": True,
    },
    {
        "name": "Davis at the Square",
        "url": "https://davisatthesquare.com/",
        "is_subject": False,
    },
    {
        "name": "Magnolia on the Green",
        "url": "https://www.magnoliaonthegreen.com/",
        "is_subject": False,
    },
    {
        "name": "The Links at Twin Creeks",
        "url": "https://livethelinkapts.com/",
        "is_subject": False,
    },
    {
        "name": "The Bridge at McKinney",
        "url": "https://www.thebridgeatmckinney.com/",
        "is_subject": False,
    },
    {
        "name": "Kinstead",
        "url": "https://www.kinsteadmckinney.com/",
        "is_subject": False,
    },
    {
        "name": "Collin Square",
        "url": "https://www.collinsquareapts.com/",
        "is_subject": False,
    },
]

SUBJECT_PROPERTY = "McKinney Terrace"

# Consistent property colors used across the HTML dashboard and Excel workbook.
PROPERTY_COLORS = {
    "McKinney Terrace":         "#C0392B",  # red — subject property
    "Davis at the Square":      "#2980B9",  # blue
    "Magnolia on the Green":    "#27AE60",  # green
    "The Links at Twin Creeks": "#8E44AD",  # purple
    "The Bridge at McKinney":   "#E67E22",  # orange
    "Kinstead":                 "#16A085",  # teal
    "Collin Square":            "#2C3E50",  # dark navy
}

# Bedroom-type display settings used by the dashboard and the Excel report.
BEDROOM_SECTIONS = [
    {"bedrooms": 0, "label": "Studios",        "section_title": "Studios"},
    {"bedrooms": 1, "label": "One-Bedrooms",   "section_title": "One-Bedrooms"},
    {"bedrooms": 2, "label": "Two-Bedrooms",   "section_title": "Two-Bedrooms"},
    {"bedrooms": 3, "label": "Three-Bedrooms", "section_title": "Three-Bedrooms"},
]

# Brand palette
NAVY = "#1B2A4A"
NAVY_HEX = "1B2A4A"  # openpyxl requires hex without the leading #
LIGHT_GRAY_HEX = "F2F2F2"
WHITE_HEX = "FFFFFF"
