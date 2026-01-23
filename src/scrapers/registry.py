import asyncio
from typing import Dict, List, Optional
from src.scrapers.base import BaseScraper
import structlog

logger = structlog.get_logger()


class ScraperRegistry:
    def __init__(self):
        self._scrapers: Dict[str, BaseScraper] = {}

    def register(self, scraper: BaseScraper):
        name = scraper.get_source_name()
        if name in self._scrapers:
            logger.warning("scraper_already_registered", name=name)
        self._scrapers[name] = scraper
        logger.info("scraper_registered", name=name)

    def get(self, name: str) -> Optional[BaseScraper]:
        return self._scrapers.get(name)

    def get_all_enabled(self) -> List[BaseScraper]:
        return [s for s in self._scrapers.values() if s.config.enabled]

    async def run_all(self) -> List[object]:
        """Run all enabled scrapers concurrently"""
        tasks = []
        for scraper in self.get_all_enabled():
            if scraper.should_run():
                tasks.append(scraper.fetch_jobs())
            else:
                logger.info("scraper_skipped", name=scraper.get_source_name())

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for res in results:
            if isinstance(res, Exception):
                logger.error("scraper_run_failed", error=str(res))
            elif isinstance(res, list):
                all_jobs.extend(res)

        return all_jobs


# Global registry instance
scraper_registry = ScraperRegistry()
