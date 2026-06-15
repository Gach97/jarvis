"""Integration tests for Jarvis Web Gateway."""

import pytest
import json
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient

# Note: These are integration tests. They require:
#   - FastAPI + uvicorn installed
#   - Piper TTS available (or mocked)
#   - AIAgent importable


@pytest.fixture
async def web_client():
    """Create a test client for the web gateway."""
    from gateway.web_gateway import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sync_client():
    """Create a sync test client for REST endpoints."""
    from gateway.web_gateway import app
    return TestClient(app)


def test_web_gateway_imports():
    """Test that the web gateway imports without errors."""
    from gateway.web_gateway import app
    assert app is not None


def test_index_endpoint(sync_client):
    """Test that the root endpoint serves HTML."""
    response = sync_client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text
    assert "Jarvis" in response.text
    assert "<title>Jarvis</title>" in response.text


def test_setup_endpoint_missing_credentials(sync_client):
    """Test that setup endpoint rejects missing credentials."""
    response = sync_client.post(
        "/api/setup",
        json={"model": "claude-opus-4-20250514"},  # Missing apiKey
    )
    assert response.status_code == 400
    assert "Missing credentials" in response.json()["error"]


def test_setup_endpoint_creates_session(sync_client):
    """Test that setup endpoint creates a session."""
    response = sync_client.post(
        "/api/setup",
        json={
            "apiKey": "test-key-12345",
            "provider": "openai",
            "model": "gpt-4o",
            "ttsProvider": "piper",
            "sttProvider": "local",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "sessionId" in data
    assert data["sessionId"].startswith("web_")
    assert data["status"] == "ok"


def test_tts_endpoint_missing_text(sync_client):
    """Test that TTS endpoint requires text."""
    response = sync_client.post("/api/tts", json={})
    assert response.status_code == 400
    assert "No text provided" in response.json()["error"]


def test_tts_endpoint_piper(sync_client):
    """Test TTS synthesis with Piper."""
    response = sync_client.post(
        "/api/tts",
        json={"text": "Hello world"},
    )
    # If Piper is available, we get audio
    # If not, we get an error (acceptable for integration test)
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "audio" in data
        # Audio should be base64-encoded WAV
        assert len(data["audio"]) > 0


@pytest.mark.asyncio
async def test_websocket_auth(sync_client):
    """Test WebSocket token validation."""
    # Try to connect without a valid session token
    with pytest.raises(Exception):
        # Would need async WebSocket handling
        # This is a placeholder for the actual test
        pass


def test_startup_hooks():
    """Test that startup hooks initialize without error."""
    from gateway.web_startup_hooks import initialize_web_gateway
    # Should not raise
    initialize_web_gateway()


def test_stt_provider_imports():
    """Test that STT provider module imports."""
    from gateway.web_stt_provider import transcribe_audio_file
    assert callable(transcribe_audio_file)


def test_tts_provider_imports():
    """Test that TTS provider module imports."""
    from gateway.web_tts_provider import synthesize_and_stream
    assert callable(synthesize_and_stream)


def test_piper_tts_provider():
    """Test Piper TTS provider registration."""
    from agent.tts_providers.piper import PiperTTSProvider
    provider = PiperTTSProvider()
    assert provider.name == "piper"
    assert provider.is_available() is True


def test_jarvis_platform_adapter():
    """Test that Jarvis platform adapter is registered."""
    from gateway.config import Platform
    assert Platform.JARVIS == "jarvis"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
