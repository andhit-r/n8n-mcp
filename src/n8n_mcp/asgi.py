"""ASGI entrypoint untuk deployment HTTP (dipakai uvicorn / Docker).

Auth sudah menempel pada objek ``mcp`` (lihat server.py), jadi modul ini hanya
membungkusnya menjadi ASGI app dengan transport Streamable HTTP — kompatibel
dengan Claude Web (claude.ai) sebagai remote MCP server.

Jalankan:
    uvicorn n8n_mcp.asgi:app --host 0.0.0.0 --port 8000
"""

import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .server import mcp

logger = logging.getLogger(__name__)


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


_mcp_app = mcp.http_app()

app = Starlette(
    lifespan=_mcp_app.lifespan,
    routes=[
        Route("/health", health),
        Mount("/", app=_mcp_app),
    ]
)
logger.info("ASGI app siap (Streamable HTTP)")
