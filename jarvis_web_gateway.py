#!/usr/bin/env python3
"""Direct entry point for Jarvis Web Gateway.

Starts the web gateway without CLI overhead.
Usage:
  python -m jarvis_web_gateway
  jarvis web
"""

import logging
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from hermes_logging import setup_logging
from gateway.web_gateway import run as run_web_gateway


def main():
    """Start the Jarvis Web Gateway."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Launching Jarvis Web Gateway...")
    
    try:
        run_web_gateway(port=8765, host="127.0.0.1")
    except KeyboardInterrupt:
        logger.info("Web gateway shutdown by user")
    except Exception as e:
        logger.exception("Web gateway failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
