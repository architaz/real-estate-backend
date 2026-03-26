"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class PropertyBase(BaseModel):
    """Base schema with common property fields."""
    address: str = Field(..., description="Property street address")
    community: Optional[str] = Field(None, description="Community/neighborhood name")
    description: Optional[str] = Field(None, description="Property description")
    living_size: Optional[int] = Field(None, description="Living area in square feet")
    lot_size: Optional[int] = Field(None, description="Lot size in square feet")
    bedrooms: Optional[int] = Field(None, ge=0, description="Number of bedrooms")
    bathrooms: Optional[Decimal] = Field(None, ge=0, description="Number of bathrooms")
    price: Decimal = Field(..., description="Property price")
    status: Optional[str] = Field(None, description="Property status (sold, active, etc)")
    sold_date: Optional[date] = Field(None, description="Date property was sold")


class PropertyCreate(PropertyBase):
    """Schema for creating a new property."""
    external_id: str = Field(..., description="Unique ID from external API")


class PropertyResponse(PropertyBase):
    """Schema for property API responses."""
    id: int = Field(..., description="Internal database ID")
    external_id: str = Field(..., description="External API ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")
    
    class Config:
        from_attributes = True  # Enables ORM mode (SQLAlchemy compatibility)


class PropertyListResponse(BaseModel):
    """Schema for paginated property list response."""
    total: int = Field(..., description="Total number of properties")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    properties: list[PropertyResponse] = Field(..., description="List of properties")


class PropertySyncResponse(BaseModel):
    """Schema for sync job response."""
    success: bool = Field(..., description="Whether sync completed successfully")
    properties_added: int = Field(..., description="Number of new properties added")
    properties_updated: int = Field(..., description="Number of properties updated")
    errors: int = Field(..., description="Number of errors encountered")
    message: str = Field(..., description="Human-readable status message")


class PropertyWithPrediction(PropertyResponse):
    """Property with ML prediction data."""
    predicted_price: Optional[Decimal] = None
    confidence_score: Optional[float] = None
    price_difference: Optional[Decimal] = None
    price_difference_percent: Optional[float] = None
    is_good_deal: Optional[bool] = None
    
    @classmethod
    def from_property_and_prediction(cls, property_obj, prediction_obj=None):
        """Create schema from property and optional prediction."""
        # Start with property data
        data = {
            'id': property_obj.id,
            'external_id': property_obj.external_id,
            'address': property_obj.address,
            'community': property_obj.community,
            'description': property_obj.description,
            'living_size': property_obj.living_size,
            'lot_size': property_obj.lot_size,
            'bedrooms': property_obj.bedrooms,
            'bathrooms': property_obj.bathrooms,
            'price': property_obj.price,
            'status': property_obj.status,
            'sold_date': property_obj.sold_date,
            'created_at': property_obj.created_at,
            'updated_at': property_obj.updated_at,
        }
        
        # Add prediction data if available
        if prediction_obj:
            data['predicted_price'] = prediction_obj.predicted_price
            data['confidence_score'] = float(prediction_obj.confidence_score) if prediction_obj.confidence_score else None
            
            # Calculate differences
            if property_obj.price and prediction_obj.predicted_price:
                diff = prediction_obj.predicted_price - property_obj.price
                diff_pct = (diff / property_obj.price) * 100
                
                data['price_difference'] = diff
                data['price_difference_percent'] = float(diff_pct)
                data['is_good_deal'] = diff > 0
        
        return cls(**data)