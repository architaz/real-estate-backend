"""
Test script for External API Client.

Run this BEFORE integrating with the rest of the backend!

Usage:
    python test_api_client.py
"""

import asyncio
import logging
from app.services.external_api import ExternalAPIClient, normalize_property_data
import json

async def main():
    client = ExternalAPIClient()
    response = await client.fetch_properties(limit=5)
    return response

if __name__ == "__main__":
    result = asyncio.run(main())
    print(result)
    with open("sample_zestimate.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
    print("✅ sample_zestimate.json updated")


# Setup logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_fetch_properties():
    """Test fetching properties from external API."""
    print("\n" + "="*60)
    print("TEST 1: Fetch Properties from External API")
    print("="*60 + "\n")
    
    try:
        # Create client
        client = ExternalAPIClient()
        
        # Fetch a small number of properties
        print("Fetching 5 properties...")
        properties = await client.fetch_properties(limit=5)
        
        print(f"✅ Successfully fetched {len(properties)} properties\n")
        
        # Print first property
        if properties:
            print("First property (raw API response):")
            print("-" * 60)
            import json
            print(json.dumps(properties[0], indent=2))
            print("-" * 60)
        
        return properties
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def test_normalization(properties):
    """Test data normalization."""
    print("\n" + "="*60)
    print("TEST 2: Normalize Property Data")
    print("="*60 + "\n")
    
    if not properties:
        print("❌ No properties to normalize (fetch failed)")
        return
    
    try:
        # Normalize first property
        raw_property = properties[0]
        
        print("Normalizing first property...")
        normalized = normalize_property_data(raw_property)
        
        print("✅ Normalization successful!\n")
        
        print("Normalized data (what goes to database):")
        print("-" * 60)
        for key, value in normalized.items():
            if key != "raw_data":  # Skip raw_data (too long)
                print(f"{key:15} : {value}")
        print("-" * 60)
        
        # Test normalizing all properties
        print(f"\nNormalizing all {len(properties)} properties...")
        success_count = 0
        error_count = 0
        
        for prop in properties:
            try:
                normalize_property_data(prop)
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"❌ Error normalizing property: {str(e)}")
        
        print(f"\n✅ Success: {success_count}/{len(properties)}")
        if error_count > 0:
            print(f"❌ Errors: {error_count}/{len(properties)}")
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_filtering():
    """Test API filtering by community."""
    print("\n" + "="*60)
    print("TEST 3: Filter by Community")
    print("="*60 + "\n")
    
    try:
        client = ExternalAPIClient()
        
        # Test with a specific community
        # CUSTOMIZE THIS: Use a real community from your API
        test_community = "Toronto"  # Change to match your API
        
        print(f"Fetching properties in '{test_community}'...")
        properties = await client.fetch_properties(
            community=test_community,
            limit=3
        )
        
        print(f"✅ Fetched {len(properties)} properties in {test_community}")
        
        if properties:
            print("\nProperty addresses:")
            for i, prop in enumerate(properties, 1):
                normalized = normalize_property_data(prop)
                print(f"{i}. {normalized['address']}")
    
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print("Note: Filtering might not be supported by your API")

async def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "="*60)
    print("EXTERNAL API CLIENT TEST SUITE")
    print("="*60)
    
    # Test 1: Fetch properties
    properties = await test_fetch_properties()
    
    # Test 2: Normalize data
    if properties:
        await test_normalization(properties)
    
    # Test 3: Test filtering
    await test_filtering()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    # Run tests
    asyncio.run(run_all_tests())