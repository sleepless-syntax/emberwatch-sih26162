# EmberWatch — SIH26162

**AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data**

EmberWatch is a presentation-ready, explainable thermal intelligence console. It fuses NASA FIRMS observations with an industrial asset catalogue and satellite context to prioritise events that need human verification.

## 90-second demo flow

1. Open the dashboard and point out the four command metrics.
2. Click **Judge scenario** to reset one consistent sample dataset and open the highest-priority dossier.
3. Use **All**, **Critical**, and **High** in the decision queue; each count is derived from the same alert list.
4. Click **Open full queue** to inspect every triage item, then select a row for its dossier.
5. Show the transparent risk factors: FRP, sensor confidence, asset proximity and persistence.
6. Click **Generate evidence brief** to download a source-preserving incident report.
7. Click **Refresh intelligence**. Without a key, the reliable demo fixtures remain; with a key, the same pipeline switches to live NASA FIRMS observations.
8. Toggle Satellite and Industrial assets to show the visual verification workflow.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open <http://localhost:8000>.

## Live data

Request a free NASA FIRMS `MAP_KEY` at <https://firms.modaps.eosdis.nasa.gov/api/map_key/>. NASA emails the key to you. Copy `.env.example` to `.env` and paste only the key value:

```bash
cp .env.example .env
# edit .env: NASA_FIRMS_MAP_KEY=your_key
uvicorn app.main:app --reload --port 8000
```

The backend loads `.env` automatically. Keep the key server-side; do not paste it into `app/static/app.js` or expose it in the browser. Click **Refresh intelligence** after restarting. If no key is present, the dashboard stays fully usable in deterministic demo mode.

The ingestion adapter requests the India bounding box from the NASA FIRMS VIIRS SNPP NRT area endpoint. The OSM adapter uses Overpass and is deliberately optional so an unreliable public endpoint can never break the hackathon demo.

## API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /api/overview` | KPIs, mode, source status |
| `GET /api/hotspots` | Enriched observations with scores and reasoning |
| `GET /api/alerts` | Prioritised decision queue |
| `GET /api/industrial-sites` | Mapped industrial context |
| `GET /api/timeline` | Detection activity buckets |
| `POST /api/refresh` | FIRMS + optional OSM refresh |
| `GET /api/report/{hotspot_id}` | Downloadable evidence brief |
| `GET /privacy` | Prototype privacy disclosure |
| `GET /terms` | Prototype terms of use |

## Architecture

```text
NASA FIRMS ──┐
             ├─> normalise ─> geospatial enrichment ─> explainable risk model ─> alert queue
OSM assets ──┘                                                    │
Satellite tiles ──────────────────────────────────────────────────┘
                                                                      ↓
                                                            FastAPI + Leaflet console
```

The score is intentionally interpretable for operational trust: thermal intensity (27%), FRP (27%), sensor confidence (18%), industrial proximity (18%), persistence (6%), and recency (4%). The demo dataset explicitly separates suspected industrial fire signals, persistent thermal sources, industrial heat, and non-industrial observations. A thermal observation near a facility is not automatically labelled a fire. Every queue item has a human-readable reason and a recommended verification step.

## Strong pitch points

- **Signal, not noise:** the dashboard ranks anomalies rather than dumping raw satellite points.
- **Industrial context:** proximity to refineries, steel plants, ports and energy hubs changes priority.
- **Persistence detection:** repeated observations in a spatial cluster surface sources that may be flaring or a sustained fire.
- **Explainable by design:** every score decomposes into evidence that an incident commander can challenge.
- **Resilient demo:** a deterministic offline fixture path keeps the product usable when public APIs throttle.
- **Human in the loop:** the system recommends dispatch and cross-checks; it does not claim satellite data alone proves an incident.

## Production extension

For deployment beyond the prototype, replace `data/state.json` with PostGIS tables for observations, assets, and alerts; add Celery/Redis for scheduled ingestion; store raw FIRMS CSVs in object storage; and add role-based alert acknowledgement and audit history. The API boundary is already separated so this can be done without changing the dashboard.
