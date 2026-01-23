# Job Intel Platform

Enterprise-grade job market intelligence platform capable of automated multi-source scraping, real-time data processing, and resource-aware management.

## 🚀 Features

- **Multi-Source Scraping**: Modular architecture supporting Tavily and extensible for other sources (Indeed, LinkedIn, etc.).
- **Real-Time Updates**: WebSocket integration for live job alerts on the frontend.
- **Resource Management**: built-in monitor that throttles scraping when Disk < 15% or CPU > 85%.
- **Data Lifecycle**: Automated freshness checks, soft-deletes for expired listings, and archival for old data.
- **Modern Stack**: FastAPI (Async), Celery + Redis, SQLAlchemy + Alembic, PostgreSQL.
- **Ops-Ready**: Docker Compose for dev, Kubernetes manifests for production, Prometheus metrics.

## 🛠️ Quick Start (Docker)

The easiest way to run the full stack (API, Worker, DB, Redis) is via Docker Compose.

1. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env and set your TAVILY_API_KEY
   ```

2. **Start Services**
   ```bash
   docker-compose up --build -d
   ```

3. **Access Interfaces**
   - **Web UI**: http://localhost:8000/index.html
   - **Admin Dashboard**: http://localhost:8000/admin.html
   - **API Docs**: http://localhost:8000/docs
   - **Metrics**: http://localhost:8000/health/metrics

## 💻 Local Development

### Prerequisites
- Python 3.9+
- Redis (running locally)
- PostgreSQL (optional, defaults to SQLite for local dev)

### Installation

1. **Install Dependencies**
   ```bash
   pip install -e .
   pip install -r requirements-dev.txt
   ```

2. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

3. **Start API Server**
   ```bash
   uvicorn src.api.main:app --reload --port 8000
   ```

4. **Start Celery Worker**
   ```bash
   celery -A workers.celery_app worker --loglevel=info
   ```

5. **Start Celery Beat (Scheduler)**
   ```bash
   celery -A workers.celery_app beat --loglevel=info
   ```

## 🧪 Testing

Run the comprehensive test suite (Unit, Integration, E2E):

```bash
# Run all tests with coverage report
pytest --cov=src --cov-report=term-missing
```

Current Test Coverage: **>87%**

## 🔧 Configuration

Key settings in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `TAVILY_API_KEY` | Key for Tavily search API | Required |
| `DATABASE_URL` | DB connection string | sqlite:///./job-intel.db |
| `REDIS_URL` | Redis connection string | redis://localhost:6379/0 |
| `RESOURCE_DISK_MIN_FREE_PERCENT` | Min disk free % before throttling | 15.0 |
| `RESOURCE_CPU_MAX_PERCENT` | Max CPU % before throttling | 85.0 |
| `RETENTION_EXPIRED_DAYS` | Days before marking job as stale | 30 |

## 🏗️ Architecture

- **`src/api`**: FastAPI routes and WebSocket handlers.
- **`src/core`**: Configuration and constants.
- **`src/db`**: Database models (SQLAlchemy) and session management.
- **`src/scrapers`**: BaseScraper class and ScraperRegistry.
- **`src/services`**: Business logic (Freshness, ResourceMonitor, JobService).
- **`src/tasks`**: Celery tasks for scraping, cleanup, and monitoring.
- **`web/`**: Vanilla JS Frontend with WebSocket support.
