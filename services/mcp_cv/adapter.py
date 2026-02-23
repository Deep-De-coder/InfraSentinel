from __future__ import annotations


class CVAdapter:
    """Real CV implementation skeleton."""

    async def read_port_label(self, evidence_id: str) -> dict:
        raise NotImplementedError("Integrate OCR/vision inference backend here.")

    async def read_cable_tag(self, evidence_id: str) -> dict:
        raise NotImplementedError("Integrate cable tag parser backend here.")
