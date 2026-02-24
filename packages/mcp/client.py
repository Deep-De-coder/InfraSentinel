from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from packages.cv.schema import CableTagResult, PortLabelResult
from packages.core.models import (
    ChangeRequest,
    EvidenceRef,
    ExpectedMapping,
    ValidationResult,
)


ToolFn = Callable[..., Awaitable[Any]]


@dataclass
class MCPToolRouter:
    """Minimal MCP client wrapper abstraction.

    In mock mode we inject direct async callables from service handlers.
    Production stdio/http transport wiring can evolve behind this contract.
    """

    camera_capture_frame: ToolFn
    camera_store_evidence: ToolFn
    cv_read_port_label: ToolFn
    cv_read_cable_tag: ToolFn
    netbox_get_expected_mapping: ToolFn
    netbox_validate_observed: ToolFn
    ticketing_get_change: ToolFn
    ticketing_post_step_result: ToolFn

    async def capture_frame(self, source: str) -> EvidenceRef:
        return await self.camera_capture_frame(source=source)

    async def store_evidence(
        self, path: str | None = None, data_b64: str | None = None, metadata: dict | None = None
    ) -> EvidenceRef:
        return await self.camera_store_evidence(path=path, data_b64=data_b64, metadata=metadata or {})

    async def read_port_label(self, evidence_id: str) -> PortLabelResult:
        return await self.cv_read_port_label(evidence_id=evidence_id)

    async def read_cable_tag(self, evidence_id: str) -> CableTagResult:
        return await self.cv_read_cable_tag(evidence_id=evidence_id)

    async def get_expected_mapping(self, change_id: str) -> ExpectedMapping:
        return await self.netbox_get_expected_mapping(change_id=change_id)

    async def validate_observed(
        self, change_id: str, panel_id: str, port_label: str, cable_tag: str
    ) -> ValidationResult:
        return await self.netbox_validate_observed(
            change_id=change_id,
            panel_id=panel_id,
            port_label=port_label,
            cable_tag=cable_tag,
        )

    async def get_change(self, change_id: str) -> ChangeRequest:
        return await self.ticketing_get_change(change_id=change_id)

    async def post_step_result(
        self,
        change_id: str,
        step_id: str,
        status: str,
        evidence_refs: list[EvidenceRef],
        notes: str | None,
    ) -> dict[str, Any]:
        return await self.ticketing_post_step_result(
            change_id=change_id,
            step_id=step_id,
            status=status,
            evidence_refs=evidence_refs,
            notes=notes,
        )
