"""
Background job to periodically sync properties from external API.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.property_service import PropertyService
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler()


def sync_job():
    """
    Job function that runs periodically.
    Fetches properties from external API and updates database.
    """
    logger.info("Starting scheduled property sync")
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        # Create service
        service = PropertyService(db)
        
        # Run sync (async function in sync context)
        result = asyncio.run(service.sync_properties_from_api())
        
        logger.info(
            f"Sync completed: {result.properties_added} added, "
            f"{result.properties_updated} updated, "
            f"{result.errors} errors"
        )
    
    except Exception as e:
        logger.error(f"Sync job failed: {str(e)}")
    
    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler.
    Called on application startup.
    """
    logger.info(
        f"Starting scheduler (sync every {settings.sync_interval_hours} hours)"
    )
    
    # Add the sync job
    scheduler.add_job(
        func=sync_job,
        trigger=IntervalTrigger(hours=settings.sync_interval_hours),
        id="sync_properties",
        name="Sync properties from external API",
        replace_existing=True,
        max_instances=1  # Only one instance at a time
    )
    
    # Start the scheduler
    scheduler.start()
    
    # Run immediately on startup (then periodically)
    sync_job()
    
    logger.info("Scheduler started successfully")


def stop_scheduler():
    """
    Stop the background scheduler.
    Called on application shutdown.
    """
    logger.info("Stopping scheduler")
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")