import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from src.services.job_service import JobService
from src.db.models import Job


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.add = Mock()  # Synchronous method
    return session


@pytest.fixture
def service(mock_db):
    return JobService(mock_db)


@pytest.mark.asyncio
async def test_upsert_batch_empty(service):
    count = await service.upsert_batch([])
    assert count == 0
    service.db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_upsert_batch_new(service):
    job = Job(source="test", external_id="1", title="New Job")

    # Mock execute to return empty (no existing job)
    result = Mock()
    result.scalars.return_value.first.return_value = None
    service.db.execute.return_value = result

    count = await service.upsert_batch([job])

    assert count == 1
    service.db.add.assert_called_with(job)
    service.db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_batch_existing(service):
    job = Job(source="test", external_id="1", title="Updated Job")

    # Mock existing job
    existing = Job(source="test", external_id="1", title="Old Job")
    result = Mock()
    result.scalars.return_value.first.return_value = existing
    service.db.execute.return_value = result

    count = await service.upsert_batch([job])

    assert count == 1
    assert existing.title == "Updated Job"  # Updated in place
    service.db.add.assert_not_called()
    service.db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_batch_error(service):
    job = Job(source="test", external_id="1")
    service.db.execute.side_effect = Exception("DB Error")

    count = await service.upsert_batch([job])

    assert count == 0
    service.db.commit.assert_awaited_once()  # Commits whatever succeeded (none here)


@pytest.mark.asyncio
async def test_list_jobs(service):
    result = Mock()
    result.scalars.return_value.all.return_value = [Job(id=1)]
    service.db.execute.return_value = result

    jobs = await service.list_jobs(skip=0, limit=10, source="tavily")

    assert len(jobs) == 1
    service.db.execute.assert_awaited_once()
