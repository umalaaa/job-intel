from asgiref.sync import async_to_sync
from celery.utils.log import get_task_logger

from workers.celery_app import celery_app
from src.services.freshness import FreshnessManager
from src.services.resource_monitor import resource_monitor, TaskType
from src.db.session import AsyncSessionLocal

logger = get_task_logger(__name__)


@celery_app.task(bind=True)
def run_cleanup(self):
    logger.info("Starting cleanup task")
    try:
        stats = async_to_sync(execute_cleanup)()
        logger.info(f"Cleanup completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise self.retry(exc=e, countdown=600)


@celery_app.task(priority=10)
def emergency_disk_cleanup():
    logger.warning("Emergency disk cleanup triggered!")
    # Implementation placeholder - could trigger aggressive archiving
    pass


async def execute_cleanup():
    # Check resources - cleanup runs unless PAUSED
    monitor = resource_monitor
    if not monitor.can_run_task(TaskType.CLEANUP):
        logger.warning("Cleanup throttled")
        raise Exception("Resource limits exceeded")

    async with AsyncSessionLocal() as session:
        manager = FreshnessManager(session)
        return await manager.run_cleanup_cycle()
