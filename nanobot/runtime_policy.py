"""Runtime policy defaults for minimal, token-efficient behavior.

These are code-level defaults used when env is absent.
"""
from __future__ import annotations

# Prompt/behavior
CONCISE_MODE: bool = True
TOOL_FIRST: bool = True

# Token budgets (aligned with v6.1 minimal profile)
TOKEN_BUDGET: int = 10240
USER_MEMORY_BUDGET: int = 10240

# Context/history
HISTORY_KEEP_RECENT: int = 12

# Memory injection budgets
MEMORY_BUDGET_MAX_LINES: int = 8
HOTMEMORY_LINES: int = 4
FACTS_LIMIT: int = 4

# HTTP/runtime
CACHE_ENABLED_DEFAULT: bool = True
HTTP_RATE_LIMIT_ENABLED_DEFAULT: bool = True
WEB_TTL_SECONDS: int = 60

# Skills injection in prompt
USE_MINIMAL_BOOTSTRAP_DEFAULT: bool = True
INCLUDE_SKILL_DOCS_DEFAULT: bool = False

# Media and pipelines (advisory constants; used by skills/pipelines)
PIXIV_MIN_BOOKMARKS: int = 10000
PIXIV_BATCH_SIZE: int = 6
PIXIV_AI_CONTENT_POLICY: str = "non-ai-priority"  # non-ai first, soft-filter AI

"""
This module centralizes code-level defaults so that missing env will not
inflate tokens or degrade behavior. Flags can still override via env vars.
"""
