"""
FastAPI Main Application Entry Point

This is the core FastAPI application that:
1. Configures middleware (CORS for frontend communication)
2. Registers all API routers (endpoints)
3. Handles application startup (database table creation)
4. Validates configuration on launch

The app runs on http://127.0.0.1:8000 by default.
API documentation available at http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from database import create_tables
from app.routers import chatbots, workflows, nodes, edges, chat, faqs, upload, auth
from fastapi.middleware.cors import CORSMiddleware
from app.logging_config import setup_logging, get_logger
from app.config import CORS_ALLOWED_ORIGINS, LOG_LEVEL, validate_config
from app.services.redis_cache_service import get_redis_cache_service

# ============================================================================
# Logging Configuration
# ============================================================================
# Set up structured logging for the entire application
setup_logging(log_level=LOG_LEVEL)
logger = get_logger(__name__)

# ============================================================================
# Configuration Validation
# ============================================================================
# Validate environment variables and settings on startup
# Logs warnings if configuration is incomplete
if not validate_config():
    logger.warning("Configuration validation failed - check environment variables")

# ============================================================================
# FastAPI Application Instance
# ============================================================================
app = FastAPI(
    title="Chatbot API",
    description="Backend API for multi-chatbot system with workflows, FAQs, and RAG",
    version="1.0.0"
)

# ============================================================================
# CORS Middleware Configuration
# ============================================================================
# Allow frontend (Next.js on localhost:3000) to make API requests
# Without CORS, browsers would block cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,  # Which domains can access the API
    allow_credentials=True,               # Allow cookies and authentication
    allow_methods=["*"],                  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],                  # Allow all request headers
)

# ============================================================================
# API Router Registration
# ============================================================================
# Each router handles a specific domain of the application
# Routers define the API endpoints (e.g., /chatbots, /chat/start, etc.)

# Authentication and user management
app.include_router(
    auth.router,
    tags=["Authentication"]
)

# Chatbot management
app.include_router(
    chatbots.router, 
    prefix="/chatbots", 
    tags=["Chatbots"]
)

# Workflow, Node, and Edge management (conversation flows)
app.include_router(
    workflows.router, 
    prefix="",  # Uses nested paths like /chatbots/{id}/workflows
    tags=["Workflows"]
)
app.include_router(
    nodes.router, 
    prefix="", 
    tags=["Nodes"]
)
app.include_router(
    edges.router, 
    prefix="", 
    tags=["Edges"]
)

# Chat conversation endpoints
app.include_router(
    chat.router, 
    prefix="/chat", 
    tags=["Chat"]
)

# FAQ management
app.include_router(
    faqs.router, 
    prefix="", 
    tags=["FAQs"]
)

# PDF upload and document management
app.include_router(
    upload.router, 
    prefix="",  # Uses /api/upload prefix defined in router
    tags=["Upload"]
)

# ============================================================================
# Application Startup Event
# ============================================================================
@app.on_event("startup")
def startup_event():
    """
    Runs once when the FastAPI application starts.
    
    Responsibilities:
    1. Create database tables if they don't exist
    2. Initialize Redis cache connection
    3. Log startup information
    
    This ensures the database schema and cache are ready before handling requests.
    SQLAlchemy will check existing tables and only create missing ones.
    """
    logger.info("="*60)
    logger.info("Application startup initiated")
    logger.info("="*60)
    
    logger.info("Creating database tables (if not exists)...")
    create_tables()
    logger.info("Database tables created successfully")
    
    logger.info("Initializing Redis cache service...")
    redis_cache = get_redis_cache_service()
    if redis_cache.is_available():
        logger.info("Redis cache initialized successfully")
    else:
        logger.warning("Redis cache not available - running without cache")
    
    logger.info("="*60)
    logger.info("Application startup complete - Ready to handle requests")
    logger.info("="*60)


# ============================================================================
# Application Shutdown Event
# ============================================================================
@app.on_event("shutdown")
def shutdown_event():
    """
    Runs once when the FastAPI application shuts down.
    
    Responsibilities:
    1. Close Redis cache connection gracefully
    2. Log shutdown information
    
    This ensures proper cleanup of resources.
    """
    logger.info("="*60)
    logger.info("Application shutdown initiated")
    logger.info("="*60)
    
    logger.info("Closing Redis cache connection...")
    redis_cache = get_redis_cache_service()
    redis_cache.close()
    logger.info("Redis cache connection closed")
    
    logger.info("="*60)
    logger.info("Application shutdown complete")
    logger.info("="*60)
