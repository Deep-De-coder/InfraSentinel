"""Unit tests for NetBox client (mock httpx)."""

import pytest
from unittest.mock import patch, MagicMock

from packages.core.models.legacy import ValidationResult
from services.mcp_netbox.src.netbox_client import (
    load_approved_mapping,
    validate_observed_netbox,
    get_expected_mapping_netbox,
)


def test_load_approved_mapping_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "services.mcp_netbox.src.netbox_client._repo_root",
        lambda: tmp_path,
    )
    (tmp_path / "runtime" / "approved_mappings").mkdir(parents=True)
    result = load_approved_mapping("CHG-X")
    assert result is None


def test_load_approved_mapping_found(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "services.mcp_netbox.src.netbox_client._repo_root",
        lambda: tmp_path,
    )
    path = tmp_path / "runtime" / "approved_mappings"
    path.mkdir(parents=True)
    (path / "CHG-1.json").write_text('{"allowed_endpoints": [{"panel_id": "P1"}]}')
    result = load_approved_mapping("CHG-1")
    assert result is not None
    assert result["allowed_endpoints"][0]["panel_id"] == "P1"


@patch("services.mcp_netbox.src.netbox_client._get_device_id")
def test_validate_observed_netbox_device_not_found(mock_get_device):
    mock_get_device.return_value = None
    result = validate_observed_netbox(
        "CHG-1", "PANEL-X", "24", "TAG", "http://localhost:8001", ""
    )
    assert result.match is False
    assert "not found" in result.reason.lower()


@patch("services.mcp_netbox.src.netbox_client._get_front_port_cable")
@patch("services.mcp_netbox.src.netbox_client._get_device_id")
def test_validate_observed_netbox_match(mock_get_device, mock_get_cable):
    mock_get_device.return_value = 1
    mock_get_cable.return_value = {"label": "MDF-01-R12-P24"}
    result = validate_observed_netbox(
        "CHG-1", "PANEL-A", "24", "MDF-01-R12-P24",
        "http://localhost:8001", "token",
    )
    assert result.match is True


@patch("services.mcp_netbox.src.netbox_client._get_front_port_cable")
@patch("services.mcp_netbox.src.netbox_client._get_device_id")
def test_validate_observed_netbox_mismatch(mock_get_device, mock_get_cable):
    mock_get_device.return_value = 1
    mock_get_cable.return_value = {"label": "OTHER-TAG"}
    result = validate_observed_netbox(
        "CHG-1", "PANEL-A", "24", "MDF-01-R12-P24",
        "http://localhost:8001", "token",
    )
    assert result.match is False
    assert "OTHER-TAG" in result.reason
