"""DFW Market Survey — CLI entry point.

Usage:
    python main.py                  # Run with sample data, generate Excel
    python main.py --live           # Scrape live data, then generate Excel
    python main.py --dashboard      # Launch Streamlit dashboard
    python main.py --live --dashboard  # Scrape live, then launch dashboard
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PROPERTIES, UNIT_TYPES
from models import Unit
from excel_export import save_workbook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "output"


def load_units(live: bool = False) -> list[Unit]:
    """Load units from live scraping or sample data."""
    if live:
        logger.info("Starting LIVE scraping of all 7 properties...")
        try:
            from scrapers.all_properties import run_all_scrapers
            units = run_all_scrapers()
            if units:
                logger.info(f"Live scraping complete: {len(units)} units captured")
                return units
            else:
                logger.warning("Live scraping returned 0 units, falling back to sample data")
        except Exception as e:
            logger.error(f"Live scraping failed: {e}")
            logger.info("Falling back to sample data")

    from scrapers.sample_data import generate_sample_data
    units = generate_sample_data()
    logger.info(f"Sample data loaded: {len(units)} units")
    return units


def units_to_dataframe(units: list[Unit]) -> pd.DataFrame:
    """Convert list of Unit objects to a DataFrame."""
    records = [u.to_dict() for u in units]
    return pd.DataFrame(records)


def validate_data(df: pd.DataFrame) -> bool:
    """Validate the scraped data meets requirements."""
    issues = []

    # Check all 7 properties present
    expected = {p.name for p in PROPERTIES}
    actual = set(df["Property Name"].unique())
    missing = expected - actual
    if missing:
        issues.append(f"Missing properties: {missing}")

    # Check McKinney Terrace specifically
    if "McKinney Terrace" not in actual:
        issues.append("McKinney Terrace NOT found in data")

    # Check unit type distribution
    for ut in UNIT_TYPES:
        count = len(df[df["Unit Type"] == ut])
        logger.info(f"  {ut}: {count} units")

    # Check for missing rent data
    no_rent = df[df["Asking Rent"].isna() | (df["Asking Rent"] == 0)]
    if len(no_rent) > 0:
        issues.append(f"{len(no_rent)} units have no rent data")

    # Check for missing sqft data
    no_sqft = df[df["Sq Ft"].isna() | (df["Sq Ft"] == 0)]
    if len(no_sqft) > 0:
        issues.append(f"{len(no_sqft)} units have no sq ft data")

    if issues:
        for issue in issues:
            logger.warning(f"VALIDATION: {issue}")
        return False

    logger.info("VALIDATION: All checks passed")
    return True


def print_summary(df: pd.DataFrame):
    """Print a summary of the data to console."""
    print("\n" + "=" * 70)
    print("DFW MARKET SURVEY SUMMARY")
    print("=" * 70)
    print(f"Scrape Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Units: {len(df)}")
    print(f"Properties:  {df['Property Name'].nunique()}")
    print()

    # Per-property summary
    print(f"{'Property':<30} {'Units':>6} {'Avg Rent':>10} {'Avg PSF':>10} {'Avg SqFt':>10}")
    print("-" * 70)
    for prop in sorted(df["Property Name"].unique()):
        pdf = df[df["Property Name"] == prop]
        avg_rent = pdf["Asking Rent"].mean()
        avg_psf = pdf["PSF"].mean()
        avg_sqft = pdf["Sq Ft"].mean()
        print(f"{prop:<30} {len(pdf):>6} ${avg_rent:>9,.0f} ${avg_psf:>9.2f} {avg_sqft:>10,.0f}")

    print()
    print(f"{'Unit Type':<15} {'Count':>8} {'Avg Rent':>12} {'Avg PSF':>10}")
    print("-" * 50)
    for ut in UNIT_TYPES:
        utdf = df[df["Unit Type"] == ut]
        if len(utdf) > 0:
            print(f"{ut:<15} {len(utdf):>8} ${utdf['Asking Rent'].mean():>11,.0f} ${utdf['PSF'].mean():>9.2f}")

    # Concessions
    conc_df = df[df["Concessions"].notna() & (df["Concessions"] != "")]
    if len(conc_df) > 0:
        print("\nACTIVE CONCESSIONS:")
        for prop in conc_df["Property Name"].unique():
            conc = conc_df[conc_df["Property Name"] == prop]["Concessions"].iloc[0]
            print(f"  {prop}: {conc}")

    # Data level warnings
    fp_only = df[df["Data Level"] == "floorplan"]
    if len(fp_only) > 0:
        print(f"\nNOTE: {len(fp_only)} entries are FLOOR PLAN LEVEL ONLY (no unit-level data)")
        for prop in fp_only["Property Name"].unique():
            print(f"  - {prop}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="DFW Market Survey Scraper & Dashboard")
    parser.add_argument("--live", action="store_true", help="Scrape live data (requires Playwright)")
    parser.add_argument("--dashboard", action="store_true", help="Launch Streamlit dashboard")
    parser.add_argument("--output", type=str, default=None, help="Output Excel file path")
    args = parser.parse_args()

    if args.dashboard:
        os.system(f"{sys.executable} -m streamlit run {Path(__file__).parent / 'app.py'}")
        return

    # Load data
    units = load_units(live=args.live)
    df = units_to_dataframe(units)

    # Validate
    validate_data(df)

    # Print summary
    print_summary(df)

    # Generate Excel
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = args.output or str(
        OUTPUT_DIR / f"DFW_Market_Survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
    save_workbook(df, output_path)
    logger.info(f"Excel workbook saved to: {output_path}")
    print(f"\nExcel file saved: {output_path}")


if __name__ == "__main__":
    main()
