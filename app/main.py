from __future__ import annotations

import csv
import io
import json
import math
import os
import random
import subprocess
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "app" / "static"
DATA_DIR = ROOT / "data"
STATE_FILE = DATA_DIR / "state.json"
load_dotenv(ROOT / ".env")

app = FastAPI(
    title="EmberWatch Intelligence API",
    version="1.0.0",
    description="Explainable industrial fire and persistent thermal source intelligence.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def demo_raw_hotspots() -> list[dict[str, Any]]:
    """Deterministic fixtures make the demo reliable without an API key or network."""
    now = utc_now()
    rows = [
        ("jam-01", 22.342, 69.858, 371.2, 42.8, "88", 0.6, 1),
        ("jam-02", 22.329, 69.836, 358.9, 31.6, "82", 2.2, 2),
        ("jam-03", 22.350, 69.872, 346.7, 16.7, "76", 7.5, 3),
        ("mum-01", 18.986, 73.036, 364.3, 55.1, "92", 1.4, 4),
        ("mum-02", 19.012, 73.008, 340.5, 12.3, "71", 8.2, 5),
        ("viz-01", 17.677, 83.232, 353.8, 28.4, "86", 3.1, 6),
        ("viz-02", 17.699, 83.204, 327.4, 7.8, "63", 15.0, 7),
        ("par-01", 20.303, 86.624, 366.5, 33.7, "89", 2.6, 8),
        ("pan-01", 29.402, 76.953, 351.9, 24.2, "81", 5.7, 9),
        ("bok-01", 23.684, 86.136, 337.0, 18.0, "74", 10.3, 10),
        ("kak-01", 16.976, 82.264, 318.4, 4.7, "54", 18.8, 11),
        ("forest-01", 22.572, 78.944, 309.8, 3.4, "48", 12.1, 12),
        ("forest-02", 21.924, 84.503, 312.1, 5.1, "52", 20.4, 13),
        ("chen-01", 13.177, 80.278, 360.1, 21.9, "84", 4.8, 14),
    ]
    result = []
    for key, lat, lon, brightness, frp, confidence, hours_ago, seed in rows:
        result.append({
            "id": f"FIRMS-DEMO-{key.upper()}",
            "latitude": lat,
            "longitude": lon,
            "brightness": brightness,
            "bright_t31": brightness - 21.4,
            "frp": frp,
            "confidence": confidence,
            "scan": round(0.45 + seed / 20, 2),
            "track": round(0.42 + seed / 22, 2),
            "acq_date": (now - timedelta(hours=hours_ago)).date().isoformat(),
            "acq_time": (now - timedelta(hours=hours_ago)).strftime("%H%M"),
            "acquired_at": iso(now - timedelta(hours=hours_ago)),
            "satellite": "N20" if seed % 2 else "NPP",
            "instrument": "VIIRS",
            "daynight": "D" if seed % 3 else "N",
            "source": "NASA FIRMS (demo fixture)",
            "source_type": "FIRMS",
        })
    return result


def nearest_site(lat: float, lon: float, sites: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any] | None, float]:
    catalogue = sites or DEMO_SITES
    distances = [(site, distance_km(lat, lon, site["lat"], site["lon"])) for site in catalogue]
    return min(distances, key=lambda x: x[1]) if distances else (None, 999.0)


