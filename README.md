# n8n MCP Server

MCP Server untuk [n8n](https://n8n.io) REST API, dibangun dengan [FastMCP](https://gofastmcp.com).
Ekspos tool untuk mengelola **workflows**, **executions**, **credentials**, **tags**, dan **variables**
langsung dari MCP client (Claude Desktop, Claude Code, Claude Web).

Dipakai lewat tiga kanal: **stdio**, **Claude Code**, dan **Claude Web (claude.ai)**.
Otentikasi memakai **Authentik** sebagai identity provider (untuk Claude Web).

## Tools yang tersedia

| Kategori | Tool | Deskripsi |
|---|---|---|
| Workflow | `list_workflows` | Daftar semua workflow |
| Workflow | `get_workflow` | Ambil detail satu workflow |
| Workflow | `create_workflow` | Buat workflow baru |
| Workflow | `update_workflow` | Perbarui workflow |
| Workflow | `delete_workflow` | Hapus workflow |
| Workflow | `activate_workflow` | Aktifkan workflow |
| Workflow | `deactivate_workflow` | Nonaktifkan workflow |
| Execution | `list_executions` | Daftar eksekusi (dengan filter) |
| Execution | `get_execution` | Ambil detail satu eksekusi |
| Execution | `delete_execution` | Hapus eksekusi |
| Credential | `list_credentials` | Daftar credentials |
| Credential | `get_credential` | Ambil detail credential |
| Credential | `create_credential` | Buat credential baru |
| Credential | `delete_credential` | Hapus credential |
| Tag | `list_tags` | Daftar semua tag |
| Tag | `create_tag` | Buat tag baru |
| Tag | `update_tag` | Perbarui nama tag |
| Tag | `delete_tag` | Hapus tag |
| Variable | `list_variables` | Daftar semua variable |
| Variable | `create_variable` | Buat variable baru |
| Variable | `delete_variable` | Hapus variable |
| Audit | `get_audit_log` | Ambil audit log n8n |

## Cara pakai per kanal

### 1. stdio — Claude Desktop / Claude Code lokal

Tidak perlu auth jaringan; client men-spawn proses langsung.

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/andhit-r/n8n-mcp@v0.1.0", "n8n-mcp"],
      "env": {
        "N8N_API_BASE_URL": "http://localhost:5678/api/v1",
        "N8N_API_KEY": "your-n8n-api-key"
      }
    }
  }
}
```

Atau via Docker (stdio):

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "MCP_TRANSPORT=stdio",
        "-e", "N8N_API_BASE_URL=http://host.docker.internal:5678/api/v1",
        "-e", "N8N_API_KEY=your-n8n-api-key",
        "ghcr.io/andhit-r/n8n-mcp:latest"
      ]
    }
  }
}
```

### 2. Claude Code

```bash
# stdio (langsung, tanpa server terpisah)
claude mcp add n8n-mcp -- uvx --from "git+https://github.com/andhit-r/n8n-mcp@v0.1.0" n8n-mcp

# remote (server HTTP yang sudah berjalan)
claude mcp add --transport http n8n-mcp https://n8n-mcp.example.com/mcp
```

### 3. Claude Web (claude.ai) — remote, WAJIB OAuth Authentik

Jalankan server sebagai service HTTP di URL publik HTTPS, daftarkan sebagai **Custom Connector** di claude.ai.

```bash
docker run -d -p 8000:8000 \
  -e N8N_API_BASE_URL=https://your-n8n.example.com/api/v1 \
  -e N8N_API_KEY=your-n8n-api-key \
  -e MCP_BASE_URL=https://n8n-mcp.example.com \
  -e AUTHENTIK_BASE_URL=https://auth.example.com \
  -e AUTHENTIK_APP_SLUG=n8n-mcp \
  -e AUTHENTIK_CLIENT_ID=... \
  -e AUTHENTIK_CLIENT_SECRET=... \
  ghcr.io/andhit-r/n8n-mcp:latest
```

> Dirilis via GitHub (GitHub Release + image GHCR). Tidak tersedia di PyPI.
> Install dari sumber: `pip install "git+https://github.com/andhit-r/n8n-mcp@v0.1.0"`.

## Konfigurasi n8n API

Aktifkan Public REST API di n8n: **Settings → n8n API → Create an API key**.
Pastikan akun memiliki izin yang sesuai (admin direkomendasikan).

| Variabel | Wajib | Contoh |
|---|---|---|
| `N8N_API_BASE_URL` | Ya | `http://localhost:5678/api/v1` |
| `N8N_API_KEY` | Ya | `n8n_api_xxx...` |
| `N8N_TIMEOUT` | Tidak | `30` (detik, default) |

## Otentikasi (Authentik)

Server memilih auth otomatis dari environment:

| Mekanisme | Untuk | Aktif jika |
|---|---|---|
| **OAuth Authentik** | Claude Web / browser | `AUTHENTIK_*` + `MCP_BASE_URL` diisi |
| **API Key statis** | VS Code / CLI | `MCP_API_KEY` diisi |
| (tanpa auth) | stdio / jaringan lokal | tidak ada yang diisi |

Buat OAuth2/OIDC Provider + Application di Authentik (Redirect URI
`https://<MCP_BASE_URL>/auth/callback`, scope `openid profile email`).

## Transport (environment)

| Variabel | Default | Keterangan |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio`, `http`, atau `sse` |
| `MCP_HOST` / `MCP_PORT` | `127.0.0.1` / `8000` | bind saat http/sse |
| `MCP_BASE_URL` | — | URL publik (wajib untuk OAuth Authentik) |

Deployment cloud: `uvicorn n8n_mcp.asgi:app --host 0.0.0.0 --port 8000`.

## Pengembangan

```bash
pip install -e .
cp .env.example .env   # isi N8N_API_BASE_URL dan N8N_API_KEY
python -m n8n_mcp      # jalankan lokal (stdio)
make test              # gate test (lint + unit)
```

## Lisensi

[MIT](LICENSE).
