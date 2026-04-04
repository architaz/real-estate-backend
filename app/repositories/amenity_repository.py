"""
Repository for Amenity database operations.

The repository pattern keeps raw SQL/ORM calls out of business logic.
Your service never touches SQLAlchemy directly — it calls this class.

Intern tip: Think of a repository as a "smart DB wrapper".
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Dict, Any
from app.models.amenity import Amenity
import logging

logger = logging.getLogger(__name__)


class AmenityRepository:

    def __init__(self, db: Session):
        self.db = db

    # ── Reads ──────────────────────────────────────────────────────────────────

    def get_by_property_id(
        self,
        property_id: int,
        amenity_type: Optional[str] = None,
    ) -> List[Amenity]:
        """
        Return all cached amenities for a property.

        Args:
            property_id:  The property we want amenities for.
            amenity_type: Optional filter ('school', 'hospital', 'park').

        Returns:
            List of Amenity ORM objects ordered by distance.
        """
        query = self.db.query(Amenity).filter(
            Amenity.property_id == property_id
        )

        if amenity_type:
            query = query.filter(Amenity.amenity_type == amenity_type)

        return query.order_by(Amenity.distance.asc()).all()

    def has_cached_amenities(self, property_id: int) -> bool:
        """
        Quick check: do we already have amenities for this property?
        Used to decide whether to hit the external API.
        """
        count = (
            self.db.query(Amenity)
            .filter(Amenity.property_id == property_id)
            .count()
        )
        return count > 0

    # ── Writes ─────────────────────────────────────────────────────────────────

    def bulk_create(
        self,
        amenities_data: List[Dict[str, Any]],
    ) -> List[Amenity]:
        """
        Insert a batch of amenities in one transaction.

        Why bulk? Calling db.commit() once for 30 rows is much faster
        than 30 individual commits.

        Args:
            amenities_data: List of dicts (each matching Amenity columns).

        Returns:
            List of created Amenity objects.
        """
        amenity_objects = [Amenity(**data) for data in amenities_data]
        self.db.add_all(amenity_objects)
        self.db.commit()

        for obj in amenity_objects:
            self.db.refresh(obj)

        logger.info(
            f"Inserted {len(amenity_objects)} amenities "
            f"for property {amenities_data[0].get('property_id') if amenities_data else '?'}"
        )
        return amenity_objects

    def delete_by_property_id(self, property_id: int) -> int:
        """
        Remove all amenities for a property (used when refreshing cache).

        Returns:
            Number of rows deleted.
        """
        deleted = (
            self.db.query(Amenity)
            .filter(Amenity.property_id == property_id)
            .delete()
        )
        self.db.commit()
        logger.info(f"Deleted {deleted} amenities for property {property_id}")
        return deleted

    # ── Stats ──────────────────────────────────────────────────────────────────

    def count_cached_properties(self) -> int:
        """How many properties already have amenity data? (useful for monitoring)"""
        from sqlalchemy import func, distinct
        result = self.db.query(func.count(distinct(Amenity.property_id))).scalar()
        return result or 0