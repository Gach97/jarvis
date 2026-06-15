"""Minimal Piper TTS provider skeleton for Jarvis.

This provider implements the TTSProvider ABC and writes a short
silent WAV file for demo/placeholder purposes. Replace with a real
Piper SDK integration when available.
"""
from __future__ import annotations

import wave
import os
from typing import Any, Dict, List, Optional

from agent.tts_provider import TTSProvider, DEFAULT_OUTPUT_FORMAT


class PiperTTSProvider(TTSProvider):
    @property
    def name(self) -> str:
        return "piper"

    def is_available(self) -> bool:
        # Minimal availability check — in real implementation verify SDK
        return True

    def list_voices(self) -> List[Dict[str, Any]]:
        return [{"id": "default", "display": "Piper Default"}]

    def synthesize(
        self,
        text: str,
        output_path: str,
        *,
        voice: Optional[str] = None,
        model: Optional[str] = None,
        speed: Optional[float] = None,
        format: str = DEFAULT_OUTPUT_FORMAT,
        **extra: Any,
    ) -> str:
        # Write a 0.5s silent WAV as a placeholder. Always produce WAV.
        # If caller asked mp3/ogg, we still write a .wav file at output_path.
        n_channels = 1
        sampwidth = 2
        framerate = 16000
        duration_s = 0.5
        n_frames = int(framerate * duration_s)

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(framerate)
            wf.writeframes(b"\x00" * n_frames * n_channels * sampwidth)

        return output_path
