"""Apartment comp tracker scraper.

Scrapes Apartments.com (with a RentCafe fallback) for McKinney Terrace and its
seven comp properties, then writes the results to ../data/data.json.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    TimeoutError as PWTimeout,
    async_playwright,
)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

SPECIALS_KEYWORDS = [
    "weeks free",
    "week free",
    "months free",
    "month free",
    "off",
    "special",
    "save",
    "waived",
    "look and lease",
    "reduced",
]

SPECIALS_CLASS_HINTS = [
    "rentSpecials",
    "specials",
    "promo",
    "banner",
    "offer",
]


@dataclass
class PropertySpec:
    name: str
    address: str
    url: str | None
    search_query: str | None
    is_subject: bool = False


PROPERTIES: list[PropertySpec] = [
    PropertySpec(
        name="McKinney Terrace",
        address="1703 Rockhill Road, McKinney, TX 75069",
        url="https://www.apartments.com/mckinney-terrace-mckinney-tx/3l4wpbs/",
        search_query=None,
        is_subject=True,
    ),
    PropertySpec(
        name="The Bridge at McKinney",
        address="McKinney, TX",
        url="https://www.apartments.com/the-bridge-at-mckinney-mckinney-tx/s7hf5p5/",
        search_query=None,
    ),
    PropertySpec(
        name="Kinstead",
        address="McKinney, TX",
        url="https://www.apartments.com/kinstead-mckinney-tx/mnwls5h/",
        search_query=None,
    ),
    PropertySpec(
        name="Collin Square",
        address="McKinney, TX",
        url="https://www.apartments.com/collin-square-mckinney-tx/cplebmg/",
        search_query=None,
    ),
    PropertySpec(
        name="Gray Branch Apartments",
        address="1760 North Ridge Road, McKinney, TX 75071",
        url=None,
        search_query="Gray Branch Apartments 1760 North Ridge Road McKinney TX 75071",
    ),
    PropertySpec(
        name="Bexley Lake Forest",
        address="5201 Collin McKinney Parkway, McKinney, TX 75070",
        url=None,
        search_query="Bexley Lake Forest 5201 Collin McKinney Parkway McKinney TX 75070",
    ),
    PropertySpec(
        name="McKinney Village",
        address="201 McKinney Village Parkway, McKinney, TX 75069",
        url=None,
        search_query="McKinney Village 201 McKinney Village Parkway McKinney TX 75069",
    ),
    PropertySpec(
        name="The Dalton",
        address="3549 Medical Center Drive, McKinney, TX 75069",
        url=None,
        search_query="The Dalton 3549 Medical Center Drive McKinney TX 75069",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_int(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d[\d,]*)", text)
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _extract_float(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _extract_rent(text: str | None) -> int | None:
    if not text:
        return None
    cleaned = text.replace(",", "")
    prices = [int(p) for p in re.findall(r"\$(\d{3,6})", cleaned)]
    if not prices:
        return None
    return min(prices)


def _extract_beds(text: str | None) -> int | None:
    if not text:
        return None
    lower = text.lower()
    if "studio" in lower or "efficiency" in lower:
        return 0
    match = re.search(r"(\d+)\s*(?:bd|bed|br)", lower)
    if match:
        return int(match.group(1))
    match = re.search(r"^(\d+)", lower.strip())
    if match:
        return int(match.group(1))
    return None


async def _apply_stealth(page: Page) -> None:
    await page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )


async def _new_context(browser: Browser) -> BrowserContext:
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )
    return context


async def _safe_goto(page: Page, url: str, *, timeout: int = 60_000) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        try:
            await page.wait_for_load_state("networkidle", timeout=15_000)
        except PWTimeout:
            pass
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ! navigation failed: {exc}", file=sys.stderr)
        return False


async def _wait_for_pricing(page: Page) -> None:
    """Wait for apartments.com's lazy-loaded pricing UI to render."""
    selectors = [
        ".pricingGridItem",
        ".mortar-wrapper",
        ".availabilityTable",
        "[data-tab-content-id]",
        ".priceGridModelWrapper",
        "[class*='pricing' i]",
        "[class*='floorplan' i]",
    ]
    for selector in selectors:
        try:
            await page.wait_for_selector(selector, timeout=8_000, state="attached")
            break
        except PWTimeout:
            continue


