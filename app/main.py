from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, SessionLocal, engine
from app.models import Lead
from app.schemas import LeadCreate, LeadCreated

ORIGINS = [value.strip() for value in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if value.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
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


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ok", "database": "ok"}


@app.post("/api/v1/leads", response_model=LeadCreated, status_code=status.HTTP_201_CREATED, tags=["leads"])
def create_lead(payload: LeadCreate) -> LeadCreated:
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
