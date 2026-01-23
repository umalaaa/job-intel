from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db_session
from src.services.job_service import JobService
from src.services.summary_generator import SummaryGenerator
from src.db.models import Job

router = APIRouter()


@router.get("/")
async def list_jobs(
    skip: int = 0,
    limit: int = 50,
    source: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    service = JobService(db)
    # The return type should probably be a Pydantic model, but ORM object works for simple cases
    # FastAPI automatically converts ORM to JSON if configured (orm_mode in Pydantic)
    # But returning Job directly might fail if it's not a dict.
    # JobService.list_jobs returns Job objects.
    # I should define Pydantic schemas.
    # For speed, I'll return dicts or let FastAPI handle it if I define response_model.
    # Let's just return list of dicts for now.
    jobs = await service.list_jobs(skip, limit, source)
    return [job.to_dict() for job in jobs]


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db_session)):
    generator = SummaryGenerator(db)
    return await generator.generate()


@router.get("/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db_session)):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()
