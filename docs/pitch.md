# EmberWatch pitch

## Problem

Satellite fire products are powerful but operationally noisy. A thermal pixel is not automatically an industrial fire, a flare, or a harmless agricultural burn. Responders need context, prioritisation and evidence.

## Solution

EmberWatch converts NASA FIRMS detections into an explainable decision queue. It links each observation to nearby industrial assets from OpenStreetMap, detects repeat thermal activity, assigns a risk score, and gives a responder a map, reason codes and an evidence brief in one screen.

## What is novel

1. **Contextual risk, not raw detection:** the same FRP value receives a different priority depending on proximity to a refinery or steel plant.
2. **Persistence-aware classification:** repeated clusters distinguish sustained sources from isolated noise.
3. **Evidence chain:** NASA observation, OSM asset, satellite context and score factors remain visible together.
4. **Graceful degradation:** live feeds are optional; the operational workflow remains testable and demonstrable offline.

## Judge demo script

> “This is EmberWatch. On the left we see the source fabric; in the middle, every thermal event is spatially anchored to an industrial asset. I click the red Jamnagar event. The system tells me why it is critical: 42.8 MW, 88% sensor confidence, and 0.7 km from the refinery complex. I can inspect each factor instead of trusting a black-box label. Finally I export the evidence brief for a response team. This turns a satellite pixel into an action.”

## Evaluation mapping

- **Innovation:** multi-source geospatial fusion with a transparent prioritisation model.
- **Technical feasibility:** public data adapters, deterministic scoring and a working browser console.
- **Impact:** earlier verification of industrial fires and persistent heat sources.
- **Usability:** one-screen queue for an analyst or disaster management cell.
- **Scalability:** India bounding-box ingestion now; PostGIS/streaming ingestion later.
