"""Jarvis browser platform adapter stub.

This adapter is a minimal stub so the gateway's platform registry can
recognize a `jarvis` platform. It should be extended to map WebSocket
messages into the platform `MessageEvent` model and vice-versa.
"""
from gateway.platforms.base import BasePlatformAdapter
import logging

logger = logging.getLogger(__name__)


class JarvisPlatformAdapter(BasePlatformAdapter):
    """Minimal in-process browser adapter for Jarvis Web UI.

    For now this is a no-op stub. Implement message conversion and
    delivery methods as needed.
    """

    def __init__(self, config=None):
        super().__init__(config or {})

    def send_message(self, event, content: str):
        logger.info("JarvisPlatformAdapter.send_message: %s", content)
        return {"ok": True}


def check_jarvis_requirements() -> bool:
    """Return True when the minimal requirements for the Jarvis adapter are met.

    This adapter is in-process and has no external deps, so always return True.
    """
    return True
