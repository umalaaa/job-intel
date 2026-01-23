import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from src.services.freshness import FreshnessManager, RetentionPolicy
from src.db.models import Job, ArchivedJob


@pytest.fixture
def mock_db():
    session = AsyncMock()
    # Mock execute result
    result = Mock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    # db.add is synchronous
    session.add = Mock()
    return session


@pytest.fixture
def mock_http():
    client = AsyncMock()
    return client


@pytest.fixture
def manager(mock_db, mock_http):
    return FreshnessManager(mock_db, mock_http)


@pytest.mark.asyncio
async def test_check_job_validity_valid(manager):
    job = Job(id=1, url="http://example.com/job")
    manager.http.head.return_value.status_code = 200

    is_valid = await manager.check_job_validity(job)

    assert is_valid
    assert job.is_valid
    assert job.last_validated_at is not None


@pytest.mark.asyncio
async def test_check_job_validity_invalid(manager):
    job = Job(id=1, url="http://example.com/404")
    manager.http.head.return_value.status_code = 404

    is_valid = await manager.check_job_validity(job)

    assert not is_valid
    assert not job.is_valid
    assert job.last_validated_at is not None


@pytest.mark.asyncio
async def test_check_job_validity_error(manager):
    job = Job(id=1, url="http://example.com/error")
    manager.http.head.side_effect = Exception("Network error")

    is_valid = await manager.check_job_validity(job)

    # Should assume valid on error to prevent accidental deletion
    assert is_valid
    # job.is_valid is not updated on error


@pytest.mark.asyncio
async def test_check_job_validity_no_url(manager):
    job = Job(id=1, url=None)

    is_valid = await manager.check_job_validity(job)

    assert is_valid
    manager.http.head.assert_not_called()


@pytest.mark.asyncio
async def test_soft_delete_job(manager):
    job = Job(id=1)
    await manager.soft_delete_job(job)

    assert job.deleted_at is not None
    manager.db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_archive_job(manager):
    job = Job(
        id=1,
        source="test",
        external_id="123",
        title="Dev",
        fetched_at=datetime.utcnow(),
    )

    await manager.archive_job(job)

    # Verify ArchivedJob was added
    assert manager.db.add.called
    added_obj = manager.db.add.call_args[0][0]
    assert isinstance(added_obj, ArchivedJob)
    assert added_obj.id == 1
    assert added_obj.title == "Dev"
    assert added_obj.archived_at is not None

    # Verify original job was deleted
    manager.db.delete.assert_awaited_once_with(job)
    manager.db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_stale_jobs(manager):
    jobs = [Job(id=1), Job(id=2)]
    manager.db.execute.return_value.scalars.return_value.all.return_value = jobs

    result = await manager.get_stale_jobs()

    assert len(result) == 2
    assert manager.db.execute.called


@pytest.mark.asyncio
async def test_run_cleanup_cycle_full(manager):
    # Setup stale jobs
    job1 = Job(id=1, url="http://ok.com")
    job2 = Job(id=2, url="http://bad.com")

    manager.get_stale_jobs = AsyncMock(return_value=[job1, job2])
    manager.check_job_validity = AsyncMock(side_effect=[True, False])
    manager.soft_delete_job = AsyncMock()

    # Setup archive jobs
    job3 = Job(id=3, deleted_at=datetime.utcnow())
    manager.db.execute.return_value.scalars.return_value.all.return_value = [job3]
    manager.archive_job = AsyncMock()

    with patch("src.services.freshness.resource_monitor") as mock_monitor:
        mock_monitor.get_current_status.return_value.throttle_level = 0

        stats = await manager.run_cleanup_cycle()

        assert stats["validated"] == 2
        assert stats["soft_deleted"] == 1
        assert stats["archived"] == 1

        manager.soft_delete_job.assert_awaited_once_with(job2)
        manager.archive_job.assert_awaited_once_with(job3)


@pytest.mark.asyncio
async def test_run_cleanup_cycle_throttled(manager):
    with patch("src.services.freshness.resource_monitor") as mock_monitor:
        mock_monitor.get_current_status.return_value.throttle_level = 2  # HEAVY

        stats = await manager.run_cleanup_cycle()

        assert stats == {"validated": 0, "soft_deleted": 0, "archived": 0}
        # Should not fetch jobs
        manager.db.execute.assert_not_called()
