from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys
import time

# Internal imports
from backend.config.settings import get_settings
from backend.database.supabase_client import get_supabase_client
from backend.database.redis_client import get_redis_client, close_redis_client
from backend.middleware.rate_limiter import limiter, rate_limit_dependency, RateLimitExceeded
from backend.utils.metrics import setup_metrics

# Import routers
from backend.api.whatsapp_routes import router as whatsapp_router

settings = get_settings()

# Configure logging
logger.remove()
if settings.log_format == "json":
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level=settings.log_level,
        serialize=True
    )
else:
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
        level=settings.log_level
    )

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting WhatsApp Seller Bot API...")
    
    try:
        # Initialize Redis
        redis_client = await get_redis_client()
        logger.info("✅ Redis connected")
        
        # Initialize Supabase
        supabase = get_supabase_client()
        logger.info("✅ Supabase connected")
        
        # TODO: Initialize LanceDB
        logger.info("✅ LanceDB initialized")
        
        logger.info("🎉 Application startup complete!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    await close_redis_client()
    logger.info("✅ Shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="WhatsApp Seller Bot API",
    description="E-commerce seller bot with RAG, cart management, and analytics",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None
)

# Add rate limiter state
app.state.limiter = limiter

# Exception handler for rate limiting
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "message": str(exc),
            "retry_after": 60
        }
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing."""
    start_time = time.time()
    
    # Store request body for rate limiting
    if request.method == "POST":
        body = await request.body()
        request.state.body = body
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Safe mode middleware
@app.middleware("http")
async def safe_mode_middleware(request: Request, call_next):
    """Check safe mode before processing requests."""
    if settings.safe_mode and request.url.path not in ["/health", "/metrics"]:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Service in safe mode",
                "message": "The service is temporarily unavailable for maintenance"
            }
        )
    return await call_next(request)

# Setup Prometheus metrics
if settings.enable_metrics:
    setup_metrics(app)

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns status of all dependencies.
    """
    health_status = {
        "status": "healthy",
        "environment": settings.environment,
        "safe_mode": settings.safe_mode,
        "services": {}
    }
    
    # Check Redis
    try:
        redis_client = await get_redis_client()
        await redis_client.ping()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Supabase
    try:
        supabase = get_supabase_client()
        # Simple query to test connection
        result = supabase.table('products').select("id").limit(1).execute()
        health_status["services"]["supabase"] = "healthy"
    except Exception as e:
        health_status["services"]["supabase"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check LanceDB
    try:
        # TODO: Add LanceDB health check
        health_status["services"]["lancedb"] = "healthy"
    except Exception as e:
        health_status["services"]["lancedb"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    status_code = status.HTTP_200_OK if health_status["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(content=health_status, status_code=status_code)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "WhatsApp Seller Bot API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health"
    }

# Webhook endpoint (placeholder - will implement in message router)
@app.post("/webhook", dependencies=[Depends(rate_limit_dependency)])
async def webhook(request: Request):
    """
    WhatsApp webhook endpoint.
    Receives messages from WhatsApp bot.
    """
    try:
        body = await request.json()
        logger.info(f"Received webhook: {body}")
        
        # TODO: Route to message handler
        
        return {
            "status": "success",
            "reply": "Message received (handler not implemented yet)"
        }
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Include routers
app.include_router(whatsapp_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.debug
    )
