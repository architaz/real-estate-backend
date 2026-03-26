"""
Prediction database model.
Stores ML model predictions for properties.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, Numeric, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.property import Base


class Prediction(Base):
    """
    Represents a price prediction for a property.
    
    Relationships:
    - Many predictions can exist for one property (different model versions)
    """
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to properties table
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    
    # Prediction results
    predicted_price = Column(Numeric(12, 2), nullable=False)
    confidence_score = Column(Numeric(5, 4), nullable=True)  # Model confidence (0-1)
    
    # Model tracking
    model_version = Column(String(50), nullable=False)  # e.g., "v1.0", "v2.0"
    features_used = Column(JSON, nullable=True)  # Which features were used
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship (optional - allows prediction.property access)
    # property = relationship("Property", back_populates="predictions")
    
    def __repr__(self):
        return f"<Prediction(property_id={self.property_id}, predicted_price={self.predicted_price})>"