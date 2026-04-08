"""Data models for market survey units."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Unit:
    property_name: str
    unit_number: str
    floorplan: str
    unit_type: str  # Studios, 1BR, 2BR, 3BR
    beds: int
    baths: float
    sqft: int
    asking_rent: Optional[float] = None
    rent_range: Optional[str] = None
    normalized_rent: Optional[float] = None
    psf: Optional[float] = None
    move_in_date: Optional[str] = None
    lease_term: Optional[str] = None
    concessions: Optional[str] = None
    concession_notes: Optional[str] = None
    source_url: str = ""
    scrape_timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    data_level: str = "unit"  # "unit" or "floorplan"

    def __post_init__(self):
        # Calculate normalized rent
        if self.asking_rent is not None:
            self.normalized_rent = self.asking_rent
        elif self.rent_range:
            try:
                low = float(self.rent_range.replace("$", "").replace(",", "").split("-")[0].strip())
                self.normalized_rent = low
            except (ValueError, IndexError):
                pass
        # Calculate PSF
        if self.normalized_rent and self.sqft and self.sqft > 0:
            self.psf = round(self.normalized_rent / self.sqft, 2)

    def to_dict(self):
        return {
            "Property Name": self.property_name,
            "Unit": self.unit_number,
            "Floorplan": self.floorplan,
            "Unit Type": self.unit_type,
            "Beds": self.beds,
            "Baths": self.baths,
            "Sq Ft": self.sqft,
            "Asking Rent": self.normalized_rent,
            "Rent Range": self.rent_range,
            "PSF": self.psf,
            "Move-In Date": self.move_in_date,
            "Lease Term": self.lease_term,
            "Concessions": self.concessions,
            "Concession Notes": self.concession_notes,
            "Source URL": self.source_url,
            "Scrape Timestamp": self.scrape_timestamp,
            "Data Level": self.data_level,
        }
