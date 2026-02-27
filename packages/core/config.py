from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "InfraSentinel"
    mode: str = Field(default="mock", alias="INFRASENTINEL_MODE")

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8080, alias="APP_PORT")

    temporal_address: str = Field(default="localhost:7233", alias="TEMPORAL_ADDRESS")
    temporal_namespace: str = Field(default="default", alias="TEMPORAL_NAMESPACE")
    temporal_task_queue: str = Field(default="infrasentinel-task-queue", alias="TEMPORAL_TASK_QUEUE")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./.data/infrasentinel.db", alias="DATABASE_URL"
    )

    evidence_backend: str = Field(default="local", alias="EVIDENCE_BACKEND")
    local_evidence_dir: Path = Field(default=Path("./.data/evidence"), alias="LOCAL_EVIDENCE_DIR")

    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minio", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minio123", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="infrasentinel-evidence", alias="MINIO_BUCKET")

    netbox_url: str = Field(default="http://localhost:8001", alias="NETBOX_URL")
    netbox_token: str = Field(default="", alias="NETBOX_TOKEN")
    cv_mode: str = Field(default="mock", alias="CV_MODE")
    scenario: str = Field(default="CHG-001_A", alias="SCENARIO")

    blur_min: float = Field(default=120.0, alias="QUALITY_BLUR_MIN")
    brightness_min: float = Field(default=60.0, alias="QUALITY_BRIGHTNESS_MIN")
    glare_max: float = Field(default=0.08, alias="QUALITY_GLARE_MAX")
    min_width: int = Field(default=800, alias="QUALITY_MIN_W")
    min_height: int = Field(default=600, alias="QUALITY_MIN_H")

    a2a_mode: str = Field(default="off", alias="A2A_MODE")
    a2a_mop_url: str = Field(default="http://localhost:8091", alias="A2A_MOP_URL")
    a2a_vision_url: str = Field(default="http://localhost:8092", alias="A2A_VISION_URL")
    a2a_cmdb_url: str = Field(default="http://localhost:8093", alias="A2A_CMDB_URL")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    langfuse_public_key: str | None = Field(default=None, alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str | None = Field(default=None, alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str | None = Field(default=None, alias="LANGFUSE_HOST")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
