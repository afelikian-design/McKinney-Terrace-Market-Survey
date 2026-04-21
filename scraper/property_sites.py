"""Scrape data directly from each property's own website.

Fallback path for when apartments.com is bot-blocked. Every property site is
different, so this module combines a handful of heuristic extractors that
cover the most common platforms (RentCafe / Yardi, Entrata, plus a generic
WordPress/Elementor fallback).
"""

from __future__ import annotations

import asyncio
import re
import sys
import traceback
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import Page, TimeoutError as PWTimeout


@dataclass
class PropertySiteSpec:
    name: str
    home_url: str
    # Optional direct floorplan page — skips the auto-discovery step.
    floorplans_url: str | None = None


# Manually curated — add per-property overrides as you learn them.
PROPERTY_SITES: dict[str, PropertySiteSpec] = {
    "McKinney Terrace": PropertySiteSpec(
        name="McKinney Terrace",
        home_url="https://mckinneyterrace.com/",
    ),
    "The Bridge at McKinney": PropertySiteSpec(
        name="The Bridge at McKinney",
        home_url="https://www.thebridgeatmckinney.com/",
    ),
    "Kinstead": PropertySiteSpec(
        name="Kinstead",
        home_url="https://www.kinsteadmckinney.com/",
    ),
    "Collin Square": PropertySiteSpec(
        name="Collin Square",
        home_url="https://www.collinsquareapts.com/",
    ),
    "Gray Branch Apartments": PropertySiteSpec(
        name="Gray Branch Apartments",
        home_url="https://livebh.com/apartments/gray-branch-apartments/",
    ),
    "Bexley Lake Forest": PropertySiteSpec(
        name="Bexley Lake Forest",
        home_url="https://www.bexleylakeforest.com/",
    ),
    "McKinney Village": PropertySiteSpec(
        name="McKinney Village",
        home_url="https://www.mckinneyvillageapts.com/",
    ),
    "The Dalton": PropertySiteSpec(
        name="The Dalton",
        home_url="https://daltonapartmentsmckinney.com/",
    ),
}


SPECIALS_KEYWORDS = [
    "weeks free",
    "week free",
    "months free",
    "month free",
    "special",
    "save",
    "waived",
    "look and lease",
    "reduced",
    "concession",
]


async def _safe_goto(page: Page, url: str, *, timeout: int = 60_000) -> bool:
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        try:
            await page.wait_for_load_state("networkidle", timeout=12_000)
        except PWTimeout:
            pass
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"    ! nav failed: {exc}", file=sys.stderr)
        return False


async def _find_floorplans_url(page: Page, home_url: str) -> str | None:
    """Scan the home page for a link labelled Floorplans / Availability."""
    candidates = await page.evaluate(
        """
        () => {
          const patterns = [
            /floor\\s*plans?/i,
            /availability/i,
            /apartments?/i,
            /current\\s*openings?/i,
            /pricing/i,
            /lease/i,
          ];
          const anchors = Array.from(document.querySelectorAll('a[href]'));
          const hits = [];
          for (const a of anchors) {
            const text = (a.innerText || '').trim();
            const href = a.getAttribute('href') || '';
            for (const p of patterns) {
              if (p.test(text) || p.test(href)) {
                hits.push({ text, href });
                break;
              }
            }
          }
          return hits;
        }
        """
    )
    if not candidates:
        return None

    def absolute(href: str) -> str:
        return urljoin(home_url, href)

    # Prefer index-style URLs: something that ends with /floorplans/ or
    # /floor-plans — not a link to a specific plan like /floor-plans/dawn-109/.
    index_patterns = (
        "/floorplans",
        "/floor-plans",
        "/floor_plans",
        "/availability",
        "/current-openings",
    )
    indexed: list[tuple[int, str]] = []
    for c in candidates:
        href = (c.get("href") or "").lower()
        if not href or href.startswith("#"):
            continue
        for pat in index_patterns:
            if pat in href:
                # Score: shorter URLs are more likely to be the index page.
                # Penalise trailing path segments past the keyword.
                idx = href.find(pat)
                suffix = href[idx + len(pat):].strip("/")
                extra_segments = suffix.count("/") + (1 if suffix else 0)
                indexed.append((extra_segments, absolute(c.get("href") or "")))
                break
    if indexed:
        indexed.sort(key=lambda t: t[0])
        return indexed[0][1]

    # Secondary priority keywords (no "index" preference available).
    for keyword in ("apartments", "pricing"):
        for c in candidates:
            href = c.get("href") or ""
            if keyword in href.lower():
                return absolute(href)

    # Fall back to first candidate with a non-fragment href.
    for c in candidates:
        href = c.get("href") or ""
        if href and not href.startswith("#"):
            return absolute(href)
    return None


