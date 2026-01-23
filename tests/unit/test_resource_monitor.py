import pytest
from unittest.mock import Mock, patch
from src.services.resource_monitor import ResourceMonitor, ThrottleLevel, TaskType
from src.core.config import settings


@pytest.fixture
def monitor():
    return ResourceMonitor()


@pytest.fixture
def mock_psutil():
    with patch("src.services.resource_monitor.psutil") as mock:
        # Default healthy state
        mock.cpu_percent.return_value = 50.0
        mock.virtual_memory.return_value.percent = 60.0
        mock.disk_usage.return_value.percent = 50.0  # 50% used = 50% free
        mock.disk_usage.return_value.free = 100 * 1024**3
        yield mock


def test_healthy_state(monitor, mock_psutil):
    status = monitor.get_current_status()
    assert status.is_healthy
    assert status.throttle_level == ThrottleLevel.NORMAL
    assert monitor.can_run_task(TaskType.SCRAPING)
    assert monitor.can_run_task(TaskType.CLEANUP)


def test_light_throttle(monitor, mock_psutil):
    # CPU > 75% or Disk Free < 20%
    mock_psutil.cpu_percent.return_value = 80.0

    status = monitor.get_current_status()
    assert not status.is_healthy
    assert status.throttle_level == ThrottleLevel.LIGHT
    assert monitor.can_run_task(TaskType.SCRAPING)  # Scraping allows LIGHT
    assert monitor.can_run_task(
        TaskType.CLEANUP
    )  # Cleanup allows HEAVY (so also LIGHT)
    assert monitor.can_run_task(TaskType.API)


def test_heavy_throttle(monitor, mock_psutil):
    # CPU > 85% or Disk Free < 15%
    mock_psutil.cpu_percent.return_value = 90.0

    status = monitor.get_current_status()
    assert not status.is_healthy
    assert status.throttle_level == ThrottleLevel.HEAVY
    assert not monitor.can_run_task(TaskType.SCRAPING)  # Scraping blocked
    assert monitor.can_run_task(TaskType.CLEANUP)  # Cleanup allows HEAVY
    assert monitor.can_run_task(TaskType.API)


def test_pause_throttle(monitor, mock_psutil):
    # CPU > 95% or Disk Free < 10%
    mock_psutil.disk_usage.return_value.percent = 95.0  # 5% free

    status = monitor.get_current_status()
    assert not status.is_healthy
    assert status.throttle_level == ThrottleLevel.PAUSE
    assert not monitor.can_run_task(TaskType.SCRAPING)
    assert not monitor.can_run_task(TaskType.CLEANUP)
    assert not monitor.can_run_task(TaskType.API)  # API blocked in PAUSE
    assert monitor.can_run_task(TaskType.CRITICAL)  # Critical always runs


@pytest.mark.asyncio
async def test_monitoring_callbacks(monitor, mock_psutil):
    callback = Mock()

    async def async_callback(status):
        callback(status)

    monitor.register_callback(async_callback)

    # Simulate unhealthy state
    mock_psutil.cpu_percent.return_value = 90.0

    # Run one check cycle
    monitor._running = True
    try:
        status = monitor.get_current_status()
        if status.throttle_level > ThrottleLevel.NORMAL:
            for cb in monitor._callbacks:
                await cb(status)
    finally:
        monitor._running = False

    callback.assert_called_once()
