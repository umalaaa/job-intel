from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Boolean,
    JSON,
    UniqueConstraint,
    Float,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "external_id": self.external_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_text": self.salary_text,
            "category": self.category,
            "tags": self.tags,
            "url": self.url,
            "published_at": self.published_at,
            "fetched_at": self.fetched_at,
            "is_remote": self.is_remote,
            "is_valid": self.is_valid,
            "last_validated_at": self.last_validated_at,
        }


class ArchivedJob(Base):
    __tablename__ = "archived_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Keep original ID
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    archived_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    total_jobs: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    new_jobs: Mapped[int] = mapped_column(Integer, default=0)