async def _extract_specials(page: Page) -> str | None:
    try:
        body = await page.inner_text("body")
    except Exception:  # noqa: BLE001
        return None
    for line in body.splitlines():
        candidate = line.strip()
        if not candidate or len(candidate) > 240:
            continue
        lower = candidate.lower()
        if any(kw in lower for kw in SPECIALS_KEYWORDS):
            return " ".join(candidate.split())
    return None


# ---------------------------------------------------------------------------
# Platform-specific extractors
# ---------------------------------------------------------------------------


_RENTCAFE_HINTS = (
    "rentcafe.com",
    "/current-openings",
    "wp-content/plugins/rentcafe",
)


async def _detect_platform(page: Page) -> str:
    """Return 'rentcafe' | 'entrata' | 'knock' | 'iframe' | 'generic'."""
    try:
        html = await page.content()
    except Exception:  # noqa: BLE001
        return "generic"
    lower = html.lower()
    if any(h in lower for h in _RENTCAFE_HINTS):
        return "rentcafe"
    if "entrata.com" in lower or "residentportal" in lower:
        return "entrata"
    if "knock" in lower and "knockcrm" in lower:
        return "knock"
    if "<iframe" in lower:
        return "iframe"
    return "generic"


_EXTRACT_SCRIPT = r"""
() => {
  const clean = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const intNum = (s) => {
    if (!s) return null;
    const m = String(s).replace(/,/g, '').match(/(\d+)/);
    return m ? parseInt(m[1], 10) : null;
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
    const m = lower.match(/(\d+)\s*(?:bd|bed|br)\b/);
    return m ? parseInt(m[1], 10) : null;
  };
  const extractBaths = (s) => {
    if (!s) return null;
    const m = s.toLowerCase().match(/(\d+(?:\.\d+)?)\s*(?:ba|bath)\b/);
    return m ? parseFloat(m[1]) : null;
  };

  const selectors = [
    '[class*="floorplan" i]',
    '[class*="floor-plan" i]',
    '[class*="fp-card" i]',
    '[class*="fp-item" i]',
    '[class*="plan-card" i]',
    '[class*="unit-card" i]',
    '[class*="plan-row" i]',
    '[data-floorplan-id]',
    '[data-fp-id]',
    '[id*="floorplan" i]',
    '.fp-container',
    '.floor_plan',
    '.model-card',
    '.model-item',
    'article[class*="plan" i]',
    'li[class*="plan" i]',
    'tr[class*="plan" i]',
    'tr[class*="unit" i]',
  ];
  let cards = [];
  for (const sel of selectors) {
    cards = cards.concat(Array.from(document.querySelectorAll(sel)));
  }
  cards = Array.from(new Set(cards));

  // Build units first, then dedupe by content signature — much more reliable
  // than a DOM "outermost" heuristic (which wrongly collapses multiple
  // cards nested under a common container).
  const seen = new Set();
  const units = [];
  for (const card of cards) {
    const text = clean(card.innerText || '');
    if (!text) continue;
    const rent = extractRent(text);
    const sqft = intNum((text.match(/(\d[\d,]*)\s*sq\.?\s*ft/i) || [])[0]);
    if (!rent && !sqft) continue;
    const beds = extractBeds(text);
    const baths = extractBaths(text);
    const planEl = card.querySelector(
      '[class*="name" i], [class*="title" i], h2, h3, h4'
    );
    const planName = planEl ? clean(planEl.innerText) : null;
    const unitEl = card.querySelector('[class*="unit" i][class*="number" i], [data-unit]');
    const unitNumber = unitEl
      ? clean(unitEl.innerText || unitEl.getAttribute('data-unit') || '') || null
      : null;
    const availMatch = text.match(
      /avail[^,.\n]*?(now|immediate|\d{1,2}\/\d{1,2}(?:\/\d{2,4})?|[A-Z][a-z]+ \d{1,2})/i
    );
    const available = availMatch ? clean(availMatch[0]) : null;

    // Dedupe by content, not DOM. Two cards describing the same unit
    // will always share planName + rent + sqft.
    const key = [planName, unitNumber, sqft, rent].join('|');
    if (seen.has(key)) continue;
    seen.add(key);
    units.push({
      unit_number: unitNumber,
      floorplan: planName,
      beds, baths, sqft, rent,
      available_date: available,
    });
  }
  return units;
}
"""