def parse_confidence(raw: Any) -> float:
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw or "0").strip().replace("%", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def enrich_hotspot(row: dict[str, Any], all_rows: list[dict[str, Any]], sites: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    item = dict(row)
    item["latitude"] = float(item.get("latitude", item.get("lat", 0)))
    item["longitude"] = float(item.get("longitude", item.get("lon", 0)))
    item["frp"] = float(item.get("frp", 0) or 0)
    item["brightness"] = float(item.get("brightness", 0) or 0)
    item["confidence_value"] = parse_confidence(item.get("confidence"))
    site, dist = nearest_site(item["latitude"], item["longitude"], sites)
    item["nearest_site"] = site["name"] if site else "Unmapped area"
    item["nearest_site_id"] = site["id"] if site else None
    item["distance_to_site_km"] = round(dist, 1)

    # A transparent, reproducible scoring model is useful in a judging demo.
    brightness_score = max(0.0, min(1.0, (item["brightness"] - 300) / 90))
    frp_score = max(0.0, min(1.0, item["frp"] / 55))
    confidence_score = item["confidence_value"] / 100
    industrial_proximity = max(0.0, min(1.0, 1 - dist / 35))
    nearby_count = sum(
        1 for other in all_rows
        if distance_km(item["latitude"], item["longitude"], float(other.get("latitude", 0)), float(other.get("longitude", 0))) < 8
    )
    recency_hours = 0.0
    acquired = item.get("acquired_at")
    if acquired:
        try:
            recency_hours = max(0.0, (utc_now() - datetime.fromisoformat(acquired.replace("Z", "+00:00"))).total_seconds() / 3600)
        except ValueError:
            pass
    recency_score = max(0.0, min(1.0, 1 - recency_hours / 48))
    persistence_score = max(0.0, min(1.0, (nearby_count - 1) / 3))
    risk = round(100 * (
        0.27 * brightness_score
        + 0.27 * frp_score
        + 0.18 * confidence_score
        + 0.18 * industrial_proximity
        + 0.06 * persistence_score
        + 0.04 * recency_score
    ))

    if industrial_proximity > 0.52 and item["frp"] >= 25 and item["confidence_value"] >= 75:
        label = "INDUSTRIAL FIRE"
        category = "industrial_fire"
    elif industrial_proximity > 0.45 and nearby_count >= 2 and item["frp"] >= 12:
        label = "PERSISTENT THERMAL"
        category = "persistent_thermal"
    elif item["frp"] >= 28 and item["confidence_value"] >= 80:
        label = "HIGH-ENERGY SOURCE"
        category = "high_energy"
    else:
        label = "UNCLASSIFIED HOTSPOT"
        category = "unclassified"
    severity = "CRITICAL" if risk >= 78 else "HIGH" if risk >= 60 else "MEDIUM" if risk >= 38 else "LOW"
    if label == "INDUSTRIAL FIRE" and risk < 78:
        severity = "HIGH"
    item.update({
        "label": label,
        "category": category,
        "severity": severity,
        "risk_score": risk,
        "confidence": round(min(99.0, max(item["confidence_value"], 52 + risk * 0.42)), 1),
        "persistence_count": nearby_count,
        "risk_factors": [
            {"name": "Thermal intensity", "value": round(100 * frp_score), "detail": f"{item['frp']:.1f} MW FRP"},
            {"name": "Industrial proximity", "value": round(100 * industrial_proximity), "detail": f"{dist:.1f} km from mapped asset"},
            {"name": "Sensor confidence", "value": round(100 * confidence_score), "detail": f"FIRMS confidence {item['confidence_value']:.0f}%"},
            {"name": "Persistence signal", "value": round(100 * persistence_score), "detail": f"{nearby_count} observations in cluster"},
        ],
        "reasoning": [
            f"{dist:.1f} km from {site['name']}" if site and dist < 35 else "Outside mapped industrial perimeter",
            f"Thermal radiative power is {item['frp']:.1f} MW",
            f"{nearby_count} FIRMS observation(s) within an 8 km spatio-temporal cluster",
            f"VIIRS {item.get('satellite', 'NRT')} confidence is {item['confidence_value']:.0f}%",
        ],
        "status": "NEW" if risk >= 60 else "MONITORING",
    })
    return item


def build_alerts(hotspots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts = []
    for item in sorted(hotspots, key=lambda x: x["risk_score"], reverse=True):
        if item["risk_score"] < 45:
            continue
        alerts.append({
            "id": f"ALERT-{item['id']}",
            "hotspot_id": item["id"],
            "severity": item["severity"],
            "title": item["label"].title(),
            "location": item["nearest_site"],
            "timestamp": item.get("acquired_at"),
            "risk_score": item["risk_score"],
            "status": item["status"],
            "summary": f"{item['frp']:.1f} MW thermal anomaly detected {item['distance_to_site_km']:.1f} km from mapped industrial assets.",
        })
    return alerts


def initial_state() -> dict[str, Any]:
    raw = demo_raw_hotspots()
    enriched = [enrich_hotspot(row, raw, DEMO_SITES) for row in raw]
    return {
        "hotspots": enriched,
        "sites": DEMO_SITES,
        "alerts": build_alerts(enriched),
        "mode": "DEMO",
        "last_updated": iso(utc_now()),
        "source_status": {"firms": "demo fixture", "osm": "catalogue seed", "satellite": "Esri World Imagery tiles"},
        "refresh_message": "Demo intelligence loaded. Add NASA_FIRMS_MAP_KEY to pull fresh FIRMS observations.",
    }


def read_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    state = initial_state()
    write_state(state)
    return state


def write_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_firms() -> tuple[list[dict[str, Any]] | None, str]:
    key = os.getenv("NASA_FIRMS_MAP_KEY", "").strip()
    if not key:
        return None, "NASA_FIRMS_MAP_KEY is not configured; demo fixtures retained."
    # India bounding box; the same adapter can be pointed at a region or a 24h endpoint.
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{urllib.parse.quote(key)}/VIIRS_SNPP_NRT/68,6,98,37/2"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "EmberWatch/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=18) as response:
                payload = response.read().decode("utf-8")
        except Exception:
            # macOS can prefer an IPv6 route for urllib while curl correctly
            # falls back to IPv4. Keep the live adapter resilient on laptops.
            result = subprocess.run(
                ["curl", "-fsSL", "--connect-timeout", "10", "--max-time", "45", "--retry", "1", url],
                capture_output=True, text=True, timeout=55, check=True,
            )
            payload = result.stdout
        rows = []
        for raw in csv.DictReader(io.StringIO(payload)):
            lat = float(raw.get("latitude", 0))
            lon = float(raw.get("longitude", 0))
            acq_date = raw.get("acq_date", "")
            acq_time = raw.get("acq_time", "0000").zfill(4)
            acquired = None
            try:
                acquired = iso(datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M").replace(tzinfo=timezone.utc))
            except ValueError:
                acquired = iso(utc_now())
            rows.append({
                "id": f"FIRMS-{acq_date}-{acq_time}-{lat:.4f}-{lon:.4f}",
                "latitude": lat,
                "longitude": lon,
                "brightness": float(raw.get("bright_ti4") or raw.get("brightness") or 0),
                "bright_t31": float(raw.get("bright_ti5") or raw.get("bright_t31") or 0),
                "frp": float(raw.get("frp") or 0),
                "confidence": raw.get("confidence", "0"),
                "scan": raw.get("scan", ""),
                "track": raw.get("track", ""),
                "acq_date": acq_date,
                "acq_time": acq_time,
                "acquired_at": acquired,
                "satellite": raw.get("satellite", "SNPP"),
                "instrument": raw.get("instrument", "VIIRS"),
                "daynight": raw.get("daynight", ""),
                "source": "NASA FIRMS",
                "source_type": "FIRMS",
            })
        if not rows:
            return None, "NASA FIRMS returned no rows for the selected region."
        return rows, f"Loaded {len(rows)} observations from NASA FIRMS."
    except Exception as exc:  # network/API errors should never break the demo
        return None, f"FIRMS refresh unavailable ({type(exc).__name__}); demo fixtures retained."


def fetch_osm_sites() -> tuple[list[dict[str, Any]] | None, str]:
    if os.getenv("ENABLE_LIVE_OSM", "false").lower() != "true":
        return None, "OSM live enrichment disabled; curated industrial catalogue retained."
    query = """[out:json][timeout:20];area[\"ISO3166-1\"=IN]->.india;(nwr[industrial~\"refinery|chemical|oil|steel\"](area.india);nwr[power=plant](area.india););out center tags;"""
    url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "EmberWatch/1.0"})
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
        sites = []
        for node in payload.get("elements", [])[:500]:
            tags = node.get("tags", {})
            center = node.get("center", node)
            if not center.get("lat") or not center.get("lon"):
                continue
            sites.append({
                "id": f"osm-{node.get('type')}-{node.get('id')}",
                "name": tags.get("name", "Unnamed industrial asset"),
                "operator": tags.get("operator", "OSM contributor"),
                "type": tags.get("industrial", tags.get("power", "Industrial asset")),
                "lat": center["lat"], "lon": center["lon"], "risk_zone": "UNASSESSED", "assets": 1,
            })
        return (sites or None), f"Loaded {len(sites)} industrial assets from OpenStreetMap."
    except Exception as exc:
        return None, f"OSM enrichment unavailable ({type(exc).__name__}); curated catalogue retained."


def refresh_state() -> dict[str, Any]:
    firms_rows, firms_message = fetch_firms()
    osm_sites, osm_message = fetch_osm_sites()
    state = read_state()
    selected_sites = osm_sites or DEMO_SITES
    if firms_rows:
        state["hotspots"] = [enrich_hotspot(row, firms_rows, selected_sites) for row in firms_rows]
        state["mode"] = "LIVE"
    else:
        demo_rows = demo_raw_hotspots()
        state["hotspots"] = [enrich_hotspot(row, demo_rows, selected_sites) for row in demo_rows]
        state["mode"] = "DEMO"
    state["sites"] = selected_sites
    state["alerts"] = build_alerts(state["hotspots"])
    state["last_updated"] = iso(utc_now())
    state["source_status"] = {"firms": "live" if firms_rows else "demo fixture", "osm": "live" if osm_sites else "catalogue seed", "satellite": "Esri World Imagery tiles"}
    state["refresh_message"] = f"{firms_message} {osm_message}"
    write_state(state)
    return state


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "emberwatch-api", "time": iso(utc_now())}


