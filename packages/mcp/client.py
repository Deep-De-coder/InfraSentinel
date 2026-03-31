from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from packages.cv.schema import CableTagResult, PortLabelResult
from packages.core.models.change import ChangeRequest
from packages.core.models.legacy import EvidenceRef, ExpectedMapping, ValidationResult


ToolFn = Callable[..., Awaitable[Any]]


@dataclass
class MCPToolRouter:
    """Minimal MCP client wrapper abstraction.

    In mock/in-process mode we inject direct async callables from service handlers
    or adapter instances.  Remote MCP transport (stdio/HTTP) can evolve behind this
    contract without changing callers.

    Use MCPToolRouter.from_settings() to build from app settings.
    Use MCPToolRouter.from_adapters(...) to build from explicit adapter instances.
    """

    camera_capture_frame: ToolFn
    camera_store_evidence: ToolFn
    cv_read_port_label: ToolFn
    cv_read_cable_tag: ToolFn
    netbox_get_expected_mapping: ToolFn
    netbox_validate_observed: ToolFn
    ticketing_get_change: ToolFn
    ticketing_post_step_result: ToolFn
    ticketing_request_approval: ToolFn

    # --- convenience passthrough methods ---

    async def capture_frame(self, source: str) -> EvidenceRef:
        return await self.camera_capture_frame(source=source)

    async def store_evidence(
        self, path: str | None = None, data_b64: str | None = None, metadata: dict | None = None
    ) -> EvidenceRef:
        return await self.camera_store_evidence(path=path, data_b64=data_b64, metadata=metadata or {})

    async def read_port_label(
        self, evidence_id: str, change_id: str = "", scenario: str | None = None
    ) -> PortLabelResult:
        return await self.cv_read_port_label(
            evidence_id=evidence_id, change_id=change_id, scenario=scenario
        )

    async def read_cable_tag(
        self, evidence_id: str, change_id: str = "", scenario: str | None = None
    ) -> CableTagResult:
        return await self.cv_read_cable_tag(
            evidence_id=evidence_id, change_id=change_id, scenario=scenario
        )

    async def get_expected_mapping(self, change_id: str) -> dict:
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

    async def request_approval(
        self,
        change_id: str,
        step_id: str,
        reason: str,
        evidence_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return await self.ticketing_request_approval(
            change_id=change_id,
            step_id=step_id,
            reason=reason,
            evidence_ids=evidence_ids,
        )

    # --- factories ---

    @classmethod
    def from_adapters(
        cls,
        camera_adapter: Any,
        cv_adapter: Any,
        netbox_adapter: Any,
        ticketing_adapter: Any,
    ) -> "MCPToolRouter":
        """Build a router from adapter instances.

        Each adapter exposes MCPToolRouter-compatible async methods that delegate
        to the appropriate mock or real backend.
        """
        return cls(
            camera_capture_frame=camera_adapter.capture_frame,
            camera_store_evidence=camera_adapter.store_evidence,
            cv_read_port_label=cv_adapter.read_port_label,
            cv_read_cable_tag=cv_adapter.read_cable_tag,
            netbox_get_expected_mapping=netbox_adapter.get_expected_mapping,
            netbox_validate_observed=netbox_adapter.validate_observed,
            ticketing_get_change=ticketing_adapter.get_change,
            ticketing_post_step_result=ticketing_adapter.post_step_result,
            ticketing_request_approval=ticketing_adapter.request_approval,
        )

    @classmethod
    def from_settings(cls) -> "MCPToolRouter":
        """Build a router from application settings.

        INFRA_MCP_TRANSPORT=in-process (default) → adapters called directly in-process.
        Remote transports (stdio/HTTP) are future work.
        """
        from packages.core.config import get_settings
        from services.mcp_camera.adapter import CameraAdapter
        from services.mcp_cv.adapter import CVAdapter
        from services.mcp_netbox.adapter import NetBoxAdapter
        from services.mcp_ticketing.adapter import TicketingAdapter

        settings = get_settings()
        transport = settings.infra_mcp_transport.lower()

        if transport == "in-process":
            return cls.from_adapters(
                camera_adapter=CameraAdapter(),
                cv_adapter=CVAdapter(cv_mode=settings.cv_mode, scenario=settings.scenario),
                netbox_adapter=NetBoxAdapter(netbox_mode=settings.netbox_mode),
                ticketing_adapter=TicketingAdapter(),
            )

        raise ValueError(
            f"Unsupported INFRA_MCP_TRANSPORT={transport!r}. "
            "Only 'in-process' is currently supported."
        )