async def _extract_units_from_frame(frame) -> list[dict[str, Any]]:
    try:
        raw_units = await frame.evaluate(_EXTRACT_SCRIPT)
    except Exception:  # noqa: BLE001
        return []
    return raw_units or []


async def _extract_units_generic(page: Page) -> list[dict[str, Any]]:
    """Run the heuristic extractor on the page AND every nested iframe."""
    # Scroll first so lazy widgets render.
    try:
        await page.evaluate(
            """
            async () => {
              const sleep = ms => new Promise(r => setTimeout(r, ms));
              let y = 0;
              while (y < document.body.scrollHeight) {
                window.scrollTo(0, y);
                await sleep(150);
                y += 600;
              }
              window.scrollTo(0, 0);
              await sleep(400);
            }
            """
        )
    except Exception:  # noqa: BLE001
        pass

    collected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _merge(units: list[dict[str, Any]]) -> None:
        for u in units:
            key = "|".join(
                str(u.get(k)) for k in ("floorplan", "unit_number", "sqft", "rent")
            )
            if key in seen:
                continue
            seen.add(key)
            collected.append(u)

    # Main frame
    _merge(await _extract_units_from_frame(page))

    # Every iframe below it. Wait briefly for iframe content to load first.
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            await frame.wait_for_load_state("domcontentloaded", timeout=4000)
        except Exception:  # noqa: BLE001
            pass
        _merge(await _extract_units_from_frame(frame))

    return collected


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def scrape_one(page: Page, spec: PropertySiteSpec) -> dict[str, Any]:
    """Return {specials, units, source_url, platform, note} for one property."""
    result: dict[str, Any] = {
        "specials": None,
        "units": [],
        "source_url": None,
        "platform": None,
        "note": None,
    }

    if not await _safe_goto(page, spec.home_url):
        result["note"] = f"home page not reachable: {spec.home_url}"
        return result

    result["specials"] = await _extract_specials(page)

    floorplans_url = spec.floorplans_url
    if not floorplans_url:
        floorplans_url = await _find_floorplans_url(page, spec.home_url)

    if floorplans_url:
        print(f"    · trying floorplans page: {floorplans_url}")
        if await _safe_goto(page, floorplans_url):
            # Let lazy-loaded widgets render.
            await asyncio.sleep(2.0)
            result["source_url"] = floorplans_url
        else:
            result["note"] = "floorplans page did not load"
    else:
        # Try extracting on the home page as a last resort.
        result["source_url"] = spec.home_url

    result["platform"] = await _detect_platform(page)
    units = await _extract_units_generic(page)
    result["units"] = units

    if not units:
        try:
            title = await page.title()
            body_len = await page.evaluate("() => document.body.innerText.length")
            result["note"] = (
                f"0 units on property site "
                f"(platform={result['platform']}, title={title!r}, body={body_len})"
            )
        except Exception:  # noqa: BLE001
            result["note"] = "0 units on property site"

    return result
