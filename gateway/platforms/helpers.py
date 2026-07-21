# 🚪 Access - gateway/platforms/helpers.py
"""Shared helper classes for platform adapters."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def atomic_json_write(
    path: str | Path, data: Any, *, indent: int = 2, **kwargs
) -> None:
    """Minimal stub: write JSON data atomically via temp file + os.replace."""
    import os
    import tempfile

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, **kwargs)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class MessageDeduplicator:
    """TTL-based message deduplication cache."""

    def __init__(self, max_size: int = 2000, ttl_seconds: float = 300):
        self._seen: Dict[str, float] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def is_duplicate(self, msg_id: str) -> bool:
        if not msg_id:
            return False
        now = time.time()
        if msg_id in self._seen:
            if now - self._seen[msg_id] < self._ttl:
                return True
            del self._seen[msg_id]
        self._seen[msg_id] = now
        if len(self._seen) > self._max_size:
            cutoff = now - self._ttl
            self._seen = {k: v for k, v in self._seen.items() if v > cutoff}
            if len(self._seen) > self._max_size:
                newest = sorted(self._seen.items(), key=lambda x: x[1])[
                    -self._max_size :
                ]
                self._seen = dict(newest)
        return False

    def clear(self) -> None:
        self._seen.clear()


class TextBatchAggregator:
    """Aggregates rapid-fire text events into single messages."""

    def __init__(self, handler, batch_delay: float = 0.6, split_threshold: int = 1900):
        self._handler = handler
        self._batch_delay = batch_delay
        self._split_threshold = split_threshold
        self._pending: Dict[str, tuple] = {}

    def is_enabled(self) -> bool:
        return True

    def enqueue(self, event, session_key: str) -> None:
        pass


import re as _re

_RE_BOLD = _re.compile(r"\*\*(.+?)\*\*", _re.DOTALL)
_RE_ITALIC_STAR = _re.compile(r"\*(.+?)\*")
_RE_BOLD_UNDER = _re.compile(r"\b__(?![\s_])(.+?)(?<![\s_])__\b")
_RE_ITALIC_UNDER = _re.compile(r"\b_(?![\s_])(.+?)(?<![\s_])_\b")
_RE_CODE_BLOCK = _re.compile(r"```[a-zA-Z0-9_+-]*\n?")
_RE_INLINE_CODE = _re.compile(r"`(.+?)`")
_RE_HEADING = _re.compile(r"^#{1,6}\s+", _re.MULTILINE)
_RE_LINK = _re.compile(r"\[([^\]]+)\]\([^\)]+\)")
_RE_MULTI_NEWLINE = _re.compile(r"\n{3,}")


def strip_markdown(text: str) -> str:
    """Strip markdown formatting for plain-text platforms."""
    text = _RE_BOLD.sub(r"\1", text)
    text = _RE_ITALIC_STAR.sub(r"\1", text)
    text = _RE_BOLD_UNDER.sub(r"\1", text)
    text = _RE_ITALIC_UNDER.sub(r"\1", text)
    text = _RE_CODE_BLOCK.sub("", text)
    text = _RE_INLINE_CODE.sub(r"\1", text)
    text = _RE_HEADING.sub("", text)
    text = _RE_LINK.sub(r"\1", text)
    text = _RE_MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def redact_phone(phone: str) -> str:
    """Redact phone number for logging, preserving country code and last 4 digits."""
    if not phone:
        return "<none>"
    if len(phone) <= 8:
        return phone[:2] + "****" + phone[-2:] if len(phone) > 4 else "****"
    return phone[:4] + "****" + phone[-4:]


class ThreadParticipationTracker:
    """Tracks thread participation per platform for require_mention bypass logic."""

    def __init__(self, platform: str):
        self.platform = platform
        self._participating_threads: dict[str, float] = {}

    def track_thread(self, thread_id: str) -> None:
        import time

        self._participating_threads[thread_id] = time.time()

    def is_participating(self, thread_id: str) -> bool:
        import time

        cutoff = time.time() - 3600
        return self._participating_threads.get(thread_id, 0) > cutoff


# ─── GFM Markdown Table → Bullet Conversion ─────────────────────────
# Shared by Discord/Telegram adapters (discord uses convert_table_to_bullets
# directly; telegram uses is_table_row / TABLE_SEPARATOR_RE primitives).

import re as _re_tbl

TABLE_SEPARATOR_RE = _re_tbl.compile(
    r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*){1,}\|?\s*$"
)


def is_table_row(line: str) -> bool:
    """Return True if *line* could plausibly be a GFM table data row."""
    stripped = line.strip()
    return bool(stripped) and "|" in stripped


def split_markdown_table_row(line: str) -> list[str]:
    """Split a GFM table row into stripped cell values."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _render_table_block(table_block: list[str]) -> str:
    """Render a detected GFM table as bold-heading + bullet groups."""
    if len(table_block) < 3:
        return "\n".join(table_block)
    headers = split_markdown_table_row(table_block[0])
    if len(headers) < 2:
        return "\n".join(table_block)
    first_data_row = (
        split_markdown_table_row(table_block[2])
        if len(table_block) > 2
        else []
    )
    has_row_label_col = len(first_data_row) == len(headers) + 1

    rendered_groups: list[str] = []
    for index, row in enumerate(table_block[2:], start=1):
        cells = split_markdown_table_row(row)
        if has_row_label_col:
            heading = cells[0] if cells and cells[0] else f"Row {index}"
            data_cells = cells[1:]
        else:
            heading = next((cell for cell in cells if cell), f"Row {index}")
            data_cells = cells

        if len(data_cells) < len(headers):
            data_cells.extend([""] * (len(headers) - len(data_cells)))
        elif len(data_cells) > len(headers):
            data_cells = data_cells[: len(headers)]

        bullets: list[str] = []
        for header, value in zip(headers, data_cells):
            if not has_row_label_col and value == heading:
                continue
            bullets.append(f"• {header}: {value}")
        group_lines = [f"**{heading}**", *bullets]
        rendered_groups.append("\n".join(group_lines))
    return "\n\n".join(rendered_groups)


def convert_table_to_bullets(text: str) -> str:
    """Rewrite GFM pipe tables into bold-heading + bullet groups.

    Tables inside fenced code blocks are left alone.
    """
    if "|" not in text or "-" not in text:
        return text

    lines = text.split("\n")
    out: list[str] = []
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue
        if (
            "|" in line
            and i + 1 < len(lines)
            and TABLE_SEPARATOR_RE.match(lines[i + 1])
        ):
            table_block = [line, lines[i + 1]]
            j = i + 2
            while j < len(lines) and is_table_row(lines[j]):
                table_block.append(lines[j])
                j += 1
            out.append(_render_table_block(table_block))
            i = j
            continue
        out.append(line)
        i += 1
    return "\n".join(out)
