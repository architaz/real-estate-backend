"""
External API service with MOCK data for development.
"""

import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random
import json
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================
# MOCK API CLIENT (Use for development)
# ============================================

class MockExternalAPIClient:
    """Mock API client - returns fake data for testing."""
    
    def __init__(self):
        logger.info("🔧 MOCK API MODE - Using generated test data")
        self.mock_properties = self._generate_mock_properties()
    
    async def fetch_properties(
        self,
        community: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Return mock property data."""
        logger.info(
            f"[MOCK] Fetching properties: "
            f"limit={limit}, community={community}"
        )
        
        properties = self.mock_properties
        
        # Filter by community if specified
        if community:
            properties = [
                p for p in properties 
                if p.get("community", "").lower() == community.lower()
            ]
        
        # Apply pagination
        end = offset + limit
        paginated = properties[offset:end]
        
        logger.info(f"[MOCK] Returning {len(paginated)} properties")
        return paginated
    
    def _generate_mock_properties(self) -> List[Dict[str, Any]]:
        """Generate 150 realistic mock properties."""
        
        communities = [
            "Fletcher's Meadow",
            "Downtown Core", 
            "Lakeside Estates",
            "Valley Green",
            "Heritage Hills",
            "Tech District"
        ]
        
        streets = [
            "Spencer Ave", "Rowland St", "Teston Rd", 
            "Tawnberry Cres", "Main Street", "Oak Avenue"
        ]
        
        properties = []
        
        for i in range(150):
            community = random.choice(communities)
            street_num = random.randint(1, 999)
            street = random.choice(streets)
            bedrooms = random.randint(2, 5)
            bathrooms = random.choice([2.0, 2.5, 3.0, 3.5, 4.0])
            living_size = random.randint(1500, 3500)
            lot_size = random.randint(2800, 4500)
            price = random.randint(700, 1800) * 1000
            
            status = random.choice(["sold", "active", "pending"])
            sold_date = None
            if status == "sold":
                days_ago = random.randint(30, 365)
                sold_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            
            property_data = {
                "id": f"mock_prop_{i+1:06d}",
                "address": {
                    "street": f"{street_num} {street}",
                    "city": "Brampton",
                    "province": "ON",
                    "postal_code": f"L6V {random.randint(1,9)}A{random.randint(0,9)}"
                },
                "community": community,
                "price": {
                    "amount": price,
                    "currency": "CAD"
                },
                "details": {
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "sqft": living_size,
                    "lot_size": lot_size
                },
                "status": status.upper(),
                "sold_date": sold_date,
                "description": f"{bedrooms}BR {bathrooms}BA home in {community}"
            }
            
            properties.append(property_data)
        
        return properties


# ============================================
# Use Mock Client (for now)
# ============================================
ExternalAPIClient = MockExternalAPIClient


# ============================================
# NORMALIZATION (Update for Mock Data)
# ============================================

def normalize_property_data(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize mock property data.
    
    This function works with the mock data structure above.
    When you switch to a real API, update this function!
    """
    try:
        # Extract ID
        external_id = raw_data.get("id")
        if not external_id:
            raise ValueError("Missing required field: id")
        
        # Build address
        address_obj = raw_data.get("address", {})
        address_parts = [
            address_obj.get("street", ""),
            address_obj.get("city", ""),
            address_obj.get("province", "")
        ]
        address = ", ".join(filter(None, address_parts))
        
        # Extract price
        price_obj = raw_data.get("price", {})
        price = price_obj.get("amount")
        if not price:
            raise ValueError("Missing required field: price")
        
        # Extract details
        details = raw_data.get("details", {})
        
        # Normalize status
        status = raw_data.get("status", "").lower()
        
        # Parse sold date
        sold_date = None
        sold_date_str = raw_data.get("sold_date")
        if sold_date_str:
            try:
                from dateutil import parser
                sold_date = parser.parse(sold_date_str).date()
            except:
                pass
        
        # Store original JSON
        raw_data_str = json.dumps(raw_data, ensure_ascii=False)
        
        # Build normalized dictionary
        normalized = {
            "external_id": str(external_id),
            "address": address,
            "community": raw_data.get("community"),
            "description": raw_data.get("description"),
            "living_size": details.get("sqft"),
            "lot_size": details.get("lot_size"),
            "bedrooms": details.get("bedrooms"),
            "bathrooms": details.get("bathrooms"),
            "price": float(price),
            "status": status,
            "sold_date": sold_date,
            "raw_data": raw_data_str
        }
        
        logger.debug(
            f"Normalized: {external_id} - {address}, ${price}"
        )
        
        return normalized
    
    except Exception as e:
        logger.error(f"Error normalizing property: {str(e)}")
        logger.debug(f"Raw data: {raw_data}")
        raise