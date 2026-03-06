from __future__ import annotations

from loguru import logger

from nanobot.utils.logging import JsonLogSink


def setup_logging_json() -> None:
    """Replace default loguru sink with JSON structured sink.

    Safe to call multiple times.
    """
    try:
        logger.remove()
    except Exception:
        pass
    logger.add(JsonLogSink().write, level="INFO")
