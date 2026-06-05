"""Test tools n8n MCP Server menggunakan FastMCP Client in-memory.

N8nClient di-mock via unittest.mock karena respx tidak kompatibel dengan
transport in-memory FastMCP. Test memverifikasi behavior tool (argumen,
return value, routing ke metode client yang tepat) tanpa perlu instance n8n nyata.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

# Pastikan env n8n tersedia sebelum import server (settings dibaca saat import).
os.environ.setdefault("N8N_API_BASE_URL", "http://n8n-test.local/api/v1")
os.environ.setdefault("N8N_API_KEY", "test-api-key")

from n8n_mcp.server import mcp  # noqa: E402  (import setelah env diset)


def _make_mock_client(get=None, post=None, put=None, patch_=None, delete=None):
    """Buat mock N8nClient dengan metode HTTP yang bisa dikonfigurasi."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=get or {})
    mock_client.post = AsyncMock(return_value=post or {})
    mock_client.put = AsyncMock(return_value=put or {})
    mock_client.patch = AsyncMock(return_value=patch_ or {})
    mock_client.delete = AsyncMock(return_value=delete or {})
    mock_client.aclose = AsyncMock()
    return mock_client


@pytest.mark.asyncio
async def test_tools_terdaftar():
    """Semua tool n8n harus terdaftar di server."""
    async with Client(mcp) as client:
        tools = {t.name for t in await client.list_tools()}
    expected = {
        "list_workflows",
        "get_workflow",
        "create_workflow",
        "update_workflow",
        "delete_workflow",
        "activate_workflow",
        "deactivate_workflow",
        "list_executions",
        "get_execution",
        "delete_execution",
        "list_credentials",
        "get_credential",
        "create_credential",
        "delete_credential",
        "list_tags",
        "create_tag",
        "update_tag",
        "delete_tag",
        "list_variables",
        "create_variable",
        "delete_variable",
        "get_audit_log",
    }
    assert expected.issubset(tools), f"Tool tidak ditemukan: {expected - tools}"


@pytest.mark.asyncio
async def test_list_workflows():
    """list_workflows harus memanggil client.get('/workflows') dan mengembalikan data."""
    expected = {"data": [{"id": "1", "name": "Test WF", "active": True}], "nextCursor": None}
    mock_client = _make_mock_client(get=expected)
    with patch("n8n_mcp.server.N8nClient.from_settings", return_value=mock_client):
        async with Client(mcp) as client:
            result = await client.call_tool("list_workflows", {})
    mock_client.get.assert_called_once()
    assert result.data["data"][0]["id"] == "1"


@pytest.mark.asyncio
async def test_get_workflow():
    """get_workflow harus memanggil client.get('/workflows/42')."""
    expected = {"id": "42", "name": "My Workflow", "active": False, "nodes": []}
    mock_client = _make_mock_client(get=expected)
    with patch("n8n_mcp.server.N8nClient.from_settings", return_value=mock_client):
        async with Client(mcp) as client:
            result = await client.call_tool("get_workflow", {"workflow_id": "42"})
    mock_client.get.assert_called_once_with("/workflows/42")
    assert result.data["id"] == "42"


@pytest.mark.asyncio
async def test_activate_workflow():
    """activate_workflow harus memanggil client.patch('/workflows/5/activate')."""
    expected = {"id": "5", "active": True}
    mock_client = _make_mock_client(patch_=expected)
    with patch("n8n_mcp.server.N8nClient.from_settings", return_value=mock_client):
        async with Client(mcp) as client:
            result = await client.call_tool("activate_workflow", {"workflow_id": "5"})
    mock_client.patch.assert_called_once_with("/workflows/5/activate")
    assert result.data["active"] is True


@pytest.mark.asyncio
async def test_deactivate_workflow():
    """deactivate_workflow harus memanggil client.patch('/workflows/5/deactivate')."""
    expected = {"id": "5", "active": False}
    mock_client = _make_mock_client(patch_=expected)
    with patch("n8n_mcp.server.N8nClient.from_settings", return_value=mock_client):
        async with Client(mcp) as client:
            result = await client.call_tool("deactivate_workflow", {"workflow_id": "5"})
    mock_client.patch.assert_called_once_with("/workflows/5/deactivate")
    assert result.data["active"] is False


@pytest.mark.asyncio
async def test_list_executions():
    """list_executions harus memanggil client.get('/executions')."""
    expected = {"data": [{"id": 1, "status": "success"}], "nextCursor": None}
    mock_client = _make_mock_client(get=expected)
    with patch("n8n_mcp.server.N8nClient.from_settings", return_value=mock_client):
        async with Client(mcp) as client:
            result = await client.call_tool("list_executions", {})
    mock_client.get.assert_called_once()
    assert result.data["data"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_create_tag():
    """create_tag harus memanggil client.post('/tags')."""
    expected = {"id": "tag-1", "name": "production"}
    mock_client = _make_mock_client(post=expected)
    with patch("n8n_mcp.server.N8nClient.from_settings", return_value=mock_client):
        async with Client(mcp) as client:
            result = await client.call_tool("create_tag", {"name": "production"})
    mock_client.post.assert_called_once_with("/tags", json={"name": "production"})
    assert result.data["name"] == "production"


@pytest.mark.asyncio
async def test_delete_workflow():
    """delete_workflow harus memanggil client.delete('/workflows/99')."""
    expected = {"success": True}
    mock_client = _make_mock_client(delete=expected)
    with patch("n8n_mcp.server.N8nClient.from_settings", return_value=mock_client):
        async with Client(mcp) as client:
            result = await client.call_tool("delete_workflow", {"workflow_id": "99"})
    mock_client.delete.assert_called_once_with("/workflows/99")
    assert result.data["success"] is True


@pytest.mark.asyncio
async def test_update_workflow_tanpa_field_raise():
    """update_workflow tanpa field apapun harus raise ToolError."""
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="Minimal satu field"):
            await client.call_tool("update_workflow", {"workflow_id": "1"})
