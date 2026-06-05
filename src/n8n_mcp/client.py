"""HTTP client untuk n8n REST API.

Menyediakan ``N8nClient`` — wrapper ``httpx.AsyncClient`` yang menyuntikkan
header ``X-N8N-API-KEY`` otomatis ke setiap request ke n8n.

Penggunaan:
    client = N8nClient.from_settings()
    data = await client.get("/workflows")
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastmcp.exceptions import ToolError

from .config import settings

logger = logging.getLogger(__name__)


class N8nClient:
    """Async HTTP client untuk n8n REST API.

    Semua method mengembalikan dict/list hasil parsing JSON. Bila n8n
    mengembalikan status error (4xx/5xx), ``ToolError`` di-raise sehingga
    pesan error aman ditampilkan ke MCP client.

    Args:
        base_url: URL dasar n8n API (tanpa trailing slash).
        api_key: API key n8n.
        timeout: Timeout HTTP dalam detik.
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 30) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "X-N8N-API-KEY": api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    @classmethod
    def from_settings(cls) -> "N8nClient":
        """Buat instance dari konfigurasi global (settings).

        Returns:
            Instance ``N8nClient`` yang sudah dikonfigurasi.

        Raises:
            ToolError: bila ``N8N_API_KEY`` tidak diisi.
        """
        if not settings.n8n_api_key:
            raise ToolError("N8N_API_KEY belum dikonfigurasi. Isi di environment atau file .env.")
        return cls(
            base_url=settings.n8n_api_base_url,
            api_key=settings.n8n_api_key,
            timeout=settings.n8n_timeout,
        )

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise ToolError bila response HTTP mengindikasikan error.

        Args:
            response: Response HTTP dari n8n.

        Raises:
            ToolError: bila status code 4xx atau 5xx.
        """
        if response.is_error:
            try:
                detail = response.json()
                msg = detail.get("message") or detail.get("error") or str(detail)
            except Exception:
                msg = response.text[:200] or f"HTTP {response.status_code}"
            raise ToolError(f"n8n API error {response.status_code}: {msg}")

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Kirim GET request ke n8n API.

        Args:
            path: Path endpoint relatif (contoh: ``/workflows``).
            params: Query parameters opsional.

        Returns:
            Hasil parsing JSON dari response.
        """
        response = await self._client.get(path, params=params)
        self._raise_for_status(response)
        return response.json()

    async def post(self, path: str, json: Any = None) -> Any:
        """Kirim POST request ke n8n API.

        Args:
            path: Path endpoint relatif.
            json: Body request dalam bentuk dict/list.

        Returns:
            Hasil parsing JSON dari response.
        """
        response = await self._client.post(path, json=json)
        self._raise_for_status(response)
        return response.json()

    async def put(self, path: str, json: Any = None) -> Any:
        """Kirim PUT request ke n8n API.

        Args:
            path: Path endpoint relatif.
            json: Body request dalam bentuk dict/list.

        Returns:
            Hasil parsing JSON dari response.
        """
        response = await self._client.put(path, json=json)
        self._raise_for_status(response)
        return response.json()

    async def patch(self, path: str, json: Any = None) -> Any:
        """Kirim PATCH request ke n8n API.

        Args:
            path: Path endpoint relatif.
            json: Body request dalam bentuk dict/list.

        Returns:
            Hasil parsing JSON dari response.
        """
        response = await self._client.patch(path, json=json)
        self._raise_for_status(response)
        return response.json()

    async def delete(self, path: str) -> Any:
        """Kirim DELETE request ke n8n API.

        Args:
            path: Path endpoint relatif.

        Returns:
            Hasil parsing JSON dari response (bisa None bila body kosong).
        """
        response = await self._client.delete(path)
        self._raise_for_status(response)
        if response.content:
            return response.json()
        return {"success": True}

    async def aclose(self) -> None:
        """Tutup HTTP client dan bebaskan resource."""
        await self._client.aclose()