async def _scroll_page(page: Page) -> None:
    """Scroll top→bottom→top to force lazy-loaded modules to render."""
    try:
        await page.evaluate(
            """
            async () => {
              const sleep = (ms) => new Promise(r => setTimeout(r, ms));
              const totalHeight = document.body.scrollHeight;
              let y = 0;
              while (y < totalHeight) {
                window.scrollTo(0, y);
                await sleep(250);
                y += 600;
              }
              window.scrollTo(0, 0);
              await sleep(500);
            }
            """
        )
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Specials / concessions
# ---------------------------------------------------------------------------


async def _extract_specials(page: Page) -> str | None:
    # 1) Look for dedicated specials containers by class hint.
    for hint in SPECIALS_CLASS_HINTS:
        selector = f"[class*='{hint}' i]"
        try:
            elements = await page.query_selector_all(selector)
        except Exception:  # noqa: BLE001
            continue
        for el in elements:
            try:
                text = (await el.inner_text()).strip()
            except Exception:  # noqa: BLE001
                continue
            if text and 5 <= len(text) <= 400:
                return " ".join(text.split())

    # 2) Fall back to scanning the body for keyword hits.
    try:
        body_text = await page.inner_text("body")
    except Exception:  # noqa: BLE001
        return None
    for line in body_text.splitlines():
        candidate = line.strip()
        if not candidate or len(candidate) > 240:
            continue
        lower = candidate.lower()
        if any(kw in lower for kw in SPECIALS_KEYWORDS):
            return " ".join(candidate.split())
    return None


# ---------------------------------------------------------------------------
# Apartments.com extraction
# ---------------------------------------------------------------------------


async def _click_show_all(page: Page) -> None:
    button_texts = ["Show All Units", "View All", "See All", "Show all"]
    for text in button_texts:
        try:
            buttons = await page.get_by_role("button", name=re.compile(text, re.I)).all()
        except Exception:  # noqa: BLE001
            buttons = []
        for btn in buttons:
            try:
                if await btn.is_visible():
                    await btn.click(timeout=3_000)
                    await asyncio.sleep(0.8)
            except Exception:  # noqa: BLE001
                continue


