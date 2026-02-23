from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import uuid4

import boto3

from packages.core.models import EvidenceRef


class EvidenceStore(Protocol):
    async def put_bytes(
        self, *, data: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> EvidenceRef: ...


class LocalEvidenceStore:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def put_bytes(
        self, *, data: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> EvidenceRef:
        evidence_id = str(uuid4())
        path = self.base_dir / f"{evidence_id}_{filename}"
        path.write_bytes(data)
        return EvidenceRef(
            evidence_id=evidence_id,
            uri=str(path),
            metadata={"backend": "local", **(metadata or {})},
        )


class MinioEvidenceStore:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"http://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )

    async def put_bytes(
        self, *, data: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> EvidenceRef:
        evidence_id = str(uuid4())
        object_key = f"evidence/{evidence_id}/{filename}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=data,
            Metadata=metadata or {},
        )
        return EvidenceRef(
            evidence_id=evidence_id,
            uri=f"s3://{self.bucket}/{object_key}",
            metadata={"backend": "minio", **(metadata or {})},
        )
