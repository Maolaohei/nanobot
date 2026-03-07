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

    # AdapterHub wiring (non-fatal if config missing)
    try:
        from nanobot.config.schema import AppSettings
        from nanobot.utils.adapter_wiring import build_adapter_hub

        settings = AppSettings()  # pydantic-settings based
        _adapter_hub = build_adapter_hub(settings)
        _ = _adapter_hub  # keep reference for potential future use
    except Exception:
        # keep startup resilient
        pass

    app()
