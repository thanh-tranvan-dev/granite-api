import hashlib
import ipaddress
import os
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException, Request
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import RateLimitBucket

WINDOW_SECONDS = 600
MAX_REQUESTS = 5


def client_ip(request: Request) -> str:
    # Render's public edge overwrites this header. Never accept X-Forwarded-For,
    # whose leftmost value can be supplied by a visitor.
    if os.getenv("RENDER"):
        forwarded = request.headers.get("cf-connecting-ip")
        if not forwarded:
            raise HTTPException(status_code=400, detail="Missing client address")
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid client address")
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip: str) -> None:
    salt = os.environ["RATE_LIMIT_SALT"]
    now = datetime.now(timezone.utc)
    bucket = int(now.timestamp()) // WINDOW_SECONDS
    key = hashlib.sha256(f"{salt}:{ip}:{bucket}".encode()).hexdigest()
    expires_at = datetime.fromtimestamp((bucket + 1) * WINDOW_SECONDS, timezone.utc)

    try:
        with SessionLocal() as session:
            statement = insert(RateLimitBucket).values(key=key, count=1, expires_at=expires_at)
            statement = statement.on_conflict_do_update(
                index_elements=[RateLimitBucket.key],
                set_={"count": RateLimitBucket.count + 1},
                where=RateLimitBucket.count < MAX_REQUESTS,
            ).returning(RateLimitBucket.count)
            allowed = session.execute(statement).scalar_one_or_none()
            # Reap expired buckets without adding a background service.
            if bucket % 100 == 0:
                session.execute(delete(RateLimitBucket).where(RateLimitBucket.expires_at < now - timedelta(hours=1)))
            session.commit()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Tạm thời chưa thể tiếp nhận yêu cầu.") from exc

    if allowed is None:
        raise HTTPException(status_code=429, detail="Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau.", headers={"Retry-After": str(WINDOW_SECONDS)})


def verify_turnstile(token: str, ip: str) -> None:
    secret = os.environ["TURNSTILE_SECRET_KEY"]
    try:
        response = httpx.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": secret, "response": token, "remoteip": ip},
            timeout=5,
        )
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Không thể xác minh yêu cầu. Vui lòng thử lại.") from exc

    expected_hostname = os.getenv("TURNSTILE_HOSTNAME", "").strip()
    if not result.get("success") or (expected_hostname and result.get("hostname") != expected_hostname):
        raise HTTPException(status_code=422, detail="Xác minh người gửi không hợp lệ. Vui lòng thử lại.")
