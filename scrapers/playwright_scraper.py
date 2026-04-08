"""Playwright-based scraper for apartment websites.

Uses a headless browser to render JavaScript-heavy pages and intercept
API/XHR calls to capture full unit-level inventory data.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext

from models import Unit
from scrapers.base import normalize_unit_type, parse_rent, parse_sqft, parse_beds, parse_baths

logger = logging.getLogger(__name__)


async def create_browser_context(playwright) -> tuple:
    """Create a browser and context with standard settings."""
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
    )
    return browser, context


async def intercept_api_responses(page: Page, patterns: list[str]) -> list[dict]:
    """Set up response interception for API calls matching patterns."""
    captured = []

    async def handle_response(response):
        url = response.url.lower()
        if any(p in url for p in patterns):
            try:
                body = await response.json()
                captured.append({"url": response.url, "data": body})
                logger.info(f"Captured API response: {response.url[:120]}")
            except Exception:
                pass

    page.on("response", handle_response)
    return captured


# ---------------------------------------------------------------------------
# Generic RENTCafe scraper (used by several properties)
# ---------------------------------------------------------------------------

async def scrape_rentcafe_property(page: Page, property_name: str,
                                    base_url: str, source_url: str) -> list[Unit]:
    """Scrape a RENTCafe-powered property website."""
    units = []
    captured = await intercept_api_responses(page, [
        "rentcafeapi", "api/units", "api/floorplan", "api/apartmentavailability",
        "availableunits", "floorplans", "pricing",
    ])

    await page.goto(base_url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(3)

    # Try clicking "View All" / "Show More" buttons
    for selector in [
        "text=View All", "text=Show All", "text=Load More",
        "text=See All Available", "text=view all",
        "button:has-text('All')", ".show-all", ".view-all",
    ]:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass

    # Try to extract from captured API data
    if captured:
        for cap in captured:
            api_units = _parse_rentcafe_api(cap["data"], property_name, source_url)
            units.extend(api_units)

    # If no API data, parse HTML
    if not units:
        units = await _parse_html_floorplans(page, property_name, source_url)

    return units


def _parse_rentcafe_api(data: dict, property_name: str, source_url: str) -> list[Unit]:
    """Parse RENTCafe API JSON response into Unit objects."""
    units = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Handle various RENTCafe response formats
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ["apartments", "units", "availableUnits", "floorPlans",
                     "data", "results", "FloorPlans", "ApartmentAvailability"]:
            if key in data:
                items = data[key] if isinstance(data[key], list) else [data[key]]
                break

    for item in items:
        if not isinstance(item, dict):
            continue

        # Extract fields from various key naming conventions
        unit_num = str(item.get("ApartmentName", item.get("unitNumber", item.get("unit_number",
                       item.get("UnitNumber", item.get("apartmentName", ""))))))
        floorplan = item.get("FloorplanName", item.get("floorPlanName", item.get("floor_plan_name",
                   item.get("floorplanName", item.get("FloorPlan", "")))))
        beds = item.get("Beds", item.get("beds", item.get("bedrooms", item.get("Bedrooms", 0))))
        baths = item.get("Baths", item.get("baths", item.get("bathrooms", item.get("Bathrooms", 1))))
        sqft = item.get("SQFT", item.get("sqft", item.get("squareFeet", item.get("SquareFeet",
               item.get("sqFt", item.get("MinimumSQFT", 0))))))
        rent = item.get("MinimumRent", item.get("rent", item.get("Rent", item.get("minimumRent",
               item.get("price", item.get("Price", None))))))
        max_rent = item.get("MaximumRent", item.get("maximumRent", item.get("maxRent", None)))
        avail_date = item.get("AvailableDate", item.get("availableDate", item.get("available_date",
                     item.get("moveInDate", item.get("MoveInDate", "")))))
        specials = item.get("Specials", item.get("specials", item.get("concessions", "")))

        if not (floorplan or unit_num):
            continue

        beds_int = int(beds) if beds else 0
        baths_float = float(baths) if baths else 1.0
        sqft_int = int(float(sqft)) if sqft else 0
        unit_type = normalize_unit_type("", beds=beds_int)

        rent_val = float(rent) if rent else None
        rent_range = None
        if max_rent and rent_val and float(max_rent) != rent_val:
            rent_range = f"${rent_val:,.0f} - ${float(max_rent):,.0f}"

        data_level = "unit" if unit_num else "floorplan"

        unit = Unit(
            property_name=property_name,
            unit_number=unit_num or floorplan,
            floorplan=floorplan or "",
            unit_type=unit_type,
            beds=beds_int,
            baths=baths_float,
            sqft=sqft_int,
            asking_rent=rent_val,
            rent_range=rent_range,
            move_in_date=str(avail_date) if avail_date else None,
            concessions=str(specials) if specials else None,
            source_url=source_url,
            scrape_timestamp=timestamp,
            data_level=data_level,
        )
        units.append(unit)

    return units


async def _parse_html_floorplans(page: Page, property_name: str,
                                  source_url: str) -> list[Unit]:
    """Fallback: parse floor plans from rendered HTML."""
    units = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Try common selectors for floor plan cards
    selectors = [
        ".floor-plan-card", ".floorplan-card", ".fp-card",
        ".unit-card", ".availability-card", "[data-floorplan]",
        ".floorplan-item", ".floor-plan-item", ".plan-card",
        ".floorplan", ".floor-plan", ".unit-item",
        "article.floorplan", ".fp-group", ".plan-group",
    ]

    cards = []
    for sel in selectors:
        cards = await page.query_selector_all(sel)
        if cards:
            logger.info(f"Found {len(cards)} cards with selector: {sel}")
            break

    if not cards:
        # Try extracting from table rows
        rows = await page.query_selector_all("table tbody tr, .table-row, .data-row")
        if rows:
            cards = rows

    for card in cards:
        text = await card.inner_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        floorplan = lines[0] if lines else ""
        beds_raw = ""
        baths_raw = ""
        sqft_raw = ""
        rent_raw = ""
        avail_raw = ""

        for line in lines:
            ll = line.lower()
            if "bed" in ll or "br" in ll or "studio" in ll:
                beds_raw = line
            if "bath" in ll or "ba" in ll:
                baths_raw = line
            if "sq" in ll or "sf" in ll or re.search(r'\d{3,4}\s*(sq|sf)', ll):
                sqft_raw = line
            if "$" in line:
                rent_raw = line
            if any(m in ll for m in ["avail", "move", "ready", "now", "/"]):
                if re.search(r'\d{1,2}/\d{1,2}', line):
                    avail_raw = line

        beds = parse_beds(beds_raw)
        baths = parse_baths(baths_raw)
        sqft = parse_sqft(sqft_raw)
        rent_val, rent_range = parse_rent(rent_raw)
        unit_type = normalize_unit_type(beds_raw, beds=beds)

        if sqft > 0 or rent_val:
            unit = Unit(
                property_name=property_name,
                unit_number=floorplan,
                floorplan=floorplan,
                unit_type=unit_type,
                beds=beds,
                baths=baths,
                sqft=sqft,
                asking_rent=rent_val,
                rent_range=rent_range,
                move_in_date=avail_raw or None,
                source_url=source_url,
                scrape_timestamp=timestamp,
                data_level="floorplan",
            )
            units.append(unit)

    return units


# ---------------------------------------------------------------------------
# Generic Entrata scraper
# ---------------------------------------------------------------------------

async def scrape_entrata_property(page: Page, property_name: str,
                                   base_url: str, source_url: str,
                                   property_id: Optional[str] = None) -> list[Unit]:
    """Scrape an Entrata-powered property website."""
    units = []
    captured = await intercept_api_responses(page, [
        "entrata", "api/units", "api/floorplan", "propertyunits",
        "floorplans", "availability", "units.json",
    ])

    await page.goto(base_url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(3)

    # Click any "View Available" / "See Units" buttons
    for selector in [
        "text=View Available", "text=See Units", "text=Check Availability",
        "text=View Units", "text=See Available",
    ]:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass

    # Parse captured API data
    if captured:
        for cap in captured:
            api_units = _parse_entrata_api(cap["data"], property_name, source_url)
            units.extend(api_units)

    if not units:
        units = await _parse_html_floorplans(page, property_name, source_url)

    return units


def _parse_entrata_api(data: dict, property_name: str, source_url: str) -> list[Unit]:
    """Parse Entrata API response."""
    units = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Entrata nests data under response -> result -> FloorPlans -> FloorPlan
    result = data
    if "response" in data:
        result = data["response"]
    if "result" in result:
        result = result["result"]

    floorplans = result.get("FloorPlans", result.get("floorPlans", []))
    if isinstance(floorplans, dict):
        floorplans = floorplans.get("FloorPlan", floorplans.get("floorPlan", []))
    if not isinstance(floorplans, list):
        floorplans = [floorplans]

    for fp in floorplans:
        if not isinstance(fp, dict):
            continue

        fp_name = fp.get("FloorPlanName", fp.get("Name", fp.get("name", "")))
        fp_beds = int(fp.get("Beds", fp.get("beds", fp.get("Bedrooms", 0))))
        fp_baths = float(fp.get("Baths", fp.get("baths", fp.get("Bathrooms", 1))))
        fp_sqft = int(float(fp.get("SQFT", fp.get("sqft", fp.get("SquareFeet", 0)))))

        # Check for individual units within the floor plan
        apt_units = fp.get("Units", fp.get("units", fp.get("Apartments", [])))
        if isinstance(apt_units, dict):
            apt_units = apt_units.get("Unit", apt_units.get("unit", []))
        if not isinstance(apt_units, list):
            apt_units = [apt_units] if apt_units else []

        if apt_units:
            for au in apt_units:
                if not isinstance(au, dict):
                    continue
                unit_num = str(au.get("UnitNumber", au.get("unitNumber",
                              au.get("ApartmentName", ""))))
                sqft = int(float(au.get("SQFT", au.get("sqft", fp_sqft))))
                rent = au.get("Rent", au.get("rent", au.get("MinRent", None)))
                max_rent = au.get("MaxRent", au.get("maxRent", None))
                avail = au.get("AvailableDate", au.get("availableDate", ""))
                specials = au.get("Specials", au.get("specials", ""))

                rent_val = float(rent) if rent else None
                rent_range = None
                if max_rent and rent_val and float(max_rent) != rent_val:
                    rent_range = f"${rent_val:,.0f} - ${float(max_rent):,.0f}"

                unit_type = normalize_unit_type("", beds=fp_beds)
                unit = Unit(
                    property_name=property_name,
                    unit_number=unit_num,
                    floorplan=fp_name,
                    unit_type=unit_type,
                    beds=fp_beds,
                    baths=fp_baths,
                    sqft=sqft,
                    asking_rent=rent_val,
                    rent_range=rent_range,
                    move_in_date=str(avail) if avail else None,
                    concessions=str(specials) if specials else None,
                    source_url=source_url,
                    scrape_timestamp=timestamp,
                    data_level="unit",
                )
                units.append(unit)
        else:
            # Floor-plan level only
            rent = fp.get("MinRent", fp.get("minRent", fp.get("Rent", None)))
            max_rent = fp.get("MaxRent", fp.get("maxRent", None))
            rent_val = float(rent) if rent else None
            rent_range = None
            if max_rent and rent_val and float(max_rent) != rent_val:
                rent_range = f"${rent_val:,.0f} - ${float(max_rent):,.0f}"

            unit_type = normalize_unit_type("", beds=fp_beds)
            unit = Unit(
                property_name=property_name,
                unit_number=fp_name,
                floorplan=fp_name,
                unit_type=unit_type,
                beds=fp_beds,
                baths=fp_baths,
                sqft=fp_sqft,
                asking_rent=rent_val,
                rent_range=rent_range,
                source_url=source_url,
                scrape_timestamp=timestamp,
                data_level="floorplan",
            )
            units.append(unit)

    return units
