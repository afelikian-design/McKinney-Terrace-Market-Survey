"""Scrape available unit data from seven apartment websites.

This script drives headless Chromium via Playwright with mild stealth
tweaks, tries a handful of likely floor-plan URLs for each property, and
then extracts every available unit it can parse off the rendered DOM.

Outputs:
  - market_data.json  (list of unit dicts, including placeholders for
                       properties that failed to yield any data)
  - market_data.csv   (flat CSV of the same records)

Run after installing the dependencies:

    pip install playwright openpyxl
    playwright install chromium
    python scrape_market.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from config import MARKET_PROPERTIES, SUBJECT_PROPERTY

try:
    from playwright.sync_api import (
        TimeoutError as PlaywrightTimeoutError,
        sync_playwright,
    )
    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - handled gracefully at runtime
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None  # type: ignore
    PlaywrightTimeoutError = Exception  # type: ignore


OUTPUT_JSON = Path("market_data.json")
OUTPUT_CSV = Path("market_data.csv")

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

FLOORPLAN_PATH_CANDIDATES = [
    "/floorplans",
    "/floor-plans",
    "/floorplans/",
    "/floor-plans/",
    "/models",
    "/apartments",
    "/availability",
]

# Fields written to CSV (and JSON, in the same key order)
FIELDNAMES = [
    "property_name",
    "is_subject",
    "floorplan_name",
    "unit_number",
    "bedrooms",
    "bathrooms",
    "sqft",
    "asking_rent",
    "base_rent",
    "date_available",
    "concession",
    "psf",
    "property_url",
    "scraped_at",
    "no_data",
]


# ---------------------------------------------------------------------------
# Regex helpers for parsing unit data out of rendered HTML / text snippets
# ---------------------------------------------------------------------------

RE_SQFT = re.compile(
    r"\b(\d{1,2},\d{3}|\d{3,4})\s*(?:sq\.?\s*ft\.?|sqft|sf)\b",
    re.IGNORECASE,
)
RE_RENT = re.compile(r"\$\s*([0-9][0-9,]{2,})")
RE_BED_STUDIO = re.compile(r"\bstudio\b", re.IGNORECASE)
RE_BED_N = re.compile(r"(\d)\s*(?:bed|br|bd|bedroom)s?\b", re.IGNORECASE)
RE_BATH_N = re.compile(r"(\d(?:\.\d)?)\s*(?:bath|ba)s?\b", re.IGNORECASE)
RE_DATE = re.compile(
    r"\b(available\s+now|now\s+available|(?:\d{1,2}/\d{1,2}/\d{2,4}))\b",
    re.IGNORECASE,
)
RE_CONCESSION = re.compile(
    r"(\d+\s*(?:month|weeks?|wks?)\s*free|free\s*\w+|"
    r"look\s*and\s*lease|reduced\s*deposit|\$\d+\s*off)",
    re.IGNORECASE,
)
RE_UNIT_NUMBER = re.compile(
    r"\b(?:unit|apt|apartment|#)\s*#?\s*([A-Z0-9\-]{2,8})\b",
    re.IGNORECASE,
)
RE_FLOORPLAN = re.compile(r"\b([A-Z]\d{1,2}[A-Z]?)\b")


def parse_int(s: str) -> int | None:
    try:
        return int(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def parse_float(s: str) -> float | None:
    try:
        return float(str(s).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _split_candidate_blocks(text: str) -> list[str]:
    """Split a page's visible text into candidate 'unit blocks' for parsing.

    Strategy: split on blank lines, then keep blocks that contain both
    a sqft mention and a dollar amount (the strong signal that a block
    represents a rentable unit/floor plan card).
    """
    raw_blocks = re.split(r"\n{2,}", text)
    good: list[str] = []
    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        if RE_SQFT.search(block) and RE_RENT.search(block):
            good.append(block)
    return good


def _extract_unit_from_block(
    block: str,
    property_name: str,
    property_url: str,
    scraped_at: str,
) -> dict[str, Any] | None:
    sqft_match = RE_SQFT.search(block)
    rent_match = RE_RENT.search(block)
    if not sqft_match or not rent_match:
        return None

    sqft = parse_int(sqft_match.group(1))
    rent = parse_int(rent_match.group(1))
    if not sqft or not rent:
        return None
    # Filter out obviously unrealistic numbers
    if sqft < 200 or sqft > 5000:
        return None
    if rent < 500 or rent > 25000:
        return None

    # Bedrooms
    bedrooms: int | None = None
    if RE_BED_STUDIO.search(block):
        bedrooms = 0
    else:
        m = RE_BED_N.search(block)
        if m:
            try:
                bedrooms = int(m.group(1))
            except ValueError:
                bedrooms = None
    if bedrooms is None or bedrooms > 4:
        return None

    # Bathrooms
    bathrooms: float | None = None
    bath_match = RE_BATH_N.search(block)
    if bath_match:
        bathrooms = parse_float(bath_match.group(1))
    if bathrooms is None:
        bathrooms = 1.0 if bedrooms <= 1 else 2.0

    # Floor plan name — common patterns: "A1", "B2", "S1", etc.
    floorplan_name: str | None = None
    fp_match = RE_FLOORPLAN.search(block)
    if fp_match:
        floorplan_name = fp_match.group(1)

    # Unit number
    unit_number: str | None = None
    unit_match = RE_UNIT_NUMBER.search(block)
    if unit_match:
        unit_number = unit_match.group(1)

    # Availability
    date_available: str | None = None
    date_match = RE_DATE.search(block)
    if date_match:
        value = date_match.group(1)
        date_available = "Available Now" if "now" in value.lower() else value

    # Concession
    concession: str | None = None
    conc_match = RE_CONCESSION.search(block)
    if conc_match:
        concession = conc_match.group(1).strip()

    psf = round(rent / sqft, 2) if sqft else None

    return {
        "property_name": property_name,
        "is_subject": property_name == SUBJECT_PROPERTY,
        "floorplan_name": floorplan_name,
        "unit_number": unit_number,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "sqft": sqft,
        "asking_rent": rent,
        "base_rent": rent,
        "date_available": date_available,
        "concession": concession,
        "psf": psf,
        "property_url": property_url,
        "scraped_at": scraped_at,
        "no_data": False,
    }


def _dedupe_units(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for u in units:
        key = (
            u.get("floorplan_name"),
            u.get("unit_number"),
            u.get("bedrooms"),
            u.get("sqft"),
            u.get("asking_rent"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(u)
    return out


def _placeholder(property_name: str, url: str, scraped_at: str) -> dict[str, Any]:
    return {
        "property_name": property_name,
        "is_subject": property_name == SUBJECT_PROPERTY,
        "floorplan_name": None,
        "unit_number": None,
        "bedrooms": None,
        "bathrooms": None,
        "sqft": None,
        "asking_rent": None,
        "base_rent": None,
        "date_available": None,
        "concession": None,
        "psf": None,
        "property_url": url,
        "scraped_at": scraped_at,
        "no_data": True,
    }


# ---------------------------------------------------------------------------
# Playwright scraping per-property
# ---------------------------------------------------------------------------


def _candidate_urls(base_url: str) -> list[str]:
    base = base_url.rstrip("/")
    urls = [base + "/"]
    for path in FLOORPLAN_PATH_CANDIDATES:
        urls.append(base + path)
    return urls


def _scrape_property(
    context,
    prop: dict[str, Any],
    scraped_at: str,
) -> list[dict[str, Any]]:
    name = prop["name"]
    base_url = prop["url"]
    print(f"[scrape] {name} — {base_url}")

    page = context.new_page()
    page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    collected_units: list[dict[str, Any]] = []
    successful_url = base_url

    for candidate in _candidate_urls(base_url):
        try:
            resp = page.goto(candidate, timeout=30000, wait_until="domcontentloaded")
        except PlaywrightTimeoutError:
            print(f"  - timeout: {candidate}")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"  - error navigating to {candidate}: {exc}")
            continue

        status = resp.status if resp is not None else None
        if status and status >= 400:
            print(f"  - HTTP {status}: {candidate}")
            continue

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except PlaywrightTimeoutError:
            pass  # Not fatal; continue with whatever rendered

        try:
            text = page.evaluate("document.body ? document.body.innerText : ''")
        except Exception:  # noqa: BLE001
            text = ""

        if not text:
            continue

        blocks = _split_candidate_blocks(text)
        parsed = [
            u
            for block in blocks
            if (u := _extract_unit_from_block(block, name, candidate, scraped_at))
        ]
        if parsed:
            collected_units.extend(parsed)
            successful_url = candidate
            print(f"  + parsed {len(parsed)} candidate unit(s) from {candidate}")
            break  # first URL that produces any data wins

    page.close()

    collected_units = _dedupe_units(collected_units)
    for u in collected_units:
        u["property_url"] = successful_url
    return collected_units


def scrape_all() -> list[dict[str, Any]]:
    scraped_at = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    if not PLAYWRIGHT_AVAILABLE:
        print(
            "[warn] Playwright is not installed. Writing placeholder entries "
            "for all properties. Install with: pip install playwright && "
            "playwright install chromium"
        )
        for prop in MARKET_PROPERTIES:
            results.append(_placeholder(prop["name"], prop["url"], scraped_at))
        return results

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] Could not launch Chromium: {exc}")
            print("       Writing placeholder entries for all properties.")
            for prop in MARKET_PROPERTIES:
                results.append(_placeholder(prop["name"], prop["url"], scraped_at))
            return results

        context = browser.new_context(
            user_agent=CHROME_UA,
            locale="en-US",
            extra_http_headers={
                "accept-language": "en-US,en;q=0.9",
                "accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
            },
            viewport={"width": 1366, "height": 900},
        )

        for prop in MARKET_PROPERTIES:
            try:
                units = _scrape_property(context, prop, scraped_at)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {prop['name']} failed: {exc}")
                traceback.print_exc()
                units = []

            if units:
                results.extend(units)
            else:
                print(f"  ! {prop['name']} — no parseable data, adding placeholder")
                results.append(_placeholder(prop["name"], prop["url"], scraped_at))

        context.close()
        browser.close()

    return results


# ---------------------------------------------------------------------------
# Persistence + summary
# ---------------------------------------------------------------------------


def write_outputs(records: Iterable[dict[str, Any]]) -> None:
    records_list = list(records)
    OUTPUT_JSON.write_text(json.dumps(records_list, indent=2, default=str))
    with OUTPUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for rec in records_list:
            writer.writerow({k: rec.get(k) for k in FIELDNAMES})


def print_summary(records: list[dict[str, Any]]) -> None:
    attempted = len(MARKET_PROPERTIES)
    prop_with_data = {
        r["property_name"] for r in records if not r.get("no_data")
    }
    live_units = [r for r in records if not r.get("no_data")]
    bed_counts = Counter(
        (
            "Studios"
            if r.get("bedrooms") == 0
            else f"{r.get('bedrooms')}BR"
        )
        for r in live_units
    )

    print()
    print("=" * 60)
    print("SCRAPE SUMMARY")
    print("=" * 60)
    print(f"Properties attempted:    {attempted}")
    print(f"Properties with data:    {len(prop_with_data)}")
    print(f"Total units extracted:   {len(live_units)}")
    print("Units per bedroom type:")
    for key in ("Studios", "1BR", "2BR", "3BR"):
        print(f"  {key:<10} {bed_counts.get(key, 0)}")
    print("=" * 60)


def main() -> int:
    records = scrape_all()
    write_outputs(records)
    print_summary(records)
    print(f"\nWrote {OUTPUT_JSON} and {OUTPUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
