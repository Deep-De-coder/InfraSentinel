from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from temporalio.client import Client

from packages.core.config import Settings, get_settings
from packages.core.db import build_engine, init_db, session_factory
from packages.core.storage import EvidenceStore, LocalEvidenceStore, MinioEvidenceStore

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker | None = None


async def get_temporal_client(settings: Settings | None = None) -> Client:
    cfg = settings or get_settings()
    return await Client.connect(cfg.temporal_address, namespace=cfg.temporal_namespace)


async def get_db_session_factory(settings: Settings | None = None) -> async_sessionmaker:
    global _engine, _session_factory
    cfg = settings or get_settings()
    if _session_factory is None:
        _engine = build_engine(cfg.database_url)
        await init_db(_engine)
        _session_factory = session_factory(_engine)
    return _session_factory


def get_evidence_store(settings: Settings | None = None) -> EvidenceStore:
    cfg = settings or get_settings()
    if cfg.mode == "mock" or cfg.evidence_backend == "local":
        return LocalEvidenceStore(cfg.local_evidence_dir)
    return MinioEvidenceStore(
        endpoint=cfg.minio_endpoint,
        access_key=cfg.minio_access_key,
        secret_key=cfg.minio_secret_key,
        bucket=cfg.minio_bucket,
    )
