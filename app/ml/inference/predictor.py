"""
Model predictor for making price predictions.
"""

import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, Any, Optional
import logging
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


class HousePricePredictor:
    """
    Loads trained model and makes predictions.
    """
    
    def __init__(self, model_version: str = "v1"):
        self.model_version = model_version
        self.model_dir = Path("app/ml/models")
        
        # FIX: proper type hints instead of None
        self.model: Optional[Pipeline] = None
        self.metadata: Optional[Dict[str, Any]] = None
        
        self._load_model()
    
    def _load_model(self):
        """Load trained model and metadata from disk."""
        try:
            model_path = self.model_dir / f"model_{self.model_version}.pkl"
            self.model = joblib.load(model_path)
            logger.info(f"✅ Loaded model: {model_path}")
            
            metadata_path = self.model_dir / f"metadata_{self.model_version}.json"
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
            logger.info(f"✅ Loaded metadata: {metadata_path}")
            
        except FileNotFoundError as e:
            logger.error(f"❌ Model files not found: {e}")
            raise RuntimeError(
                f"Model version '{self.model_version}' not found. "
                "Have you run training? python -m app.ml.training.train_model"
            )
    
    def predict(self, property_data: Dict) -> Tuple[float, float]:
        """
        Predict house price for a property.

        Returns:
            Tuple of (predicted_price, confidence_score)
        """
        # FIX: guard against None
        if self.model is None or self.metadata is None:
            raise RuntimeError("Model or metadata is not loaded.")

        features = self._prepare_features(property_data)
        
        numeric_features = self.metadata['numeric_features']
        categorical_features = self.metadata['categorical_features']
        all_feature_names = numeric_features + categorical_features
        
        features_dict = {}
        for i, feature_name in enumerate(all_feature_names):
            features_dict[feature_name] = [features[i]]
        
        df = pd.DataFrame(features_dict)
        
        predicted_price = self.model.predict(df)[0]
        confidence = self._calculate_confidence(df)
        
        return float(predicted_price), float(confidence)
    
    def _prepare_features(self, property_data: Dict) -> list:
        """Prepare features in the exact format expected by the model."""
        # FIX: guard against None
        if self.metadata is None:
            raise RuntimeError("Metadata is not loaded.")

        numeric_features = self.metadata['numeric_features']
        categorical_features = self.metadata['categorical_features']
        
        features = []
        
        for feat in numeric_features:
            if feat == 'lot_ratio':
                living_size = property_data.get('living_size', 1)
                lot_size = property_data.get('lot_size', 0)
                features.append(lot_size / (living_size + 1))
            
            elif feat == 'total_rooms':
                bedrooms = property_data.get('bedrooms', 0) or 0
                bathrooms = property_data.get('bathrooms', 0) or 0
                features.append(bedrooms + bathrooms)
            
            elif feat == 'is_sold':
                status = property_data.get('status', '').lower()
                features.append(1 if status == 'sold' else 0)
            
            else:
                value = property_data.get(feat, 0)
                features.append(float(value) if value is not None else 0.0)
        
        for feat in categorical_features:
            value = property_data.get(feat, 'Unknown')
            features.append(str(value) if value is not None else 'Unknown')
        
        return features
    
    def _calculate_confidence(self, features_df: pd.DataFrame) -> float:
        """
        Calculate prediction confidence score.

        Returns:
            Float between 0 and 1 (1 = highest confidence)
        """
        try:
            # FIX: guard against None
            if self.model is None:
                return 0.5

            if hasattr(self.model.named_steps['regressor'], 'estimators_'):
                tree_predictions = []
                
                features_preprocessed = self.model.named_steps['preprocessor'].transform(features_df)
                
                for tree in self.model.named_steps['regressor'].estimators_:
                    pred = tree.predict(features_preprocessed)[0]
                    tree_predictions.append(pred)
                
                std = np.std(tree_predictions)
                mean = np.mean(tree_predictions)
                
                cv = std / (mean + 1)
                confidence = 1 / (1 + cv)
                
                # FIX: explicit float() cast to resolve numpy floating[Any] type error
                return float(min(max(confidence, 0.0), 1.0))
            
            else:
                return 0.75
        
        except Exception as e:
            logger.warning(f"Error calculating confidence: {e}")
            return 0.5
    
    def get_feature_names(self) -> list:
        """Get list of features used by the model."""
        # FIX: guard against None
        if self.metadata is None:
            raise RuntimeError("Metadata is not loaded.")

        return (
            self.metadata['numeric_features'] + 
            self.metadata['categorical_features']
        )