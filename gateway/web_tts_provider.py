"""TTS (Text-to-Speech) streaming provider for web gateway.

Handles response synthesis and streaming back to browser via WebSocket.
"""

import logging
import base64
import tempfile
import os
from pathlib import Path
from typing import Optional, AsyncIterator

logger = logging.getLogger(__name__)


async def synthesize_and_stream(
    text: str,
    tts_provider: str = "piper",
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Synthesize text to audio and return base64-encoded audio data.
    
    Args:
        text: Text to synthesize
        tts_provider: One of "piper", "openai", "elevenlabs"
        api_key: API key if required by provider
    
    Returns:
        Base64-encoded audio data (WAV format), or None if synthesis failed.
    """
    if not text or not text.strip():
        return None
    
    try:
        if tts_provider == "piper":
            return await _synthesize_piper(text)
        elif tts_provider == "openai":
            return await _synthesize_openai(text, api_key)
        elif tts_provider == "elevenlabs":
            return await _synthesize_elevenlabs(text, api_key)
        else:
            logger.warning("Unknown TTS provider: %s", tts_provider)
            return None
    except Exception as e:
        logger.exception("TTS synthesis failed: %s", e)
        return None


async def _synthesize_piper(text: str) -> Optional[str]:
    """Synthesize using local Piper TTS."""
    try:
        from agent.tts_providers.piper import PiperTTSProvider
        import asyncio
        
        provider = PiperTTSProvider()
        
        # Create temp file
        fd, output_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
        try:
            # Run synthesis in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: provider.synthesize(text, output_path)
            )
            
            # Read and encode as base64
            with open(output_path, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode()
            
            logger.info("Piper TTS synthesized %s chars", len(text))
            return audio_data
        finally:
            try:
                os.unlink(output_path)
            except:
                pass
    except Exception as e:
        logger.exception("Piper TTS synthesis failed: %s", e)
        return None


async def _synthesize_openai(text: str, api_key: Optional[str]) -> Optional[str]:
    """Synthesize using OpenAI Text-to-Speech API."""
    if not api_key:
        logger.error("OpenAI API key required for TTS")
        return None
    
    try:
        from openai import OpenAI
        import asyncio
        
        client = OpenAI(api_key=api_key)
        
        # Create temp file
        fd, output_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        
        try:
            # Run in executor
            loop = asyncio.get_event_loop()
            
            def _call_openai():
                response = client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=text,
                )
                response.stream_to_file(output_path)
            
            await loop.run_in_executor(None, _call_openai)
            
            # Read and encode as base64
            with open(output_path, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode()
            
            logger.info("OpenAI TTS synthesized %s chars", len(text))
            return audio_data
        finally:
            try:
                os.unlink(output_path)
            except:
                pass
    except Exception as e:
        logger.exception("OpenAI TTS synthesis failed: %s", e)
        return None


async def _synthesize_elevenlabs(text: str, api_key: Optional[str]) -> Optional[str]:
    """Synthesize using ElevenLabs Text-to-Speech API."""
    if not api_key:
        logger.error("ElevenLabs API key required for TTS")
        return None
    
    try:
        from elevenlabs.client import ElevenLabs
        import asyncio
        
        client = ElevenLabs(api_key=api_key)
        
        # Create temp file
        fd, output_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        
        try:
            # Run in executor
            loop = asyncio.get_event_loop()
            
            def _call_elevenlabs():
                audio = client.text_to_speech.convert(
                    text=text,
                    voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel voice
                    model_id="eleven_monolingual_v1",
                )
                with open(output_path, "wb") as f:
                    for chunk in audio:
                        f.write(chunk)
            
            await loop.run_in_executor(None, _call_elevenlabs)
            
            # Read and encode as base64
            with open(output_path, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode()
            
            logger.info("ElevenLabs TTS synthesized %s chars", len(text))
            return audio_data
        finally:
            try:
                os.unlink(output_path)
            except:
                pass
    except Exception as e:
        logger.exception("ElevenLabs TTS synthesis failed: %s", e)
        return None
