"""
Train the house price prediction model.

Run this script once to create the initial model:
    python -m app.ml.training.train_model

For retraining:
    python scripts/retrain_model.py
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
import joblib
import json
from pathlib import Path
from datetime import datetime
import logging

from app.core.database import SessionLocal
from app.models.property import Property

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HousePriceModelTrainer:
    """
    Trains and saves a house price prediction model.
    
    Architecture:
    1. Load data from database
    2. Feature engineering
    3. Preprocessing pipeline
    4. Model training
    5. Evaluation
    6. Save artifacts
    """
    
    def __init__(self, model_version: str = "v1"):
        self.model_version = model_version
        self.model_dir = Path("app/ml/models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        # Define features
        self.numeric_features = ['bedrooms', 'bathrooms', 'living_size', 'lot_size']
        self.categorical_features = ['community', 'status']
        
        self.preprocessor = None
        self.model = None
        self.metadata = {}
    
    def load_data(self):
        """
        Load training data from database.
        
        Returns:
            pd.DataFrame: Property data with features and target
        """
        logger.info("Loading training data from database...")
        
        db = SessionLocal()
        try:
            # Query all properties with complete data
            properties = db.query(Property).filter(
                Property.price.isnot(None),
                Property.bedrooms.isnot(None),
                Property.bathrooms.isnot(None),
                Property.living_size.isnot(None)
            ).all()
            
            # Convert to DataFrame
            data = []
            for prop in properties:
                data.append({
                    'id': prop.id,
                    'bedrooms': prop.bedrooms,
                    'bathrooms': float(prop.bathrooms) if prop.bathrooms else 0,
                    'living_size': prop.living_size,
                    'lot_size': prop.lot_size or 0,
                    'community': prop.community or 'Unknown',
                    'status': prop.status or 'unknown',
                    'price': float(prop.price)
                })
            
            df = pd.DataFrame(data)
            logger.info(f"Loaded {len(df)} properties")
            
            return df
        
        finally:
            db.close()
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create engineered features.
        
        Args:
            df: Raw property data
        
        Returns:
            DataFrame with additional features
        """
        logger.info("Engineering features...")
        
        df = df.copy()
        
        # Price per square foot (helpful but don't use as feature - would leak target!)
        # df['price_per_sqft'] = df['price'] / df['living_size']
        
        # Lot to living ratio
        df['lot_ratio'] = df['lot_size'] / (df['living_size'] + 1)  # +1 to avoid division by zero
        
        # Total rooms
        df['total_rooms'] = df['bedrooms'] + df['bathrooms']
        
        # Is sold indicator
        df['is_sold'] = (df['status'].str.lower() == 'sold').astype(int)
        
        # Add new features to numeric list
        self.numeric_features.extend(['lot_ratio', 'total_rooms', 'is_sold'])
        
        logger.info(f"Features: {self.numeric_features + self.categorical_features}")
        
        return df
    
    def create_preprocessor(self):
        """
        Create preprocessing pipeline for features.
        
        Returns:
            ColumnTransformer: Preprocessing pipeline
        """
        logger.info("Creating preprocessing pipeline...")
        
        # Numeric transformer: scale to standard normal
        numeric_transformer = StandardScaler()
        
        # Categorical transformer: one-hot encoding
        categorical_transformer = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        
        # Combine transformers
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numeric_transformer, self.numeric_features),
                ('cat', categorical_transformer, self.categorical_features)
            ]
        )
        
        return preprocessor
    
    def train(self, df: pd.DataFrame):
        """
        Train the price prediction model.
        
        Args:
            df: Training data
        """
        logger.info("Starting model training...")
        
        # Separate features and target
        X = df[self.numeric_features + self.categorical_features]
        y = df['price']
        
        logger.info(f"Training data shape: {X.shape}")
        logger.info(f"Target range: ${y.min():,.0f} - ${y.max():,.0f}")
        
        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        logger.info(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
        
        # Create preprocessing pipeline
        self.preprocessor = self.create_preprocessor()
        
        # Create full pipeline with model
        # Using Random Forest (good for tabular data, handles non-linearity)
        self.model = Pipeline([
            ('preprocessor', self.preprocessor),
            ('regressor', RandomForestRegressor(
                n_estimators=100,
                max_depth=20,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1  # Use all CPU cores
            ))
        ])
        
        # Alternative: Gradient Boosting (often better accuracy)
        # self.model = Pipeline([
        #     ('preprocessor', self.preprocessor),
        #     ('regressor', GradientBoostingRegressor(
        #         n_estimators=100,
        #         learning_rate=0.1,
        #         max_depth=5,
        #         random_state=42
        #     ))
        # ])
        
        # Train the model
        logger.info("Training Random Forest model...")
        self.model.fit(X_train, y_train)
        
        # Evaluate
        self._evaluate(X_train, y_train, X_test, y_test)
    
    def _evaluate(self, X_train, y_train, X_test, y_test):
        """Evaluate model performance."""
        logger.info("Evaluating model...")
        
        # Training metrics
        y_train_pred = self.model.predict(X_train)
        train_mae = mean_absolute_error(y_train, y_train_pred)
        train_r2 = r2_score(y_train, y_train_pred)
        
        # Test metrics
        y_test_pred = self.model.predict(X_test)
        test_mae = mean_absolute_error(y_test, y_test_pred)
        test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
        test_r2 = r2_score(y_test, y_test_pred)
        
        # MAPE (Mean Absolute Percentage Error)
        test_mape = np.mean(np.abs((y_test - y_test_pred) / y_test)) * 100
        
        # Log results
        logger.info(f"\n{'='*60}")
        logger.info(f"MODEL EVALUATION - {self.model_version}")
        logger.info(f"{'='*60}")
        logger.info(f"Training MAE:   ${train_mae:,.0f}")
        logger.info(f"Training R²:    {train_r2:.4f}")
        logger.info(f"")
        logger.info(f"Test MAE:       ${test_mae:,.0f}")
        logger.info(f"Test RMSE:      ${test_rmse:,.0f}")
        logger.info(f"Test R²:        {test_r2:.4f}")
        logger.info(f"Test MAPE:      {test_mape:.2f}%")
        logger.info(f"{'='*60}\n")
        
        # Store in metadata
        self.metadata.update({
            'train_mae': float(train_mae),
            'train_r2': float(train_r2),
            'test_mae': float(test_mae),
            'test_rmse': float(test_rmse),
            'test_r2': float(test_r2),
            'test_mape': float(test_mape),
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        })
        
        # Feature importance (if using tree-based model)
        if hasattr(self.model.named_steps['regressor'], 'feature_importances_'):
            self._log_feature_importance()
    
    def _log_feature_importance(self):
        """Log feature importance from trained model."""
        # Get feature names after preprocessing
        feature_names = (
            self.numeric_features +
            list(self.model.named_steps['preprocessor']
                 .named_transformers_['cat']
                 .get_feature_names_out(self.categorical_features))
        )
        
        # Get importances
        importances = self.model.named_steps['regressor'].feature_importances_
        
        # Sort by importance
        indices = np.argsort(importances)[::-1][:10]  # Top 10
        
        logger.info("\nTop 10 Feature Importances:")
        logger.info("-" * 50)
        for i, idx in enumerate(indices, 1):
            logger.info(f"{i:2d}. {feature_names[idx]:30s} {importances[idx]:.4f}")
        logger.info("")
    
    def save_model(self):
        """Save trained model and metadata to disk."""
        logger.info(f"Saving model artifacts (version {self.model_version})...")
        
        # Save model
        model_path = self.model_dir / f"model_{self.model_version}.pkl"
        joblib.dump(self.model, model_path)
        logger.info(f"✅ Saved model: {model_path}")
        
        # Save metadata
        self.metadata.update({
            'model_version': self.model_version,
            'trained_at': datetime.utcnow().isoformat(),
            'numeric_features': self.numeric_features,
            'categorical_features': self.categorical_features,
            'model_type': 'RandomForestRegressor',
            'model_params': self.model.named_steps['regressor'].get_params()
        })
        
        metadata_path = self.model_dir / f"metadata_{self.model_version}.json"
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        logger.info(f"✅ Saved metadata: {metadata_path}")
        
        logger.info(f"\n🎉 Model training complete! Version: {self.model_version}")


def main():
    """Main training function."""
    # Create trainer
    trainer = HousePriceModelTrainer(model_version="v1")
    
    # Load data
    df = trainer.load_data()
    
    if len(df) < 50:
        logger.error("❌ Not enough data! Need at least 50 properties.")
        return
    
    # Engineer features
    df = trainer.engineer_features(df)
    
    # Train model
    trainer.train(df)
    
    # Save artifacts
    trainer.save_model()


if __name__ == "__main__":
    main()