@app.get("/health", include_in_schema=False)
def health_alias() -> dict[str, Any]:
    return health()


@app.get("/api/overview")
def overview() -> dict[str, Any]:
    state = read_state()
    hotspots = state["hotspots"]
    alerts = state["alerts"]
    counts = Counter(item["severity"] for item in hotspots)
    categories = Counter(item["category"] for item in hotspots)
    return {
        "mode": state["mode"], "last_updated": state["last_updated"], "refresh_message": state["refresh_message"],
        "metrics": {
            "active_alerts": len(alerts), "critical_zones": counts.get("CRITICAL", 0), "hotspots_24h": len(hotspots),
            "industrial_fires": categories.get("industrial_fire", 0), "persistent_sources": categories.get("persistent_thermal", 0),
            "mapped_assets": len(state["sites"]), "mean_confidence": round(sum(x["confidence"] for x in hotspots) / max(1, len(hotspots))),
        },
        "severity_counts": dict(counts), "category_counts": dict(categories), "source_status": state["source_status"],
    }


@app.get("/api/hotspots")
def hotspots(
    severity: str | None = Query(default=None),
    category: str | None = Query(default=None),
    min_risk: int = Query(default=0, ge=0, le=100),
) -> list[dict[str, Any]]:
    items = read_state()["hotspots"]
    if severity:
        items = [x for x in items if x["severity"].lower() == severity.lower()]
    if category:
        items = [x for x in items if x["category"].lower() == category.lower()]
    return sorted([x for x in items if x["risk_score"] >= min_risk], key=lambda x: x["risk_score"], reverse=True)


