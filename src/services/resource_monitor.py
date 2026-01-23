import asyncio
import psutil
from enum import Enum
from dataclasses import dataclass
from typing import List, Callable, Optional, Awaitable
from datetime import datetime

from src.core.config import settings
from src.monitoring.metrics import CPU_USAGE, MEMORY_USAGE, DISK_FREE, THROTTLE_EVENTS


class ThrottleLevel(int, Enum):
    NORMAL = 0
    LIGHT = 1
    HEAVY = 2
    PAUSE = 3


class TaskType(str, Enum):
    CRITICAL = "critical"
    SCRAPING = "scraping"
    CLEANUP = "cleanup"
    API = "api"


@dataclass
class ResourceStatus:
    cpu_percent: float
    memory_percent: float
    disk_free_percent: float
    disk_free_gb: float
    is_healthy: bool
    throttle_level: ThrottleLevel
    checked_at: datetime = datetime.utcnow()

    def to_dict(self):
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_free_percent": self.disk_free_percent,
            "disk_free_gb": self.disk_free_gb,
            "is_healthy": self.is_healthy,
            "throttle_level": self.throttle_level.value,
            "checked_at": self.checked_at.isoformat(),
        }


class ResourceMonitor:
    def __init__(self):
        self.check_interval = 30  # seconds
        self._callbacks: List[Callable[[ResourceStatus], Awaitable[None]]] = []
        self._current_status: Optional[ResourceStatus] = None
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

    def get_current_status(self) -> ResourceStatus:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=None)  # Non-blocking check
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        disk_free_gb = disk.free / (1024**3)
        disk_free_pct = 100 - disk.percent

        # Determine throttle level based on thresholds
        # CRITICAL: Disk < 10% OR CPU > 95%
        if disk_free_pct < 10 or cpu_percent > 95:
            throttle_level = ThrottleLevel.PAUSE
        # HEAVY: Disk < 15% OR CPU > 85%
        elif (
            disk_free_pct < settings.RESOURCE_DISK_MIN_FREE_PERCENT
            or cpu_percent > settings.RESOURCE_CPU_MAX_PERCENT
        ):
            throttle_level = ThrottleLevel.HEAVY
        # LIGHT: Disk < 20% OR CPU > 75%
        elif disk_free_pct < 20 or cpu_percent > 75:
            throttle_level = ThrottleLevel.LIGHT
        else:
            throttle_level = ThrottleLevel.NORMAL

        CPU_USAGE.set(cpu_percent)
        MEMORY_USAGE.set(memory.percent)
        DISK_FREE.set(disk_free_pct)

        if throttle_level > ThrottleLevel.NORMAL:
            THROTTLE_EVENTS.inc()

        self._current_status = ResourceStatus(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_free_percent=disk_free_pct,
            disk_free_gb=disk_free_gb,
            is_healthy=throttle_level == ThrottleLevel.NORMAL,
            throttle_level=throttle_level,
        )

        return self._current_status

    def can_run_task(self, task_type: TaskType) -> bool:
        if not self._current_status:
            self.get_current_status()

        status = self._current_status
        if not status:  # Should not happen, but safe guard
            return True

        if task_type == TaskType.CRITICAL:
            return True

        if task_type == TaskType.API:
            # API requests only throttled in extreme cases
            return status.throttle_level < ThrottleLevel.PAUSE

        if task_type == TaskType.SCRAPING:
            return status.throttle_level <= ThrottleLevel.LIGHT

        if task_type == TaskType.CLEANUP:
            return status.throttle_level <= ThrottleLevel.HEAVY

        return status.is_healthy

    def register_callback(self, callback: Callable[[ResourceStatus], Awaitable[None]]):
        """Register async callback for resource updates"""
        self._callbacks.append(callback)

    async def start_monitoring(self):
        """Start background monitoring task"""
        if self._running:
            return

        self._running = True
        while self._running:
            try:
                status = self.get_current_status()

                # Notify callbacks if system is under load
                if status.throttle_level > ThrottleLevel.NORMAL:
                    for callback in self._callbacks:
                        await callback(status)

            except Exception as e:
                # Log error but don't crash monitor
                print(f"Error in resource monitor: {e}")

            await asyncio.sleep(self.check_interval)

    def stop_monitoring(self):
        self._running = False


# Global instance
resource_monitor = ResourceMonitor()
