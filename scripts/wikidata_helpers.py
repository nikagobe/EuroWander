"""
Shared Wikidata SPARQL helpers used by both:
  - fetch_coordinates.py   (updates MongoDB)
  - enrich_seeds.py        (updates JSON seed files)
"""

import asyncio
from typing import Any

import httpx

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SPARQL_BATCH_SIZE = 200
RATE_LIMIT_DELAY = 1.0
USER_AGENT = "EuroWanderCityCoords/1.0 (educational project; contact: dev@eurowander.example)"


def build_sparql_query(wikidata_ids: list[str]) -> str:
    values = " ".join(f"wd:{qid}" for qid in wikidata_ids)
    return f"""
SELECT ?item ?lat ?lng WHERE {{
  VALUES ?item {{ {values} }}
  ?item wdt:P625 ?coord .
  BIND(geof:latitude(?coord)  AS ?lat)
  BIND(geof:longitude(?coord) AS ?lng)
}}
"""


async def fetch_coordinates_batch(
    client: httpx.AsyncClient,
    wikidata_ids: list[str],
) -> dict[str, tuple[float, float]]:
    """
    Fetch coordinates for up to SPARQL_BATCH_SIZE IDs.
    Returns { "Q90": (48.8566, 2.3522), ... }
    """
    query = build_sparql_query(wikidata_ids)
    params = {"query": query, "format": "json"}
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }

    response_data: dict[str, Any] = {}
    for attempt in range(3):
        try:
            response = await client.get(
                SPARQL_ENDPOINT,
                params=params,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            response_data = response.json()
            break
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            print(f"    ⚠ SPARQL request failed (attempt {attempt + 1}/3): {exc}")
            if attempt < 2:
                await asyncio.sleep(5)
            else:
                return {}

    results: dict[str, tuple[float, float]] = {}
    for binding in response_data.get("results", {}).get("bindings", []):
        try:
            qid = binding["item"]["value"].split("/")[-1]
            lat = float(binding["lat"]["value"])
            lng = float(binding["lng"]["value"])
            results[qid] = (lat, lng)
        except (KeyError, ValueError):
            continue

    return results


async def fetch_all_coordinates(
    unique_ids: list[str],
    label: str = "",
) -> dict[str, tuple[float, float]]:
    """
    Fetch coordinates for all IDs in batches, with progress logging.
    Returns a merged dict of all results.
    """
    batches = [
        unique_ids[i: i + SPARQL_BATCH_SIZE]
        for i in range(0, len(unique_ids), SPARQL_BATCH_SIZE)
    ]
    total_batches = len(batches)
    all_coords: dict[str, tuple[float, float]] = {}

    try:
        import ssl as _ssl
        import truststore
        ssl_ctx = truststore.SSLContext(_ssl.PROTOCOL_TLS_CLIENT)
        verify: bool | object = ssl_ctx
    except ImportError:
        verify = True

    async with httpx.AsyncClient(verify=verify) as http:
        for idx, batch in enumerate(batches, start=1):
            prefix = f"[{label}] " if label else ""
            print(f"  {prefix}📡 Batch {idx}/{total_batches} ({len(batch)} IDs)...")
            coords = await fetch_coordinates_batch(http, batch)
            all_coords.update(coords)
            print(f"     ✓ Got {len(coords)}/{len(batch)} coordinates.")
            if idx < total_batches:
                await asyncio.sleep(RATE_LIMIT_DELAY)

    return all_coords

