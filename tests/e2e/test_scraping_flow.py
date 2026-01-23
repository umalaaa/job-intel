import pytest
from unittest.mock import Mock, patch
from src.tasks.scraping import run_scrape
from src.db.models import Job
from sqlalchemy import select


@pytest.mark.asyncio
@patch("src.scrapers.tavily.TavilyScraper.fetch_jobs")
@patch("src.tasks.scraping.AsyncSessionLocal")
async def test_full_scraping_flow(mock_session_cls, mock_fetch, test_db_session):
    # Setup scraper registry
    from src.scrapers.registry import scraper_registry
    from src.scrapers.tavily import TavilyScraper
    from src.scrapers.base import ScraperConfig

    # Register mock scraper
    config = ScraperConfig(name="tavily", enabled=True)
    scraper = TavilyScraper(config, Mock(), Mock(), api_key="key")
    scraper_registry.register(scraper)

    # Mock AsyncSessionLocal to return test session
    # AsyncSessionLocal() returns a session. It is used as context manager.
    mock_session_cls.return_value.__aenter__.return_value = test_db_session
    mock_session_cls.return_value.__aexit__.return_value = None

    # Mock scraper output
    job = Job(
        source="tavily",
        external_id="e2e_1",
        title="E2E Job",
        url="http://example.com/e2e",
        fetched_at=None,  # Will be set by scraper usually, but here we return Job objects
    )
    # Scrapers return Job objects
    mock_fetch.return_value = [job]

    # Run scraping task
    result = await run_scrape("tavily")

    assert result["count"] == 1

    # Verify DB
    result = await test_db_session.execute(
        select(Job).where(Job.external_id == "e2e_1")
    )
    saved_job = result.scalars().first()
    assert saved_job is not None
    assert saved_job.title == "E2E Job"
