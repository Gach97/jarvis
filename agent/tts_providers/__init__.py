"""Built-in TTS providers.

This package auto-registers Piper and other built-in TTS providers
at import time so they are available to the agent without additional setup.
"""

import logging

logger = logging.getLogger(__name__)


def _register_builtin_tts_providers():
    """Auto-register Piper and other built-in TTS providers."""
    try:
        from agent.tts_providers.piper import PiperTTSProvider
        from agent.tts_registry import register_provider

        provider = PiperTTSProvider()
        register_provider(provider)
        logger.info("Registered built-in TTS provider: Piper")
    except Exception as e:
        logger.debug("Failed to register Piper TTS provider: %s", e)


# Auto-register on import
_register_builtin_tts_providers()
