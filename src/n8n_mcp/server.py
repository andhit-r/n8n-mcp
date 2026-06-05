"""Definisi MCP Server (FastMCP) untuk n8n REST API.

Auth pintu depan dipilih berdasarkan konfigurasi (lihat config.py):
  - Authentik OAuth (Claude.ai): aktif bila AUTHENTIK_* + MCP_BASE_URL diisi.
  - API Key (VS Code/CLI): aktif bila MCP_API_KEY diisi.
  - Keduanya bisa aktif bersamaan via MultiAuth.
  - Tanpa konfigurasi: tanpa auth (hanya untuk stdio / jaringan lokal).

Semua tool menggunakan ``N8nClient.from_settings()`` sehingga credential n8n
dibaca dari environment — tidak pernah diterima sebagai argumen tool.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from . import __version__
from .client import N8nClient
from .config import settings

logger = logging.getLogger(__name__)

# ── Pemilihan auth pintu depan ────────────────────────────────────────────────
_auth = None
_authentik_aktif = bool(
    settings.authentik_base_url
    and settings.authentik_app_slug
    and settings.authentik_client_id
    and settings.authentik_client_secret
    and settings.mcp_base_url
)

if _authentik_aktif:
    from fastmcp.server.auth import MultiAuth

    from .auth_provider import AuthentikProvider, BearerApiKeyVerifier

    logger.info("OAuth Authentik AKTIF — slug: %s", settings.authentik_app_slug)
    _provider = AuthentikProvider(
        authentik_base_url=settings.authentik_base_url,
        application_slug=settings.authentik_app_slug,
        client_id=settings.authentik_client_id,
        client_secret=settings.authentik_client_secret,
        base_url=settings.mcp_base_url,
        allowed_usernames=settings.authentik_allowed_usernames,
        require_authorization_consent="external",
    )
    if settings.mcp_api_key:
        logger.info("API Key AKTIF (MultiAuth: Authentik OAuth + API Key)")
        _auth = MultiAuth(
            server=_provider,
            verifiers=[BearerApiKeyVerifier(api_key=settings.mcp_api_key)],
        )
    else:
        _auth = _provider

elif settings.mcp_api_key:
    from fastmcp.server.auth import MultiAuth

    from .auth_provider import BearerApiKeyVerifier

    logger.info("API Key AKTIF (tanpa OAuth)")
    _auth = MultiAuth(verifiers=[BearerApiKeyVerifier(api_key=settings.mcp_api_key)])

else:
    logger.warning(
        "Tidak ada auth dikonfigurasi — server terbuka. Isi AUTHENTIK_* + MCP_BASE_URL "
        "untuk deployment Claude Web."
    )

mcp = FastMCP(name=settings.mcp_server_name, auth=_auth)


# ── Resource ──────────────────────────────────────────────────────────────────


@mcp.resource("config://version")
def version() -> str:
    """Versi n8n MCP Server yang sedang berjalan."""
    return __version__


# ── Helper ────────────────────────────────────────────────────────────────────


def _strip_none(d: dict[str, Any]) -> dict[str, Any]:
    """Hapus key dengan nilai None dari dict."""
    return {k: v for k, v in d.items() if v is not None}


# ── Workflow Tools ────────────────────────────────────────────────────────────


@mcp.tool
async def list_workflows(
    active: Annotated[
        bool | None, "Filter: True = hanya aktif, False = hanya nonaktif, None = semua"
    ] = None,
    tags: Annotated[
        str | None, "Filter by tag ID (pisahkan dengan koma bila lebih dari satu)"
    ] = None,
    name: Annotated[str | None, "Filter berdasarkan nama workflow (pencarian parsial)"] = None,
    limit: Annotated[int, "Jumlah maksimum hasil yang dikembalikan (1-250)"] = 100,
    cursor: Annotated[
        str | None, "Cursor untuk paginasi (dari field nextCursor respons sebelumnya)"
    ] = None,
) -> dict[str, Any]:
    """Ambil daftar semua workflow di n8n.

    Mendukung filter berdasarkan status aktif, tag, dan nama workflow.
    Hasil di-paginate; gunakan ``cursor`` dari ``nextCursor`` respons untuk halaman berikutnya.

    Args:
        active: Filter status aktif workflow.
        tags: Filter by tag ID (pisahkan dengan koma).
        name: Filter berdasarkan nama (pencarian parsial, case-insensitive).
        limit: Jumlah hasil per halaman (1-250, default 100).
        cursor: Cursor paginasi.

    Returns:
        Dict dengan key ``data`` (list workflow) dan ``nextCursor`` (opsional).
    """
    client = N8nClient.from_settings()
    try:
        params: dict[str, Any] = _strip_none(
            {"active": active, "tags": tags, "name": name, "limit": limit, "cursor": cursor}
        )
        return await client.get("/workflows", params=params)
    finally:
        await client.aclose()


@mcp.tool
async def get_workflow(
    workflow_id: Annotated[str, "ID workflow yang ingin diambil"],
) -> dict[str, Any]:
    """Ambil detail lengkap satu workflow berdasarkan ID.

    Mengembalikan definisi workflow termasuk nodes, connections, dan pengaturan.

    Args:
        workflow_id: ID unik workflow di n8n.

    Returns:
        Dict berisi detail workflow (id, name, nodes, connections, settings, dll).
    """
    client = N8nClient.from_settings()
    try:
        return await client.get(f"/workflows/{workflow_id}")
    finally:
        await client.aclose()


@mcp.tool
async def create_workflow(
    name: Annotated[str, "Nama workflow baru"],
    nodes: Annotated[list[dict[str, Any]], "Daftar node workflow dalam format n8n"],
    connections: Annotated[dict[str, Any], "Koneksi antar node dalam format n8n"],
    settings: Annotated[
        dict[str, Any] | None, "Pengaturan workflow (opsional, mis. timezone, errorWorkflow)"
    ] = None,
    static_data: Annotated[dict[str, Any] | None, "Static data workflow (opsional)"] = None,
) -> dict[str, Any]:
    """Buat workflow baru di n8n.

    Workflow dibuat dalam keadaan nonaktif. Gunakan ``activate_workflow`` untuk mengaktifkannya.
    Format node dan koneksi mengikuti skema n8n (lihat dokumentasi n8n API).

    Args:
        name: Nama workflow.
        nodes: List definisi node n8n.
        connections: Mapping koneksi antar node.
        settings: Pengaturan workflow seperti timezone dan error handler.
        static_data: Data statis workflow.

    Returns:
        Dict detail workflow yang baru dibuat, termasuk ID yang ditetapkan n8n.
    """
    client = N8nClient.from_settings()
    try:
        payload: dict[str, Any] = _strip_none(
            {
                "name": name,
                "nodes": nodes,
                "connections": connections,
                "settings": settings,
                "staticData": static_data,
            }
        )
        return await client.post("/workflows", json=payload)
    finally:
        await client.aclose()


@mcp.tool
async def update_workflow(
    workflow_id: Annotated[str, "ID workflow yang ingin diperbarui"],
    name: Annotated[str | None, "Nama baru workflow (kosongkan untuk tidak mengubah)"] = None,
    nodes: Annotated[
        list[dict[str, Any]] | None, "Definisi nodes baru (kosongkan untuk tidak mengubah)"
    ] = None,
    connections: Annotated[
        dict[str, Any] | None, "Koneksi baru (kosongkan untuk tidak mengubah)"
    ] = None,
    settings: Annotated[
        dict[str, Any] | None, "Pengaturan baru (kosongkan untuk tidak mengubah)"
    ] = None,
) -> dict[str, Any]:
    """Perbarui workflow yang sudah ada di n8n.

    Hanya field yang diisi yang akan diperbarui. Minimal berikan salah satu field.
    Perbarui nodes dan connections sekaligus bila mengubah struktur workflow.

    Args:
        workflow_id: ID workflow yang akan diperbarui.
        name: Nama baru (opsional).
        nodes: List node baru (opsional, menggantikan seluruh nodes).
        connections: Koneksi baru (opsional, menggantikan seluruh connections).
        settings: Pengaturan baru (opsional).

    Returns:
        Dict detail workflow setelah diperbarui.

    Raises:
        ToolError: Bila tidak ada field yang diisi atau workflow tidak ditemukan.
    """
    payload = _strip_none(
        {"name": name, "nodes": nodes, "connections": connections, "settings": settings}
    )
    if not payload:
        raise ToolError("Minimal satu field (name, nodes, connections, settings) harus diisi.")
    client = N8nClient.from_settings()
    try:
        return await client.put(f"/workflows/{workflow_id}", json=payload)
    finally:
        await client.aclose()


@mcp.tool
async def delete_workflow(
    workflow_id: Annotated[str, "ID workflow yang ingin dihapus"],
) -> dict[str, Any]:
    """Hapus workflow dari n8n secara permanen.

    Operasi ini tidak dapat dibatalkan. Workflow yang sedang aktif akan dihentikan
    terlebih dahulu sebelum dihapus.

    Args:
        workflow_id: ID workflow yang akan dihapus.

    Returns:
        Dict konfirmasi penghapusan.
    """
    client = N8nClient.from_settings()
    try:
        return await client.delete(f"/workflows/{workflow_id}")
    finally:
        await client.aclose()


@mcp.tool
async def activate_workflow(
    workflow_id: Annotated[str, "ID workflow yang ingin diaktifkan"],
) -> dict[str, Any]:
    """Aktifkan workflow di n8n agar mulai memproses trigger.

    Setelah diaktifkan, workflow akan merespons trigger (webhook, schedule, dll)
    secara otomatis. Pastikan workflow sudah memiliki trigger node.

    Args:
        workflow_id: ID workflow yang akan diaktifkan.

    Returns:
        Dict detail workflow dengan status ``active: true``.
    """
    client = N8nClient.from_settings()
    try:
        return await client.patch(f"/workflows/{workflow_id}/activate")
    finally:
        await client.aclose()


@mcp.tool
async def deactivate_workflow(
    workflow_id: Annotated[str, "ID workflow yang ingin dinonaktifkan"],
) -> dict[str, Any]:
    """Nonaktifkan workflow di n8n sehingga berhenti memproses trigger.

    Setelah dinonaktifkan, workflow tidak akan merespons trigger baru.
    Eksekusi yang sedang berjalan tidak akan dihentikan.

    Args:
        workflow_id: ID workflow yang akan dinonaktifkan.

    Returns:
        Dict detail workflow dengan status ``active: false``.
    """
    client = N8nClient.from_settings()
    try:
        return await client.patch(f"/workflows/{workflow_id}/deactivate")
    finally:
        await client.aclose()


# ── Execution Tools ───────────────────────────────────────────────────────────


@mcp.tool
async def list_executions(
    workflow_id: Annotated[str | None, "Filter berdasarkan ID workflow tertentu"] = None,
    status: Annotated[str | None, "Filter status: 'success', 'error', 'waiting', 'running'"] = None,
    limit: Annotated[int, "Jumlah maksimum hasil (1-250)"] = 20,
    cursor: Annotated[str | None, "Cursor paginasi"] = None,
    include_data: Annotated[bool, "Sertakan data input/output eksekusi (membesar respons)"] = False,
) -> dict[str, Any]:
    """Ambil daftar eksekusi workflow di n8n.

    Mendukung filter berdasarkan workflow, status, dan paginasi. Data eksekusi
    (input/output node) hanya disertakan bila ``include_data=True``.

    Args:
        workflow_id: Filter hanya eksekusi dari workflow tertentu.
        status: Filter berdasarkan status eksekusi.
        limit: Jumlah hasil per halaman (1-250, default 20).
        cursor: Cursor paginasi dari ``nextCursor`` respons sebelumnya.
        include_data: Bila True, sertakan data input/output dalam respons.

    Returns:
        Dict dengan key ``data`` (list eksekusi) dan ``nextCursor`` (opsional).
    """
    client = N8nClient.from_settings()
    try:
        params: dict[str, Any] = _strip_none(
            {
                "workflowId": workflow_id,
                "status": status,
                "limit": limit,
                "cursor": cursor,
                "includeData": include_data if include_data else None,
            }
        )
        return await client.get("/executions", params=params)
    finally:
        await client.aclose()


@mcp.tool
async def get_execution(
    execution_id: Annotated[int, "ID eksekusi yang ingin diambil"],
    include_data: Annotated[bool, "Sertakan data input/output node dalam respons"] = True,
) -> dict[str, Any]:
    """Ambil detail lengkap satu eksekusi workflow.

    Mengembalikan informasi eksekusi termasuk status, waktu mulai/selesai,
    dan (opsional) data input/output tiap node.

    Args:
        execution_id: ID numerik eksekusi.
        include_data: Bila True (default), sertakan data node dalam respons.

    Returns:
        Dict detail eksekusi (id, status, startedAt, stoppedAt, workflowId, data, dll).
    """
    client = N8nClient.from_settings()
    try:
        params = {"includeData": include_data} if include_data else {}
        return await client.get(f"/executions/{execution_id}", params=params)
    finally:
        await client.aclose()


@mcp.tool
async def delete_execution(
    execution_id: Annotated[int, "ID eksekusi yang ingin dihapus"],
) -> dict[str, Any]:
    """Hapus rekaman eksekusi dari n8n secara permanen.

    Operasi ini tidak dapat dibatalkan. Eksekusi yang sedang berjalan tidak bisa dihapus.

    Args:
        execution_id: ID numerik eksekusi yang akan dihapus.

    Returns:
        Dict konfirmasi penghapusan.
    """
    client = N8nClient.from_settings()
    try:
        return await client.delete(f"/executions/{execution_id}")
    finally:
        await client.aclose()


# ── Credential Tools ──────────────────────────────────────────────────────────


@mcp.tool
async def list_credentials(
    credential_type: Annotated[
        str | None, "Filter berdasarkan tipe credential (mis. 'githubApi', 'slackApi')"
    ] = None,
    limit: Annotated[int, "Jumlah maksimum hasil (1-250)"] = 100,
    cursor: Annotated[str | None, "Cursor paginasi"] = None,
) -> dict[str, Any]:
    """Ambil daftar credentials yang tersimpan di n8n.

    Data sensitif (token, password) tidak dikembalikan oleh API.
    Hanya metadata credential (id, name, type, createdAt) yang tersedia.

    Args:
        credential_type: Filter berdasarkan tipe credential.
        limit: Jumlah hasil per halaman (1-250, default 100).
        cursor: Cursor paginasi.

    Returns:
        Dict dengan key ``data`` (list credential metadata) dan ``nextCursor``.
    """
    client = N8nClient.from_settings()
    try:
        params: dict[str, Any] = _strip_none(
            {"type": credential_type, "limit": limit, "cursor": cursor}
        )
        return await client.get("/credentials", params=params)
    finally:
        await client.aclose()


@mcp.tool
async def get_credential(
    credential_id: Annotated[str, "ID credential yang ingin diambil"],
) -> dict[str, Any]:
    """Ambil metadata satu credential berdasarkan ID.

    Nilai sensitif (token, password, secret key) tidak dikembalikan oleh n8n API
    demi keamanan. Hanya metadata seperti name, type, dan createdAt yang tersedia.

    Args:
        credential_id: ID credential di n8n.

    Returns:
        Dict metadata credential (id, name, type, createdAt, updatedAt).
    """
    client = N8nClient.from_settings()
    try:
        return await client.get(f"/credentials/{credential_id}")
    finally:
        await client.aclose()


@mcp.tool
async def create_credential(
    name: Annotated[str, "Nama credential (mis. 'GitHub Personal Token')"],
    credential_type: Annotated[
        str, "Tipe credential n8n (mis. 'githubApi', 'slackApi', 'httpHeaderAuth')"
    ],
    data: Annotated[
        dict[str, Any],
        "Data credential sesuai skema tipe (mis. {'accessToken': '...'} untuk githubApi)",
    ],
) -> dict[str, Any]:
    """Buat credential baru di n8n.

    Tipe credential dan skema data-nya bergantung pada integrasi n8n.
    Contoh: tipe ``githubApi`` memerlukan ``{"accessToken": "ghp_xxx"}``.
    Lihat dokumentasi node n8n untuk skema data per tipe.

    Args:
        name: Nama tampilan credential.
        credential_type: Identifier tipe credential n8n.
        data: Dict berisi nilai credential sesuai skema tipe.

    Returns:
        Dict metadata credential yang baru dibuat (tanpa data sensitif).
    """
    client = N8nClient.from_settings()
    try:
        payload = {"name": name, "type": credential_type, "data": data}
        return await client.post("/credentials", json=payload)
    finally:
        await client.aclose()


@mcp.tool
async def delete_credential(
    credential_id: Annotated[str, "ID credential yang ingin dihapus"],
) -> dict[str, Any]:
    """Hapus credential dari n8n secara permanen.

    Operasi ini tidak dapat dibatalkan. Workflow yang menggunakan credential ini
    akan gagal bila dieksekusi setelah credential dihapus.

    Args:
        credential_id: ID credential yang akan dihapus.

    Returns:
        Dict konfirmasi penghapusan.
    """
    client = N8nClient.from_settings()
    try:
        return await client.delete(f"/credentials/{credential_id}")
    finally:
        await client.aclose()


# ── Tag Tools ─────────────────────────────────────────────────────────────────


@mcp.tool
async def list_tags(
    limit: Annotated[int, "Jumlah maksimum hasil (1-250)"] = 100,
    cursor: Annotated[str | None, "Cursor paginasi"] = None,
) -> dict[str, Any]:
    """Ambil daftar semua tag yang tersedia di n8n.

    Tag digunakan untuk mengkategorikan dan memfilter workflow.

    Args:
        limit: Jumlah hasil per halaman (1-250, default 100).
        cursor: Cursor paginasi.

    Returns:
        Dict dengan key ``data`` (list tag) dan ``nextCursor``.
    """
    client = N8nClient.from_settings()
    try:
        params = _strip_none({"limit": limit, "cursor": cursor})
        return await client.get("/tags", params=params)
    finally:
        await client.aclose()


@mcp.tool
async def create_tag(
    name: Annotated[str, "Nama tag baru"],
) -> dict[str, Any]:
    """Buat tag baru di n8n.

    Tag dapat digunakan untuk mengkategorikan workflow sehingga mudah difilter.
    Nama tag harus unik.

    Args:
        name: Nama tag yang ingin dibuat.

    Returns:
        Dict detail tag yang baru dibuat (id, name, createdAt).
    """
    client = N8nClient.from_settings()
    try:
        return await client.post("/tags", json={"name": name})
    finally:
        await client.aclose()


@mcp.tool
async def update_tag(
    tag_id: Annotated[str, "ID tag yang ingin diperbarui"],
    name: Annotated[str, "Nama baru tag"],
) -> dict[str, Any]:
    """Perbarui nama tag yang sudah ada di n8n.

    Args:
        tag_id: ID tag yang akan diperbarui.
        name: Nama baru untuk tag.

    Returns:
        Dict detail tag setelah diperbarui.
    """
    client = N8nClient.from_settings()
    try:
        return await client.patch(f"/tags/{tag_id}", json={"name": name})
    finally:
        await client.aclose()


@mcp.tool
async def delete_tag(
    tag_id: Annotated[str, "ID tag yang ingin dihapus"],
) -> dict[str, Any]:
    """Hapus tag dari n8n.

    Tag yang dihapus akan dilepas dari semua workflow yang menggunakannya.
    Workflow tidak ikut terhapus.

    Args:
        tag_id: ID tag yang akan dihapus.

    Returns:
        Dict konfirmasi penghapusan.
    """
    client = N8nClient.from_settings()
    try:
        return await client.delete(f"/tags/{tag_id}")
    finally:
        await client.aclose()


# ── Variable Tools ────────────────────────────────────────────────────────────


@mcp.tool
async def list_variables(
    limit: Annotated[int, "Jumlah maksimum hasil (1-250)"] = 100,
    cursor: Annotated[str | None, "Cursor paginasi"] = None,
) -> dict[str, Any]:
    """Ambil daftar semua variable n8n (fitur Enterprise).

    Variable n8n adalah pasangan key-value yang bisa diakses dari semua workflow.
    Fitur ini memerlukan lisensi n8n Enterprise atau Self-hosted dengan fitur variable aktif.

    Args:
        limit: Jumlah hasil per halaman (1-250, default 100).
        cursor: Cursor paginasi.

    Returns:
        Dict dengan key ``data`` (list variable) dan ``nextCursor``.
    """
    client = N8nClient.from_settings()
    try:
        params = _strip_none({"limit": limit, "cursor": cursor})
        return await client.get("/variables", params=params)
    finally:
        await client.aclose()


@mcp.tool
async def create_variable(
    key: Annotated[str, "Kunci variable (huruf, angka, underscore; unik di seluruh instance)"],
    value: Annotated[str, "Nilai variable (selalu string)"],
) -> dict[str, Any]:
    """Buat variable baru di n8n (fitur Enterprise).

    Variable bisa diakses di workflow via ekspresi ``{{ $vars.NAMA_VAR }}``.
    Kunci harus unik dan hanya boleh berisi huruf, angka, dan underscore.

    Args:
        key: Kunci unik variable.
        value: Nilai variable (string).

    Returns:
        Dict detail variable yang baru dibuat (id, key, value).
    """
    client = N8nClient.from_settings()
    try:
        return await client.post("/variables", json={"key": key, "value": value})
    finally:
        await client.aclose()


@mcp.tool
async def delete_variable(
    variable_id: Annotated[str, "ID variable yang ingin dihapus"],
) -> dict[str, Any]:
    """Hapus variable dari n8n secara permanen.

    Workflow yang mereferensikan variable ini mungkin akan error setelah dihapus.

    Args:
        variable_id: ID variable yang akan dihapus.

    Returns:
        Dict konfirmasi penghapusan.
    """
    client = N8nClient.from_settings()
    try:
        return await client.delete(f"/variables/{variable_id}")
    finally:
        await client.aclose()


# ── Audit Log Tool ────────────────────────────────────────────────────────────


@mcp.tool
async def get_audit_log(
    days_ago: Annotated[int, "Ambil event dalam N hari terakhir (maksimum 365)"] = 30,
    resource_type: Annotated[
        str | None, "Filter tipe resource: 'Workflow', 'Credential', 'User', dll"
    ] = None,
) -> dict[str, Any]:
    """Ambil audit log aktivitas di n8n (fitur Enterprise).

    Mengembalikan rekaman aktivitas pengguna dan sistem seperti pembuatan/penghapusan
    workflow, login, perubahan credential, dll. Memerlukan lisensi n8n Enterprise.

    Args:
        days_ago: Rentang waktu audit log dalam hari (1-365, default 30).
        resource_type: Filter berdasarkan tipe resource yang diaudit.

    Returns:
        Dict berisi daftar event audit log dengan timestamp, user, dan detail aksi.
    """
    client = N8nClient.from_settings()
    try:
        payload: dict[str, Any] = _strip_none(
            {
                "daysAgo": days_ago,
                "filters": {"resourceType": resource_type} if resource_type else None,
            }
        )
        return await client.post("/audit", json=payload)
    finally:
        await client.aclose()
