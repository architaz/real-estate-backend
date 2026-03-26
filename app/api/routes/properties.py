"""
FastAPI routes for property endpoints.
These define the HTTP API that your frontend will call.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Any
from app.api.dependencies import get_db
from app.services.property_service import PropertyService
from app.schemas.property import PropertyResponse, PropertyListResponse, PropertySyncResponse, PropertyWithPrediction
from app.services.prediction_service import PredictionService
from app.schemas.prediction import PredictionWithComparison
from app.repositories.prediction_repository import PredictionRepository  # Add this import

router = APIRouter(
    prefix="/api/properties",
    tags=["properties"]
)


@router.get("/", response_model=list[PropertyWithPrediction])  # ← Changed this line
def list_properties(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    community: Optional[str] = Query(None, description="Filter by community"),
    status: Optional[str] = Query(None, description="Filter by status (sold, active, etc)"),
    db: Session = Depends(get_db)
):
    """Get a paginated list of properties with predictions."""
    service = PropertyService(db)
    prediction_repo = PredictionRepository(db)
    
    # Get properties (returns PropertyListResponse)
    result = service.get_properties(
        skip=skip,
        limit=limit,
        community=community,
        status=status
    )
    
    # Attach predictions to each property
    properties_with_predictions = []
    for prop in result.properties:  # Note: result.properties, not just result
        prediction = prediction_repo.get_by_property_id(prop.id, model_version="v1")
        prop_with_pred = PropertyWithPrediction.from_property_and_prediction(prop, prediction)
        properties_with_predictions.append(prop_with_pred)
    
    return properties_with_predictions


@router.get("/{property_id}", response_model=PropertyWithPrediction)  # ← Changed this line
def get_property(
    property_id: int,
    db: Session = Depends(get_db)
):
    """Get a single property by ID with prediction."""
    service = PropertyService(db)
    prediction_repo = PredictionRepository(db)
    
    property_obj = service.get_property_by_id(property_id)
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get prediction
    prediction = prediction_repo.get_by_property_id(property_id, model_version="v1")
    
    # Return combined response
    return PropertyWithPrediction.from_property_and_prediction(property_obj, prediction)


@router.post("/sync", response_model=PropertySyncResponse)
async def sync_properties(
    community: Optional[str] = Query(None, description="Only sync this community"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a sync from the external API.
    This is useful for testing and on-demand updates.
    
    **Frontend Usage:**
    ```javascript
    // Sync all properties
    fetch('/api/properties/sync', { method: 'POST' })
    
    // Sync only Fletcher's Meadow
    fetch('/api/properties/sync?community=Fletcher%27s%20Meadow', { method: 'POST' })
    ```
    
    Returns:
        Sync statistics (added, updated, errors)
    """
    service = PropertyService(db)
    return await service.sync_properties_from_api(community=community)

@router.get("/{property_id}/with-prediction", response_model=dict)
def get_property_with_prediction(
    property_id: int,
    model_version: str = Query("v1", description="Model version"),
    db: Session = Depends(get_db)
):
    """
    Get property details including price prediction.
    
    **Example:**
```
    GET /api/properties/123/with-prediction
```
    
    **Returns:**
```json
    {
      "property": {
        "id": 123,
        "address": "30 Spencer Ave",
        "price": 1260000,
        ...
      },
      "prediction": {
        "predicted_price": 1350000,
        "actual_price": 1260000,
        "price_difference": 90000,
        "price_difference_percent": 7.14,
        "is_good_deal": true,
        "confidence_score": 0.85
      }
    }
```
    """
    # Get property
    property_service = PropertyService(db)
    property_obj = property_service.get_property_by_id(property_id)
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get prediction
    prediction_service = PredictionService(db, model_version=model_version)
    prediction = prediction_service.get_prediction_for_property(property_id)
    
    response: dict[str, Any] = {
        "property": property_obj
    }
    
    if prediction:
        # Create comparison
        prediction_with_comparison = PredictionWithComparison.from_prediction_and_property(
            prediction,
            property_obj.price
        )
        response["prediction"] = prediction_with_comparison
    else:
        response["prediction"] = None
    
    return response