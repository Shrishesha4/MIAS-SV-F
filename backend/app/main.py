from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import asyncio
import os

from app.config import settings
from app.database import engine
from app.api.v1.router import api_router
from app.core.middleware import limiter
from app.services.notification_scheduler import run_notification_scheduler

# Import all models so they are registered with metadata
import app.models  # noqa: F401

# Ensure uploads directory exists
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(os.path.join(UPLOADS_DIR, "photos"), exist_ok=True)
os.makedirs(os.path.join(UPLOADS_DIR, "signatures"), exist_ok=True)
os.makedirs(os.path.join(UPLOADS_DIR, "forms"), exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start notification scheduler as background task
    scheduler_task = asyncio.create_task(run_notification_scheduler())
    yield
    # Shutdown
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    await engine.dispose()


app = FastAPI(
    title="MIAS-MP API",
    description="Medical Information Application System API",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
