"""
Entry point for running nanobot as a module: python -m nanobot
"""

from nanobot.utils.log_setup import setup_logging_json
from nanobot.utils.tracing import setup_tracing
from nanobot.cli.commands import app

if __name__ == "__main__":
    # Minimal structured logging by default
    try:
        setup_logging_json()
    except Exception:
        pass

    # Optional tracing via env (no hard dependency)
    try:
        setup_tracing()
    except Exception:
        pass

    app()
