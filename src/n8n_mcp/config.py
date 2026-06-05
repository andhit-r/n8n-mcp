"""Konfigurasi runtime via pydantic-settings.

Semua nilai dibaca dari environment / file ``.env``. Diinstansiasi sekali sebagai
singleton ``settings`` dan diimpor dari modul lain.

Konfigurasi Pola A: n8n memiliki auth sendiri (API key), MCP mengamankan pintu
depannya dengan Authentik atau API key statis.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfigurasi n8n MCP Server.

    Attributes:
        n8n_api_base_url: URL dasar n8n REST API, contoh
            ``http://localhost:5678/api/v1``.
        n8n_api_key: API key n8n untuk otentikasi ke n8n REST API.
        n8n_timeout: Timeout HTTP ke n8n dalam detik.
        mcp_server_name: Nama server yang ditampilkan ke MCP client.
        mcp_log_level: Level logging (DEBUG, INFO, WARNING, ERROR).
        mcp_transport: Transport saat dijalankan via ``python -m n8n_mcp``
            (``stdio`` default, atau ``http``/``sse``).
        mcp_host: Host bind saat transport http/sse.
        mcp_port: Port saat transport http/sse.
        mcp_base_url: URL publik MCP server. WAJIB diisi agar OAuth Authentik
            (Claude.ai) berfungsi. Contoh: ``https://n8n-mcp.example.com``.
        authentik_base_url: URL dasar Authentik, contoh ``https://auth.example.com``.
        authentik_app_slug: Slug OAuth2/OIDC Provider di Authentik.
        authentik_client_id: Client ID dari Authentik OAuth2 Provider.
        authentik_client_secret: Client Secret dari Authentik OAuth2 Provider.
        authentik_allowed_usernames: Daftar ``preferred_username`` yang diizinkan
            (kosong = semua user yang lolos policy Authentik diizinkan).
        mcp_api_key: API key statis untuk klien non-OAuth (VS Code/CLI).
    """

    # n8n API
    n8n_api_base_url: str = "http://localhost:5678/api/v1"
    n8n_api_key: str = ""
    n8n_timeout: int = 30

    # Server
    mcp_server_name: str = "n8n-mcp"
    mcp_log_level: str = "INFO"

    # Transport
    mcp_transport: str = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000

    # OAuth Authentik (pintu depan — untuk Claude.ai)
    mcp_base_url: str | None = None
    authentik_base_url: str | None = None
    authentik_app_slug: str | None = None
    authentik_client_id: str | None = None
    authentik_client_secret: str | None = None
    authentik_allowed_usernames: list[str] = []

    # API key (untuk VS Code / CLI / tools non-OAuth)
    mcp_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
