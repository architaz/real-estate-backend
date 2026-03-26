"""
Database models for properties.
These define the structure of our MySQL tables.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Property(Base):
    """
    Represents a real estate property listing.
    
    Key fields:
    - external_id: Unique identifier from the external API (prevents duplicates)
    - raw_data: Stores the original JSON from the API (useful for debugging)
    - created_at/updated_at: Track when records are added/modified
    """
    __tablename__ = "properties"

    # Primary key (auto-incrementing)
    id = Column(Integer, primary_key=True, index=True)
    
    # External API identifier - UNIQUE constraint prevents duplicates
    external_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Property details (normalized from API)
    address = Column(String(500), nullable=False)
    community = Column(String(255), nullable=True, index=True)  # Indexed for filtering
    description = Column(Text, nullable=True)
    
    # Property specifications
    living_size = Column(Integer, nullable=True)  # Square feet
    lot_size = Column(Integer, nullable=True)     # Square feet
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Numeric(3, 1), nullable=True)  # e.g., 2.5 bathrooms
    
    # Pricing and status
    price = Column(Numeric(12, 2), nullable=False)  # Up to 999,999,999.99
    status = Column(String(50), nullable=True)      # e.g., "sold", "active"
    sold_date = Column(Date, nullable=True)
    
    # Store original API response as JSON string
    # This is helpful for debugging and preserving data we might need later
    raw_data = Column(Text, nullable=True)
    
    # Timestamps (automatically managed)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Create composite index for common queries
    __table_args__ = (
        Index('idx_community_status', 'community', 'status'),
    )

    def __repr__(self):
        return f"<Property(id={self.id}, address='{self.address}', price={self.price})>"