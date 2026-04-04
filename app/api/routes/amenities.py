"""
Amenity API Routes
==================
Exposes:
  GET  /api/properties/{property_id}/amenities
  POST /api/properties/{property_id}/amenities/refresh

These routes are thin — they just call AmenityService and return the result.
No business logic here.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.services.amenity_service import AmenityService
from app.schemas.amenity import PropertyAmenitiesResponse

router = APIRouter(
    prefix="/api/properties",
    tags=["amenities"],
)


@router.get("/{property_id}/amenities", response_model=PropertyAmenitiesResponse)
async def get_property_amenities(
    property_id: int,
    force_refresh: bool = Query(
        False,
        description="Set to true to bypass cache and re-fetch from external API"
    ),
    db: Session = Depends(get_db),
):
    """
    Return nearby amenities (schools, hospitals, parks, transit)
    for a given property.

    **How it works:**
    1. On first call: geocodes the address, calls Overpass API, caches results.
    2. On subsequent calls: serves instantly from the database cache.
    3. Use `force_refresh=true` to update stale data.

    **Example:**
    ```
    GET /api/properties/42/amenities
    GET /api/properties/42/amenities?force_refresh=true
    ```

    **Returns:**
    ```json
    {
      "property_id": 42,
      "property_lat": 43.7315,
      "property_lng": -79.7624,
      "property_address": "30 Spencer Ave, Brampton, ON",
      "total_count": 18,
      "cached": true,
      "groups": [
        {
          "type": "school",
          "icon": "🏫",
          "label": "Schools",
          "items": [
            {
              "id": 1,
              "name": "Fletcher's Meadow Public School",
              "amenity_type": "school",
              "lat": 43.732,
              "lng": -79.763,
              "distance": 350.5
            }
          ]
        }
      ]
    }
    ```
    """
    service = AmenityService(db)
    result = await service.get_amenities_for_property(
        property_id=property_id,
        force_refresh=force_refresh,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Property {property_id} not found",
        )

    return result


@router.post("/{property_id}/amenities/refresh", response_model=PropertyAmenitiesResponse)
async def refresh_property_amenities(
    property_id: int,
    db: Session = Depends(get_db),
):
    """
    Force a fresh fetch of amenities from the external API.

    Use this when:
    - You suspect the cached data is outdated.
    - A new amenity (school, clinic) has opened near the property.

    **Example:**
    ```
    POST /api/properties/42/amenities/refresh
    ```
    """
    service = AmenityService(db)
    result = await service.get_amenities_for_property(
        property_id=property_id,
        force_refresh=True,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Property {property_id} not found",
        )

    return result