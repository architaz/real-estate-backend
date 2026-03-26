"""
Pydantic schemas for predictions.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal


class PredictionBase(BaseModel):
    """Base prediction schema."""
    predicted_price: Decimal = Field(..., description="Predicted property price")
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1, description="Prediction confidence (0-1)")
    model_version: str = Field(..., description="ML model version used")


class PredictionCreate(PredictionBase):
    """Schema for creating a prediction."""
    property_id: int = Field(..., description="Property ID")
    features_used: Optional[str] = Field(None, description="JSON string of features used")


class PredictionResponse(PredictionBase):
    """Schema for prediction API responses."""
    id: int = Field(..., description="Prediction ID")
    property_id: int = Field(..., description="Property ID")
    features_used: Optional[str] = Field(None, description="Features used in JSON format")
    created_at: datetime = Field(..., description="When prediction was created")
    updated_at: datetime = Field(..., description="When prediction was last updated")
    
    class Config:
        from_attributes = True  # Enable ORM mode


class PredictionWithComparison(PredictionResponse):
    """
    Prediction with comparison to actual price.
    Used in property detail endpoint.
    """
    actual_price: Decimal = Field(..., description="Actual listed/sold price")
    price_difference: Decimal = Field(..., description="Predicted - Actual")
    price_difference_percent: float = Field(..., description="Percentage difference")
    is_good_deal: bool = Field(..., description="True if predicted > actual (underpriced)")
    
    @classmethod
    def from_prediction_and_property(cls, prediction: PredictionResponse, actual_price: Decimal):
        """
        Create comparison from prediction and actual price.
        
        Args:
            prediction: PredictionResponse object
            actual_price: Actual property price
        
        Returns:
            PredictionWithComparison instance
        """
        price_diff = prediction.predicted_price - actual_price
        price_diff_percent = float((price_diff / actual_price) * 100)
        
        return cls(
            **prediction.model_dump(),
            actual_price=actual_price,
            price_difference=price_diff,
            price_difference_percent=price_diff_percent,
            is_good_deal=price_diff > 0  # Predicted > Actual = underpriced = good deal
        )


class PredictionStatsResponse(BaseModel):
    """Statistics about predictions."""
    predictions_by_version: Dict[str, int] = Field(..., description="Count by model version")
    total_predictions: int = Field(..., description="Total predictions made")
    recent_predictions_count: int = Field(..., description="Recent predictions")
    current_model_version: str = Field(..., description="Active model version")


class BulkPredictionResponse(BaseModel):
    """Response from bulk prediction job."""
    total_properties: int = Field(..., description="Total properties checked")
    already_predicted: int = Field(..., description="Properties already predicted")
    newly_predicted: int = Field(..., description="New predictions created")
    failed: int = Field(..., description="Failed predictions")
    success_rate: float = Field(..., description="Success percentage")
    
    @classmethod
    def from_stats(cls, stats: Dict[str, int]):
        """Create response from stats dictionary."""
        total = stats['total_properties']
        success = stats['newly_predicted'] + stats['already_predicted']
        success_rate = (success / total * 100) if total > 0 else 0
        
        return cls(
            **stats,
            success_rate=success_rate
        )