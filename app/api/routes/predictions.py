"""
API routes for predictions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.api.dependencies import get_db
from app.services.prediction_service import PredictionService
from app.schemas.prediction import (
    PredictionResponse,
    PredictionStatsResponse,
    BulkPredictionResponse
)

router = APIRouter(
    prefix="/api/predictions",
    tags=["predictions"]
)


@router.get("/property/{property_id}", response_model=PredictionResponse)
def get_prediction_for_property(
    property_id: int,
    model_version: str = Query("v1", description="Model version to use"),
    db: Session = Depends(get_db)
):
    """
    Get prediction for a specific property.
    
    If prediction doesn't exist, generates it automatically.
    
    **Example:**
```
    GET /api/predictions/property/123?model_version=v1
```
    """
    service = PredictionService(db, model_version=model_version)
    prediction = service.get_prediction_for_property(property_id)
    
    if not prediction:
        raise HTTPException(
            status_code=404,
            detail=f"Could not generate prediction for property {property_id}"
        )
    
    return prediction


@router.post("/generate/{property_id}", response_model=PredictionResponse)
def generate_prediction(
    property_id: int,
    model_version: str = Query("v1", description="Model version to use"),
    db: Session = Depends(get_db)
):
    """
    Force regenerate prediction for a property.
    
    Useful for:
    - Updating predictions with new model
    - Refreshing stale predictions
    
    **Example:**
```
    POST /api/predictions/generate/123?model_version=v1
```
    """
    service = PredictionService(db, model_version=model_version)
    prediction = service.predict_for_property(property_id)
    
    if not prediction:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to generate prediction for property {property_id}"
        )
    
    return prediction


@router.post("/generate-all", response_model=BulkPredictionResponse)
def generate_all_predictions(
    model_version: str = Query("v1", description="Model version to use"),
    db: Session = Depends(get_db)
):
    """
    Generate predictions for all properties without predictions.
    
    This is a batch operation that may take time for large datasets.
    
    **Example:**
```
    POST /api/predictions/generate-all?model_version=v1
```
    
    **Returns:**
```json
    {
      "total_properties": 150,
      "already_predicted": 50,
      "newly_predicted": 95,
      "failed": 5,
      "success_rate": 96.67
    }
```
    """
    service = PredictionService(db, model_version=model_version)
    stats = service.predict_all_unpredicted()
    
    return BulkPredictionResponse.from_stats(stats)


@router.get("/stats", response_model=PredictionStatsResponse)
def get_prediction_stats(
    db: Session = Depends(get_db)
):
    """
    Get statistics about predictions.
    
    **Example:**
```
    GET /api/predictions/stats
```
    
    **Returns:**
```json
    {
      "predictions_by_version": {
        "v1": 150
      },
      "total_predictions": 150,
      "recent_predictions_count": 10,
      "current_model_version": "v1"
    }
```
    """
    service = PredictionService(db)
    return service.get_prediction_stats()