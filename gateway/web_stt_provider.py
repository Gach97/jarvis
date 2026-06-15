"""STT (Speech-to-Text) provider integration for web gateway.

Handles audio transcription via configured backend (local Whisper, OpenAI, Groq, etc.)
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


async def transcribe_audio_file(
    audio_path: str,
    stt_provider: str = "local",
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Transcribe an audio file to text.
    
    Args:
        audio_path: Path to audio file (WAV, MP3, etc.)
        stt_provider: One of "local", "openai", "groq"
        api_key: API key if required by provider
    
    Returns:
        Transcribed text, or None if transcription failed.
    """
    if not Path(audio_path).exists():
        logger.error("Audio file not found: %s", audio_path)
        return None
    
    try:
        if stt_provider == "local":
            return await _transcribe_local_whisper(audio_path)
        elif stt_provider == "openai":
            return await _transcribe_openai(audio_path, api_key)
        elif stt_provider == "groq":
            return await _transcribe_groq(audio_path, api_key)
        else:
            logger.warning("Unknown STT provider: %s", stt_provider)
            return None
    except Exception as e:
        logger.exception("Transcription failed: %s", e)
        return None


async def _transcribe_local_whisper(audio_path: str) -> Optional[str]:
    """Transcribe using local Whisper (requires faster-whisper package)."""
    try:
        from faster_whisper import WhisperModel
        
        # Load tiny model (fastest, lowest resource usage)
        model = WhisperModel("tiny")
        
        # Run transcription in executor to avoid blocking
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            lambda: model.transcribe(audio_path)
        )
        
        # Combine all segments
        text = " ".join(segment.text for segment in segments)
        
        if text.strip():
            logger.info("Local Whisper transcribed %s chars from %s", len(text), audio_path)
            return text.strip()
        
        return None
    except ImportError:
        logger.warning("Local Whisper not installed; install with: pip install faster-whisper")
        return None
    except Exception as e:
        logger.exception("Local Whisper transcription failed: %s", e)
        return None


async def _transcribe_openai(audio_path: str, api_key: Optional[str]) -> Optional[str]:
    """Transcribe using OpenAI Whisper API."""
    if not api_key:
        logger.error("OpenAI API key required for STT")
        return None
    
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        async def _call_openai():
            with open(audio_path, "rb") as f:
                transcript = await loop.run_in_executor(
                    None,
                    lambda: client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                    )
                )
            return transcript.text
        
        text = await _call_openai()
        
        if text.strip():
            logger.info("OpenAI Whisper transcribed %s chars from %s", len(text), audio_path)
            return text.strip()
        
        return None
    except Exception as e:
        logger.exception("OpenAI Whisper transcription failed: %s", e)
        return None


async def _transcribe_groq(audio_path: str, api_key: Optional[str]) -> Optional[str]:
    """Transcribe using Groq Whisper API."""
    if not api_key:
        logger.error("Groq API key required for STT")
        return None
    
    try:
        from groq import Groq
        
        client = Groq(api_key=api_key)
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        async def _call_groq():
            with open(audio_path, "rb") as f:
                transcript = await loop.run_in_executor(
                    None,
                    lambda: client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=f,
                    )
                )
            return transcript.text
        
        text = await _call_groq()
        
        if text.strip():
            logger.info("Groq Whisper transcribed %s chars from %s", len(text), audio_path)
            return text.strip()
        
        return None
    except Exception as e:
        logger.exception("Groq Whisper transcription failed: %s", e)
        return None
