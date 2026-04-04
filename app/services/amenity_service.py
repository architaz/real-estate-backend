"""
Amenity Service
===============
The brain of Sprint 3. Orchestrates:

  1. Geocoding  → turns a property address into lat/lng
  2. Caching    → checks DB before hitting the external API
  3. Fetching   → calls Overpass API for nearby POIs
  4. Storing    → saves POIs to DB for future requests
  5. Serving    → formats data for the API response

Architecture rule:
  Routes → AmenityService → (AmenityRepository | GeocodingService | AmenityExternalAPIClient)
  Routes NEVER call repositories or external APIs directly.
"""
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from app.repositories.amenity_repository import AmenityRepository
from app.repositories.property_repository import PropertyRepository
from app.services.geocoding_service import GeocodingService
from app.services.amenity_external_api import AmenityExternalAPIClient, AMENITY_CONFIG
from app.schemas.amenity import (
    AmenityResponse,
    AmenityGroup,
    PropertyAmenitiesResponse,
)
import logging

logger = logging.getLogger(__name__)


class AmenityService:
    """
    High-level amenity operations for the API layer.
    """

    def __init__(self, db: Session):
        self.db               = db
        self.amenity_repo     = AmenityRepository(db)
        self.property_repo    = PropertyRepository(db)
        self.geocoder         = GeocodingService()
        self.external_client  = AmenityExternalAPIClient()

    # ── Main public method ─────────────────────────────────────────────────────

    async def get_amenities_for_property(
        self,
        property_id: int,
        force_refresh: bool = False,
    ) -> Optional[PropertyAmenitiesResponse]:
        """
        Fetch and return amenities for a property.

        Flow:
          1. Load property from DB.
          2. If amenities already cached AND not force_refresh → return cache.
          3. Otherwise geocode the address, fetch from Overpass, store in DB.
          4. Group by type and return.

        Args:
            property_id:    Which property to look up.
            force_refresh:  If True, ignore cache and re-fetch from API.

        Returns:
            PropertyAmenitiesResponse or None if property not found.
        """
        # ── Step 1: Load property ──────────────────────────────────────────────
        property_obj = self.property_repo.get_by_id(property_id)
        if not property_obj:
            logger.warning(f"Property {property_id} not found")
            return None

        # ── Step 2: Check cache ────────────────────────────────────────────────
        cached = self.amenity_repo.has_cached_amenities(property_id)

        if cached and not force_refresh:
            logger.info(f"Serving amenities for property {property_id} from cache")
            amenities = self.amenity_repo.get_by_property_id(property_id)
            return self._build_response(property_obj, amenities, cached=True)

        # ── Step 3: Geocode the address ────────────────────────────────────────
        coords = await self.geocoder.geocode(str(property_obj.address))

        if coords is None:
            # Nominatim couldn't find the address.
            # Fall back to Brampton centre so we still return *something*.
            logger.warning(
                f"Geocoding failed for '{property_obj.address}', "
                "using Brampton centre as fallback"
            )
            coords = GeocodingService.mock_coords_for_brampton()

        lat, lng = coords

        # ── Step 4: Fetch from Overpass API ────────────────────────────────────
        logger.info(
            f"Fetching amenities for property {property_id} "
            f"at ({lat:.4f}, {lng:.4f})"
        )
        raw_amenities = await self.external_client.fetch_amenities(lat, lng)

        # ── Step 5: Attach property_id and store in DB ─────────────────────────
        if raw_amenities:
            # Clear old data if refreshing
            if cached and force_refresh:
                self.amenity_repo.delete_by_property_id(property_id)

            for item in raw_amenities:
                item["property_id"] = property_id

            db_amenities = self.amenity_repo.bulk_create(raw_amenities)
        else:
            logger.warning(
                f"No amenities returned from Overpass for property {property_id}"
            )
            db_amenities = []

        return self._build_response(property_obj, db_amenities, cached=False, lat=lat, lng=lng)

    # ── Bulk prefetch (used by background job) ─────────────────────────────────

    async def prefetch_amenities_for_all(self) -> Dict[str, int]:
        """
        Pre-populate amenities for all properties that don't have them yet.

        Called by the background job on startup so users never wait.

        Returns:
            Stats dict: { fetched, skipped, failed }
        """
        all_properties = self.property_repo.get_all(limit=10_000)
        stats = {"fetched": 0, "skipped": 0, "failed": 0}

        for prop in all_properties:
            if self.amenity_repo.has_cached_amenities(int(prop.id)):
                stats["skipped"] += 1
                continue
            try:
                result = await self.get_amenities_for_property(int(prop.id)) 
                if result:
                    stats["fetched"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.error(f"Failed prefetch for property {prop.id}: {e}")
                stats["failed"] += 1

        logger.info(f"Prefetch complete: {stats}")
        return stats

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_response(
        self,
        property_obj,
        amenities: list,
        cached: bool,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> PropertyAmenitiesResponse:
        """
        Turn a flat list of Amenity ORM objects into the grouped
        PropertyAmenitiesResponse the frontend expects.
        """
        # Convert ORM objects → Pydantic schemas
        amenity_responses = [AmenityResponse.model_validate(a) for a in amenities]

        # Group by type
        groups: Dict[str, AmenityGroup] = {}
        for amenity_type, config in AMENITY_CONFIG.items():
            groups[amenity_type] = AmenityGroup(
                type=amenity_type,
                icon=config["icon"],
                label=config["label"],
                items=[a for a in amenity_responses if a.amenity_type == amenity_type],
            )

        return PropertyAmenitiesResponse(
            property_id=property_obj.id,
            property_lat=lat,
            property_lng=lng,
            property_address=property_obj.address,
            total_count=len(amenity_responses),
            groups=list(groups.values()),
            cached=cached,
        )