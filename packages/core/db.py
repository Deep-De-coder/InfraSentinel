from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from packages.core.models.legacy import AuditEvent, StepResultLegacy


class Base(DeclarativeBase):
    pass


class StepResultRow(Base):
    __tablename__ = "step_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    change_id: Mapped[str] = mapped_column(String(128), index=True)
    step_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    evidence_refs_json: Mapped[str] = mapped_column(Text(), default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    change_id: Mapped[str] = mapped_column(String(128), index=True)
    step_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text(), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def build_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, future=True, echo=False)


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def persist_step_result(session: AsyncSession, result: StepResultLegacy) -> None:
    row = StepResultRow(
        change_id=result.change_id,
        step_id=result.step_id,
        status=result.status.value,
        notes=result.notes,
        evidence_refs_json=json.dumps([item.model_dump(mode="json") for item in result.evidence_refs]),
        created_at=result.created_at,
    )
    session.add(row)
    await session.commit()


async def persist_audit_event(session: AsyncSession, event: AuditEvent) -> None:
    row = AuditEventRow(
        event_id=event.event_id,
        change_id=event.change_id,
        step_id=event.step_id,
        event_type=event.event_type,
        payload_json=json.dumps(event.payload),
        created_at=event.created_at,
    )
    session.add(row)
    await session.commit()