async def _extract_units_apartments(page: Page) -> list[dict[str, Any]]:
    """Pull every available unit visible on an Apartments.com listing page."""
    await _wait_for_pricing(page)
    await _scroll_page(page)
    await _click_show_all(page)
    await _scroll_page(page)
    await asyncio.sleep(1.0)

    # JS extraction is much more robust than DOM-level python selectors here
    # because Apartments.com uses a mix of table- and card-based layouts.
    script = r"""
    () => {
      const units = [];

      const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const num = (s) => {
        if (!s) return null;
        const m = String(s).replace(/,/g, '').match(/(\d+(?:\.\d+)?)/);
        return m ? parseFloat(m[1]) : null;
      };
      const intNum = (s) => {
        const v = num(s);
        return v == null ? null : Math.round(v);
      };
      const extractRent = (s) => {
        if (!s) return null;
        const matches = String(s).replace(/,/g, '').match(/\$(\d{3,6})/g);
        if (!matches) return null;
        const vals = matches.map(m => parseInt(m.replace('$', ''), 10));
        return Math.min(...vals);
      };
      const extractBeds = (s) => {
        if (!s) return null;
        const lower = s.toLowerCase();
        if (lower.includes('studio') || lower.includes('efficiency')) return 0;
        const m = lower.match(/(\d+)\s*(?:bd|bed|br)/);
        if (m) return parseInt(m[1], 10);
        const m2 = lower.match(/^(\d+)/);
        return m2 ? parseInt(m2[1], 10) : null;
      };
      const extractBaths = (s) => {
        if (!s) return null;
        const lower = s.toLowerCase();
        const m = lower.match(/(\d+(?:\.\d+)?)\s*(?:ba|bath)/);
        if (m) return parseFloat(m[1]);
        return null;
      };

      // Collect floorplan containers. Apartments.com uses several naming
      // conventions across experiments, so cast a wide net.
      const planSelectors = [
        '.pricingGridItem',
        '.mortar-wrapper',
        '.availabilityTable',
        '[data-tab-content-id]',
        '.priceGridModelWrapper',
      ];
      const planNodes = new Set();
      for (const sel of planSelectors) {
        document.querySelectorAll(sel).forEach(n => planNodes.add(n));
      }
      if (planNodes.size === 0) {
        document.querySelectorAll('[class*="pricing" i], [class*="floorplan" i]').forEach(n => planNodes.add(n));
      }

      const seen = new Set();

      const pushUnit = (u) => {
        if (!u) return;
        if (u.rent == null && u.sqft == null) return;
        const key = [u.unit_number, u.floorplan, u.sqft, u.rent, u.available_date].join('|');
        if (seen.has(key)) return;
        seen.add(key);
        units.push(u);
      };

      const headerBeds = (container) => {
        const txt = clean(container.innerText || '');
        return extractBeds(txt);
      };
      const headerBaths = (container) => {
        const txt = clean(container.innerText || '');
        return extractBaths(txt);
      };
      const headerPlan = (container) => {
        const nameEl = container.querySelector(
          '.modelName, [class*="modelName" i], [class*="planName" i], h2, h3'
        );
        return nameEl ? clean(nameEl.innerText) : null;
      };

      for (const plan of planNodes) {
        const planName = headerPlan(plan);
        const planBeds = headerBeds(plan);
        const planBaths = headerBaths(plan);

        // Per-unit rows inside a plan.
        const rowSelectors = [
          '.unitContainer',
          '.availabilityRow',
          'li.unit',
          '[class*="unitRow" i]',
          'tr[data-unit]',
        ];
        let rows = [];
        for (const sel of rowSelectors) {
          rows = rows.concat(Array.from(plan.querySelectorAll(sel)));
        }
        rows = Array.from(new Set(rows));

        if (rows.length) {
          for (const row of rows) {
            const rowText = clean(row.innerText || '');
            const unitEl = row.querySelector(
              '[class*="unitColumn" i], [class*="unitLabel" i], [data-unit]'
            );
            let unitNumber = null;
            if (unitEl) {
              const raw = clean(unitEl.innerText || unitEl.getAttribute('data-unit') || '');
              const m = raw.match(/(?:unit|apt|#)\s*([\w-]+)/i) || raw.match(/^#?([\w-]+)/);
              unitNumber = m ? m[1] : (raw || null);
            }

            const sqftEl = row.querySelector('[class*="sqft" i], [class*="sqFt" i]');
            const rentEl = row.querySelector('[class*="rent" i], [class*="price" i]');
            const dateEl = row.querySelector(
              '[class*="dateAvailable" i], [class*="availability" i], [class*="available" i]'
            );

            const sqft = intNum((sqftEl && sqftEl.innerText) || rowText.match(/(\d[\d,]*)\s*sq\s*ft/i)?.[0]);
            const rent = extractRent((rentEl && rentEl.innerText) || rowText);
            const available = clean(
              (dateEl && dateEl.innerText) ||
              (rowText.match(/(?:avail(?:able)?\s*(?:now|[A-Za-z]+ \d+|\d{4}-\d{2}-\d{2}))/i) || [''])[0]
            ) || null;

            pushUnit({
              unit_number: unitNumber && unitNumber !== '' ? unitNumber : null,
              floorplan: planName,
              beds: planBeds,
              baths: planBaths,
              sqft: sqft,
              rent: rent,
              available_date: available,
            });
          }
        } else {
          // No per-unit rows — fall back to the plan summary itself.
          const rowText = clean(plan.innerText || '');
          const sqft = intNum(rowText.match(/(\d[\d,]*)\s*sq\s*ft/i)?.[0]);
          const rent = extractRent(rowText);
          const available = (rowText.match(/(?:avail(?:able)?\s*(?:now|[A-Za-z]+ \d+|\d{4}-\d{2}-\d{2}))/i) || [null])[0];
          pushUnit({
            unit_number: null,
            floorplan: planName,
            beds: planBeds,
            baths: planBaths,
            sqft: sqft,
            rent: rent,
            available_date: available ? clean(available) : null,
          });
        }
      }

      return units;
    }
    """
    try:
        raw_units = await page.evaluate(script)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! unit extraction failed: {exc}", file=sys.stderr)
        return []

    units: list[dict[str, Any]] = []
    for u in raw_units or []:
        if u.get("rent") is None and u.get("sqft") is None:
            continue
        units.append(
            {
                "unit_number": u.get("unit_number"),
                "floorplan": u.get("floorplan"),
                "beds": u.get("beds") if u.get("beds") is not None else None,
                "baths": u.get("baths") if u.get("baths") is not None else None,
                "sqft": u.get("sqft"),
                "rent": u.get("rent"),
                "available_date": u.get("available_date") or "Now",
            }
        )
    return units


