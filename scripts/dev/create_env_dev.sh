#!/usr/bin/env bash
# Create infra/env/.env.dev from example and write secrets interactively.
# Secrets are never echoed or logged.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

ENV_DEV="infra/env/.env.dev"
ENV_EXAMPLE="infra/env/.env.dev.example"

if [ ! -f "$ENV_EXAMPLE" ]; then
  echo "ERROR: $ENV_EXAMPLE not found. Is this the InfraSentinel repo root?"
  exit 1
fi

if [ ! -f "$ENV_DEV" ]; then
  cp "$ENV_EXAMPLE" "$ENV_DEV"
  echo "Copied $ENV_EXAMPLE -> $ENV_DEV"
else
  echo "$ENV_DEV already exists; updating keys in place."
fi

# --- ANTHROPIC_API_KEY ---
printf "Enter ANTHROPIC_API_KEY (input hidden, required): "
read -rs ANTHROPIC_KEY_INPUT
echo ""
if [ -z "$ANTHROPIC_KEY_INPUT" ]; then
  echo "ERROR: ANTHROPIC_API_KEY cannot be empty."
  exit 1
fi

# --- INFRA_API_KEY ---
printf "Enter INFRA_API_KEY (leave blank to auto-generate): "
read -r INFRA_KEY_INPUT
echo ""
if [ -z "$INFRA_KEY_INPUT" ]; then
  INFRA_KEY_INPUT="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  echo "  Generated INFRA_API_KEY."
fi

# --- MCP_API_KEY ---
printf "Enter MCP_API_KEY (leave blank to auto-generate): "
read -r MCP_KEY_INPUT
echo ""
if [ -z "$MCP_KEY_INPUT" ]; then
  MCP_KEY_INPUT="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  echo "  Generated MCP_API_KEY."
fi

# Write values using Python (avoids macOS vs GNU sed -i differences).
python3 - "$ENV_DEV" "$ANTHROPIC_KEY_INPUT" "$INFRA_KEY_INPUT" "$MCP_KEY_INPUT" <<'PYEOF'
import sys, re

env_file, anthropic_key, infra_key, mcp_key = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

def set_key(content: str, key: str, value: str) -> str:
    return re.sub(
        rf'^({re.escape(key)}=).*',
        lambda m: f'{m.group(1)}{value}',
        content,
        flags=re.MULTILINE,
    )

content = open(env_file).read()
content = set_key(content, 'ANTHROPIC_API_KEY', anthropic_key)
content = set_key(content, 'INFRA_API_KEY', infra_key)
content = set_key(content, 'MCP_API_KEY', mcp_key)
open(env_file, 'w').write(content)
PYEOF

echo ""
echo "Created $ENV_DEV (not committed)."
