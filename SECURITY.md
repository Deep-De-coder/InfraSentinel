# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

Please report security vulnerabilities by opening a private security advisory on GitHub, or by emailing the maintainers directly. Do not open public issues for security vulnerabilities.

## Security Notes

- **MCP servers** (camera, cv, netbox, ticketing) use stdio transport and are intended to be spawned by a trusted parent process. **Do not expose MCP servers publicly.** They are not designed for network exposure and lack authentication.
- **API authentication**: Set `INFRA_API_KEY` and use the `X-INFRA-KEY` header for authenticated requests. In production, enable `AUTH_READS=true` to require auth for read endpoints (proofpack, steps).
- **Secrets**: Use environment variables only. Never hardcode credentials. Store secrets in your orchestrator (e.g., Docker secrets, Kubernetes secrets).
- **NetBox**: When using real NetBox, use `NETBOX_TOKEN` for API authentication. Restrict NetBox access to trusted networks.
