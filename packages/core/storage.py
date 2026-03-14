from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import boto3

from packages.core.models import EvidenceRef


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _content_type(filename: str) -> str:
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext, "application/octet-stream")


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
        sha = _sha256(data)
        return EvidenceRef(
            evidence_id=evidence_id,
            uri=str(path),
            metadata={"backend": "local", "sha256": sha, **(metadata or {})},
        )


class MinioEvidenceStore:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.bucket = bucket
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.client = boto3.client(
            "s3",
            endpoint_url=f"http://{endpoint}",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )
        try:
            self.client.head_bucket(Bucket=bucket)
        except Exception:
            self.client.create_bucket(Bucket=bucket)

    async def put_bytes(
        self, *, data: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> EvidenceRef:
        evidence_id = str(uuid4())
        change_id = (metadata or {}).get("change_id", "unknown")
        ext = filename.split(".")[-1] if "." in filename else "jpg"
        object_key = f"evidence/{change_id}/{evidence_id}.{ext}"
        sha = _sha256(data)
        content_type = _content_type(filename)
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=data,
            ContentType=content_type,
            Metadata={"sha256": sha, "retention": "90d", **(metadata or {})},
        )
        uri = f"s3://{self.bucket}/{object_key}"
        return EvidenceRef(
            evidence_id=evidence_id,
            uri=uri,
            metadata={
                "backend": "minio",
                "sha256": sha,
                "object_key": object_key,
                "retention": "90d",
                **(metadata or {})},
        )

    def generate_presigned_url(self, object_key: str, expires_in: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )
