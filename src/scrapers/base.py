from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
import hashlib
from dataclasses import dataclass
from src.db.models import Job
from src.services.resource_monitor import ResourceMonitor, TaskType


@dataclass
class ScraperConfig:
    name: str
    enabled: bool = True
    max_results: int = 50
    rate_limit_rpm: int = 60


class BaseScraper(ABC):
    def __init__(
        self,
        config: ScraperConfig,
        http_client: httpx.AsyncClient,
        resource_monitor: ResourceMonitor,
    ):
        self.config = config
        self.http = http_client
        self.resource_monitor = resource_monitor

    @abstractmethod
    async def fetch_jobs(self) -> List[Job]:
        """Fetch jobs from source"""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get source name identifier"""
        pass

    def should_run(self) -> bool:
        """Check if scraper should run based on config and resources"""
        return self.config.enabled and self.resource_monitor.can_run_task(
            TaskType.SCRAPING
        )
