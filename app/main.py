"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.api.routes import properties, health, predictions
from app.jobs.sync_properties import start_scheduler, stop_scheduler
from app.jobs.predict_prices import start_prediction_scheduler, stop_prediction_scheduler
from app.api.routes import amenities                              
from app.jobs.prefetch_amenities import (start_amenity_scheduler, stop_amenity_scheduler)
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events.
    
    This runs when the application starts and stops.
    """
    # Startup
    logger.info("Starting application...")
    init_db()  # Create database tables
    start_scheduler()  # Start background job scheduler
    start_amenity_scheduler() 
    start_prediction_scheduler()
    logger.info("Application started successfully")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down application...")
    stop_scheduler()  # Stop background jobs
    stop_amenity_scheduler()
    stop_prediction_scheduler()
    logger.info("Application stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Real Estate Backend API for property listings",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=True
)

# Configure CORS (allow frontend to call our API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins, 
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(health.router)
app.include_router(properties.router)
app.include_router(predictions.router) 
app.include_router(amenities.router)   


@app.get("/")
def root():
    """Root endpoint - basic API info."""
    return {
        "message": "Real Estate Backend API",
        "version": "2.0.0",
        "features": ["Property Listings", "Price Predictions", "Background Jobs"],
        "docs": "/docs"  # Interactive API documentation
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug  # Auto-reload on code changes in debug mode
    )