from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import structlog

from src.db.models import Job
from src.core.config import settings

logger = structlog.get_logger()


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_batch(self, jobs: List[Job]) -> int:
        if not jobs:
            return 0

        count = 0
        for job in jobs:
            try:
                # Check if exists
                query = select(Job).where(
                    Job.source == job.source, Job.external_id == job.external_id
                )
                result = await self.db.execute(query)
                existing = result.scalars().first()

                if existing:
                    # Update existing
                    existing.title = job.title
                    existing.company = job.company
                    existing.location = job.location
                    existing.salary_min = job.salary_min
                    existing.salary_max = job.salary_max
                    existing.salary_text = job.salary_text
                    existing.tags = job.tags
                    existing.url = job.url
                    existing.is_remote = job.is_remote
                    existing.fetched_at = job.fetched_at
                    # Don't update is_valid or first_seen (implied)
                else:
                    self.db.add(job)

                count += 1
            except Exception as e:
                logger.error(
                    "job_upsert_failed",
                    source=job.source,
                    ext_id=job.external_id,
                    error=str(e),
                )

        await self.db.commit()
        return count

    async def list_jobs(
        self, skip: int = 0, limit: int = 50, source: str = None
    ) -> List[Job]:
        query = select(Job).offset(skip).limit(limit)
        if source:
            query = query.where(Job.source == source)

        result = await self.db.execute(query)
        return list(result.scalars().all())
