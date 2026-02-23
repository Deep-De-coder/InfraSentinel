from pathlib import Path

import pytest

from services.mcp_camera.handlers import CameraHandlers


@pytest.mark.asyncio
async def test_camera_store_evidence(tmp_path: Path) -> None:
    handlers = CameraHandlers(evidence_dir=tmp_path)
    p = tmp_path / "img.txt"
    p.write_text("hello", encoding="utf-8")
    out = await handlers.store_evidence(path=str(p), metadata={"k": "v"})
    assert out.evidence_id
    assert out.metadata["k"] == "v"
