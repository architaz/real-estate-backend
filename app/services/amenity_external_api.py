"""
External Amenities API Client
==============================
Fetches nearby points of interest using the Overpass API (OpenStreetMap).

Why Overpass API?
- 100% free, no API key required
- Covers schools, hospitals, parks, transit globally
- Returns GeoJSON-style data with names + coordinates

How to swap to a different provider:
- Implement the same interface (fetch_amenities method)
- Change the normalise_* functions below
- No other file needs to change — clean architecture!

Overpass API docs: https://overpass-api.de/
"""
import httpx
import math
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ── What amenity types we care about and their OSM tags ───────────────────────
# Keys are our internal type names; values are lists of OSM tag queries.
AMENITY_CONFIG: Dict[str, Dict] = {
    "school": {
        "label": "Schools",
        "icon":  "🎓",
        "osm_filters": [
            'amenity="school"',
            'amenity="kindergarten"',
            'amenity="college"',
        ],
    },
    "hospital": {
        "label": "Healthcare",
        "icon":  "🏥",
        "osm_filters": [
            'amenity="hospital"',
            'amenity="clinic"',
            'amenity="doctors"',
        ],
    },
    "park": {
        "label": "Parks & Recreation",
        "icon":  "🌳",
        "osm_filters": [
            'leisure="park"',
            'leisure="playground"',
            'leisure="sports_centre"',
        ],
    },
    "transit": {
        "label": "Transit",
        "icon":  "🚌",
        "osm_filters": [
            'highway="bus_stop"',
            'railway="station"',
            'railway="subway_entrance"',
        ],
    },
    "restaurant": {
        "label": "Restaurants",
        "icon":  "🍴",
        "osm_filters": [
            'amenity="restaurant"',
            'amenity="fast_food"',
        ],
    },
    "cafe": {
        "label": "Cafes",
        "icon":  "☕",
        "osm_filters": [
            'amenity="cafe"',
        ],
    },
    "pharmacy": {
        "label": "Pharmacies",
        "icon":  "💊",
        "osm_filters": [
            'amenity="pharmacy"',
        ],
    },
    "gym": {
        "label": "Gyms",
        "icon":  "💪",
        "osm_filters": [
            'leisure="fitness_centre"',
            'leisure="gym"',
        ],
    },
    "shopping": {
        "label": "Shopping",
        "icon":  "🛍️",
        "osm_filters": [
            'shop="mall"',
            'shop="supermarket"',
            'shop="convenience"',
        ],
    },
}

SEARCH_RADIUS_METRES = 2000   # Look within 1.5 km


class AmenityExternalAPIClient:
    """
    Fetches nearby amenities from OpenStreetMap via Overpass API.

    Usage:
        client = AmenityExternalAPIClient()
        amenities = await client.fetch_amenities(43.7315, -79.7624)
    """

    async def fetch_amenities(
        self,
        lat: float,
        lng: float,
        radius: int = SEARCH_RADIUS_METRES,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all configured amenity types near a coordinate.

        Args:
            lat, lng: Centre point (the property's location).
            radius:   Search radius in metres.

        Returns:
            List of normalised amenity dicts ready for DB insertion.
        """
        all_amenities: List[Dict[str, Any]] = []

        for amenity_type, config in AMENITY_CONFIG.items():
            try:
                raw_results = await self._query_overpass(
                    lat, lng, radius, config["osm_filters"]
                )
                normalised = self._normalise(raw_results, amenity_type, lat, lng)
                all_amenities.extend(normalised)
                logger.info(
                    f"  {config['icon']} Found {len(normalised)} {amenity_type}s"
                )
            except Exception as e:
                # One category failing should NOT kill the whole fetch
                logger.warning(f"Failed to fetch '{amenity_type}': {e}")

        logger.info(f"Total amenities fetched: {len(all_amenities)}")
        return all_amenities

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _query_overpass(
        self,
        lat: float,
        lng: float,
        radius: int,
        osm_filters: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Build and execute an Overpass QL query.

        Overpass QL: a query language for OpenStreetMap data.
        We query both 'node' (single points) and 'way' (polygons)
        because parks are often stored as ways, not nodes.
        """
        # Build one filter block per tag
        filter_blocks = []
        for osm_filter in osm_filters:
            # node[amenity="school"](around:1500,43.73,-79.76);
            filter_blocks.append(f'node[{osm_filter}](around:{radius},{lat},{lng});')
            filter_blocks.append(f'way[{osm_filter}](around:{radius},{lat},{lng});')

        query = f"""
        [out:json][timeout:50];
        (
          {''.join(filter_blocks)}
        );
        out center tags;
        """

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                OVERPASS_URL,
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()

        return data.get("elements", [])

    def _normalise(
        self,
        elements: List[Dict],
        amenity_type: str,
        origin_lat: float,
        origin_lng: float,
    ) -> List[Dict[str, Any]]:
        """
        Convert raw Overpass elements → clean dicts for our DB.

        Overpass returns two formats:
        - node: has lat/lon directly
        - way:  has a 'center' object with lat/lon
        """
        results = []
        seen_ids = set()   # deduplicate by OSM id

        for el in elements:
            el_id = str(el.get("id", ""))
            if el_id in seen_ids:
                continue
            seen_ids.add(el_id)

            tags = el.get("tags", {})

            # Resolve coordinates (node vs way)
            if el.get("type") == "node":
                el_lat = el.get("lat")
                el_lng = el.get("lon")
            else:
                centre = el.get("center", {})
                el_lat = centre.get("lat")
                el_lng = centre.get("lon")

            if el_lat is None or el_lng is None:
                continue

            # Name: try 'name', fall back to tag-based description
            name = (
                tags.get("name")
                or tags.get("operator")
                or tags.get("amenity", "").replace("_", " ").title()
                or tags.get("leisure", "").replace("_", " ").title()
                or tags.get("highway", "").replace("_", " ").title()
                or f"Unnamed {amenity_type.title()}"
            )

            category = (
                tags.get("amenity")
                or tags.get("leisure")
                or tags.get("highway")
                or tags.get("railway")
            )

            distance = _haversine_metres(origin_lat, origin_lng, el_lat, el_lng)

            results.append({
                "external_id":  el_id,
                "name":         name,
                "amenity_type": amenity_type,
                "category":     category,
                "lat":          el_lat,
                "lng":          el_lng,
                "distance":     round(distance, 1),
            })

        # Sort closest first, keep top 10 per type to avoid noise
        results.sort(key=lambda x: x["distance"])
        return results


# ── Pure function: haversine distance ─────────────────────────────────────────

def _haversine_metres(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance (in metres) between two GPS points.

    The haversine formula accounts for Earth's curvature.
    Accurate to within ~0.5% for distances < 10 km.
    """
    R = 6_371_000   # Earth radius in metres

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c