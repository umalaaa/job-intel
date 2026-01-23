from celery.utils.log import get_task_logger

from workers.celery_app import celery_app
from src.services.resource_monitor import resource_monitor, ThrottleLevel
from src.tasks.cleanup import emergency_disk_cleanup

logger = get_task_logger(__name__)


@celery_app.task
def check_resources():
    status = resource_monitor.get_current_status()

    logger.info(
        f"Resource status: CPU={status.cpu_percent}%, DiskFree={status.disk_free_percent}%, Throttle={status.throttle_level}"
    )

    if status.disk_free_percent < 10:
        logger.warning("Low disk space! Triggering emergency cleanup")
        emergency_disk_cleanup.apply_async(queue="critical")

    if status.throttle_level >= 2:
        # Pause low-priority tasks
        celery_app.control.cancel_consumer("low")
    else:
        celery_app.control.add_consumer("low")

    return status.to_dict()
