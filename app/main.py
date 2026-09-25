from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, SessionLocal, engine
from app.models import Lead
from app.schemas import LeadCreate, LeadCreated
from app.security import check_rate_limit, client_ip, verify_turnstile

ORIGINS = [value.strip() for value in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if value.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    for key in ("RATE_LIMIT_SALT", "TURNSTILE_SECRET_KEY"):
        if not os.getenv(key):
            raise RuntimeError(f"{key} must be configured")
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Granite Workshop API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def limit_lead_body(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/api/v1/leads":
        if request.headers.get("content-length", "").isdigit() and int(request.headers["content-length"]) > 8192:
            return JSONResponse(status_code=413, content={"detail": "Yêu cầu quá lớn."})
        body = await request.body()
        if len(body) > 8192:
            return JSONResponse(status_code=413, content={"detail": "Yêu cầu quá lớn."})
    return await call_next(request)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
def ready() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ok", "database": "ok"}


@app.post("/api/v1/leads", response_model=LeadCreated, status_code=status.HTTP_201_CREATED, tags=["leads"])
def create_lead(payload: LeadCreate, request: Request) -> LeadCreated:
    ip = client_ip(request)
    check_rate_limit(ip)
    verify_turnstile(payload.turnstile_token, ip)
    phone = re.sub(r"[() .-]", "", payload.phone)
    if len(re.sub(r"\D", "", phone)) < 9:
        raise HTTPException(status_code=422, detail="Số điện thoại không hợp lệ.")

    lead = Lead(
        id=str(uuid4()),
        name=payload.name,
        phone=phone,
        service_slug=payload.service_slug,
        message=payload.message,
        area=payload.area,
        stone_type=payload.stone_type,
        expected_size=payload.expected_size,
    )
    try:
        with SessionLocal() as session:
            session.add(lead)
            session.commit()
            session.refresh(lead)
    except SQLAlchemyError as exc:
        # Do not log submitted contact details.
        raise HTTPException(status_code=503, detail="Tạm thời chưa thể lưu yêu cầu. Vui lòng thử lại.") from exc

    return LeadCreated(id=lead.id, received_at=lead.created_at)
