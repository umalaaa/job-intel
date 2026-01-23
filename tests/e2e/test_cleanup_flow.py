import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from src.tasks.cleanup import execute_cleanup
from src.db.models import Job, ArchivedJob
from sqlalchemy import select


@pytest.mark.asyncio
@patch("src.tasks.cleanup.AsyncSessionLocal")
async def test_full_cleanup_flow(mock_session_cls, test_db_session):
    # Mock AsyncSessionLocal
    mock_session_cls.return_value.__aenter__.return_value = test_db_session
    mock_session_cls.return_value.__aexit__.return_value = None

    # Insert old job
    old_date = datetime.utcnow() - timedelta(days=60)
    job = Job(
        source="tavily",
        external_id="e2e_old",
        title="Old Job",
        url="http://example.com/old",
        fetched_at=old_date,
        tags={},
    )
    test_db_session.add(job)
    await test_db_session.commit()

    # Mock resource monitor to allow cleanup
    with patch("src.services.freshness.resource_monitor") as mock_monitor:
        mock_monitor.get_current_status.return_value.throttle_level = 0

        # Mock HTTP head to return 404 (invalid)
        with patch("src.services.freshness.httpx.AsyncClient.head") as mock_head:
            mock_head.return_value.status_code = 404

            # Execute cleanup
            stats = await execute_cleanup()

            # Verify stats
            # Since expired_days defaults to 30, this job is stale.
            # 404 means invalid -> soft delete.
            # archive_days defaults to 90. Soft deleted now. Not archived yet.
            assert stats["validated"] == 1
            assert stats["soft_deleted"] == 1
            assert stats["archived"] == 0

            # Verify DB state
            await test_db_session.refresh(job)
            assert job.deleted_at is not None
            assert not job.is_valid
