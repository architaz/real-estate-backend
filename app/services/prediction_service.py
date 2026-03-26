"""
Service layer for prediction operations.
Coordinates between ML predictor, property data, and prediction repository.
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.property_repository import PropertyRepository
from app.ml.inference.predictor import HousePricePredictor
from app.schemas.prediction import PredictionCreate, PredictionResponse
import logging
import json

logger = logging.getLogger(__name__)


class PredictionService:
    """
    Handles prediction business logic.
    
    Responsibilities:
    - Load property data
    - Call ML predictor
    - Store predictions in database
    - Retrieve predictions for API
    """
    
    def __init__(self, db: Session, model_version: str = "v1"):
        self.db = db
        self.prediction_repo = PredictionRepository(db)
        self.property_repo = PropertyRepository(db)
        self.model_version = model_version
        
        # Initialize ML predictor
        try:
            self.predictor = HousePricePredictor(model_version=model_version)
            logger.info(f"✅ Prediction service initialized with model {model_version}")
        except RuntimeError as e:
            logger.error(f"❌ Failed to load model: {e}")
            self.predictor = None
    
    def predict_for_property(self, property_id: int) -> Optional[PredictionResponse]:
        """
        Generate and store prediction for a single property.
        
        Args:
            property_id: ID of property to predict
        
        Returns:
            PredictionResponse or None if prediction fails
        
        Example:
            service = PredictionService(db)
            prediction = service.predict_for_property(property_id=123)
            if prediction:
                print(f"Predicted price: ${prediction.predicted_price:,.2f}")
        """
        if not self.predictor:
            logger.error("Predictor not available - model may not be trained")
            return None
        
        try:
            # Get property data
            property_obj = self.property_repo.get_by_id(property_id)
            
            if not property_obj:
                logger.warning(f"Property {property_id} not found")
                return None
            
            # Check if property has minimum required features
            if not self._has_required_features(property_obj):
                logger.warning(
                    f"Property {property_id} missing required features, skipping prediction"
                )
                return None
            
            # Prepare property data for prediction
            property_data = {
                'bedrooms': property_obj.bedrooms,
                'bathrooms': float(str(property_obj.bathrooms)) if property_obj.bathrooms is not None else 0,
                'living_size': property_obj.living_size,
                'lot_size': property_obj.lot_size or 0,
                'community': property_obj.community or 'Unknown',
                'status': property_obj.status or 'unknown'
            }
            
            # Make prediction
            predicted_price, confidence = self.predictor.predict(property_data)
            
            logger.info(
                f"Predicted ${predicted_price:,.2f} for property {property_id} "
                f"(confidence: {confidence:.2%})"
            )
            
            # Store features used
            features_used = {
                'features': self.predictor.get_feature_names(),
                'values': property_data
            }
            
            # Save prediction to database
            prediction_data = {
                'property_id': property_id,
                'predicted_price': predicted_price,
                'confidence_score': confidence,
                'model_version': self.model_version,
                'features_used': json.dumps(features_used)
            }
            
            prediction = self.prediction_repo.upsert(prediction_data)
            
            # Convert to response schema
            return PredictionResponse.model_validate(prediction)
        
        except Exception as e:
            logger.error(f"Error predicting for property {property_id}: {str(e)}")
            return None
    
    def predict_for_multiple_properties(
        self, 
        property_ids: List[int]
    ) -> Dict[int, Optional[PredictionResponse]]:
        """
        Generate predictions for multiple properties.
        
        Args:
            property_ids: List of property IDs
        
        Returns:
            Dictionary mapping property_id to prediction
        
        Example:
            predictions = service.predict_for_multiple_properties([1, 2, 3])
            for prop_id, prediction in predictions.items():
                if prediction:
                    print(f"Property {prop_id}: ${prediction.predicted_price:,.2f}")
        """
        results = {}
        
        for property_id in property_ids:
            prediction = self.predict_for_property(property_id)
            results[property_id] = prediction
        
        return results
    
    def predict_all_unpredicted(self) -> Dict[str, int]:
        """
        Generate predictions for all properties without predictions.
        
        Returns:
            Dictionary with statistics:
            {
                'total_properties': 150,
                'already_predicted': 50,
                'newly_predicted': 95,
                'failed': 5
            }
        """
        logger.info("Starting bulk prediction for unpredicted properties...")
        
        # Get all properties
        all_properties = self.property_repo.get_all(limit=10000)
        
        stats = {
            'total_properties': len(all_properties),
            'already_predicted': 0,
            'newly_predicted': 0,
            'failed': 0
        }
        
        for property_obj in all_properties:
            prop_id = getattr(property_obj, 'id', None) or getattr(property_obj, 'property_id', None)

            if prop_id is None:
                logger.warning("Property object has no resolvable ID, skipping")
                stats['failed'] += 1
                continue
            # Check if prediction exists for current model version
            existing_prediction = self.prediction_repo.get_by_property_id(
                prop_id,
                model_version=self.model_version
            )
            
            if existing_prediction:
                stats['already_predicted'] += 1
                continue
            
            # Generate prediction
            prediction = self.predict_for_property(prop_id)
            
            if prediction:
                stats['newly_predicted'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(
            f"Bulk prediction complete: "
            f"{stats['newly_predicted']} new, "
            f"{stats['already_predicted']} existing, "
            f"{stats['failed']} failed"
        )
        
        return stats
    
    def get_prediction_for_property(
        self, 
        property_id: int
    ) -> Optional[PredictionResponse]:
        """
        Get existing prediction for a property.
        
        If no prediction exists, generates one.
        
        Args:
            property_id: Property ID
        
        Returns:
            PredictionResponse or None
        """
        # Try to get existing prediction
        prediction = self.prediction_repo.get_by_property_id(
            property_id,
            model_version=self.model_version
        )
        
        if prediction:
            return PredictionResponse.model_validate(prediction)
        
        # No prediction exists - generate one
        logger.info(f"No prediction found for property {property_id}, generating...")
        return self.predict_for_property(property_id)
    
    def _has_required_features(self, property_obj) -> bool:
        """
        Check if property has minimum required features for prediction.
        
        Required:
        - bedrooms (can be 0)
        - bathrooms (can be 0)
        - living_size (must be > 0)
        """
        if property_obj.living_size is None or property_obj.living_size <= 0:
            return False
        
        # Bedrooms and bathrooms can be None, we'll default to 0
        return True
    
    def get_prediction_stats(self) -> Dict[str, Any]:
        """
        Get statistics about predictions.
        
        Returns:
            Dictionary with various statistics
        """
        version_counts = self.prediction_repo.count_by_model_version()
        recent = self.prediction_repo.get_recent_predictions(limit=10)
        
        return {
            'predictions_by_version': version_counts,
            'total_predictions': sum(version_counts.values()),
            'recent_predictions_count': len(recent),
            'current_model_version': self.model_version
        }