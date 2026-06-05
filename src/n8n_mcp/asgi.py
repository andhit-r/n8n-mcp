"""ASGI entrypoint untuk deployment HTTP (dipakai uvicorn / Docker).

Auth sudah menempel pada objek ``mcp`` (lihat server.py), jadi modul ini hanya
membungkusnya menjadi ASGI app dengan transport Streamable HTTP — kompatibel
dengan Claude Web (claude.ai) sebagai remote MCP server.

Jalankan:
    uvicorn n8n_mcp.asgi:app --host 0.0.0.0 --port 8000
"""

import logging

from .server import mcp

logger = logging.getLogger(__name__)

app = mcp.http_app()
logger.info("ASGI app siap (Streamable HTTP)")
