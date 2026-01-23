import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from src.services.summary_generator import SummaryGenerator
from src.db.models import Job


@pytest.fixture
def mock_db():
    session = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_generate_summary(mock_db):
    generator = SummaryGenerator(mock_db)

    # Mock jobs
    jobs = [
        Job(
            title="Python Dev",
            location="Remote",
            is_remote=True,
            tags={"skills": ["Python"]},
            fetched_at=datetime.utcnow(),
            company="A",
        ),
        Job(
            title="Java Dev",
            location="Toronto",
            is_remote=False,
            tags={"skills": ["Java"]},
            fetched_at=datetime.utcnow(),
            company="B",
        ),
    ]

    # Mock db execution
    result = Mock()
    result.scalars.return_value.all.return_value = jobs
    mock_db.execute.return_value = result

    summary = await generator.generate()

    assert summary["metadata"]["total_jobs"] == 2
    assert summary["stats"]["remote_percentage"] == 50.0
    assert summary["stats"]["regions"]["Remote"] == 1

    # Verify top skills
    skills = [s["name"] for s in summary["top_skills"]]
    assert "Python" in skills
    assert "Java" in skills

    # Verify roles table
    assert len(summary["roles"]) == 2
    assert summary["roles"][0]["title"] in ["Python Dev", "Java Dev"]


@pytest.mark.asyncio
async def test_get_rare_jobs(mock_db):
    generator = SummaryGenerator(mock_db)

    jobs = [
        Job(title="Normal", tags={}),
        Job(title="Weird", tags={"weird": ["Futurist"]}),
    ]

    rare = generator._get_rare_jobs(jobs)

    assert len(rare) == 1
    assert rare[0]["title"] == "Weird"
    assert rare[0]["tags"] == ["Futurist"]
