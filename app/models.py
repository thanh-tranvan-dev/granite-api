from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(16), nullable=False)
    service_slug: Mapped[str | None] = mapped_column(String(80))
    message: Mapped[str | None] = mapped_column(Text)
    area: Mapped[str | None] = mapped_column(String(300))
    stone_type: Mapped[str | None] = mapped_column(String(300))
    expected_size: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    __table_args__ = (Index("ix_rate_limit_buckets_expires_at", "expires_at"),)

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
