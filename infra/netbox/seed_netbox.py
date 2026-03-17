#!/usr/bin/env python3
"""Idempotent NetBox seed script for InfraSentinel dev. Creates site, device type, devices, ports, cables."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

NETBOX_URL = os.environ.get("NETBOX_URL", "http://localhost:8001")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN", "")
HEADERS = {"Authorization": f"Token {NETBOX_TOKEN}", "Content-Type": "application/json"} if NETBOX_TOKEN else {"Content-Type": "application/json"}


def _get(path: str) -> dict | list:
    r = httpx.get(f"{NETBOX_URL}/api/{path}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def _post(path: str, data: dict) -> dict:
    r = httpx.post(f"{NETBOX_URL}/api/{path}", headers=HEADERS, json=data, timeout=30)
    if r.status_code in (200, 201):
        return r.json()
    if r.status_code == 400 and "already exists" in r.text.lower():
        return {}
    r.raise_for_status()
    return r.json()


def _get_or_create(path: str, data: dict, lookup_key: str = "name") -> dict:
    results = _get(path)
    for obj in results.get("results", [results] if isinstance(results, dict) else []):
        if isinstance(obj, dict) and obj.get(lookup_key) == data.get(lookup_key):
            return obj
    return _post(path, data)


def main() -> int:
    base = Path(__file__).resolve().parent
    print("Seeding NetBox...", file=sys.stderr)

    # 1. Site
    site = _get_or_create("dcim/sites/", {"name": "dc1", "slug": "dc1", "status": "active"})
    site_id = site.get("id") if isinstance(site, dict) else None
    if not site_id:
        site_resp = _get("dcim/sites/?name=dc1")
        site_id = site_resp["results"][0]["id"] if site_resp.get("results") else None
    if not site_id:
        print("Could not get site dc1", file=sys.stderr)
        return 1

    # 2. Device role (required in NetBox v4+)
    role = _get_or_create("dcim/device-roles/", {"name": "Server", "slug": "server"})
    role_id = role.get("id") if isinstance(role, dict) else None
    if not role_id:
        role_resp = _get("dcim/device-roles/?slug=server")
        role_id = role_resp["results"][0]["id"] if role_resp.get("results") else None
    if not role_id:
        print("Could not get device role", file=sys.stderr)
        return 1

    # 3. Manufacturer + Device type
    mfr = _get_or_create("dcim/manufacturers/", {"name": "Generic", "slug": "generic"})
    mfr_id = mfr.get("id") if isinstance(mfr, dict) else None
    dt = _get_or_create("dcim/device-types/", {
        "model": "Patch Panel 24",
        "slug": "patch-panel-24",
        "manufacturer": mfr_id,
    })
    dt_id = dt.get("id") if isinstance(dt, dict) else None
    if not dt_id:
        dt_resp = _get("dcim/device-types/?slug=patch-panel-24")
        dt_id = dt_resp["results"][0]["id"] if dt_resp.get("results") else None

    # 4. Front port template
    _get_or_create("dcim/front-port-templates/", {
        "device_type": dt_id,
        "name": "p24",
        "type": "8p8c",
    }, lookup_key="name")
    _get_or_create("dcim/front-port-templates/", {
        "device_type": dt_id,
        "name": "p12",
        "type": "8p8c",
    }, lookup_key="name")
    _get_or_create("dcim/front-port-templates/", {
        "device_type": dt_id,
        "name": "p23",
        "type": "8p8c",
    }, lookup_key="name")

    # 5. Devices
    dev_a = _get_or_create("dcim/devices/", {
        "name": "PANEL-A",
        "device_type": dt_id,
        "role": role_id,
        "site": site_id,
        "status": "active",
    })
    dev_pp1 = _get_or_create("dcim/devices/", {
        "name": "PP1",
        "device_type": dt_id,
        "role": role_id,
        "site": site_id,
        "status": "active",
    })
    dev_a_id = dev_a.get("id") if isinstance(dev_a, dict) else None
    dev_pp1_id = dev_pp1.get("id") if isinstance(dev_pp1, dict) else None
    if not dev_a_id:
        dev_resp = _get("dcim/devices/?name=PANEL-A")
        dev_a_id = dev_resp["results"][0]["id"] if dev_resp.get("results") else None
    if not dev_pp1_id:
        dev_resp = _get("dcim/devices/?name=PP1")
        dev_pp1_id = dev_resp["results"][0]["id"] if dev_resp.get("results") else None

    # 6. Front ports (create if not exist)
    for dev_id, dev_name, port_name in [(dev_a_id, "PANEL-A", "24"), (dev_pp1_id, "PP1", "P24"), (dev_pp1_id, "PP1", "P12"), (dev_pp1_id, "PP1", "P23")]:
        if not dev_id:
            continue
        ports = _get(f"dcim/front-ports/?device_id={dev_id}&name={port_name}")
        if not ports.get("results"):
            _post("dcim/front-ports/", {
                "device": dev_id,
                "name": port_name,
                "type": "8p8c",
            })

    # 7. Get front port IDs and create cable with label
    ports_a = _get("dcim/front-ports/?device_id=" + str(dev_a_id))
    port_a_24 = next((p for p in ports_a.get("results", []) if p.get("name") == "24"), None)
    ports_pp1 = _get("dcim/front-ports/?device_id=" + str(dev_pp1_id))
    port_pp1_24 = next((p for p in ports_pp1.get("results", []) if p.get("name") == "P24"), None)

    if port_a_24 and port_pp1_24:
        cables = _get("dcim/cables/")
        existing = next((c for c in cables.get("results", []) if c.get("label") == "MDF-01-R12-P24"), None)
        if not existing:
            _post("dcim/cables/", {
                "a_terminations": [{"object_type": "dcim.frontport", "object_id": port_a_24["id"]}],
                "b_terminations": [{"object_type": "dcim.frontport", "object_id": port_pp1_24["id"]}],
                "type": "cat6",
                "status": "connected",
                "label": "MDF-01-R12-P24",
            })

    print("NetBox seed complete.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
