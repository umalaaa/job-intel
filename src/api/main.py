from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import structlog
import os

from src.core.config import settings
from src.api.routes import jobs, health, admin
from src.api.websockets import updates
from src.services.resource_monitor import resource_monitor

logger = structlog.get_logger()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise Job Market Intelligence API",
    version="2.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (Frontend)
# Check if web directory exists (it should in Docker and local)
if os.path.exists("web"):
    app.mount("/static", StaticFiles(directory="web"), name="static")
    # Serve index.html at root? Or just let user go to /static/index.html?
    # Usually better to serve / -> index.html
    # But StaticFiles at root captures everything.
    # Let's mount at root but excluding API routes.
    # FastAPI matches routes in order. API routes are included below.
    # So we should include routers FIRST, then mount static files at root.
    pass


@app.on_event("startup")
async def startup_event():
    logger.info("application_startup")
    # Start resource monitor in background
    asyncio.create_task(resource_monitor.start_monitoring())


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("application_shutdown")
    resource_monitor.stop_monitoring()


# Include Routers
app.include_router(jobs.router, prefix=f"{settings.API_V1_STR}/jobs", tags=["jobs"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["admin"])
app.include_router(updates.router, tags=["websockets"])

# Mount static files at root (catch-all)
if os.path.exists("web"):
    app.mount("/", StaticFiles(directory="web", html=True), name="static")
