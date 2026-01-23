from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.db.session import get_db_session
from src.services.resource_monitor import resource_monitor, ResourceStatus
from src.monitoring.metrics import CPU_USAGE, MEMORY_USAGE, DISK_FREE

router = APIRouter()


@router.get("/live")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db_session)):
    """Kubernetes readiness probe"""
    try:
        # Check DB connection
        await db.execute(text("SELECT 1"))
        # Check resource monitor status (optional, maybe don't fail ready if resources low)
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {str(e)}")


@router.get("/metrics")
async def metrics() -> dict:
    """Expose resource metrics"""
    status = resource_monitor.get_current_status()

    # Ensure Prometheus metrics are up to date
    # (ResourceMonitor updates them on get_current_status)

    return status.to_dict()
