"""Startup hooks for Jarvis Web UI.

Runs initialization tasks when the web gateway starts, including TTS announcements.
"""

import logging
import asyncio
import threading

logger = logging.getLogger(__name__)


def startup_announce_online():
    """Announce 'Systems Online' via TTS on startup (non-blocking)."""
    def _announce():
        try:
            from agent.tts_providers.piper import PiperTTSProvider
            import tempfile
            import subprocess

            provider = PiperTTSProvider()
            fd, path = tempfile.mkstemp(suffix=".wav")
            import os
            os.close(fd)
            
            provider.synthesize("Systems Online", path)
            
            # Try to play audio (best effort)
            try:
                subprocess.run(["aplay", path], capture_output=True, timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                try:
                    subprocess.run(["paplay", path], capture_output=True, timeout=5)
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    logger.debug("Audio playback not available; skipping startup announcement")
            
            try:
                os.unlink(path)
            except:
                pass
        except Exception as e:
            logger.debug("Startup TTS announcement failed: %s", e)
    
    # Run in background thread so it doesn't block startup
    thread = threading.Thread(target=_announce, daemon=True, name="startup-announce")
    thread.start()


def initialize_web_gateway():
    """Run initialization tasks for the web gateway."""
    logger.info("Jarvis Web Gateway initializing...")
    
    # Announce systems online
    startup_announce_online()
