"""
Debug prediction with detailed logging.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("\n" + "="*70)
print("DEBUGGING PREDICTION FOR PROPERTY 1")
print("="*70 + "\n")

try:
    print("Step 1: Importing modules...")
    from app.core.database import SessionLocal
    from app.services.prediction_service import PredictionService
    from app.repositories.property_repository import PropertyRepository
    print("✅ Imports successful\n")
    
    print("Step 2: Creating database session...")
    db = SessionLocal()
    print("✅ Database session created\n")
    
    print("Step 3: Checking if property 1 exists...")
    property_repo = PropertyRepository(db)
    prop = property_repo.get_by_id(1)
    
    if not prop:
        print("❌ Property 1 not found!")
        print("Available properties:")
        all_props = property_repo.get_all(limit=5)
        for p in all_props:
            print(f"   ID {p.id}: {p.address}")
        sys.exit(1)
    
    print(f"✅ Property 1 found: {prop.address}")
    print(f"   Price: ${prop.price}")
    print(f"   Bedrooms: {prop.bedrooms}")
    print(f"   Bathrooms: {prop.bathrooms}")
    print(f"   Living Size: {prop.living_size}")
    print(f"   Lot Size: {prop.lot_size}")
    print(f"   Community: {prop.community}")
    print(f"   Status: {prop.status}\n")
    
    print("Step 4: Initializing prediction service...")
    service = PredictionService(db, model_version="v1")
    
    if not service.predictor:
        print("❌ Predictor failed to initialize!")
        print("Check if model files exist:")
        model_dir = Path("app/ml/models")
        print(f"   Directory exists: {model_dir.exists()}")
        if model_dir.exists():
            files = list(model_dir.iterdir())
            print(f"   Files in directory: {[f.name for f in files]}")
        sys.exit(1)
    
    print("✅ Prediction service initialized\n")
    
    print("Step 5: Making prediction...")
    prediction = service.predict_for_property(1)
    
    if prediction:
        print("\n" + "="*70)
        print("✅ PREDICTION SUCCESSFUL!")
        print("="*70)
        print(f"Property ID: {prediction.property_id}")
        print(f"Predicted Price: ${prediction.predicted_price:,.2f}")
        print(f"Confidence: {prediction.confidence_score:.2%}")
        print(f"Model Version: {prediction.model_version}")
        print("="*70 + "\n")
    else:
        print("\n❌ Prediction returned None")
        print("Check backend logs for detailed error\n")
    
    db.close()

except Exception as e:
    print(f"\n❌ ERROR: {e}\n")
    import traceback
    traceback.print_exc()
    print()