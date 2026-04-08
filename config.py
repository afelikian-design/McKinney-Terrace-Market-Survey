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
