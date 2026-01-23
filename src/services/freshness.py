import httpx
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.core.config import settings
from src.db.models import Job, ArchivedJob
from src.services.resource_monitor import resource_monitor, ThrottleLevel

logger = structlog.get_logger()


class RetentionPolicy:
    def __init__(
        self,
        expired_days: int = settings.RETENTION_EXPIRED_DAYS,
        archive_days: int = settings.RETENTION_ARCHIVE_DAYS,
    ):
        self.expired_days = expired_days
        self.archive_days = archive_days


class FreshnessManager:
    def __init__(
        self,
        db: AsyncSession,
        http_client: Optional[httpx.AsyncClient] = None,
        policy: Optional[RetentionPolicy] = None,
    ):
        self.db = db
        self.http = http_client or httpx.AsyncClient(
            timeout=10.0, follow_redirects=True
        )
        self.policy = policy or RetentionPolicy()

    async def check_job_validity(self, job: Job) -> bool:
        """Check if job URL is still valid (not 404/410/403)"""
        if not job.url:
            return True  # Assume valid if no URL

        try:
            # We use HEAD to save bandwidth
            response = await self.http.head(job.url)
            is_valid = response.status_code not in [404, 410, 403]

            job.is_valid = is_valid
            job.last_validated_at = datetime.utcnow()

            return is_valid
        except Exception as e:
            logger.warning(
                "validity_check_failed", job_id=job.id, url=job.url, error=str(e)
            )
            # Don't mark invalid on transient network errors
            return True

    async def get_stale_jobs(self) -> List[Job]:
        """Get jobs that haven't been validated recently"""
        cutoff = datetime.utcnow() - timedelta(days=self.policy.expired_days)

        query = (
            select(Job)
            .where(Job.fetched_at < cutoff, Job.deleted_at.is_(None))
            .limit(100)
        )  # Process in batches

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def soft_delete_job(self, job: Job) -> None:
        """Mark job as deleted"""
        job.deleted_at = datetime.utcnow()
        await self.db.commit()
        logger.info("job_soft_deleted", job_id=job.id)

    async def archive_job(self, job: Job) -> None:
        """Move job to archive table and delete from main table"""
        # Create archive record
        job_dict = job.to_dict()
        del job_dict["id"]  # Let DB assign new ID or copy if needed.
        # Models usually define ID as PK. ArchivedJob has its own ID.
        # But wait, logic says we should preserve ID if possible or just archive data.
        # Let's check model definition. ArchivedJob has id: Mapped[int] = mapped_column(Integer, primary_key=True)
        # If we want to keep original ID, we should set it.

        archived = ArchivedJob(**job_dict, archived_at=datetime.utcnow())
        # Explicitly set ID if we want to preserve it, assuming no conflict
        archived.id = job.id

        self.db.add(archived)
        await self.db.delete(job)
        await self.db.commit()
        logger.info("job_archived", job_id=job.id)

    async def run_cleanup_cycle(self) -> Dict[str, int]:
        """Run full cleanup cycle: validate -> soft-delete -> archive"""
        stats = {"validated": 0, "soft_deleted": 0, "archived": 0}

        # Check resource status first
        status = resource_monitor.get_current_status()
        if status.throttle_level >= ThrottleLevel.HEAVY:
            logger.warning("cleanup_skipped_throttled", level=status.throttle_level)
            return stats

        # 1. Soft delete expired/invalid jobs
        stale_jobs = await self.get_stale_jobs()
        for job in stale_jobs:
            is_valid = await self.check_job_validity(job)
            stats["validated"] += 1

            if not is_valid:
                await self.soft_delete_job(job)
                stats["soft_deleted"] += 1

        # 2. Archive old soft-deleted jobs
        archive_cutoff = datetime.utcnow() - timedelta(days=self.policy.archive_days)
        query = select(Job).where(Job.deleted_at < archive_cutoff).limit(100)

        result = await self.db.execute(query)
        to_archive = result.scalars().all()

        for job in to_archive:
            await self.archive_job(job)
            stats["archived"] += 1

        return stats
