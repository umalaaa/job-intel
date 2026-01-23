import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.scrapers.base import BaseScraper, ScraperConfig
from src.scrapers.tavily import TavilyScraper
from src.scrapers.registry import ScraperRegistry
from src.db.models import Job


@pytest.fixture
def mock_http():
    return AsyncMock()


@pytest.fixture
def mock_monitor():
    monitor = Mock()
    monitor.can_run_task.return_value = True
    return monitor


@pytest.fixture
def tavily_scraper(mock_http, mock_monitor):
    config = ScraperConfig(name="tavily", max_results=10)
    return TavilyScraper(config, mock_http, mock_monitor, api_key="test-key")


@pytest.mark.asyncio
async def test_tavily_fetch_jobs(tavily_scraper):
    # Mock response
    response_mock = Mock()
    response_mock.json.return_value = {
        "results": [
            {
                "title": "Python Developer",
                "content": "We are hiring a Python developer in Toronto. Salary $100k.",
                "url": "http://company.com/job1",
                "published_date": "2023-01-01",
            }
        ]
    }
    tavily_scraper.http.post.return_value = response_mock

    jobs = await tavily_scraper.fetch_jobs()

    assert len(jobs) == 1

    job = jobs[0]
    assert job.title == "Python Developer"
    assert job.source == "tavily"
    assert job.location == "Canada"
    assert job.salary_min == 100


@pytest.mark.asyncio
async def test_tavily_throttling(tavily_scraper):
    tavily_scraper.resource_monitor.can_run_task.return_value = False

    jobs = await tavily_scraper.fetch_jobs()

    assert len(jobs) == 0
    tavily_scraper.http.post.assert_not_called()


@pytest.mark.asyncio
async def test_registry_run_all(mock_monitor):
    registry = ScraperRegistry()

    scraper1 = Mock(spec=BaseScraper)
    scraper1.get_source_name.return_value = "s1"
    scraper1.config = Mock()
    scraper1.config.enabled = True
    scraper1.should_run.return_value = True
    scraper1.fetch_jobs = AsyncMock(return_value=[1])

    scraper2 = Mock(spec=BaseScraper)
    scraper2.get_source_name.return_value = "s2"
    scraper2.config = Mock()
    scraper2.config.enabled = True
    scraper2.should_run.return_value = False

    registry.register(scraper1)
    registry.register(scraper2)

    results = await registry.run_all()

    assert len(results) == 1
    scraper1.fetch_jobs.assert_called()
    scraper2.fetch_jobs.assert_not_called()


def test_base_scraper_should_run():
    config = ScraperConfig(name="test", enabled=True)
    monitor = Mock()
    monitor.can_run_task.return_value = True

    # Concrete implementation for abstract class
    class ConcreteScraper(BaseScraper):
        async def fetch_jobs(self):
            return []

        def get_source_name(self):
            return "test"

    scraper = ConcreteScraper(config, Mock(), monitor)

    assert scraper.should_run()

    config.enabled = False
    assert not scraper.should_run()

    config.enabled = True
    monitor.can_run_task.return_value = False
    assert not scraper.should_run()


@pytest.mark.asyncio
async def test_tavily_filtering(tavily_scraper):
    response_mock = Mock()
    response_mock.json.return_value = {
        "results": [
            {
                "title": "Blocked Job",
                "content": "Desc",
                "url": "https://linkedin.com/jobs/view/123",  # Blocked
            },
            {
                "title": "Irrelevant",
                "content": "Just a blog post",
                "url": "http://blog.com/post",
            },
        ]
    }
    tavily_scraper.http.post.return_value = response_mock

    jobs = await tavily_scraper.fetch_jobs()
    assert len(jobs) == 0


@pytest.mark.asyncio
async def test_tavily_api_key_missing(tavily_scraper):
    tavily_scraper.api_key = None
    jobs = await tavily_scraper.fetch_jobs()
    assert len(jobs) == 0
    tavily_scraper.http.post.assert_not_called()
