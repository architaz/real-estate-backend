"""
Background Job: Prefetch Amenities
====================================
Runs once at startup, then every N hours.

Purpose:
  Populate the amenities cache for all properties so the FIRST
  user to open a property page never has to wait for the Overpass API.

This pattern is called "eager caching" or "cache warming".
"""
import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.database import SessionLocal
from app.services.amenity_service import AmenityService

logger = logging.getLogger(__name__)

amenity_scheduler = BackgroundScheduler()


def prefetch_amenities_job():
    """
    Sync wrapper around the async prefetch method.
    APScheduler runs sync functions; we use asyncio.run() to bridge.
    """
    logger.info("▶ Starting amenity prefetch job...")
    db = SessionLocal()
    try:
        service = AmenityService(db)
        stats = asyncio.run(service.prefetch_amenities_for_all())
        logger.info(
            f"✅ Amenity prefetch complete — "
            f"fetched={stats['fetched']}, "
            f"skipped={stats['skipped']}, "
            f"failed={stats['failed']}"
        )
    except Exception as e:
        logger.error(f"❌ Amenity prefetch job failed: {e}")
    finally:
        db.close()


def start_amenity_scheduler(interval_hours: int = 24):
    """
    Start the prefetch job.
    Re-runs every `interval_hours` hours so new properties get covered.
    """
    logger.info(f"Starting amenity scheduler (every {interval_hours}h)")

    amenity_scheduler.add_job(
        func=prefetch_amenities_job,
        trigger=IntervalTrigger(hours=interval_hours),
        id="prefetch_amenities",
        name="Pre-warm amenity cache for all properties",
        replace_existing=True,
        max_instances=1,
    )
    amenity_scheduler.start()

    # Run immediately so data is ready when the server starts
    prefetch_amenities_job()
    logger.info("✅ Amenity scheduler started")


def stop_amenity_scheduler():
    amenity_scheduler.shutdown(wait=True)
    logger.info("Amenity scheduler stopped")