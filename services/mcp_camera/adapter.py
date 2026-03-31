"""Camera adapter — captures image bytes from file path, base64, or mock samples."""

from __future__ import annotations

import base64
import os
from pathlib import Path


class CameraAdapter:
    """Unified camera/evidence adapter.

    CAMERA_MODE=mock  → loads from samples/images/ (default fixture image)
    CAMERA_MODE=file  → reads from the path given by CAMERA_FILE_PATH or argument
    """

    def __init__(self, camera_mode: str | None = None) -> None:
        self.camera_mode = (camera_mode or os.getenv("CAMERA_MODE", "mock")).lower()

    # --- high-level domain API ---

    async def capture_image(self, source: str | None = None) -> bytes:
        """Capture or load raw image bytes.

        source:  file path, or None to use CAMERA_FILE_PATH / default fixture.
        """
        if self.camera_mode == "file" or (
            self.camera_mode == "mock" and source and Path(source).exists()
        ):
            path = Path(source) if source else Path(os.getenv("CAMERA_FILE_PATH", ""))
            if path.exists():
                return path.read_bytes()

        b64 = os.getenv("CAMERA_IMAGE_B64")
        if b64:
            return base64.b64decode(b64.encode("utf-8"))

        # fall back to default fixture sample
        default = _default_sample_path()
        if default.exists():
            return default.read_bytes()
        return b"mock-frame"

    # --- MCPToolRouter-compatible async methods ---

    async def capture_frame(self, source: str) -> object:
        from services.mcp_camera.handlers import CameraHandlers

        handlers = CameraHandlers()
        return await handlers.capture_frame(source)

    async def store_evidence(
        self,
        path: str | None = None,
        data_b64: str | None = None,
        metadata: dict | None = None,
    ) -> object:
        from services.mcp_camera.handlers import CameraHandlers

        handlers = CameraHandlers()
        return await handlers.store_evidence(path=path, data_b64=data_b64, metadata=metadata)


def _default_sample_path() -> Path:
    return Path(__file__).resolve().parents[2] / "samples" / "images" / "default.png"
