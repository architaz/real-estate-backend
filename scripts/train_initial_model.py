"""
Script to train the initial ML model.

Run this ONCE after you have property data:
    python scripts/train_initial_model.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.training.train_model import HousePriceModelTrainer
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Train the initial model."""
    print("\n" + "="*60)
    print("TRAINING HOUSE PRICE PREDICTION MODEL")
    print("="*60 + "\n")
    
    # Create trainer
    trainer = HousePriceModelTrainer(model_version="v1")
    
    # Load data
    print("📊 Loading training data from database...")
    df = trainer.load_data()
    
    if len(df) < 50:
        print(f"\n❌ ERROR: Not enough data!")
        print(f"   Found: {len(df)} properties")
        print(f"   Need: At least 50 properties")
        print(f"\n   Make sure:")
        print(f"   1. Backend sync job has run")
        print(f"   2. Properties exist in database")
        print(f"   3. Properties have required fields (bedrooms, living_size, price)")
        return
    
    print(f"✅ Loaded {len(df)} properties\n")
    
    # Engineer features
    print("🔧 Engineering features...")
    df = trainer.engineer_features(df)
    print("✅ Features engineered\n")
    
    # Train model
    print("🤖 Training Random Forest model...")
    print("   This may take a few minutes...\n")
    trainer.train(df)
    
    # Save model
    print("\n💾 Saving model...")
    trainer.save_model()
    
    print("\n" + "="*60)
    print("✅ MODEL TRAINING COMPLETE!")
    print("="*60)
    print(f"\nModel saved to: app/ml/models/")
    print(f"Files created:")
    print(f"  - model_v1.pkl")
    print(f"  - metadata_v1.json")
    print(f"\nNext steps:")
    print(f"  1. Restart backend to load the model")
    print(f"  2. Predictions will be generated automatically")
    print(f"  3. Test: curl http://localhost:8000/api/predictions/property/1")
    print()


if __name__ == "__main__":
    main()