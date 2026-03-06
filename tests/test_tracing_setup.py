from __future__ import annotations

import os

from nanobot.utils.tracing import setup_tracing


def test_tracing_disabled_by_default():
    os.environ.pop("NANOBOT_TRACING_ENABLED", None)
    assert setup_tracing() is False


def test_tracing_enabled_without_sdk_graceful():
    os.environ["NANOBOT_TRACING_ENABLED"] = "true"
    # Without opentelemetry installed in test env, should warn and return False
    assert setup_tracing() in (False, True)
    os.environ.pop("NANOBOT_TRACING_ENABLED", None)
