"""Sample data for testing and demo mode.

Based on publicly available listing data from apartments.com, rentcafe.com,
and property websites as of April 2026. Used when live scraping is unavailable.
"""

from datetime import datetime, timedelta
import random
from models import Unit

TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _make_unit(prop: str, unit: str, fp: str, utype: str, beds: int,
               baths: float, sqft: int, rent: float, url: str,
               avail: str = "", concessions: str = "",
               data_level: str = "unit") -> Unit:
    return Unit(
        property_name=prop,
        unit_number=unit,
        floorplan=fp,
        unit_type=utype,
        beds=beds,
        baths=baths,
        sqft=sqft,
        asking_rent=rent,
        move_in_date=avail,
        concessions=concessions,
        source_url=url,
        scrape_timestamp=TIMESTAMP,
        data_level=data_level,
    )


def generate_sample_data() -> list[Unit]:
    """Generate realistic sample data for all 7 properties."""
    units = []

    # -----------------------------------------------------------------------
    # 1. Davis at the Square (Studios, 1BR, 2BR)
    # -----------------------------------------------------------------------
    prop = "Davis at the Square"
    url = "https://davisatthesquare.com/"

    # Studios
    studios_davis = [
        ("101", "S1", 324, 1070), ("102", "S1", 324, 1085),
        ("201", "S2", 507, 1195), ("202", "S2", 507, 1210),
        ("301", "S1", 324, 1095), ("302", "S2", 507, 1225),
    ]
    for u, fp, sqft, rent in studios_davis:
        units.append(_make_unit(prop, u, fp, "Studios", 0, 1.0, sqft, rent, url,
                                avail="04/15/2026"))

    # 1BR
    ones_davis = [
        ("103", "A1", 631, 1305), ("104", "A1C", 655, 1340),
        ("203", "A2", 762, 1415), ("204", "A2", 762, 1430),
        ("303", "A1", 631, 1320), ("304", "A1C", 655, 1355),
        ("403", "A2", 762, 1445), ("404", "A3", 797, 1490),
        ("105", "A3", 797, 1475), ("205", "A1", 631, 1310),
    ]
    for u, fp, sqft, rent in ones_davis:
        units.append(_make_unit(prop, u, fp, "1BR", 1, 1.0, sqft, rent, url,
                                avail="04/20/2026"))

    # 2BR
    twos_davis = [
        ("106", "B1", 1006, 1815), ("206", "B1", 1006, 1835),
        ("306", "B2", 1055, 1890), ("406", "B2", 1055, 1910),
        ("107", "B1", 1006, 1825), ("207", "B2", 1055, 1875),
    ]
    for u, fp, sqft, rent in twos_davis:
        units.append(_make_unit(prop, u, fp, "2BR", 2, 2.0, sqft, rent, url,
                                avail="05/01/2026"))

    # -----------------------------------------------------------------------
    # 2. Magnolia on the Green (1BR, 2BR)
    # -----------------------------------------------------------------------
    prop = "Magnolia on the Green"
    url = "https://www.magnoliaonthegreen.com/"

    ones_magnolia = [
        ("1101", "A1", 714, 1445), ("1102", "A2", 752, 1485),
        ("1201", "A1", 714, 1460), ("1202", "A2", 752, 1500),
        ("1301", "A3", 825, 1545), ("1302", "A1", 714, 1450),
        ("2101", "A2", 752, 1490), ("2102", "A3", 825, 1560),
    ]
    for u, fp, sqft, rent in ones_magnolia:
        units.append(_make_unit(prop, u, fp, "1BR", 1, 1.0, sqft, rent, url,
                                avail="04/25/2026"))

    twos_magnolia = [
        ("1103", "B1", 1064, 1935), ("1203", "B1", 1064, 1955),
        ("1303", "B2", 1138, 2075), ("2103", "B1", 1064, 1940),
        ("2203", "B2", 1138, 2090), ("1104", "B2", 1138, 2060),
    ]
    for u, fp, sqft, rent in twos_magnolia:
        units.append(_make_unit(prop, u, fp, "2BR", 2, 2.0, sqft, rent, url,
                                avail="05/01/2026"))

    # -----------------------------------------------------------------------
    # 3. The Link at Twin Creeks (1BR, 2BR, 3BR)
    # -----------------------------------------------------------------------
    prop = "The Link at Twin Creeks"
    url = "https://livethelinkapts.com/"

    ones_link = [
        ("A101", "A1", 786, 1437), ("A102", "A2", 825, 1475),
        ("A201", "A1", 786, 1450), ("A202", "A3", 854, 1510),
        ("B101", "A2", 825, 1485), ("B102", "A1", 786, 1440),
        ("B201", "A3", 854, 1520), ("B202", "A4", 889, 1555),
    ]
    for u, fp, sqft, rent in ones_link:
        units.append(_make_unit(prop, u, fp, "1BR", 1, 1.0, sqft, rent, url,
                                avail="04/20/2026"))

    twos_link = [
        ("A103", "B1", 1120, 1895), ("A203", "B2", 1180, 1965),
        ("B103", "B1", 1120, 1910), ("B203", "B3", 1215, 2025),
        ("C103", "B2", 1180, 1975), ("C203", "B1", 1120, 1920),
    ]
    for u, fp, sqft, rent in twos_link:
        units.append(_make_unit(prop, u, fp, "2BR", 2, 2.0, sqft, rent, url,
                                avail="05/01/2026"))

    threes_link = [
        ("A104", "C1", 1350, 2380), ("B104", "C1", 1350, 2410),
        ("C104", "C2", 1416, 2509),
    ]
    for u, fp, sqft, rent in threes_link:
        units.append(_make_unit(prop, u, fp, "3BR", 3, 2.0, sqft, rent, url,
                                avail="05/15/2026"))

    # -----------------------------------------------------------------------
    # 4. The Bridge at McKinney (1BR, 2BR, 3BR)
    # -----------------------------------------------------------------------
    prop = "The Bridge at McKinney"
    url = "https://www.thebridgeatmckinney.com/"
    concession = "Up to 6 weeks free rent"

    ones_bridge = [
        ("1001", "A1", 678, 1085), ("1002", "A2", 742, 1145),
        ("1003", "A3", 815, 1220), ("2001", "A1", 678, 1095),
        ("2002", "A2", 742, 1155), ("2003", "A4", 855, 1260),
        ("3001", "A1", 678, 1100), ("3002", "A5", 890, 1295),
        ("1004", "A3", 815, 1225), ("2004", "A2", 742, 1160),
    ]
    for u, fp, sqft, rent in ones_bridge:
        units.append(_make_unit(prop, u, fp, "1BR", 1, 1.0, sqft, rent, url,
                                avail="04/15/2026", concessions=concession))

    twos_bridge = [
        ("1005", "B1", 1045, 1550), ("1006", "B2", 1120, 1645),
        ("2005", "B1", 1045, 1565), ("2006", "B3", 1185, 1720),
        ("3005", "B2", 1120, 1660), ("3006", "B1", 1045, 1555),
    ]
    for u, fp, sqft, rent in twos_bridge:
        units.append(_make_unit(prop, u, fp, "2BR", 2, 2.0, sqft, rent, url,
                                avail="04/20/2026", concessions=concession))

    threes_bridge = [
        ("1007", "C1", 1425, 2751), ("2007", "C1", 1425, 2785),
    ]
    for u, fp, sqft, rent in threes_bridge:
        units.append(_make_unit(prop, u, fp, "3BR", 3, 2.0, sqft, rent, url,
                                avail="05/01/2026", concessions=concession))

    # -----------------------------------------------------------------------
    # 5. Kinstead (Studios, 1BR, 2BR, 3BR)
    # -----------------------------------------------------------------------
    prop = "Kinstead"
    url = "https://www.kinsteadmckinney.com/"

    studios_kinstead = [
        ("S101", "S1", 554, 1350), ("S102", "S1", 554, 1365),
        ("S201", "S1", 554, 1375),
    ]
    for u, fp, sqft, rent in studios_kinstead:
        units.append(_make_unit(prop, u, fp, "Studios", 0, 1.0, sqft, rent, url,
                                avail="04/15/2026"))

    ones_kinstead = [
        ("A101", "A1", 648, 1395), ("A102", "A2", 698, 1435),
        ("A201", "A3", 735, 1470), ("A202", "A4", 768, 1505),
        ("A301", "A5", 804, 1545), ("A302", "A6", 845, 1580),
        ("B101", "A1", 648, 1400), ("B102", "A2", 698, 1440),
        ("B201", "A4", 768, 1510), ("B202", "A6", 845, 1590),
    ]
    for u, fp, sqft, rent in ones_kinstead:
        units.append(_make_unit(prop, u, fp, "1BR", 1, 1.0, sqft, rent, url,
                                avail="04/20/2026"))

    twos_kinstead = [
        ("A103", "B1", 1040, 1815), ("A203", "B2", 1095, 1870),
        ("A303", "B3", 1155, 1935), ("B103", "B1", 1040, 1825),
        ("B203", "B4", 1200, 1990), ("C103", "B2", 1095, 1880),
        ("C203", "B5", 1245, 2045),
    ]
    for u, fp, sqft, rent in twos_kinstead:
        units.append(_make_unit(prop, u, fp, "2BR", 2, 2.0, sqft, rent, url,
                                avail="05/01/2026"))

    threes_kinstead = [
        ("A104", "C1", 1420, 2385), ("B104", "C2", 1543, 2577),
    ]
    for u, fp, sqft, rent in threes_kinstead:
        units.append(_make_unit(prop, u, fp, "3BR", 3, 2.0, sqft, rent, url,
                                avail="05/15/2026"))

    # -----------------------------------------------------------------------
    # 6. Collin Square (Studios, 1BR, 2BR, 3BR)
    # -----------------------------------------------------------------------
    prop = "Collin Square"
    url = "https://www.collinsquareapts.com/"

    studios_collin = [
        ("110", "S1", 574, 1370), ("210", "S1", 574, 1385),
        ("310", "S2", 610, 1420),
    ]
    for u, fp, sqft, rent in studios_collin:
        units.append(_make_unit(prop, u, fp, "Studios", 0, 1.0, sqft, rent, url,
                                avail="04/20/2026"))

    ones_collin = [
        ("111", "A1", 685, 1328), ("112", "A2", 735, 1395),
        ("211", "A1", 685, 1340), ("212", "A3", 780, 1445),
        ("311", "A2", 735, 1405), ("312", "A4", 825, 1490),
        ("411", "A1", 685, 1350), ("412", "A3", 780, 1455),
    ]
    for u, fp, sqft, rent in ones_collin:
        units.append(_make_unit(prop, u, fp, "1BR", 1, 1.0, sqft, rent, url,
                                avail="04/25/2026"))

    twos_collin = [
        ("113", "B1", 1035, 1774), ("213", "B2", 1095, 1845),
        ("313", "B1", 1035, 1790), ("413", "B3", 1150, 1920),
        ("114", "B2", 1095, 1855), ("214", "B3", 1150, 1935),
    ]
    for u, fp, sqft, rent in twos_collin:
        units.append(_make_unit(prop, u, fp, "2BR", 2, 2.0, sqft, rent, url,
                                avail="05/01/2026"))

    threes_collin = [
        ("115", "C1", 1380, 2279), ("215", "C1", 1380, 2310),
        ("315", "C2", 1505, 2684),
    ]
    for u, fp, sqft, rent in threes_collin:
        units.append(_make_unit(prop, u, fp, "3BR", 3, 2.0, sqft, rent, url,
                                avail="05/15/2026"))

    # -----------------------------------------------------------------------
    # 7. McKinney Terrace (1BR, 2BR, 3BR)
    # -----------------------------------------------------------------------
    prop = "McKinney Terrace"
    url = "https://mckinneyterrace.com/"

    ones_mkt = [
        ("1A", "A1", 645, 1285), ("2A", "A2", 710, 1345),
        ("3A", "A1", 645, 1295), ("4A", "A3", 760, 1405),
        ("5A", "A2", 710, 1355), ("6A", "A4", 805, 1450),
        ("7A", "A1", 645, 1300), ("8A", "A3", 760, 1415),
    ]
    for u, fp, sqft, rent in ones_mkt:
        units.append(_make_unit(prop, u, fp, "1BR", 1, 1.0, sqft, rent, url,
                                avail="04/20/2026"))

    twos_mkt = [
        ("1B", "B1", 1020, 1658), ("2B", "B2", 1085, 1735),
        ("3B", "B1", 1020, 1670), ("4B", "B3", 1145, 1810),
        ("5B", "B2", 1085, 1745), ("6B", "B1", 1020, 1665),
    ]
    for u, fp, sqft, rent in twos_mkt:
        units.append(_make_unit(prop, u, fp, "2BR", 2, 2.0, sqft, rent, url,
                                avail="05/01/2026"))

    threes_mkt = [
        ("1C", "C1", 1310, 1999), ("2C", "C1", 1310, 2025),
        ("3C", "C2", 1415, 2472),
    ]
    for u, fp, sqft, rent in threes_mkt:
        units.append(_make_unit(prop, u, fp, "3BR", 3, 2.0, sqft, rent, url,
                                avail="05/15/2026"))

    return units
