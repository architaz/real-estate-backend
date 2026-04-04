"""
Amenity database model.

Stores nearby points of interest (schools, hospitals, parks, etc.)
linked to a property. We cache them here so we don't hit the
external API every time a user loads a property page.

Table: amenities
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric,
    DateTime, ForeignKey, Index, Float
)
from app.models.property import Base   # re-use the same declarative base


class Amenity(Base):
    """
    Represents a single nearby amenity for a property.

    Why store distance?
    - Pre-computed once, cheap to read many times.
    - Avoids haversine maths on every API call.

    Why store lat/lng?
    - Frontend needs coordinates to place map markers.
    """
    __tablename__ = "amenities"

    id = Column(Integer, primary_key=True, index=True)

    property_id = Column(
        Integer,
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    external_id  = Column(String(255), nullable=True)
    name         = Column(String(500), nullable=False)
    amenity_type = Column(String(100), nullable=False)  # school | hospital | park
    category     = Column(String(100), nullable=True)

    lat      = Column(Float, nullable=False)
    lng      = Column(Float, nullable=False)
    distance = Column(Float, nullable=True)   # metres

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_amenity_property_type", "property_id", "amenity_type"),
    )

    def __repr__(self):
        dist = f"{self.distance:.0f}m" if self.distance is not None else "unknown"
        return f"<Amenity(id={self.id}, name='{self.name}', type='{self.amenity_type}', dist={dist})>"