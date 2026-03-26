"""
Service layer for property business logic.
Coordinates between API client, repository, and external services.
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.repositories.property_repository import PropertyRepository
from app.services.external_api import ExternalAPIClient, normalize_property_data
from app.schemas.property import PropertyResponse, PropertyListResponse, PropertySyncResponse
import logging

logger = logging.getLogger(__name__)


class PropertyService:
    """
    Handles business logic for property operations.
    
    Responsibilities:
    - Coordinate between repository and external API
    - Implement business rules
    - Handle data transformation
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = PropertyRepository(db)
        self.api_client = ExternalAPIClient()
    
    def get_properties(
        self,
        skip: int = 0,
        limit: int = 100,
        community: Optional[str] = None,
        status: Optional[str] = None
    ) -> PropertyListResponse:
        """
        Get paginated list of properties.
        
        Args:
            skip: Pagination offset
            limit: Items per page
            community: Filter by community
            status: Filter by status
        
        Returns:
            PropertyListResponse with properties and metadata
        """
        # Get properties from database
        properties = self.repository.get_all(
            skip=skip,
            limit=limit,
            community=community,
            status=status
        )
        
        # Get total count for pagination
        total = self.repository.count(community=community, status=status)
        
        # Calculate page number
        page = (skip // limit) + 1 if limit > 0 else 1
        
        # Convert to response schemas
        property_responses = [
            PropertyResponse.model_validate(prop) for prop in properties
        ]
        
        return PropertyListResponse(
            total=total,
            page=page,
            page_size=limit,
            properties=property_responses
        )
    
    def get_property_by_id(self, property_id: int) -> Optional[PropertyResponse]:
        """Get a single property by ID."""
        property_obj = self.repository.get_by_id(property_id)
        
        if not property_obj:
            return None
        
        return PropertyResponse.model_validate(property_obj)
    
    async def sync_properties_from_api(
        self,
        community: Optional[str] = None
    ) -> PropertySyncResponse:
        """
        Sync properties from external API to database.
        This is the core synchronization logic!
        
        Args:
            community: Only sync properties from this community (optional)
        
        Returns:
            PropertySyncResponse with sync statistics
        """
        logger.info(f"Starting property sync (community: {community or 'all'})")
        
        added = 0
        updated = 0
        errors = 0
        
        try:
            # Fetch properties from external API
            raw_properties = await self.api_client.fetch_properties(community=community)
            
            logger.info(f"Fetched {len(raw_properties)} properties from API")
            
            # Process each property
            for raw_prop in raw_properties:
                try:
                    # Normalize data
                    normalized = normalize_property_data(raw_prop)
                    
                    # Upsert into database
                    _, is_new = self.repository.upsert(normalized)
                    
                    if is_new:
                        added += 1
                    else:
                        updated += 1
                
                except Exception as e:
                    logger.error(f"Error processing property: {str(e)}")
                    errors += 1
                    continue
            
            # Log summary
            logger.info(
                f"Sync completed: {added} added, {updated} updated, {errors} errors"
            )
            
            return PropertySyncResponse(
                success=True,
                properties_added=added,
                properties_updated=updated,
                errors=errors,
                message=f"Successfully synced {added + updated} properties"
            )
        
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            return PropertySyncResponse(
                success=False,
                properties_added=added,
                properties_updated=updated,
                errors=errors + 1,
                message=f"Sync failed: {str(e)}"
            )