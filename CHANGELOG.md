# Changelog

Semua perubahan penting pada project ini didokumentasikan di file ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-05

### Added
- MCP Server untuk n8n REST API dengan FastMCP.
- Tools untuk mengelola workflows: list, get, create, update, delete, activate, deactivate.
- Tools untuk mengelola executions: list, get, delete.
- Tools untuk mengelola credentials: list, get, create, delete.
- Tools untuk mengelola tags: list, create, update, delete.
- Tools untuk mengelola variables: list, create, delete.
- Tool untuk mengambil audit log.
- Dukungan tiga kanal: stdio, Claude Code, Claude Web (via Authentik OAuth).
- Otentikasi via Authentik (OAuth2/OIDC) dan API key statis.
- Docker image runtime (GHCR) via GitHub Actions.
