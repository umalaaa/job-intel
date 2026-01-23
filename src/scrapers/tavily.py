import json
import asyncio
import datetime
import structlog
from typing import List, Dict, Optional
import httpx

from src.core.config import settings
from src.core.constants import (
    SOURCE_TAVILY,
    BLOCKLIST_DOMAINS,
    WHITELIST_DOMAINS,
    JOB_URL_KEYWORDS,
    CANADA_HINTS,
    TAVILY_DEFAULT_QUERIES,
)
from src.db.models import Job
from src.services.parsers import (
    parse_salary_range,
    parse_title_company,
    build_external_id,
    tokenize,
    infer_location,
)


from src.scrapers.base import BaseScraper, ScraperConfig

logger = structlog.get_logger()


class TavilyScraper(BaseScraper):
    def __init__(
        self,
        config: ScraperConfig,
        http_client: httpx.AsyncClient,
        resource_monitor,
        api_key: str,
    ):
        super().__init__(config, http_client, resource_monitor)
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/search"
        self.queries = [q.strip() for q in TAVILY_DEFAULT_QUERIES.split(";") if q]

    def get_source_name(self) -> str:
        return SOURCE_TAVILY

    async def fetch_jobs(self) -> List[Job]:
        if not self.api_key:
            logger.error("tavily_api_key_missing")
            return []

        jobs: List[Job] = []
        seen: set[str] = set()

        for query in self.queries:
            if not self.should_run():
                logger.warning("scraper_stopped_throttling", source=SOURCE_TAVILY)
                break

            try:
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": self.config.max_results,
                    "search_depth": settings.TAVILY_SEARCH_DEPTH,
                    "include_answer": False,
                    "include_raw_content": False,
                }

                response = await self.http.post(
                    self.base_url, json=payload, timeout=45.0
                )
                response.raise_for_status()
                data = response.json()

                for result in data.get("results", []):
                    job = self._process_result(result, query)
                    if job and job.external_id not in seen:
                        seen.add(job.external_id)
                        jobs.append(job)

                # Respect rate limits
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error("tavily_fetch_error", query=query, error=str(e))

        return jobs

    def _process_result(self, result: Dict, query: str) -> Optional[Job]:
        title_text = (result.get("title") or "").strip()
        content = (result.get("content") or "").strip()
        url = (result.get("url") or "").strip()

        if not title_text and not content:
            return None

        if url:
            if self._is_blocklisted_url(url):
                return None
            if not self._is_whitelisted_url(url) and not self._has_job_url_keyword(url):
                return None

        if not self._is_job_result(title_text, content):
            return None

        combined_text = f"{title_text} {content} {url}".lower()
        if "remote" not in combined_text and not any(
            h in combined_text for h in CANADA_HINTS
        ):
            return None

        title, company = parse_title_company(title_text)
        salary_min, salary_max, salary_text = parse_salary_range(
            f"{title_text} {content}"
        )

        if salary_text and len(salary_text) > 200:
            salary_text = None

        tags = tokenize(f"{title_text} {content}")
        ext_id = build_external_id(url or title_text, title)

        return Job(
            source=SOURCE_TAVILY,
            external_id=ext_id,
            title=title,
            company=company or "Unknown",
            location=self._infer_location(f"{title_text} {content}", query),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_text=salary_text,
            category="Tavily Search",
            tags={"raw": tags},
            url=url,
            published_at=None,
            fetched_at=datetime.datetime.utcnow(),
            is_remote="remote" in (title_text + " " + content).lower(),
        )

    def _is_blocklisted_url(self, url: str) -> bool:
        lowered = url.lower()
        return any(d in lowered for d in BLOCKLIST_DOMAINS)

    def _is_whitelisted_url(self, url: str) -> bool:
        lowered = url.lower()
        return any(d in lowered for d in WHITELIST_DOMAINS)

    def _has_job_url_keyword(self, url: str) -> bool:
        lowered = url.lower()
        return any(k in lowered for k in JOB_URL_KEYWORDS)

    def _is_job_result(self, title: str, content: str) -> bool:
        text = f"{title} {content}".lower()
        keywords = ["job", "jobs", "hiring", "career", "careers", "position", "opening"]
        return any(k in text for k in keywords)

    def _infer_location(self, text: str, query: str) -> str:
        lowered = f"{text} {query}".lower()
        if "remote" in lowered:
            return "Remote"
        if "canada" in lowered:
            return "Canada"
        return "Canada"
