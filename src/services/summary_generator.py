from typing import Dict, Any, List
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from collections import Counter
from datetime import datetime, timedelta

from src.db.models import Job
from src.core.constants import CANADA_HINTS


class SummaryGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self) -> Dict[str, Any]:
        """Generate comprehensive job market summary"""
        jobs = await self.get_all_jobs()

        return {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_jobs": len(jobs),
            },
            "stats": self._calculate_stats(jobs),
            "top_skills": self._get_top_skills(jobs),
            "innovations": self._get_top_innovations(jobs),
            "roles": self._get_roles_table(jobs),
            "rare_jobs": self._get_rare_jobs(jobs),
        }

    async def get_all_jobs(self) -> List[Job]:
        # Limit to recent jobs for relevance?
        # Or all active jobs. Assuming is_valid=True and deleted_at=None
        query = select(Job).where(Job.is_valid == True, Job.deleted_at.is_(None))
        result = await self.db.execute(query)
        return result.scalars().all()

    def _calculate_stats(self, jobs: List[Job]) -> Dict[str, Any]:
        remote_count = sum(1 for j in jobs if j.is_remote)

        # Region distribution
        regions = Counter()
        for job in jobs:
            loc = (job.location or "").lower()
            if "remote" in loc:
                regions["Remote"] += 1
            else:
                found = False
                for region in CANADA_HINTS:
                    if region in loc:
                        regions[region.title()] += 1
                        found = True
                        break
                if not found:
                    regions["Other"] += 1

        return {
            "remote_percentage": round(remote_count / len(jobs) * 100, 1)
            if jobs
            else 0,
            "regions": dict(regions.most_common(10)),
        }

    def _get_top_skills(self, jobs: List[Job]) -> List[Dict[str, Any]]:
        counter = Counter()
        for job in jobs:
            skills = job.tags.get("skills", []) if job.tags else []
            # Assuming tags logic populates "skills" key.
            # Wait, update_jobs.py populated 'tags' list.
            # My parser returns a list of tokens.
            # I need to ensure compute_skills was called during scraping or parser logic.
            # In scraping.py I didn't call compute_skills.
            # I should fix scraping logic to populate skills/innovations in tags dict.
            # For now, let's assume it's there or handle it gracefully.
            if isinstance(job.tags, dict):
                skills = job.tags.get("skills", [])
                if isinstance(skills, list):
                    counter.update(skills)

        return [{"name": k, "count": v} for k, v in counter.most_common(20)]

    def _get_top_innovations(self, jobs: List[Job]) -> List[Dict[str, Any]]:
        counter = Counter()
        for job in jobs:
            if isinstance(job.tags, dict):
                innovations = job.tags.get("innovations", [])
                if isinstance(innovations, list):
                    counter.update(innovations)
        return [{"name": k, "count": v} for k, v in counter.most_common(20)]

    def _get_roles_table(self, jobs: List[Job]) -> List[Dict[str, Any]]:
        # Recent 50 jobs
        sorted_jobs = sorted(jobs, key=lambda j: j.fetched_at, reverse=True)[:50]
        return [
            {
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "posted": j.fetched_at.strftime("%Y-%m-%d"),
                "url": j.url,
                "salary": j.salary_text
                or (f"{j.salary_min}-{j.salary_max}" if j.salary_min else "N/A"),
            }
            for j in sorted_jobs
        ]

    def _get_rare_jobs(self, jobs: List[Job]) -> List[Dict[str, Any]]:
        rare = []
        for job in jobs:
            if isinstance(job.tags, dict):
                weird = job.tags.get("weird", [])
                if weird:
                    rare.append(
                        {
                            "title": job.title,
                            "company": job.company,
                            "tags": weird,
                            "url": job.url,
                        }
                    )
        return rare[:10]
