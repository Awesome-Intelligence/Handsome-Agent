#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WisdomMixin — 哲学语录异步生成

🚪 Access - 💬 TUI - Textual App - Wisdom

依赖主类的 ``self._agent`` / ``self._widget_cache`` / ``self._banner_cache`` / ``self._logger``。
"""

from __future__ import annotations

import asyncio
import logging

from .imports import RichText


class WisdomMixin:
    """哲学语录 Mixin."""

    _logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Wisdom（异步生成）
    # ------------------------------------------------------------------

    def _generate_wisdom_async(self) -> None:
        """后台异步生成哲学语录并更新 Banner 显示."""
        try:
            agent = self._get_agent()
            if not agent or not agent.llm_provider:
                return

            from common.i18n import get_language

            lang = get_language()
            lang_prompt = {"zh": "中文", "en": "English"}.get(lang, "English")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 一次简单 LLM 调用
                response = loop.run_until_complete(
                    agent.llm_provider.generate(
                        prompt=(
                            f"Give me one short philosophical quote "
                            f"(max 25 characters) in {lang_prompt} about life, "
                            f"existence, or wisdom. Only return the quote, nothing else."
                        ),
                        max_tokens=60,
                        temperature=1.0,
                    )
                )
                wisdom = (
                    response.content.strip() if response and response.content else None
                )
                if wisdom:
                    # LLM 常把语录包在引号里，去掉首尾各类引号。
                    wisdom = wisdom.strip("\"'“”‘’「」『』 ")
            finally:
                loop.close()

            if wisdom:
                version_widget = self._widget_cache.get("version_info")
                if version_widget and self._banner_cache.get("version"):
                    version_text = RichText.from_markup(
                        f"[dim]{self._banner_cache['version']}[/] "
                        f"[dim]·[/] [italic dim]{wisdom}[/]"
                    )
                    version_widget.update(version_text)
        except Exception:
            pass  # 静默失败，用户看到的是 fallback


__all__ = ["WisdomMixin"]
