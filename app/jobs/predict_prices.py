"""
Background job to predict prices for properties.

This job:
1. Finds properties without predictions
2. Generates predictions using ML model
3. Stores predictions in database

Runs periodically via APScheduler.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.prediction_service import PredictionService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
prediction_scheduler = BackgroundScheduler()


def predict_prices_job():
    """
    Job function that runs periodically to generate predictions.
    
    This finds all properties without predictions and generates them.
    """
    logger.info("Starting prediction job...")
    
    db: Session = SessionLocal()
    
    try:
        # Create prediction service
        service = PredictionService(db, model_version="v1")
        
        # Generate predictions for all unpredicted properties
        stats = service.predict_all_unpredicted()
        
        logger.info(
            f"✅ Prediction job complete: "
            f"{stats['newly_predicted']} new predictions, "
            f"{stats['already_predicted']} already existed, "
            f"{stats['failed']} failed"
        )
        
        return stats
    
    except Exception as e:
        logger.error(f"❌ Prediction job failed: {str(e)}")
        raise
    
    finally:
        db.close()


def start_prediction_scheduler():
    """
    Start the prediction job scheduler.
    Called on application startup.
    """
    # Get interval from settings (default: every 2 hours)
    interval_hours = getattr(settings, 'prediction_interval_hours', 2)
    
    logger.info(
        f"Starting prediction scheduler (every {interval_hours} hours)"
    )
    
    # Add the prediction job
    prediction_scheduler.add_job(
        func=predict_prices_job,
        trigger=IntervalTrigger(hours=interval_hours),
        id="predict_prices",
        name="Generate price predictions for properties",
        replace_existing=True,
        max_instances=1  # Only one instance at a time
    )
    
    # Start scheduler
    prediction_scheduler.start()
    
    # Run immediately on startup
    logger.info("Running initial prediction job...")
    predict_prices_job()
    
    logger.info("✅ Prediction scheduler started")


def stop_prediction_scheduler():
    """
    Stop the prediction scheduler.
    Called on application shutdown.
    """
    logger.info("Stopping prediction scheduler...")
    prediction_scheduler.shutdown(wait=True)
    logger.info("✅ Prediction scheduler stopped")