async def _find_apartments_url(page: Page, query: str) -> str | None:
    search_url = f"https://www.apartments.com/search/?keyword={quote_plus(query)}"
    if not await _safe_goto(page, search_url):
        return None
    try:
        link = await page.query_selector(
            "a.property-link, a[href*='apartments.com/'][data-listingid], article a[href*='apartments.com/']"
        )
        if link:
            href = await link.get_attribute("href")
            if href:
                return href
    except Exception:  # noqa: BLE001
        pass

    # Backup: any anchor whose href looks like a property detail page.
    try:
        hrefs = await page.eval_on_selector_all(
            "a",
            "els => els.map(e => e.href).filter(h => /apartments\\.com\\/[a-z0-9-]+-[a-z]{2,}\\//i.test(h))",
        )
        for href in hrefs:
            if "search" in href or "listings" in href:
                continue
            return href
    except Exception:  # noqa: BLE001
        pass
    return None


# ---------------------------------------------------------------------------
# RentCafe fallback
# ---------------------------------------------------------------------------


async def _rentcafe_fallback(page: Page, prop: PropertySpec) -> list[dict[str, Any]] | None:
    query = prop.search_query or f"{prop.name} {prop.address}"
    search_url = f"https://www.rentcafe.com/search-apartments.aspx?search={quote_plus(query)}"
    if not await _safe_goto(page, search_url):
        return None

    property_url: str | None = None
    try:
        href = await page.eval_on_selector(
            "a.result-item, a[href*='rentcafe.com/apartments']",
            "el => el && el.href",
        )
        if href:
            property_url = href
    except Exception:  # noqa: BLE001
        property_url = None

    if not property_url:
        return None
    if not await _safe_goto(page, property_url):
        return None

    script = r"""
    () => {
      const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const extractRent = (s) => {
        if (!s) return null;
        const matches = String(s).replace(/,/g, '').match(/\$(\d{3,6})/g);
        if (!matches) return null;
        const vals = matches.map(m => parseInt(m.replace('$', ''), 10));
        return Math.min(...vals);
      };
      const extractBeds = (s) => {
        if (!s) return null;
        const lower = s.toLowerCase();
        if (lower.includes('studio')) return 0;
        const m = lower.match(/(\d+)\s*(?:bd|bed|br)/);
        return m ? parseInt(m[1], 10) : null;
      };
      const extractBaths = (s) => {
        if (!s) return null;
        const m = s.toLowerCase().match(/(\d+(?:\.\d+)?)\s*(?:ba|bath)/);
        return m ? parseFloat(m[1]) : null;
      };
      const intNum = (s) => {
        if (!s) return null;
        const m = String(s).replace(/,/g, '').match(/(\d+)/);
        return m ? parseInt(m[1], 10) : null;
      };

      const rows = Array.from(document.querySelectorAll(
        '.fp-unit-row, .unit-card, [class*="unit" i][class*="row" i], tr.unit'
      ));
      const seen = new Set();
      const units = [];
      for (const row of rows) {
        const txt = clean(row.innerText || '');
        if (!txt) continue;
        const rent = extractRent(txt);
        const sqft = intNum((txt.match(/(\d[\d,]*)\s*sq\s*ft/i) || [])[0]);
        if (!rent && !sqft) continue;
        const beds = extractBeds(txt);
        const baths = extractBaths(txt);
        const available = (txt.match(/avail[^,.]*?(now|\d{1,2}\/\d{1,2}\/\d{2,4}|[A-Z][a-z]+ \d+)/i) || [])[1] || 'Now';
        const unitMatch = txt.match(/(?:unit|apt|#)\s*([\w-]+)/i);
        const planMatch = row.querySelector('[class*="plan" i], [class*="model" i], h3, h4');
        const entry = {
          unit_number: unitMatch ? unitMatch[1] : null,
          floorplan: planMatch ? clean(planMatch.innerText) : null,
          beds, baths, sqft, rent,
          available_date: available,
        };
        const key = [entry.unit_number, entry.floorplan, entry.sqft, entry.rent].join('|');
        if (seen.has(key)) continue;
        seen.add(key);
        units.push(entry);
      }
      return units;
    }
    """
    try:
        raw_units = await page.evaluate(script)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! rentcafe extraction failed: {exc}", file=sys.stderr)
        return None
    return raw_units or []


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def scrape_property(browser: Browser, prop: PropertySpec) -> dict[str, Any]:
    print(f"→ {prop.name}")
    context = await _new_context(browser)
    page = await context.new_page()
    await _apply_stealth(page)

    result: dict[str, Any] = {
        "name": prop.name,
        "address": prop.address,
        "is_subject": prop.is_subject,
        "source": "apartments.com",
        "specials": None,
        "total_available": 0,
        "units": [],
        "error": None,
    }

    try:
        target_url = prop.url
        if not target_url and prop.search_query:
            target_url = await _find_apartments_url(page, prop.search_query)
            if not target_url:
                raise RuntimeError("property not found via apartments.com search")

        if not await _safe_goto(page, target_url):
            raise RuntimeError(f"failed to load {target_url}")

        result["specials"] = await _extract_specials(page)
        units = await _extract_units_apartments(page)

        if not units:
            try:
                title = await page.title()
                body_len = await page.evaluate("() => document.body.innerText.length")
                print(f"  · 0 units on apartments.com (title={title!r}, body_chars={body_len}) — trying RentCafe fallback")
            except Exception:  # noqa: BLE001
                print("  · 0 units on apartments.com — trying RentCafe fallback")
            fallback = await _rentcafe_fallback(page, prop)
            if fallback:
                result["source"] = "rentcafe"
                units = fallback

        result["units"] = units
        result["total_available"] = len(units)
        print(f"  ✓ {len(units)} unit(s) captured ({result['source']})")
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        result["error"] = f"Failed: {exc}"
        result["units"] = []
        result["total_available"] = 0
    finally:
        await context.close()

    return result


async def main() -> int:
    out_path = Path(__file__).resolve().parent.parent / "data" / "data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        properties: list[dict[str, Any]] = []
        for idx, prop in enumerate(PROPERTIES):
            if idx > 0:
                await asyncio.sleep(random.uniform(2, 4))
            properties.append(await scrape_property(browser, prop))
        await browser.close()

    payload = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "properties": properties,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {out_path} with {len(properties)} properties")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
