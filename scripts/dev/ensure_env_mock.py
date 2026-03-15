#!/usr/bin/env python3
"""Create infra/env/.env.mock from example with generated keys if missing."""
import re
import secrets
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "infra" / "env" / ".env.mock.example"
OUT = REPO_ROOT / "infra" / "env" / ".env.mock"

if OUT.exists():
    exit(0)

content = EXAMPLE.read_text()
content = re.sub(
    r"^INFRA_API_KEY=.*",
    f"INFRA_API_KEY={secrets.token_urlsafe(32)}",
    content,
    flags=re.MULTILINE,
)
content = re.sub(
    r"^MCP_API_KEY=.*",
    f"MCP_API_KEY={secrets.token_urlsafe(32)}",
    content,
    flags=re.MULTILINE,
)
OUT.write_text(content)
print("Created infra/env/.env.mock with generated keys")
