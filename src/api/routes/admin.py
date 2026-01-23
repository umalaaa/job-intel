from fastapi import APIRouter, Depends, HTTPException
from src.services.resource_monitor import resource_monitor, ResourceStatus

# Basic auth dependency could be added here
router = APIRouter()


@router.get("/resources")
async def get_resources():
    return resource_monitor.get_current_status().to_dict()


@router.post("/scraper/trigger/{source}")
async def trigger_scraper(source: str):
    # This would call the celery task asynchronously
    from src.tasks.scraping import scrape_source

    task = scrape_source.delay(source)
    return {"status": "triggered", "task_id": str(task.id)}


@router.post("/cleanup/trigger")
async def trigger_cleanup():
    from src.tasks.cleanup import run_cleanup

    task = run_cleanup.delay()
    return {"status": "triggered", "task_id": str(task.id)}
