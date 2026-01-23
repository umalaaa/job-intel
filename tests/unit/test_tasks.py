import pytest
from unittest.mock import Mock, patch, AsyncMock
from celery.exceptions import Retry
from src.tasks.scraping import scrape_source, run_scrape
from src.tasks.cleanup import run_cleanup, execute_cleanup
from src.tasks.monitoring import check_resources
from src.services.resource_monitor import ThrottleLevel, TaskType

# --- Wrapper Tests ---


@patch("src.tasks.scraping.async_to_sync")
@patch("src.tasks.scraping.run_scrape")
def test_scrape_source_wrapper(mock_run_scrape, mock_async_to_sync):
    mock_async_to_sync.return_value = lambda x: {"count": 10}

    result = scrape_source("tavily")
    assert result == {"count": 10}


@patch("src.tasks.cleanup.async_to_sync")
@patch("src.tasks.cleanup.execute_cleanup")
def test_run_cleanup_wrapper(mock_execute, mock_async_to_sync):
    mock_async_to_sync.return_value = lambda: {"archived": 5}

    result = run_cleanup()
    assert result == {"archived": 5}


# --- Core Logic Tests ---


@pytest.mark.asyncio
@patch("src.tasks.scraping.scraper_registry")
@patch("src.tasks.scraping.resource_monitor")
@patch("src.tasks.scraping.AsyncSessionLocal")
@patch("src.tasks.scraping.JobService")
async def test_run_scrape_success(
    mock_service_cls, mock_session, mock_monitor, mock_registry
):
    mock_monitor.can_run_task.return_value = True

    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [Mock(source="tavily")]
    mock_registry.get.return_value = scraper

    mock_service = AsyncMock()
    mock_service.upsert_batch.return_value = 1
    mock_service_cls.return_value = mock_service

    result = await run_scrape("tavily")

    assert result["count"] == 1
    mock_registry.get.assert_called_with("tavily")
    scraper.fetch_jobs.assert_awaited_once()
    mock_service.upsert_batch.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.tasks.scraping.resource_monitor")
async def test_run_scrape_throttled(mock_monitor):
    mock_monitor.can_run_task.return_value = False

    with pytest.raises(Exception, match="Resource limits exceeded"):
        await run_scrape("tavily")


@pytest.mark.asyncio
@patch("src.tasks.cleanup.resource_monitor")
@patch("src.tasks.cleanup.AsyncSessionLocal")
@patch("src.tasks.cleanup.FreshnessManager")
async def test_execute_cleanup_success(mock_manager_cls, mock_session, mock_monitor):
    mock_monitor.can_run_task.return_value = True

    mock_manager = AsyncMock()
    mock_manager.run_cleanup_cycle.return_value = {"validated": 10}
    mock_manager_cls.return_value = mock_manager

    result = await execute_cleanup()

    assert result == {"validated": 10}
    mock_manager.run_cleanup_cycle.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.tasks.cleanup.resource_monitor")
async def test_execute_cleanup_throttled(mock_monitor):
    mock_monitor.can_run_task.return_value = False

    with pytest.raises(Exception, match="Resource limits exceeded"):
        await execute_cleanup()


# --- Monitoring Tests ---


@patch("src.tasks.monitoring.resource_monitor")
@patch("src.tasks.monitoring.emergency_disk_cleanup")
@patch("src.tasks.monitoring.celery_app")
def test_check_resources_emergency(mock_celery, mock_cleanup, mock_monitor):
    status = Mock()
    status.disk_free_percent = 5.0
    status.cpu_percent = 50.0
    status.throttle_level = 0
    status.to_dict.return_value = {}
    mock_monitor.get_current_status.return_value = status

    check_resources()

    mock_cleanup.apply_async.assert_called_with(queue="critical")


@patch("src.tasks.monitoring.resource_monitor")
@patch("src.tasks.monitoring.celery_app")
def test_check_resources_throttle(mock_celery, mock_monitor):
    status = Mock()
    status.disk_free_percent = 50.0
    status.cpu_percent = 50.0
    status.throttle_level = 2  # HEAVY
    status.to_dict.return_value = {"throttle": 2}
    mock_monitor.get_current_status.return_value = status

    result = check_resources()

    assert result == {"throttle": 2}
    mock_celery.control.cancel_consumer.assert_called_with("low")


@patch("src.tasks.monitoring.resource_monitor")
@patch("src.tasks.monitoring.celery_app")
def test_check_resources_normal(mock_celery, mock_monitor):
    status = Mock()
    status.disk_free_percent = 50.0
    status.cpu_percent = 50.0
    status.throttle_level = 0  # NORMAL
    status.to_dict.return_value = {"throttle": 0}
    mock_monitor.get_current_status.return_value = status

    result = check_resources()

    assert result == {"throttle": 0}
    mock_celery.control.add_consumer.assert_called_with("low")
