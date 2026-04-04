from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AmenityBase(BaseModel):
    name:         str            = Field(..., description="Display name")
    amenity_type: str            = Field(..., description="school | hospital | park | transit")
    category:     Optional[str] = Field(None, description="e.g. 'primary_school'")
    lat:          float          = Field(..., description="Latitude")
    lng:          float          = Field(..., description="Longitude")
    distance:     Optional[float] = Field(None, description="Metres from property")


class AmenityResponse(AmenityBase):
    id:          int
    property_id: int
    created_at:  datetime

    class Config:
        from_attributes = True   # lets SQLAlchemy ORM objects be passed directly


class AmenityGroup(BaseModel):
    type:  str                   = Field(..., description="Amenity type key")
    icon:  str                   = Field(..., description="Emoji for UI")
    label: str                   = Field(..., description="Human-readable label")
    items: List[AmenityResponse] = Field(default_factory=list)


class PropertyAmenitiesResponse(BaseModel):
    property_id:      int
    property_lat:     Optional[float] = None
    property_lng:     Optional[float] = None
    property_address: str
    total_count:      int
    groups:           List[AmenityGroup]
    cached:           bool