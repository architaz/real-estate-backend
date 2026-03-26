"""
Repository for prediction database operations.
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.prediction import Prediction
import logging

logger = logging.getLogger(__name__)


class PredictionRepository:
    """
    Handles database operations for predictions.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, prediction_data: Dict[str, Any]) -> Prediction:
        """
        Create a new prediction record.
        
        Args:
            prediction_data: Dictionary with prediction fields
        
        Returns:
            Created Prediction object
        """
        prediction = Prediction(**prediction_data)
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        
        logger.info(
            f"Created prediction for property {prediction.property_id}: "
            f"${prediction.predicted_price:,.2f}"
        )
        
        return prediction
    
    def get_by_property_id(
        self, 
        property_id: int,
        model_version: Optional[str] = None
    ) -> Optional[Prediction]:
        """
        Get the latest prediction for a property.
        
        Args:
            property_id: Property ID
            model_version: Optional specific model version
        
        Returns:
            Latest Prediction object or None
        """
        query = self.db.query(Prediction).filter(
            Prediction.property_id == property_id
        )
        
        if model_version:
            query = query.filter(Prediction.model_version == model_version)
        
        # Get most recent prediction
        return query.order_by(Prediction.created_at.desc()).first()
    
    def get_by_id(self, prediction_id: int) -> Optional[Prediction]:
        """Get a single prediction by ID."""
        return self.db.query(Prediction).filter(
            Prediction.id == prediction_id
        ).first()
    
    def get_all_for_property(self, property_id: int) -> List[Prediction]:
        """
        Get all predictions for a property (all versions).
        
        Useful for tracking prediction history.
        """
        return self.db.query(Prediction).filter(
            Prediction.property_id == property_id
        ).order_by(Prediction.created_at.desc()).all()
    
    def upsert(self, prediction_data: Dict[str, Any]) -> Prediction:
        """
        Create or update prediction for a property + model version.
        
        Args:
            prediction_data: Must include property_id and model_version
        
        Returns:
            Created or updated Prediction object
        """
        property_id = prediction_data.get('property_id')
        model_version = prediction_data.get('model_version')
        
        if not property_id or not model_version:
            raise ValueError("property_id and model_version are required")
        
        # Check if prediction exists for this property + model version
        existing = self.db.query(Prediction).filter(
            Prediction.property_id == property_id,
            Prediction.model_version == model_version
        ).first()
        
        if existing:
            # Update existing prediction
            for key, value in prediction_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            
            self.db.commit()
            self.db.refresh(existing)
            
            logger.info(
                f"Updated prediction for property {property_id}: "
                f"${existing.predicted_price:,.2f}"
            )
            
            return existing
        else:
            # Create new prediction
            return self.create(prediction_data)
    
    def get_recent_predictions(
        self, 
        limit: int = 100,
        model_version: Optional[str] = None
    ) -> List[Prediction]:
        """
        Get recent predictions.
        
        Args:
            limit: Maximum number to return
            model_version: Optional filter by model version
        
        Returns:
            List of recent Prediction objects
        """
        query = self.db.query(Prediction)
        
        if model_version:
            query = query.filter(Prediction.model_version == model_version)
        
        return query.order_by(
            Prediction.created_at.desc()
        ).limit(limit).all()
    
    def count_by_model_version(self) -> Dict[str, int]:
        """
        Count predictions by model version.
        
        Useful for tracking which model versions are in use.
        
        Returns:
            Dictionary mapping version to count
        """
        from sqlalchemy import func
        
        results = self.db.query(
            Prediction.model_version,
            func.count(Prediction.id).label('count')
        ).group_by(
            Prediction.model_version
        ).all()
        
        return {version: count for version, count in results}
    
    def delete_old_predictions(
        self, 
        property_id: int, 
        keep_latest: int = 3
    ) -> int:
        """
        Delete old predictions for a property, keeping only the latest N.
        
        Args:
            property_id: Property ID
            keep_latest: Number of predictions to keep
        
        Returns:
            Number of predictions deleted
        """
        # Get all predictions for property
        all_predictions = self.db.query(Prediction).filter(
            Prediction.property_id == property_id
        ).order_by(Prediction.created_at.desc()).all()
        
        # Keep only the latest N
        to_delete = all_predictions[keep_latest:]
        
        if not to_delete:
            return 0
        
        # Delete old predictions
        for pred in to_delete:
            self.db.delete(pred)
        
        self.db.commit()
        
        logger.info(
            f"Deleted {len(to_delete)} old predictions for property {property_id}"
        )
        
        return len(to_delete)