@app.get("/api/hotspots/{hotspot_id}")
def hotspot(hotspot_id: str) -> dict[str, Any]:
    for item in read_state()["hotspots"]:
        if item["id"] == hotspot_id:
            return item
    raise HTTPException(status_code=404, detail="Hotspot not found")


@app.get("/api/industrial-sites")
def industrial_sites() -> list[dict[str, Any]]:
    return read_state()["sites"]


@app.get("/api/alerts")
def alerts() -> list[dict[str, Any]]:
    return read_state()["alerts"]


@app.get("/api/timeline")
def timeline() -> list[dict[str, Any]]:
    items = read_state()["hotspots"]
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0})
    for item in items:
        try:
            stamp = datetime.fromisoformat(item["acquired_at"].replace("Z", "+00:00"))
            key = stamp.strftime("%H:00")
        except (KeyError, ValueError):
            key = "now"
        buckets[key][item["severity"].lower()] += 1
    return [{"time": key, **value, "total": sum(value.values())} for key, value in sorted(buckets.items())]


@app.post("/api/refresh")
def refresh() -> dict[str, Any]:
    state = refresh_state()
    return {"ok": True, "mode": state["mode"], "last_updated": state["last_updated"], "message": state["refresh_message"]}


@app.post("/api/demo/reset")
def demo_reset() -> dict[str, Any]:
    state = initial_state()
    write_state(state)
    return {"ok": True, "mode": state["mode"], "message": state["refresh_message"]}


@app.get("/api/report/{hotspot_id}")
def report(hotspot_id: str) -> dict[str, Any]:
    item = hotspot(hotspot_id)
    generated = iso(utc_now())
    markdown = f"""# EmberWatch Incident Brief\n\n**Alert:** {item['label'].title()}  \n**Generated:** {generated}\n\n## Location\n- Coordinates: {item['latitude']:.4f}, {item['longitude']:.4f}\n- Nearest mapped asset: {item['nearest_site']} ({item['distance_to_site_km']:.1f} km)\n- Severity: **{item['severity']}**\n- Risk score: **{item['risk_score']}/100**\n\n## Sensor evidence\n- NASA FIRMS source: {item.get('source', 'FIRMS')}\n- Thermal radiative power: {item['frp']:.1f} MW\n- Brightness temperature: {item['brightness']:.1f} K\n- Sensor confidence: {item['confidence_value']:.0f}%\n- Cluster observations: {item['persistence_count']}\n\n## Explainable AI assessment\n""" + "".join(f"- {reason}\n" for reason in item["reasoning"]) + "\n## Recommended action\nDispatch verification to the mapped industrial zone, cross-check local CCTV/SCADA telemetry, and retain this observation for temporal persistence analysis.\n"
    return {"hotspot": item, "generated_at": generated, "markdown": markdown}


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
