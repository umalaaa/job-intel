import asyncio
from src.db.session import AsyncSessionLocal
from src.db.models import Job, Metric
from datetime import datetime


async def verify_db():
    async with AsyncSessionLocal() as session:
        # Create a test job
        job = Job(
            source="test_source",
            external_id="12345",
            title="Senior Python Developer",
            company="Tech Corp",
            fetched_at=datetime.utcnow(),
            tags={"skills": ["python", "fastapi"]},
        )
        session.add(job)

        # Create a metric
        metric = Metric(source="test_source", total_jobs=1, duration_seconds=1.5)
        session.add(metric)

        await session.commit()

        # Verify job
        job_result = await session.get(Job, 1)
        print(f"Verified Job: {job_result.title} from {job_result.company}")
        print(f"Tags: {job_result.tags}")

        # Verify metric
        metric_result = await session.get(Metric, 1)
        print(
            f"Verified Metric: {metric_result.total_jobs} jobs from {metric_result.source}"
        )


if __name__ == "__main__":
    asyncio.run(verify_db())
