"""Configuration persistence for Jarvis Web Gateway setup.

Saves and loads setup credentials to/from ~/.jarvis/config.yaml.
"""

import logging
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)


def load_web_config() -> Optional[Dict[str, str]]:
    """Load web gateway config from ~/.jarvis/config.yaml."""
    try:
        config_path = get_hermes_home() / "config.yaml"
        
        if not config_path.exists():
            logger.debug("No config file found at %s", config_path)
            return None
        
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
        
        # Extract web section
        web_config = config.get("web", {})
        
        return {
            "apiKey": web_config.get("api_key"),
            "provider": web_config.get("provider", "openrouter"),
            "model": web_config.get("model"),
            "ttsProvider": web_config.get("tts_provider", "piper"),
            "sttProvider": web_config.get("stt_provider", "local"),
        }
    except Exception as e:
        logger.exception("Failed to load web config: %s", e)
        return None


def save_web_config(
    api_key: str,
    provider: str = "openrouter",
    model: str = "",
    tts_provider: str = "piper",
    stt_provider: str = "local",
) -> bool:
    """Save web gateway config to ~/.jarvis/config.yaml."""
    try:
        config_path = get_hermes_home() / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        
        # Update web section
        if "web" not in config:
            config["web"] = {}
        
        config["web"].update({
            "api_key": api_key,
            "provider": provider,
            "model": model,
            "tts_provider": tts_provider,
            "stt_provider": stt_provider,
        })
        
        # Write config
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info("Web config saved to %s", config_path)
        return True
    except Exception as e:
        logger.exception("Failed to save web config: %s", e)
        return False
