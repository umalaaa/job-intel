import pytest
from src.db.models import Job
from datetime import datetime


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_check(client):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_jobs_empty(client):
    response = await client.get("/api/v1/jobs/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_jobs_with_data(client, test_db_session):
    # Insert test data
    job = Job(
        source="test",
        external_id="1",
        title="Test Job",
        fetched_at=datetime.utcnow(),
        tags={},
    )
    test_db_session.add(job)
    await test_db_session.commit()

    response = await client.get("/api/v1/jobs/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Job"


@pytest.mark.asyncio
async def test_get_job_detail(client, test_db_session):
    job = Job(
        source="test",
        external_id="2",
        title="Detail Job",
        fetched_at=datetime.utcnow(),
        tags={},
    )
    test_db_session.add(job)
    await test_db_session.commit()

    response = await client.get(f"/api/v1/jobs/{job.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Detail Job"


@pytest.mark.asyncio
async def test_get_job_not_found(client):
    response = await client.get("/api/v1/jobs/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_summary(client, test_db_session):
    # Insert jobs with different locations
    jobs = [
        Job(
            source="t",
            external_id="1",
            title="J1",
            location="Remote",
            fetched_at=datetime.utcnow(),
            is_remote=True,
            tags={},
        ),
        Job(
            source="t",
            external_id="2",
            title="J2",
            location="Toronto",
            fetched_at=datetime.utcnow(),
            is_remote=False,
            tags={},
        ),
    ]
    test_db_session.add_all(jobs)
    await test_db_session.commit()

    response = await client.get("/api/v1/jobs/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["metadata"]["total_jobs"] == 2
    assert data["stats"]["remote_percentage"] == 50.0
    assert "Toronto" in data["stats"]["regions"]


@pytest.mark.asyncio
async def test_admin_resources(client):
    response = await client.get("/api/v1/admin/resources")
    assert response.status_code == 200
    assert "cpu_percent" in response.json()
