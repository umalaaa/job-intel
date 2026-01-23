import asyncio
from asgiref.sync import async_to_sync
from celery.utils.log import get_task_logger

from workers.celery_app import celery_app
from src.scrapers.registry import scraper_registry
from src.services.resource_monitor import resource_monitor, TaskType
from src.services.job_service import JobService
from src.db.session import AsyncSessionLocal

logger = get_task_logger(__name__)


@celery_app.task(bind=True, max_retries=3)
def scrape_source(self, source_name: str):
    logger.info(f"Starting scrape task for {source_name}")

    # Run async logic synchronously
    try:
        result = async_to_sync(run_scrape)(source_name)
        return result
    except Exception as e:
        logger.error(f"Scrape task failed: {e}")
        raise self.retry(exc=e, countdown=300)


async def run_scrape(source_name: str):
    # Check resources
    monitor = resource_monitor
    if not monitor.can_run_task(TaskType.SCRAPING):
        logger.warning("Scraping throttled due to resource limits")
        raise Exception("Resource limits exceeded")

    scraper = scraper_registry.get(source_name)
    if not scraper:
        logger.error(f"Scraper {source_name} not found")
        return {"count": 0, "status": "not_found"}

    jobs = await scraper.fetch_jobs()

    if jobs:
        async with AsyncSessionLocal() as session:
            service = JobService(session)
            count = await service.upsert_batch(jobs)
            logger.info(f"Upserted {count} jobs from {source_name}")
            return {"count": count, "source": source_name}

    return {"count": 0, "source": source_name}
