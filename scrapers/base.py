"""Base scraper with shared utilities."""

import logging
import re
import json
import time
from typing import Optional
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from config import UNIT_TYPE_MAP
from models import Unit

logger = logging.getLogger(__name__)


def normalize_unit_type(raw: str, beds: Optional[int] = None) -> str:
    """Map raw unit type string to standard type."""
    if beds is not None:
        if beds == 0:
            return "Studios"
        elif beds == 1:
            return "1BR"
        elif beds == 2:
            return "2BR"
        elif beds >= 3:
            return "3BR"
    key = raw.strip().lower()
    return UNIT_TYPE_MAP.get(key, key)


def parse_rent(raw: str) -> tuple[Optional[float], Optional[str]]:
    """Parse rent from raw string. Returns (exact_rent, rent_range)."""
    if not raw:
        return None, None
    cleaned = raw.replace("$", "").replace(",", "").strip()
    # Check for range (e.g. "1,200 - 1,500")
    range_match = re.search(r'([\d,]+(?:\.\d+)?)\s*[-–]\s*\$?([\d,]+(?:\.\d+)?)', cleaned)
    if range_match:
        low = float(range_match.group(1).replace(",", ""))
        high = float(range_match.group(2).replace(",", ""))
        return low, f"${low:,.0f} - ${high:,.0f}"
    # Single value
    val_match = re.search(r'([\d,]+(?:\.\d+)?)', cleaned)
    if val_match:
        return float(val_match.group(1).replace(",", "")), None
    return None, None


def parse_sqft(raw: str) -> int:
    """Parse square footage from string."""
    if not raw:
        return 0
    cleaned = raw.replace(",", "").replace("sq ft", "").replace("SF", "").replace("sqft", "").strip()
    match = re.search(r'(\d+)', cleaned)
    return int(match.group(1)) if match else 0


def parse_beds(raw: str) -> int:
    """Parse bed count from string."""
    if not raw:
        return 0
    lower = raw.strip().lower()
    if "studio" in lower:
        return 0
    match = re.search(r'(\d+)', lower)
    return int(match.group(1)) if match else 0


def parse_baths(raw: str) -> float:
    """Parse bath count from string."""
    if not raw:
        return 1.0
    match = re.search(r'(\d+\.?\d*)', raw)
    return float(match.group(1)) if match else 1.0


def fetch_with_retry(url: str, max_retries: int = 3, timeout: int = 30,
                     headers: Optional[dict] = None) -> Optional[httpx.Response]:
    """Fetch URL with retry logic."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        default_headers.update(headers)

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
                resp = client.get(url, headers=default_headers)
                resp.raise_for_status()
                return resp
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


def fetch_json(url: str, max_retries: int = 3, timeout: int = 30,
               headers: Optional[dict] = None) -> Optional[dict]:
    """Fetch JSON endpoint with retry logic."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        default_headers.update(headers)

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
                resp = client.get(url, headers=default_headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f"JSON attempt {attempt + 1} failed for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


def post_json(url: str, data: dict, max_retries: int = 3, timeout: int = 30,
              headers: Optional[dict] = None) -> Optional[dict]:
    """POST JSON endpoint with retry logic."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if headers:
        default_headers.update(headers)

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
                resp = client.post(url, json=data, headers=default_headers)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f"POST attempt {attempt + 1} failed for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None
