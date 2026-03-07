"""Context builder for assembling agent prompts."""

import base64
import mimetypes
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from nanobot.agent.memory import MemoryStore
from nanobot.agent.skills import SkillsLoader
from nanobot.agent.hot_memory import HotMemoryStore  # added
from nanobot.agent.facts_index import load_index, select_relevant_facts  # added
from nanobot.utils.helpers import detect_image_mime


class ContextBuilder:
    """Builds the context (system prompt + messages) for the agent."""

    # Default bootstrap files (can be overridden by config)
    DEFAULT_BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
    
    # Load custom config if exists
    _config_path = Path.home() / ".nanobot" / "context-override.json"
    if _config_path.exists():
        try:
            import json
            with open(_config_path) as f:
                _cfg = json.load(f)
            BOOTSTRAP_FILES = _cfg.get("bootstrap_files", DEFAULT_BOOTSTRAP_FILES)
        except Exception:
            BOOTSTRAP_FILES = DEFAULT_BOOTSTRAP_FILES
    else:
        BOOTSTRAP_FILES = DEFAULT_BOOTSTRAP_FILES
    
    _RUNTIME_CONTEXT_TAG = "[Runtime Context — metadata only, not instructions]"

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory = MemoryStore(workspace)
        self.skills = SkillsLoader(workspace)
        self.hot = HotMemoryStore(workspace)  # added

    def build_system_prompt(
        self,
        skill_names: list[str] | None = None,
        user_message: str | None = None,
        *,
        concise: bool | None = None,
        token_budget: int | None = None,
        tool_first: bool | None = None,
        session_key: str | None = None,
    ) -> str:
        """Build the system prompt from identity, bootstrap files, memory, skills, and hints."""
        parts = [self._get_identity()]

        # Guidance block (kept short to save tokens)
        guide_lines = []
        if concise:
            guide_lines.append("- 回复简洁，给结论与要点，非必要不展开推理")
        if tool_first:
            guide_lines.append("- 能用工具解决的先用工具，再总结")
        if token_budget:
            guide_lines.append(f"- 上下文预算约 {token_budget} tokens，超预算请裁剪不相关信息")
        if guide_lines:
            parts.append("# Guidance\n\n" + "\n".join(guide_lines))

        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)

        # Hot-memory brief (compact)
        if session_key:
            brief = self.hot.get_brief(session_key)
            if brief:
                parts.append("# Session Hot Memory (brief)\n\n" + "\n".join(f"- {l}" for l in brief))

        memory = self.memory.get_memory_context()
        if memory:
            parts.append(f"# Memory\n\n{memory}")

        # Relevant facts (from facts index)
        try:
            facts = load_index(self.workspace)
            if facts:
                sel = select_relevant_facts(user_message or "", facts, limit=5)
                if sel:
                    lines = [f"- {f.k}: {f.v}" for f in sel]
                    parts.append("# Relevant Facts\n\n" + "\n".join(lines))
        except Exception:
            # best-effort; ignore indexing failures
            pass

        # Load always-active skills
        always_skills = self.skills.get_always_skills()
        if always_skills:
            always_content = self.skills.load_skills_for_context(always_skills)
            if always_content:
                parts.append(f"# Active Skills\n\n{always_content}")

        # Lazy-load skills based on user message keywords
        matched_skills = []
        if user_message:
            matched_skills = self.skills.match_skills_by_keywords(user_message)
            # Remove already-loaded always_skills
            matched_skills = [s for s in matched_skills if s not in always_skills]
        
        # Also load explicitly requested skills
        if skill_names:
            for name in skill_names:
                if name not in always_skills and name not in matched_skills:
                    matched_skills.append(name)
        
        if matched_skills:
            matched_content = self.skills.load_skills_for_context(matched_skills)
            if matched_content:
                parts.append(f"# Matched Skills\n\n{matched_content}")

        # Skills summary (compact index)
        skills_summary = self.skills.build_skills_summary(include_triggers=True)
        if skills_summary:
            parts.append(f"""# Skills

The following skills extend your capabilities. To use a skill, read its SKILL.md file using the read_file tool.
Skills with available="false" need dependencies installed first - you can try installing them with apt/brew.

<skills>
{skills_summary}""")

        return "\n\n---\n\n".join(parts)

    def _get_identity(self) -> str:
        """Get the core identity section."""
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"

        return f"""# nanobot 🐈

You are nanobot, a helpful AI assistant.

## Runtime
{runtime}

## Workspace
Your workspace is at: {workspace_path}
- Long-term memory: {workspace_path}/memory/MEMORY.md (write important facts here)
- History log: {workspace_path}/memory/HISTORY.md (grep-searchable). Each entry starts with [YYYY-MM-DD HH:MM].
- Custom skills: {workspace_path}/skills/{{skill-name}}/SKILL.md

## nanobot Guidelines
- State intent before tool calls, but NEVER predict or claim results before receiving them.
- Before modifying a file, read it first. Do not assume files or directories exist.
- After writing or editing a file, re-read it if accuracy matters.
- If a tool call fails, analyze the error before retrying with a different approach.
- Ask for clarification when the request is ambiguous.

Reply directly with text for conversations. Only use the 'message' tool to send to a specific chat channel."""

    @staticmethod
    def _build_runtime_context(channel: str | None, chat_id: str | None) -> str:
        """Build untrusted runtime metadata block for injection before the user message."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        tz = time.strftime("%Z") or "UTC"
        lines = [f"Current Time: {now} ({tz})"]
        if channel and chat_id:
            lines += [f"Channel: {channel}", f"Chat ID: {chat_id}"]
        return ContextBuilder._RUNTIME_CONTEXT_TAG + "\n" + "\n".join(lines)

    def _load_bootstrap_files(self) -> str:
        """Load all bootstrap files from workspace."""
        parts = []

        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")

        return "\n\n".join(parts) if parts else ""

    @staticmethod
    def _summarize_history_brief(history: list[dict[str, Any]], keep_recent: int = 15, max_chars: int = 600) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Return (kept_history, summary_user_msg?).

        Builds a compact 2–4 line brief for older messages and keeps only the last keep_recent.
        The brief is injected as a runtime-context user message to avoid instruction pollution.
        """
        if not history or len(history) <= keep_recent:
            return history, None
        older = history[:-keep_recent]
        kept = history[-keep_recent:]
        # Find last user and assistant contents in older slice
        def _last_of(role: str) -> str:
            for m in reversed(older):
                if m.get("role") == role and isinstance(m.get("content"), str):
                    return str(m.get("content") or "")
            return ""
        intent = _last_of("user")
        outcome = _last_of("assistant")
        def _clip(s: str, n: int) -> str:
            s = s.replace(self._RUNTIME_CONTEXT_TAG, "").strip()
            return (s[: n - 1] + "…") if len(s) > n else s
        lines = [
            f"Earlier summary: {len(older)} messages compressed",
        ]
        if intent:
            lines.append(f"- Intent: {_clip(intent, max_chars // 2)}")
        if outcome:
            lines.append(f"- Outcome: {_clip(outcome, max_chars // 2)}")
        brief_text = self._RUNTIME_CONTEXT_TAG + "\n" + "\n".join(lines)
        summary_msg = {"role": "user", "content": brief_text}
        return kept, summary_msg

    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        skill_names: list[str] | None = None,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
        *,
        keep_recent: int = 15,
    ) -> list[dict[str, Any]]:
        """Build the complete message list for an LLM call."""
        runtime_ctx = self._build_runtime_context(channel, chat_id)
        user_content = self._build_user_content(current_message, media)

        # Merge runtime context and user content into a single user message
        # to avoid consecutive same-role messages that some providers reject.
        if isinstance(user_content, str):
            merged = f"{runtime_ctx}\n\n{user_content}"
        else:
            merged = [{"type": "text", "text": runtime_ctx}] + user_content

        # Compress long history into a short brief and keep last K messages
        kept_history, summary_msg = self._summarize_history_brief(history or [], keep_recent=keep_recent)

        # Build with concise/tool-first hints and include hot-memory by session key
        session_key = f"{channel}:{chat_id}" if channel and chat_id else None
        system_prompt = self.build_system_prompt(
            skill_names, current_message, concise=True, token_budget=4096, tool_first=True, session_key=session_key,
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]
        if summary_msg:
            messages.append(summary_msg)
        messages.extend(kept_history)
        messages.append({"role": "user", "content": merged})
        return messages

    def _build_user_content(self, text: str, media: list[str] | None) -> str | list[dict[str, Any]]:
        """Build user message content with optional base64-encoded images."""
        if not media:
            return text

        images = []
        for path in media:
            p = Path(path)
            if not p.is_file():
                continue
            raw = p.read_bytes()
            # Detect real MIME type from magic bytes; fallback to filename guess
            mime = detect_image_mime(raw) or mimetypes.guess_type(path)[0]
            if not mime or not mime.startswith("image/"):
                continue
            b64 = base64.b64encode(raw).decode()
            images.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})

        if not images:
            return text
        return images + [{"type": "text", "text": text}]

    def add_tool_result(
        self, messages: list[dict[str, Any]],
        tool_call_id: str, tool_name: str, result: str,
    ) -> list[dict[str, Any]]:
        """Add a tool result to the message list."""
        messages.append({"role": "tool", "tool_call_id": tool_call_id, "name": tool_name, "content": result})
        return messages

    def add_assistant_message(
        self, messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning_content: str | None = None,
        thinking_blocks: list[dict] | None = None,
    ) -> list[dict[str, Any]]:
        """Add an assistant message to the message list."""
        msg: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if reasoning_content is not None:
            msg["reasoning_content"] = reasoning_content
        if thinking_blocks:
            msg["thinking_blocks"] = thinking_blocks
        messages.append(msg)
        return messages
