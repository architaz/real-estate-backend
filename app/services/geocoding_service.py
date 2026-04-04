"""
Geocoding Service
=================
Converts a street address → (latitude, longitude).

We use the free Nominatim API (OpenStreetMap) so there are zero costs.
If you need higher throughput, swap for Google Geocoding API — just
change _geocode_nominatim() below and the rest stays the same.

Rate limits (Nominatim):
    - 1 request / second
    - Must include a descriptive User-Agent header
"""
import httpx
import asyncio
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Nominatim requires a unique, descriptive User-Agent
NOMINATIM_USER_AGENT = "RealEstateApp/1.0 (archita.0240@gmail.com)"
NOMINATIM_URL        = "https://nominatim.openstreetmap.org/search"


class GeocodingService:
    """
    Thin wrapper around the Nominatim geocoding API.

    Usage:
        svc = GeocodingService()
        lat, lng = await svc.geocode("30 Spencer Ave, Brampton, ON")
    """

    async def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert an address string to (lat, lng).

        Returns:
            Tuple (lat, lng) or None if geocoding fails.
        """
        try:
            coords = await self._geocode_nominatim(address)
            if coords:
                logger.info(f"Geocoded '{address}' → {coords}")
                return coords

            logger.warning(f"Could not geocode address: '{address}'")
            return None

        except Exception as e:
            logger.error(f"Geocoding error for '{address}': {e}")
            return None

    async def _geocode_nominatim(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Call the Nominatim API.

        Nominatim docs: https://nominatim.org/release-docs/develop/api/Search/
        """
        params = {
            "q":      address,
            "format": "json",
            "limit":  1,             # We only want the top result
        }
        headers = {"User-Agent": NOMINATIM_USER_AGENT}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(NOMINATIM_URL, params=params, headers=headers)
            resp.raise_for_status()

            results = resp.json()
            if not results:
                return None

            top = results[0]
            return float(top["lat"]), float(top["lon"])

    # ------------------------------------------------------------------
    # Fallback / mock for testing without internet
    # ------------------------------------------------------------------

    @staticmethod
    def mock_coords_for_brampton() -> Tuple[float, float]:
        """
        Returns approximate centre of Brampton, ON.
        Use this in tests / when Nominatim is unavailable.
        """
        return (43.7315, -79.7624)