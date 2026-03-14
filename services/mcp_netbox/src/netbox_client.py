"""NetBox REST API client for real DCIM/CMDB validation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import httpx

from packages.core.models.legacy import ValidationResult


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@lru_cache(maxsize=256)
def _get_device_id(base_url: str, token: str, panel_id: str) -> int | None:
    """Cache device lookup by name."""
    headers = {"Authorization": f"Token {token}"} if token else {}
    r = httpx.get(
        f"{base_url.rstrip('/')}/api/dcim/devices/",
        params={"name": panel_id},
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    return results[0]["id"] if results else None


@lru_cache(maxsize=512)
def _get_front_port_cable(base_url: str, token: str, device_id: int, port_label: str) -> dict | None:
    """Cache front port + cable lookup."""
    headers = {"Authorization": f"Token {token}"} if token else {}
    r = httpx.get(
        f"{base_url.rstrip('/')}/api/dcim/front-ports/",
        params={"device_id": device_id, "name": port_label},
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    if not results:
        for alt in ("P" + port_label, "p" + port_label):
            r2 = httpx.get(
                f"{base_url.rstrip('/')}/api/dcim/front-ports/",
                params={"device_id": device_id, "name": alt},
                headers=headers,
                timeout=10,
            )
            if r2.status_code == 200:
                res2 = r2.json().get("results", [])
                if res2:
                    results = res2
                    break
    if not results:
        return None
    port = results[0]
    cable_id = port.get("cable")
    if not cable_id:
        return None
    r3 = httpx.get(
        f"{base_url.rstrip('/')}/api/dcim/cables/{cable_id}/",
        headers=headers,
        timeout=10,
    )
    if r3.status_code != 200:
        return None
    return r3.json()


def load_approved_mapping(change_id: str) -> dict | None:
    """Load approved mapping from runtime/approved_mappings/{change_id}.json."""
    path = _repo_root() / "runtime" / "approved_mappings" / f"{change_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_expected_mapping_netbox(change_id: str, base_url: str, token: str) -> dict:
    """Get expected mapping from approved_mappings file (netbox mode)."""
    data = load_approved_mapping(change_id)
    if data:
        return data
    return {"allowed_endpoints": [], "default": {}}


def validate_observed_netbox(
    change_id: str,
    panel_id: str,
    port_label: str,
    cable_tag: str,
    base_url: str,
    token: str,
) -> ValidationResult:
    """Validate observed against NetBox: device -> front port -> cable label."""
    device_id = _get_device_id(base_url, token, panel_id)
    if not device_id:
        return ValidationResult(
            match=False,
            reason=f"Device '{panel_id}' not found in NetBox",
            confidence=0.0,
        )
    cable_data = _get_front_port_cable(base_url, token, device_id, port_label)
    if not cable_data:
        return ValidationResult(
            match=False,
            reason=f"Port '{port_label}' on {panel_id} not found or has no cable",
            confidence=0.0,
        )
    nb_label = cable_data.get("label") or ""
    if nb_label == cable_tag:
        return ValidationResult(match=True, reason="Cable label matches NetBox.", confidence=0.99)
    return ValidationResult(
        match=False,
        reason=f"Expected cable label '{nb_label}' but observed '{cable_tag}'",
        confidence=0.99,
    )
