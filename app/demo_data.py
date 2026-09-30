"""Single source of truth for the EmberWatch judge scenario.

The observations are deliberately explicit about classification. A thermal
observation near an industrial asset is not automatically a fire. The demo
scenario contains suspected fires, persistent industrial heat, and
non-industrial observations so the UI can show the distinction honestly.
"""

from typing import Any


DEMO_SITES: list[dict[str, Any]] = [
    {"id": "site-jamnagar", "name": "Jamnagar Refining Complex", "operator": "Reliance Industries", "type": "Refinery", "lat": 22.337, "lon": 69.845, "risk_zone": "CRITICAL", "assets": 18},
    {"id": "site-mumbai", "name": "Mumbai Petrochemical Belt", "operator": "MRPL / HPCL corridor", "type": "Petrochemical", "lat": 19.000, "lon": 73.022, "risk_zone": "HIGH", "assets": 26},
    {"id": "site-vizag", "name": "Visakhapatnam Industrial Port", "operator": "HPCL / VPA corridor", "type": "Port & Refinery", "lat": 17.686, "lon": 83.218, "risk_zone": "HIGH", "assets": 14},
    {"id": "site-paradip", "name": "Paradip Industrial Cluster", "operator": "IOCL / PPL corridor", "type": "Refinery & Fertilizer", "lat": 20.316, "lon": 86.611, "risk_zone": "HIGH", "assets": 11},
    {"id": "site-panipat", "name": "Panipat Refinery Zone", "operator": "Indian Oil Corporation", "type": "Refinery", "lat": 29.389, "lon": 76.969, "risk_zone": "HIGH", "assets": 12},
    {"id": "site-bokaro", "name": "Bokaro Steel Works", "operator": "SAIL", "type": "Steel Plant", "lat": 23.669, "lon": 86.151, "risk_zone": "MEDIUM", "assets": 9},
    {"id": "site-kakinada", "name": "Kakinada Energy Hub", "operator": "ONGC / port corridor", "type": "Energy", "lat": 16.989, "lon": 82.247, "risk_zone": "MEDIUM", "assets": 8},
    {"id": "site-chennai", "name": "Manali Industrial Estate", "operator": "CPCL corridor", "type": "Petrochemical", "lat": 13.164, "lon": 80.265, "risk_zone": "HIGH", "assets": 17},
]


# key, latitude, longitude, brightness K, FRP MW, sensor confidence,
# hours ago, seed, classification.
DEMO_OBSERVATIONS: list[tuple[str, float, float, float, float, str, float, int, str]] = [
    ("jam-01", 22.342, 69.858, 371.2, 42.8, "88", 0.6, 1, "suspected_industrial_fire"),
    ("jam-02", 22.329, 69.836, 358.9, 31.6, "82", 2.2, 2, "persistent_thermal"),
    ("jam-03", 22.350, 69.872, 346.7, 16.7, "76", 7.5, 3, "persistent_thermal"),
    ("mum-01", 18.986, 73.036, 364.3, 55.1, "92", 1.4, 4, "suspected_industrial_fire"),
    ("mum-02", 19.012, 73.008, 340.5, 12.3, "71", 8.2, 5, "persistent_thermal"),
    ("viz-01", 17.677, 83.232, 353.8, 28.4, "86", 3.1, 6, "persistent_thermal"),
    ("viz-02", 17.699, 83.204, 327.4, 7.8, "63", 15.0, 7, "persistent_thermal"),
    ("par-01", 20.303, 86.624, 366.5, 33.7, "89", 2.6, 8, "persistent_thermal"),
    ("pan-01", 29.402, 76.953, 351.9, 24.2, "81", 5.7, 9, "persistent_thermal"),
    ("bok-01", 23.684, 86.136, 337.0, 18.0, "74", 10.3, 10, "persistent_thermal"),
    ("kak-01", 16.976, 82.264, 318.4, 4.7, "54", 18.8, 11, "industrial_thermal"),
    ("forest-01", 22.572, 78.944, 309.8, 3.4, "48", 12.1, 12, "non_industrial_thermal"),
    ("forest-02", 21.924, 84.503, 312.1, 5.1, "52", 20.4, 13, "non_industrial_thermal"),
    ("chen-01", 13.177, 80.278, 360.1, 21.9, "84", 4.8, 14, "persistent_thermal"),
]
