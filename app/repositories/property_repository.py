
"""
Repository pattern for property database operations.
Abstracts SQLAlchemy queries from business logic.
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
from app.models.property import Property
import logging

logger = logging.getLogger(__name__)


class PropertyRepository:
    """
    Handles all database operations for properties.
    
    Why use a repository?
    - Centralizes database logic
    - Makes testing easier (can mock this)
    - Keeps business logic clean
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        community: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Property]:
        """
        Fetch properties with pagination and optional filters.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum records to return
            community: Filter by community name
            status: Filter by property status
        
        Returns:
            List of Property objects
        """
        query = self.db.query(Property)
        
        # Apply filters if provided
        filters = []
        if community:
            filters.append(Property.community == community)
        if status:
            filters.append(Property.status == status)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Order by most recent first
        query = query.order_by(Property.created_at.desc())
        
        # Apply pagination
        return query.offset(skip).limit(limit).all()
    
    def get_by_id(self, property_id: int) -> Optional[Property]:
        """Get a single property by internal ID."""
        return self.db.query(Property).filter(Property.id == property_id).first()
    
    def get_by_external_id(self, external_id: str) -> Optional[Property]:
        """
        Get a property by its external API ID.
        Used to check if a property already exists before inserting.
        """
        return self.db.query(Property).filter(
            Property.external_id == external_id
        ).first()
    
    def create(self, property_data: Dict[str, Any]) -> Property:
        """
        Create a new property record.
        
        Args:
            property_data: Dictionary with property fields
        
        Returns:
            Created Property object
        """
        property_obj = Property(**property_data)
        self.db.add(property_obj)
        self.db.commit()
        self.db.refresh(property_obj)  # Get the auto-generated ID
        
        logger.info(f"Created property: {property_obj.id} ({property_obj.address})")
        return property_obj
    
    def update(self, property_obj: Property, property_data: Dict[str, Any]) -> Property:
        """
        Update an existing property record.
        
        Args:
            property_obj: Existing Property object
            property_data: Dictionary with updated fields
        
        Returns:
            Updated Property object
        """
        # Update only provided fields
        for key, value in property_data.items():
            if hasattr(property_obj, key):
                setattr(property_obj, key, value)
        
        self.db.commit()
        self.db.refresh(property_obj)
        
        logger.info(f"Updated property: {property_obj.id} ({property_obj.address})")
        return property_obj
    
    def upsert(self, property_data: Dict[str, Any]) -> tuple[Property, bool]:
        """
        Insert a new property or update if it already exists.
        This is the KEY method for avoiding duplicates!
        
        Args:
            property_data: Dictionary with property fields (must include external_id)
        
        Returns:
            Tuple of (Property object, is_new)
            - Property object: The created or updated property
            - is_new: True if created, False if updated
        
        Example:
            property, is_new = repo.upsert(data)
            if is_new:
                print("Created new property")
            else:
                print("Updated existing property")
        """
        external_id = property_data.get("external_id")
        if not external_id:
            raise ValueError("external_id is required for upsert")
        
        # Check if property exists
        existing = self.get_by_external_id(external_id)
        
        if existing:
            # Update existing property
            updated = self.update(existing, property_data)
            return updated, False
        else:
            # Create new property
            created = self.create(property_data)
            return created, True
    
    def count(
        self,
        community: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """
        Count total properties (useful for pagination).
        
        Args:
            community: Filter by community
            status: Filter by status
        
        Returns:
            Total count
        """
        query = self.db.query(Property)
        
        filters = []
        if community:
            filters.append(Property.community == community)
        if status:
            filters.append(Property.status == status)
        
        if filters:
            query = query.filter(and_(*filters))
        
        return query.count()