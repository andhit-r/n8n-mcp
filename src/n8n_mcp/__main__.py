"""Entrypoint server n8n MCP.

Pilih transport via environment (config.py):
  - ``stdio`` (default) → MCP client lokal (Claude Desktop / Claude Code stdio).
  - ``http`` / ``sse``  → service / remote (Claude Code remote, Claude Web).

Dijalankan via ``python -m n8n_mcp`` atau entrypoint script ``n8n-mcp``
(lihat pyproject.toml). Untuk deployment cloud lewat uvicorn, gunakan
``n8n_mcp.asgi:app`` (lihat Dockerfile).
"""

from __future__ import annotations

from .config import settings
from .server import mcp


def main() -> None:
    """Jalankan server dengan transport sesuai konfigurasi."""
    if settings.mcp_transport == "stdio":
        mcp.run()
    else:
        mcp.run(
            transport=settings.mcp_transport,
            host=settings.mcp_host,
            port=settings.mcp_port,
        )


if __name__ == "__main__":
    main()
