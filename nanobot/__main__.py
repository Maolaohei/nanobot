"""
Entry point for running nanobot as a module: python -m nanobot
"""

import os

from nanobot.utils.log_setup import setup_logging_json
from nanobot.utils.tracing import setup_tracing
from nanobot.cli.commands import app
from nanobot import runtime_policy as RP

if __name__ == "__main__":
    # Structured logging optional by Feature Flag (defaults off in minimal profile)
    try:
        if os.environ.get("NANOBOT__FEATURES__STRUCTURED_LOGGING", "false").lower() not in {"0", "false", "no"}:
            setup_logging_json()
    except Exception:
        pass

    # Optional tracing via env (no hard dependency)
    try:
        if os.environ.get("NANOBOT_TRACING_ENABLED", "false").lower() not in {"0", "false", "no"}:
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
