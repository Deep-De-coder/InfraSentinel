from __future__ import annotations

import base64
from pathlib import Path

from packages.core.models import EvidenceRef
from packages.core.storage import LocalEvidenceStore


class CameraHandlers:
    def __init__(self, evidence_dir: Path = Path("./.data/evidence")):
        self.store = LocalEvidenceStore(evidence_dir)

    async def capture_frame(self, source: str) -> EvidenceRef:
        path = Path(source)
        data = path.read_bytes() if path.exists() else b"mock-frame"
        return await self.store.put_bytes(data=data, filename=path.name or "capture.bin", metadata={})

    async def store_evidence(
        self,
        path: str | None = None,
        data_b64: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> EvidenceRef:
        if path:
            p = Path(path)
            data = p.read_bytes()
            filename = p.name
        elif data_b64:
            data = base64.b64decode(data_b64.encode("utf-8"))
            filename = "uploaded.bin"
        else:
            data = b"mock-evidence"
            filename = "mock.bin"
        return await self.store.put_bytes(data=data, filename=filename, metadata=metadata or {})
