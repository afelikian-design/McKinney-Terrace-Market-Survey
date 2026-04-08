"""Individual scraper functions for each of the 7 target properties.

Each function uses Playwright to navigate to the property's floor plans /
availability page, intercepts API responses, and falls back to HTML parsing.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright, Page

from models import Unit
from scrapers.base import normalize_unit_type, parse_rent, parse_sqft, parse_beds, parse_baths
from scrapers.playwright_scraper import (
    create_browser_context,
    intercept_api_responses,
    scrape_rentcafe_property,
    scrape_entrata_property,
    _parse_html_floorplans,
    _parse_rentcafe_api,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Davis at the Square  (Willow Bridge / custom site)
# ---------------------------------------------------------------------------

async def scrape_davis_at_the_square() -> list[Unit]:
    """Scrape Davis at the Square - 260 E Davis St, McKinney TX."""
    property_name = "Davis at the Square"
    base_url = "https://davisatthesquare.com/floorplans/"
    source_url = "https://davisatthesquare.com/"

    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        page = await context.new_page()
        units = []

        try:
            captured = await intercept_api_responses(page, [
                "api", "units", "floorplan", "availability", "pricing",
                "rentcafe", "entrata", "realpage",
            ])

            await page.goto(base_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            # Try to find and click individual floor plan links to get unit data
            fp_links = await page.query_selector_all("a[href*='floorplan'], a[href*='floor-plan']")
            fp_urls = []
            for link in fp_links:
                href = await link.get_attribute("href")
                if href and href not in fp_urls:
                    fp_urls.append(href)

            # Parse main page first
            if captured:
                for cap in captured:
                    units.extend(_parse_rentcafe_api(cap["data"], property_name, source_url))

            if not units:
                units = await _parse_html_floorplans(page, property_name, source_url)

            # If still no units, try parsing the page content more aggressively
            if not units:
                units = await _scrape_generic_floorplan_page(page, property_name, source_url)

        except Exception as e:
            logger.error(f"Error scraping {property_name}: {e}")
        finally:
            await browser.close()

        return units


# ---------------------------------------------------------------------------
# 2. Magnolia on the Green  (RENTCafe / Yardi)
# ---------------------------------------------------------------------------

async def scrape_magnolia_on_the_green() -> list[Unit]:
    """Scrape Magnolia on the Green - 1845 Chelsea Blvd, Allen TX."""
    property_name = "Magnolia on the Green"
    source_url = "https://www.magnoliaonthegreen.com/"

    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        page = await context.new_page()
        units = []

        try:
            # Try the main website first
            captured = await intercept_api_responses(page, [
                "rentcafe", "api", "units", "floorplan", "availability",
                "pricing", "yardi", "realpage",
            ])

            fp_url = "https://www.magnoliaonthegreen.com/floorplans"
            await page.goto(fp_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            if captured:
                for cap in captured:
                    units.extend(_parse_rentcafe_api(cap["data"], property_name, source_url))

            if not units:
                units = await _parse_html_floorplans(page, property_name, source_url)

            if not units:
                units = await _scrape_generic_floorplan_page(page, property_name, source_url)

            # Try RENTCafe direct listing as fallback
            if not units:
                await page.goto(
                    "https://www.rentcafe.com/apartments/tx/allen/magnolia-on-the-green-0/default.aspx",
                    wait_until="networkidle", timeout=60000,
                )
                await asyncio.sleep(3)
                units = await _scrape_rentcafe_listing(page, property_name, source_url)

        except Exception as e:
            logger.error(f"Error scraping {property_name}: {e}")
        finally:
            await browser.close()

        return units


# ---------------------------------------------------------------------------
# 3. The Link at Twin Creeks  (Greystar / RENTCafe)
# ---------------------------------------------------------------------------

async def scrape_links_at_twin_creeks() -> list[Unit]:
    """Scrape The Link at Twin Creeks - 729 Junction Dr, Allen TX."""
    property_name = "The Link at Twin Creeks"
    source_url = "https://livethelinkapts.com/"

    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        page = await context.new_page()
        units = []

        try:
            captured = await intercept_api_responses(page, [
                "api", "units", "floorplan", "availability", "pricing",
                "rentcafe", "entrata", "realpage", "greystar",
            ])

            fp_url = "https://livethelinkapts.com/floorplans/"
            await page.goto(fp_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            if captured:
                for cap in captured:
                    units.extend(_parse_rentcafe_api(cap["data"], property_name, source_url))

            if not units:
                units = await _parse_html_floorplans(page, property_name, source_url)

            if not units:
                units = await _scrape_generic_floorplan_page(page, property_name, source_url)

        except Exception as e:
            logger.error(f"Error scraping {property_name}: {e}")
        finally:
            await browser.close()

        return units


# ---------------------------------------------------------------------------
# 4. The Bridge at McKinney  (RENTCafe)
# ---------------------------------------------------------------------------

async def scrape_bridge_at_mckinney() -> list[Unit]:
    """Scrape The Bridge at McKinney - 2650 S McDonald St, McKinney TX."""
    property_name = "The Bridge at McKinney"
    source_url = "https://www.thebridgeatmckinney.com/"

    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        page = await context.new_page()
        units = []

        try:
            captured = await intercept_api_responses(page, [
                "rentcafe", "api", "units", "floorplan", "availability",
                "pricing", "yardi", "realpage",
            ])

            fp_url = "https://www.thebridgeatmckinney.com/floorplans"
            await page.goto(fp_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            if captured:
                for cap in captured:
                    units.extend(_parse_rentcafe_api(cap["data"], property_name, source_url))

            if not units:
                units = await _parse_html_floorplans(page, property_name, source_url)

            if not units:
                units = await _scrape_generic_floorplan_page(page, property_name, source_url)

            # Try RENTCafe direct
            if not units:
                await page.goto(
                    "https://www.rentcafe.com/apartments/tx/mckinney/the-bridge-at-mckinney/default.aspx",
                    wait_until="networkidle", timeout=60000,
                )
                await asyncio.sleep(3)
                units = await _scrape_rentcafe_listing(page, property_name, source_url)

        except Exception as e:
            logger.error(f"Error scraping {property_name}: {e}")
        finally:
            await browser.close()

        return units


# ---------------------------------------------------------------------------
# 5. Kinstead  (CBRE / RENTCafe)
# ---------------------------------------------------------------------------

async def scrape_kinstead() -> list[Unit]:
    """Scrape Kinstead - 5701 McKinney Place Dr, McKinney TX."""
    property_name = "Kinstead"
    source_url = "https://www.kinsteadmckinney.com/"

    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        page = await context.new_page()
        units = []

        try:
            captured = await intercept_api_responses(page, [
                "rentcafe", "api", "units", "floorplan", "availability",
                "pricing", "yardi", "realpage", "cbre",
            ])

            fp_url = "https://www.kinsteadmckinney.com/floorplans/"
            await page.goto(fp_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            # Click through floor plan categories
            for tab_text in ["Studio", "1 Bed", "2 Bed", "3 Bed", "All"]:
                try:
                    tab = page.locator(f"text={tab_text}").first
                    if await tab.is_visible(timeout=2000):
                        await tab.click()
                        await asyncio.sleep(2)
                except Exception:
                    pass

            if captured:
                for cap in captured:
                    units.extend(_parse_rentcafe_api(cap["data"], property_name, source_url))

            if not units:
                units = await _parse_html_floorplans(page, property_name, source_url)

            if not units:
                units = await _scrape_generic_floorplan_page(page, property_name, source_url)

            # Try RENTCafe direct
            if not units:
                await page.goto(
                    "https://www.rentcafe.com/apartments/tx/mckinney/kinstead/default.aspx",
                    wait_until="networkidle", timeout=60000,
                )
                await asyncio.sleep(3)
                units = await _scrape_rentcafe_listing(page, property_name, source_url)

        except Exception as e:
            logger.error(f"Error scraping {property_name}: {e}")
        finally:
            await browser.close()

        return units


# ---------------------------------------------------------------------------
# 6. Collin Square  (ZRS Management)
# ---------------------------------------------------------------------------

async def scrape_collin_square() -> list[Unit]:
    """Scrape Collin Square - 3751 N Central Expy, McKinney TX."""
    property_name = "Collin Square"
    source_url = "https://www.collinsquareapts.com/"

    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        page = await context.new_page()
        units = []

        try:
            captured = await intercept_api_responses(page, [
                "api", "units", "floorplan", "availability", "pricing",
                "rentcafe", "entrata", "realpage", "yardi",
            ])

            fp_url = "https://www.collinsquareapts.com/floorplans"
            await page.goto(fp_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            if captured:
                for cap in captured:
                    units.extend(_parse_rentcafe_api(cap["data"], property_name, source_url))

            if not units:
                units = await _parse_html_floorplans(page, property_name, source_url)

            if not units:
                units = await _scrape_generic_floorplan_page(page, property_name, source_url)

        except Exception as e:
            logger.error(f"Error scraping {property_name}: {e}")
        finally:
            await browser.close()

        return units


# ---------------------------------------------------------------------------
# 7. McKinney Terrace  (Greystar)
# ---------------------------------------------------------------------------

async def scrape_mckinney_terrace() -> list[Unit]:
    """Scrape McKinney Terrace - 1703 Rockhill Rd, McKinney TX."""
    property_name = "McKinney Terrace"
    source_url = "https://mckinneyterrace.com/"

    async with async_playwright() as p:
        browser, context = await create_browser_context(p)
        page = await context.new_page()
        units = []

        try:
            captured = await intercept_api_responses(page, [
                "api", "units", "floorplan", "availability", "pricing",
                "rentcafe", "entrata", "realpage", "greystar",
            ])

            fp_url = "https://mckinneyterrace.com/floorplans/"
            await page.goto(fp_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)

            if captured:
                for cap in captured:
                    units.extend(_parse_rentcafe_api(cap["data"], property_name, source_url))

            if not units:
                units = await _parse_html_floorplans(page, property_name, source_url)

            if not units:
                units = await _scrape_generic_floorplan_page(page, property_name, source_url)

        except Exception as e:
            logger.error(f"Error scraping {property_name}: {e}")
        finally:
            await browser.close()

        return units


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _scrape_generic_floorplan_page(page: Page, property_name: str,
                                          source_url: str) -> list[Unit]:
    """Last-resort parser: extract floor plan data from any page structure."""
    units = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Try to find JSON-LD or embedded JSON data
    scripts = await page.query_selector_all("script[type='application/ld+json'], script")
    for script in scripts:
        text = await script.inner_text()
        if not text:
            continue

        # Look for embedded apartment data
        json_matches = re.findall(r'(?:floorplans?|units?|apartments?)\s*[:=]\s*(\[[\s\S]*?\]);', text, re.I)
        for match in json_matches:
            try:
                data = json.loads(match)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            fp_units = _parse_rentcafe_api({"apartments": [item]}, property_name, source_url)
                            units.extend(fp_units)
            except (json.JSONDecodeError, ValueError):
                pass

    if units:
        return units

    # Try extracting from page text content using regex patterns
    content = await page.content()

    # Find all floor plan sections
    fp_pattern = re.compile(
        r'(?:class="[^"]*(?:floor|plan|unit)[^"]*"[^>]*>)'
        r'([\s\S]*?)'
        r'(?:</div>|</section>|</article>)',
        re.I
    )

    # Broader pattern: find blocks with bed/bath/sqft/price info
    text_content = await page.inner_text("body")
    blocks = re.split(r'\n{2,}', text_content)

    for block in blocks:
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue

        has_beds = any(re.search(r'(\d+)\s*(?:bed|br|bedroom)|studio', l, re.I) for l in lines)
        has_price = any("$" in l for l in lines)
        has_sqft = any(re.search(r'\d{3,4}\s*(?:sq|sf)', l, re.I) for l in lines)

        if has_beds and (has_price or has_sqft):
            floorplan = lines[0]
            beds_str = ""
            baths_str = ""
            sqft_str = ""
            rent_str = ""
            avail_str = ""

            for line in lines:
                if re.search(r'(\d+)\s*(?:bed|br)|studio', line, re.I):
                    beds_str = line
                if re.search(r'(\d+\.?\d*)\s*(?:bath|ba)', line, re.I):
                    baths_str = line
                if re.search(r'\d{3,4}\s*(?:sq|sf)', line, re.I):
                    sqft_str = line
                if "$" in line:
                    rent_str = line
                if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', line):
                    avail_str = line

            beds = parse_beds(beds_str)
            baths = parse_baths(baths_str)
            sqft = parse_sqft(sqft_str)
            rent_val, rent_range = parse_rent(rent_str)
            unit_type = normalize_unit_type(beds_str, beds=beds)

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
                    move_in_date=avail_str or None,
                    source_url=source_url,
                    scrape_timestamp=timestamp,
                    data_level="floorplan",
                )
                units.append(unit)

    return units


async def _scrape_rentcafe_listing(page: Page, property_name: str,
                                    source_url: str) -> list[Unit]:
    """Scrape units from a RENTCafe listing page."""
    units = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # RENTCafe uses specific selectors
    cards = await page.query_selector_all(
        ".apartmentCard, .unit-card, .floorplan-card, "
        "[class*='apartment'], [class*='floorplan']"
    )

    for card in cards:
        text = await card.inner_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            continue

        floorplan = ""
        unit_num = ""
        beds = 0
        baths = 1.0
        sqft = 0
        rent_val = None
        rent_range = None
        avail = ""

        for line in lines:
            ll = line.lower()
            if re.match(r'^[A-Z]\d', line) or re.match(r'^(?:apt|unit)\s*#?\s*\d', line, re.I):
                unit_num = line
            elif re.search(r'studio', ll):
                beds = 0
                floorplan = floorplan or line
            elif re.search(r'(\d+)\s*(?:bed|br)', ll):
                beds = int(re.search(r'(\d+)', ll).group(1))
            elif re.search(r'(\d+\.?\d*)\s*(?:bath|ba)', ll):
                baths = float(re.search(r'(\d+\.?\d*)', ll).group(1))
            elif re.search(r'\d{3,4}\s*(?:sq|sf)', ll):
                sqft = parse_sqft(line)
            elif "$" in line:
                rent_val, rent_range = parse_rent(line)
            elif re.search(r'\d{1,2}/\d{1,2}', line):
                avail = line
            elif not floorplan and len(line) < 30:
                floorplan = line

        unit_type = normalize_unit_type("", beds=beds)

        if sqft > 0 or rent_val:
            unit = Unit(
                property_name=property_name,
                unit_number=unit_num or floorplan,
                floorplan=floorplan,
                unit_type=unit_type,
                beds=beds,
                baths=baths,
                sqft=sqft,
                asking_rent=rent_val,
                rent_range=rent_range,
                move_in_date=avail or None,
                source_url=source_url,
                scrape_timestamp=timestamp,
                data_level="unit" if unit_num else "floorplan",
            )
            units.append(unit)

    return units


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

SCRAPER_MAP = {
    "davis_at_the_square": scrape_davis_at_the_square,
    "magnolia_on_the_green": scrape_magnolia_on_the_green,
    "links_at_twin_creeks": scrape_links_at_twin_creeks,
    "bridge_at_mckinney": scrape_bridge_at_mckinney,
    "kinstead": scrape_kinstead,
    "collin_square": scrape_collin_square,
    "mckinney_terrace": scrape_mckinney_terrace,
}


async def scrape_all_properties() -> list[Unit]:
    """Run all scrapers sequentially and return combined results."""
    all_units = []
    for name, scraper_fn in SCRAPER_MAP.items():
        logger.info(f"Scraping {name}...")
        try:
            units = await scraper_fn()
            logger.info(f"  -> {len(units)} units found")
            all_units.extend(units)
        except Exception as e:
            logger.error(f"  -> FAILED: {e}")
    return all_units


def run_all_scrapers() -> list[Unit]:
    """Synchronous wrapper for scrape_all_properties."""
    return asyncio.run(scrape_all_properties())
