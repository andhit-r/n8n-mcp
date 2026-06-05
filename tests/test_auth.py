"""Test mekanisme auth pintu depan (tanpa Authentik nyata).

BearerApiKeyVerifier diuji langsung; pemeriksaan username Authentik di-mock.
"""

from __future__ import annotations

import pytest

from n8n_mcp.auth_provider import BearerApiKeyVerifier


class TestBearerApiKeyVerifier:
    """Test BearerApiKeyVerifier — API key statis untuk klien non-OAuth."""

    def test_api_key_kosong_raise(self):
        """Konstruktor harus raise ValueError bila api_key kosong."""
        with pytest.raises(ValueError, match="api_key"):
            BearerApiKeyVerifier(api_key="")

    def test_api_key_spasi_raise(self):
        """Konstruktor harus raise ValueError bila api_key hanya spasi."""
        with pytest.raises(ValueError, match="api_key"):
            BearerApiKeyVerifier(api_key="   ")

    @pytest.mark.asyncio
    async def test_token_cocok(self):
        """Token yang cocok dengan api_key harus mengembalikan AccessToken valid."""
        verifier = BearerApiKeyVerifier(api_key="rahasia-n8n")
        result = await verifier.verify_token("rahasia-n8n")
        assert result is not None
        assert result.client_id == "api-key-client"

    @pytest.mark.asyncio
    async def test_token_salah(self):
        """Token yang tidak cocok harus mengembalikan None."""
        verifier = BearerApiKeyVerifier(api_key="rahasia-n8n")
        assert await verifier.verify_token("token-salah") is None

    @pytest.mark.asyncio
    async def test_token_kosong(self):
        """Token kosong harus mengembalikan None."""
        verifier = BearerApiKeyVerifier(api_key="rahasia-n8n")
        assert await verifier.verify_token("") is None
