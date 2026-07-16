#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internationalization (i18n) Module for Agent-Z

Provides multilingual support for user-facing messages.
Supports: Chinese (zh), English (en), Korean (ko), Japanese (ja)

This module combines:
1. YAML catalog files (common/locales/*.yaml) - for setup wizard and CLI messages
2. Embedded translations - for agent flow messages

Language resolution order:
    1. Explicit ``lang`` argument passed to :func:`t`
    2. ``AGENTZ_LANGUAGE`` environment variable (for tests / quick override)
    3. ``language`` from config.yaml
    4. ``"zh"`` (Chinese default for Agent-Z)

Supported languages: en, zh, ja, ko.
"""

from __future__ import annotations

import logging
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES: tuple[str, ...] = (
    "en", "zh", "ja", "ko",
)
DEFAULT_LANGUAGE = "zh"  # Chinese default for Agent-Z

# Language aliases - maps natural language names to supported codes
_LANGUAGE_ALIASES: dict[str, str] = {
    # English
    "english": "en", "en-us": "en", "en-gb": "en",
    # Chinese - Simplified (default)
    "chinese": "zh", "mandarin": "zh", "zh-cn": "zh", "zh-hans": "zh", "zh-sg": "zh",
    # Japanese
    "japanese": "ja", "jp": "ja", "ja-jp": "ja",
    # Korean
    "korean": "ko", "한국어": "ko", "ko-kr": "ko",
}

_catalog_cache: dict[str, dict[str, str]] = {}
_catalog_lock = threading.Lock()


def _locales_dir() -> Path:
    """Return the directory containing locale YAML files.

    Lives under common/ so both bundled install and editable
    checkouts find it without PYTHONPATH gymnastics.
    """
    # common/i18n.py -> common/ -> project root -> common/locales/
    return Path(__file__).resolve().parent / "locales"


def _normalize_lang(value: Any) -> str:
    """Normalize a user-supplied language value to a supported code.

    Accepts supported codes directly, common aliases (``chinese`` -> ``zh``),
    and case-insensitive regional tags (``zh-CN`` -> ``zh``).  Returns the
    default language for unknown values.
    """
    if not isinstance(value, str):
        return DEFAULT_LANGUAGE
    key = value.strip().lower()
    if not key:
        return DEFAULT_LANGUAGE
    if key in SUPPORTED_LANGUAGES:
        return key
    if key in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[key]
    # Try stripping a region suffix (e.g. "zh-CN" -> "zh")
    base = key.split("-", 1)[0]
    if base in SUPPORTED_LANGUAGES:
        return base
    return DEFAULT_LANGUAGE


def _load_catalog(lang: str) -> dict[str, str]:
    """Load and flatten one locale YAML file into a dotted-key dict.

    YAML files can be nested for human readability; this produces the flat
    key space :func:`t` expects.  Cached per-language for the process.
    """
    with _catalog_lock:
        cached = _catalog_cache.get(lang)
        if cached is not None:
            return cached

    path = _locales_dir() / f"{lang}.yaml"
    if not path.is_file():
        logger.debug("i18n catalog missing for %s at %s", lang, path)
        with _catalog_lock:
            _catalog_cache[lang] = {}
        return {}

    try:
        import yaml  # PyYAML is already a dependency
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.warning("Failed to load i18n catalog %s: %s", path, exc)
        with _catalog_lock:
            _catalog_cache[lang] = {}
        return {}

    flat: dict[str, str] = {}
    _flatten_into(raw, "", flat)
    with _catalog_lock:
        _catalog_cache[lang] = flat
    return flat


def _flatten_into(node: Any, prefix: str, out: dict[str, str]) -> None:
    """Recursively flatten a nested dict into dotted keys."""
    if isinstance(node, dict):
        for key, value in node.items():
            child_key = f"{prefix}.{key}" if prefix else str(key)
            _flatten_into(value, child_key, out)
    elif isinstance(node, str):
        out[prefix] = node
    # Non-string, non-dict leaves are ignored -- catalogs are text-only.


@lru_cache(maxsize=1)
def _config_language_cached() -> str | None:
    """Read ``language`` from config.yaml once per process.

    Cached because ``t()`` is called in hot paths and re-reading YAML
    each call would be wasteful.  ``reset_language_cache()`` clears this
    when config changes at runtime (e.g. after the setup wizard).
    """
    try:
        config_dir = Path.home() / ".agent_z"
        config_file = config_dir / "config.json"
        if config_file.exists():
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                lang = cfg.get("language")
                if lang:
                    return _normalize_lang(lang)
    except Exception as exc:
        logger.debug("Could not read language from config: %s", exc)
    return None


def reset_language_cache() -> None:
    """Invalidate cached language resolution and catalogs.

    Call after config changes at runtime (e.g. after the setup wizard).
    """
    _config_language_cached.cache_clear()
    with _catalog_lock:
        _catalog_cache.clear()


def get_language() -> str:
    """Resolve the active language using env > config > default order."""
    # 1. HERMES_LANGUAGE or AGENTZ_LANGUAGE environment variable
    env_lang = os.environ.get("HERMES_LANGUAGE") or os.environ.get("AGENTZ_LANGUAGE")
    if env_lang:
        return _normalize_lang(env_lang)
    # 2. Config file language setting
    cfg_lang = _config_language_cached()
    if cfg_lang:
        return cfg_lang
    # 3. Default
    return DEFAULT_LANGUAGE


def t(
    key: str,
    lang: str | None = None,
    fallback: str | None = None,
    **format_kwargs: Any,
) -> str:
    """Translate a dotted key to the active language.

    Parameters
    ----------
    key
        Dotted path into the catalog, e.g. ``"setup.banner.title"``.
    lang
        Explicit language override.  Takes precedence over env + config.
    fallback
        Optional string to return when the key is missing in *all*
        catalogs (target language + default).  When provided, ``fallback``
        is formatted with ``format_kwargs`` instead of the raw key, so
        callers can supply developer-friendly English text without
        registering a new catalog entry.
    **format_kwargs
        ``str.format`` substitution arguments
        (e.g. ``t("setup.banner.title", name="John")`` expects a catalog entry
        with a ``{name}`` placeholder).

    Returns
    -------
    The translated string, or the explicit ``fallback`` if provided and
    the key is missing, or the bare key as a last-ditch default.
    """
    target = _normalize_lang(lang) if lang else get_language()
    catalog = _load_catalog(target)
    value = catalog.get(key)

    if value is None and target != DEFAULT_LANGUAGE:
        # Fall through to default language rather than showing a key path
        value = _load_catalog(DEFAULT_LANGUAGE).get(key)

    if value is None:
        # Last-ditch: caller-supplied fallback, else the bare key
        if fallback is not None:
            value = fallback
        else:
            logger.debug("i18n miss: key=%r lang=%r", key, target)
            value = key

    if format_kwargs:
        try:
            return value.format(**format_kwargs)
        except (KeyError, IndexError, ValueError) as exc:
            logger.warning(
                "i18n format failed for key=%r lang=%r kwargs=%r: %s",
                key, target, format_kwargs, exc,
            )
            return value
    return value


# =============================================================================
# Legacy I18n class for backward compatibility
# =============================================================================

LAYER_EMOJI = {
    "access": "🚪",
    "decision": "🧠",
    "execution": "🏃",
}


class I18n:
    """Internationalization handler for agent messages (legacy support)."""

    # Legacy translations for agent flow messages
    TRANSLATIONS: dict[str, dict[str, str]] = {
        "zh": {
            "flow_start": "开始处理用户输入",
            "validation_pass": "输入格式验证通过",
            "session_add": "添加用户消息到会话",
            "cache_hit": "缓存命中，跳过处理",
            "cache_miss": "缓存未命中，执行正常流程",
            "processing_start": "开始处理请求",
            "routing_enabled": "启用路由功能，开始意图分类",
            "routing_match": "找到匹配的路由",
            "routing_no_match": "未找到匹配的路由，尝试技能执行",
            "skill_enabled": "启用技能执行，开始意图分类",
            "skill_discovery": "发现相关技能",
            "skill_execute": "执行技能",
            "skill_success": "技能执行成功",
            "skill_fail": "技能执行失败",
            "explanation_module": "使用解释模块生成响应",
            "response_complete": "响应生成完成",
            "session_add_assistant": "添加助手响应到会话",
            "cache_store": "存储响应到缓存",
            "complete": "响应生成完成",
            "intent_classifying": "正在对输入进行意图分类",
            "intent_result": "分类结果",
            "intent_final": "最终意图",
            "intent_default": "未匹配到关键词，默认使用",
            "router_checking": "检查注册的路由",
            "router_found": "找到匹配路由",
            "skill_discovery_start": "开始技能发现",
            "skill_manager_execute": "尝试执行技能",
            "skill_not_found": "技能未找到",
            "skill_detail": "技能详情",
            "skill_validate_fail": "参数验证失败",
            "skill_execute_start": "参数验证通过，开始执行",
            "skill_execute_success": "技能执行成功",
            "skill_execute_error": "技能执行异常",
            "session_add_msg": "添加消息",
            "session_trim": "历史记录已修剪",
            "flow_header": "=" * 70,
            "step_input": "接收用户输入",
            "step_validation": "输入格式验证通过",
            "step_session": "消息已添加到会话",
            "step_cache_hit": "缓存命中，跳过处理",
            "step_cache_miss": "缓存未命中，执行正常流程",
            "step_processing": "开始处理请求",
            "step_routing": "进入任务路由模块",
            "step_skill": "进入技能管理器",
            "step_explanation": "调用解释模块处理请求",
            "step_complete": "🚪 [完成] 总耗时",
            "layer_access": "[接入层]",
            "layer_decision": "[决策层]",
            "layer_execution": "[执行层]",
            "subtitle": "今天的你，也很帅气",
        },
        "en": {
            "flow_start": "🚪 [Access Layer] Starting to process user input",
            "validation_pass": "🧠 [Decision Layer] Input validation passed",
            "session_add": "🏃 [Execution Layer] Adding user message to session",
            "cache_hit": "🧠 [Decision Layer] Cache hit, skipping processing",
            "cache_miss": "🧠 [Decision Layer] Cache miss, continuing normal flow",
            "processing_start": "🧠 [Decision Layer] Starting request processing",
            "routing_enabled": "🧠 [Decision Layer] Routing enabled, starting intent classification",
            "routing_match": "🧠 [Decision Layer] Found matching route",
            "routing_no_match": "🧠 [Decision Layer] No matching route found, trying skills",
            "skill_enabled": "🧠 [Decision Layer] Skills enabled, starting intent classification",
            "skill_discovery": "🧠 [Decision Layer] Found relevant skills",
            "skill_execute": "🏃 [Execution Layer] Executing skill",
            "skill_success": "🧠 [Decision Layer] Skill executed successfully",
            "skill_fail": "🧠 [Decision Layer] Skill execution failed",
            "explanation_module": "🧠 [Decision Layer] Using explanation module to generate response",
            "response_complete": "🧠 [Decision Layer] Response generation complete",
            "session_add_assistant": "🏃 [Execution Layer] Adding assistant response to session",
            "cache_store": "🧠 [Decision Layer] Storing response to cache",
            "complete": "🚪 [Complete] Response generation complete",
            "intent_classifying": "🧠 [Decision Layer] Classifying intent for input",
            "intent_result": "🧠 [Decision Layer] Classification result",
            "intent_final": "🧠 [Decision Layer] Final intent",
            "intent_default": "🧠 [Decision Layer] No keywords matched, using default",
            "router_checking": "🧠 [Decision Layer] Checking registered routes",
            "router_found": "🧠 [Decision Layer] Found matching routes",
            "skill_discovery_start": "🧠 [Decision Layer] Starting skill discovery",
            "skill_manager_execute": "🏃 [Execution Layer] Attempting to execute skill",
            "skill_not_found": "🧠 [Decision Layer] Skill not found",
            "skill_detail": "🏃 [Execution Layer] Skill details",
            "skill_validate_fail": "🧠 [Decision Layer] Parameter validation failed",
            "skill_execute_start": "🏃 [Execution Layer] Parameter validation passed, executing",
            "skill_execute_success": "🧠 [Decision Layer] Skill executed successfully",
            "skill_execute_error": "🧠 [Decision Layer] Skill execution error",
            "session_add_msg": "🏃 [Execution Layer] Adding message",
            "session_trim": "🏃 [Execution Layer] History trimmed",
            "flow_header": "=" * 70,
            "step_input": "🚪 [Access Layer] Received user input",
            "step_validation": "🧠 [Decision Layer] Input validation passed",
            "step_session": "🏃 [Execution Layer] Message added to session",
            "step_cache_hit": "🧠 [Decision Layer] Cache hit, skipping",
            "step_cache_miss": "🧠 [Decision Layer] Cache miss, continuing",
            "step_processing": "🧠 [Decision Layer] Starting processing",
            "step_routing": "🧠 [Decision Layer] Entering task router",
            "step_skill": "🏃 [Execution Layer] Entering skill manager",
            "step_explanation": "🧠 [Decision Layer] Calling explanation module",
            "step_complete": "🚪 [Complete] Total time",
            "layer_access": "[Access Layer]",
            "layer_decision": "[Decision Layer]",
            "layer_execution": "[Execution Layer]",
            "subtitle": "You look agentz today too",
        },
        "ko": {
            "flow_start": "🚪 [액세스 계층] 사용자 입력 처리 시작",
            "validation_pass": "🧠 [결정 계층] 입력 유효성 검사 통과",
            "session_add": "🏃 [실행 계층] 세션에 사용자 메시지 추가",
            "cache_hit": "🧠 [결정 계층] 캐시 히트, 처리 건너뛰기",
            "cache_miss": "🧠 [결정 계층] 캐시 미스, 정상 처리 계속",
            "processing_start": "🧠 [결정 계층] 요청 처리 시작",
            "routing_enabled": "🧠 [결정 계층] 라우팅 활성화, 의도 분류 시작",
            "routing_match": "🧠 [결정 계층] 매칭 라우트 발견",
            "routing_no_match": "🧠 [결정 계층] 매칭 라우트 없음, 스킬 시도",
            "skill_enabled": "🧠 [결정 계층] 스킬 활성화, 의도 분류 시작",
            "skill_discovery": "🧠 [결정 계층] 관련 스킬 발견",
            "skill_execute": "🏃 [실행 계층] 스킬 실행",
            "skill_success": "🧠 [결정 계층] 스킬 실행 성공",
            "skill_fail": "🧠 [결정 계층] 스킬 실행 실패",
            "explanation_module": "🧠 [결정 계층] 설명 모듈로 응답 생성",
            "response_complete": "🧠 [결정 계층] 응답 생성 완료",
            "session_add_assistant": "🏃 [실행 계층] 세션에 어시스턴트 응답 추가",
            "cache_store": "🧠 [결정 계층] 응답을 캐시에 저장",
            "complete": "🚪 [완료] 응답 생성 완료",
            "intent_classifying": "🧠 [결정 계층] 입력 의도 분류 중",
            "intent_result": "🧠 [결정 계층] 분류 결과",
            "intent_final": "🧠 [결정 계층] 최종 의도",
            "intent_default": "🧠 [결정 계층] 키워드 미매칭, 기본값 사용",
            "router_checking": "🧠 [결정 계층] 등록된 라우트 확인",
            "router_found": "🧠 [결정 계층] 매칭 라우트 발견",
            "skill_discovery_start": "🧠 [결정 계층] 스킬 발견 시작",
            "skill_manager_execute": "🏃 [실행 계층] 스킬 실행 시도",
            "skill_not_found": "🧠 [결정 계층] 스킬을 찾을 수 없음",
            "skill_detail": "🏃 [실행 계층] 스킬 상세정보",
            "skill_validate_fail": "🧠 [결정 계층] 매개변수 유효성 검사 실패",
            "skill_execute_start": "🏃 [실행 계층] 매개변수 유효성 검사 통과, 실행 시작",
            "skill_execute_success": "🧠 [결정 계층] 스킬 실행 성공",
            "skill_execute_error": "🧠 [결정 계층] 스킬 실행 오류",
            "session_add_msg": "🏃 [실행 계층] 메시지 추가",
            "session_trim": "🏃 [실행 계층] 히스토리 정리됨",
            "flow_header": "=" * 70,
            "step_input": "🚪 [액세스 계층] 사용자 입력 수신",
            "step_validation": "🧠 [결정 계층] 입력 유효성 검사 통과",
            "step_session": "🏃 [실행 계층] 메시지가 세션에 추가됨",
            "step_cache_hit": "🧠 [결정 계층] 캐시 히트, 건너뛰기",
            "step_cache_miss": "🧠 [결정 계층] 캐시 미스, 계속",
            "step_processing": "🧠 [결정 계층] 처리 시작",
            "step_routing": "🧠 [결정 계층] 태스크 라우터 진입",
            "step_skill": "🏃 [실행 계층] 스킬 매니저 진입",
            "step_explanation": "🧠 [결정 계층] 설명 모듈 호출",
            "step_complete": "🚪 [완료] 총 소요 시간",
            "layer_access": "[액세스 계층]",
            "layer_decision": "[결정 계층]",
            "layer_execution": "[실행 계층]",
            "subtitle": "오늘의 당신도 멋지네요",
        },
        "ja": {
            "flow_start": "🚪 [アクセス層] ユーザー入力の処理を開始",
            "validation_pass": "🧠 [決定層] 入力バリデーション合格",
            "session_add": "🏃 [実行層] セッションにユーザーメッセージを追加",
            "cache_hit": "🧠 [決定層] キャッシュヒット、処理をスキップ",
            "cache_miss": "🧠 [決定層] キャッシュミス、通常処理を続行",
            "processing_start": "🧠 [決定層] リクエスト処理を開始",
            "routing_enabled": "🧠 [決定層] ルーティング有効化、意図分類を開始",
            "routing_match": "🧠 [決定層] 一致するルートを発見",
            "routing_no_match": "🧠 [決定層] 一致するルートなし、技能を試す",
            "skill_enabled": "🧠 [決定層] スキル有効化、意図分類を開始",
            "skill_discovery": "🧠 [決定層] 関連するスキルを発見",
            "skill_execute": "🏃 [実行層] スキルを実行",
            "skill_success": "🧠 [決定層] スキル実行成功",
            "skill_fail": "🧠 [決定層] スキル実行失敗",
            "explanation_module": "🧠 [決定層] 説明モジュールでレスポンス生成",
            "response_complete": "🧠 [決定層] レスポンス生成完了",
            "session_add_assistant": "🏃 [実行層] セッションにアシスタントレスポンスを追加",
            "cache_store": "🧠 [決定層] レスポンスをキャッシュに保存",
            "complete": "🚪 [完了] レスポンス生成完了",
            "intent_classifying": "🧠 [決定層] 入力の意図を分類中",
            "intent_result": "🧠 [決定層] 分類結果",
            "intent_final": "🧠 [決定層] 最終的な意図",
            "intent_default": "🧠 [決定層] キーワードが一致しない、デフォルトを使用",
            "router_checking": "🧠 [決定層] 登録されたルートを確認中",
            "router_found": "🧠 [決定層] 一致するルートを発見",
            "skill_discovery_start": "🧠 [決定層] スキル発見を開始",
            "skill_manager_execute": "🏃 [実行層] スキル実行を試み中",
            "skill_not_found": "🧠 [決定層] スキルが見つかりません",
            "skill_detail": "🏃 [実行層] スキル詳細情報",
            "skill_validate_fail": "🧠 [決定層] パラメーターバリデーション失敗",
            "skill_execute_start": "🏃 [実行層] パラメーターバリデーション合格、実行開始",
            "skill_execute_success": "🧠 [決定層] スキル実行成功",
            "skill_execute_error": "🧠 [決定層] スキル実行エラー",
            "session_add_msg": "🏃 [実行層] メッセージを追加",
            "session_trim": "🏃 [実行層] 履歴が整理されました",
            "flow_header": "=" * 70,
            "step_input": "🚪 [アクセス層] ユーザー入力を受信",
            "step_validation": "🧠 [決定層] 入力バリデーション合格",
            "step_session": "🏃 [実行層] メッセージがセッションに追加されました",
            "step_cache_hit": "🧠 [決定層] キャッシュヒット、スキップ",
            "step_cache_miss": "🧠 [決定層] キャッシュミス、続行",
            "step_processing": "🧠 [決定層] 処理を開始",
            "step_routing": "🧠 [決定層] タスクルーティングに侵入",
            "step_skill": "🏃 [実行層] スキルマネージャーに入る",
            "step_explanation": "🧠 [決定層] 説明モジュールを呼び出す",
            "step_complete": "🚪 [完了] 合計時間",
            "layer_access": "[アクセス層]",
            "layer_decision": "[決定層]",
            "layer_execution": "[実行層]",
            "subtitle": "今日のあなたもハンサムです",
        }
    }

    SUPPORTED_LANGUAGES = {
        "zh": "中文",
        "en": "English",
        "ko": "한국어",
        "ja": "日本語"
    }

    LAYERS = {
        "access": "接入层",
        "decision": "决策层",
        "execution": "执行层",
    }

    def __init__(self, language: str = None):
        """Initialize I18n handler.

        Args:
            language: Optional language code. If None, uses get_language() resolution.
        """
        if language:
            self.language = _normalize_lang(language)
        else:
            self.language = get_language()

    def t(self, key: str, **kwargs) -> str:
        """Translate a key using YAML catalogs first, then fallback to legacy translations."""
        # Try YAML catalog first
        result = t(key, lang=self.language, **kwargs)
        if result != key:
            return result
        # Fallback to legacy translations
        template = self.TRANSLATIONS.get(self.language, {}).get(
            key,
            self.TRANSLATIONS.get(DEFAULT_LANGUAGE, {}).get(key, key)
        )
        if kwargs:
            return template.format(**kwargs)
        return template

    def set_language(self, language: str):
        if language in SUPPORTED_LANGUAGES:
            self.language = _normalize_lang(language)

    def get_language(self) -> str:
        return self.language

    @classmethod
    def get_supported_languages(cls) -> dict[str, str]:
        return cls.SUPPORTED_LANGUAGES.copy()

    @classmethod
    def get_layers(cls) -> dict[str, str]:
        return cls.LAYERS.copy()

    @classmethod
    def get_layer_emoji(cls) -> dict[str, str]:
        return LAYER_EMOJI.copy()


# =============================================================================
# Random Greeting for Banner
# =============================================================================

# Fallback greetings when YAML config is unavailable
_FALLBACK_GREETINGS: dict[str, list[str]] = {
    "zh": [
        "代码写得好，bug 少；注释写得妙，问题早知道。",
        "Talk is cheap, show me the code.",
        "一个优秀的程序员是在穿过地狱时还在写注释的人。",
        "Debug 比写代码难两倍，所以如果你写代码时很聪明，Debug 时就更难了。",
        "先把事情做对，再把事情做巧。",
        "好的代码是最好的文档。",
        "不要只会 Ctrl+C/Ctrl+V，要理解背后的逻辑。",
        "程序员的三大谎言：我明天就改、注释以后补、这是最后一版。",
        "代码之美在于简洁，智慧之美在于分享。",
        "学会阅读他人代码，是成长的捷径。",
        "保持代码简洁，避免不必要的复杂性。",
        "写代码时想着维护你代码的人，可能就是你自己。",
    ],
    "en": [
        "Code is poetry, written by caffeinated artists.",
        "Talk is cheap, show me the code.",
        "Simplicity is the ultimate sophistication.",
        "First, make it work. Then, make it right.",
        "The best error message is no error at all.",
        "Readable code is maintainable code.",
        "Don't repeat yourself, but when you do, keep it consistent.",
        "A clever person solves problems, a wise person avoids them.",
        "Debugging is twice as hard as writing code, so write clever code.",
        "The function of good software is to make the complex appear simple.",
        "Programs must be written for people to read, and only incidentally for machines.",
        "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away.",
    ],
    "ja": [
        "コードは詩である。コーヒーを飲みながら書かれた芸術だ。",
        "Talk is cheap, show me the code.",
        "シンプルさは究極の洗練だ。",
        "まず動かせ。それから正しくしろ。",
        "最高のエラーメッセージはエラーがないことだ。",
        "読めるコードは保守しやすいコードだ。",
        "複製するな。だが複製する場合は、一貫性を保て。",
        "聪明人は問題を解決し、賢い人は問題を避ける。",
        "デバッグはコードを書くことの2倍難しい。",
        "良いソフトウェアの本質は、複雑なことをシンプルに見せること。",
        "プログラムは人が読むために書くものであり、偶然にも機械のためにある。",
    ],
    "ko": [
        "코드시는 시이다. 커피를 마시며 쓰여진 예술.",
        "Talk is cheap, show me the code.",
        "단순함이 궁극적인 세련됨이다.",
        "먼저 작동시켜라. 그 다음 올바르게 만들어라.",
        "최고의 오류 메시지는 오류가 없는 것이다.",
        "읽을 수 있는 코드는 유지보수하기 좋은 코드다.",
        "반복하지 마라. 하지만 반복한다면 일관성을 유지하라.",
        "현명한 사람은 문제를 해결하고, 지혜로운 사람은 문제를 피한다.",
        "디버깅은 코딩보다 두 배 어렵다.",
        "좋은 소프트웨어의 기능은 복잡한 것이 단순해 보이게 하는 것이다.",
    ],
}


def get_random_greeting(lang: str | None = None) -> str:
    """Get a random greeting for Banner display.

    Attempts to read from YAML config first, falls back to hardcoded list.

    Args:
        lang: Optional language code. Defaults to resolved language.

    Returns:
        A random greeting string in the appropriate language.
    """
    import random

    target = _normalize_lang(lang) if lang else get_language()

    # Try to read from YAML catalog
    try:
        greeting_key = "banner.random_greeting"
        catalog = _load_catalog(target)
        value = catalog.get(greeting_key)

        if value is None and target != DEFAULT_LANGUAGE:
            value = _load_catalog(DEFAULT_LANGUAGE).get(greeting_key)

        if value:
            greetings = [g.strip() for g in value.split("|") if g.strip()]
            if greetings:
                return random.choice(greetings)
    except Exception:
        pass

    # Fallback to hardcoded list
    greetings = _FALLBACK_GREETINGS.get(target, _FALLBACK_GREETINGS.get(DEFAULT_LANGUAGE, []))
    if greetings:
        return random.choice(greetings)

    # Ultimate fallback
    return "Hello, World!"


# Global instance
i18n = I18n()


def get_i18n(language: str | None = None) -> I18n:
    """Get an I18n instance.

    Args:
        language: Optional language code. If None, uses config/env resolution.

    Returns:
        I18n instance with resolved language.
    """
    return I18n(language)


__all__ = [
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "t",
    "get_language",
    "reset_language_cache",
    "get_random_greeting",
    "I18n",
    "i18n",
    "get_i18n",
]