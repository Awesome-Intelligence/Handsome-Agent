#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handsome Agent Setup Wizard.

🚪 Access - 💬 CLI - 设置向导

与 Hermes 的 setup.py 保持一致的重命名版本（原 setup_wizard.py）。
参考 Hermes 的模块化设计，支持独立的可运行配置部分。

Config files are stored in ~/.handsome_agent/ for easy access.
"""

import os
import re
import shutil
import sys
import json
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any
from cli import ui
from common.i18n import t, get_language, reset_language_cache, SUPPORTED_LANGUAGES

# Docs base URL
_DOCS_BASE = "https://handsome-agent.nousresearch.com/docs"

# Default model lists per provider — used as fallback when the live
# /models endpoint can't be reached.
_DEFAULT_PROVIDER_MODELS = {
    "openai": [
        "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano",
        "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"
    ],
    "anthropic": [
        "claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5",
        "claude-opus-4", "claude-sonnet-4", "claude-haiku-4",
        "claude-3-5-sonnet", "claude-3-opus", "claude-3-sonnet", "claude-3-haiku"
    ],
    "google": [
        "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash",
        "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b"
    ],
    "deepseek": [
        "deepseek-chat", "deepseek-coder", "deepseek-reasoner"
    ],
    "minimax": [
        "MiniMax-M2", "MiniMax-M2.1", "MiniMax-M2.5", "MiniMax-M2.7"
    ],
    "moonshot": [
        "kimi-k2", "kimi-k2.5", "kimi-k2-turbo", "kimi-k2-thinking",
        "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"
    ],
    "zhipu": [
        "glm-4", "glm-4-flash", "glm-4-plus", "glm-4-long",
        "glm-3", "glm-3-flash"
    ],
    "dashscope": [
        "qwen-plus", "qwen-plus-latest", "qwen-turbo", "qwen-max",
        "qwen2.5-72b-instruct", "qwen2.5-7b-instruct"
    ],
    "groq": [
        "llama-3.3-70b-versatile", "llama-3.1-70b-versatile",
        "mixtral-8x7b-32768", "gemma2-9b-it"
    ],
    "siliconflow": [
        "Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3",
        "anthropic/claude-3.5-sonnet"
    ],
}

# 检查是否在交互式 TTY 环境
def is_interactive_stdin() -> bool:
    """Return True when stdin looks like a usable interactive TTY."""
    stdin = getattr(sys, "stdin", None)
    if stdin is None:
        return False
    try:
        return bool(stdin.isatty())
    except Exception:
        return False


def print_noninteractive_setup_guidance(reason: str | None = None) -> None:
    """Print guidance for headless/non-interactive setup flows."""
    print()
    ui.print_header_text("⚕ Handsome Agent Setup — Non-interactive mode")
    print()
    if reason:
        ui.print_info(reason)
    ui.print_info("The interactive wizard cannot be used here.")
    print()
    ui.print_info("Configure Handsome Agent using environment variables or config commands:")
    ui.print_info("  handsome config set model.provider openai")
    ui.print_info("  handsome config set model.base_url http://localhost:8080/v1")
    ui.print_info("  handsome config set model.default your-model-name")
    print()
    ui.print_info("Or set OPENAI_API_KEY / OPENROUTER_API_KEY in your environment.")
    ui.print_info("Run 'handsome setup' in an interactive terminal to use the full wizard.")
    print()


def _sanitize_pasted_input(value: str) -> str:
    """Strip terminal bracketed-paste control markers from pasted text."""
    if not isinstance(value, str) or not value:
        return value
    # 清除 bracketed paste 标记
    bracket_pattern = re.compile(r"\x1b\[\s*200~|\x1b\[\s*201~")
    return bracket_pattern.sub("", value)


def prompt(question: str, default: str = None, password: bool = False) -> str:
    """Prompt for input with optional default."""
    if default:
        display = f"{question} [{default}]: "
    else:
        display = f"{question}: "

    try:
        if password:
            import getpass
            value = getpass.getpass(ui.print_prompt() + display)
        else:
            value = input(display).strip()

        cleaned = _sanitize_pasted_input(value)
        return cleaned.strip() or default or ""
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(1)


def prompt_choice(question: str, choices: list, default: int = 0, description: str | None = None) -> int:
    """Prompt for a choice from a list."""
    print()
    print(question)
    for i, choice in enumerate(choices):
        marker = "●" if i == default else "○"
        if i == default:
            ui.print_success(f"  {marker} {choice}")
        else:
            print(f"  {marker} {choice}")
    print()
    default_str = str(default + 1)
    while True:
        try:
            value = input(f"  Select [1-{len(choices)}] ({default_str}): ").strip()
            if not value:
                return default
            idx = int(value) - 1
            if 0 <= idx < len(choices):
                return idx
            ui.print_error(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            ui.print_error("Please enter a number")
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(1)


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt for yes/no. Ctrl+C exits, empty input returns default."""
    default_str = "Y/n" if default else "y/N"

    while True:
        try:
            value = input(f"{question} [{default_str}]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(1)

        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        ui.print_error("Please enter 'y' or 'n'")


def print_header(title: str):
    """Print a section header."""
    print()
    ui.print_header_text(f"◆ {title}")


def print_success(msg: str):
    """Print success message."""
    ui.print_success(msg)


def print_info(msg: str):
    """Print info message."""
    ui.print_info(msg)


def print_warning(msg: str):
    """Print warning message."""
    ui.print_warning(msg)


def print_error(msg: str):
    """Print error message."""
    ui.print_error(msg)


ui.enable_ansi_support()

# 导入增强的 Banner 模块
from cli.banner import print_setup_banner, print_simple_banner, print_setup_summary


CONFIG_DIR = os.path.expanduser("~/.handsome_agent")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


QUIT_COMMANDS = ['quit', 'exit', 'q', '退出', 'back', 'b', '返回']


def should_quit(response: str) -> bool:
    """检查是否要退出."""
    return response.lower() in [c.lower() for c in QUIT_COMMANDS]


def ask_yes_no(question: str, default: bool = True) -> bool | None:
    """询问是/否."""
    suffix = t("setup.common.yes_no_yes") if default else t("setup.common.yes_no_no")
    while True:
        try:
            ui.print_substep(f"{question} {suffix}")
            ui.print_substep(f"{ui.Theme.SECONDARY_DIM}{t('setup.common.quit_hint')}{ui.Colors.RESET}")
            response = input(ui.print_prompt()).strip()
            
            if should_quit(response):
                return None
            if not response:
                return default
            if response in ['y', 'yes', '是', '好']:
                return True
            if response in ['n', 'no', '否', '不']:
                return False
            ui.print_warning(t("setup.questions.invalid_input"))
        except (EOFError, KeyboardInterrupt):
            return None


def ask_choice(question: str, options: list, default: int = 0, current_value: str = None) -> int | None:
    """让用户从选项中选择 - 不显示重复的 logo."""
    print()
    from cli.interactive_select import select_option
    result = select_option(options, question, current_value=current_value, show_logo=False, show_config=False)
    return result


def ask_checkbox(question: str, options: list, defaults: list = None) -> list | None:
    """让用户多选（checkbox 模式，空格切换，回车确认）."""
    print()
    from cli.interactive_select import checkbox_with_inquirer
    result = checkbox_with_inquirer(options, title=question, defaults=defaults)
    return result


def ask_input(question: str, default: str = None, password: bool = False, required: bool = True) -> str | None:
    """询问用户输入."""
    if default:
        prompt_text = f"{question} {t('setup.common.enter_to_default', default=default)}"
    else:
        prompt_text = question
    
    print()
    ui.print_substep(prompt_text)
    if required:
        ui.print_substep(f"{ui.Theme.SECONDARY_DIM}{t('setup.common.quit_hint')}{ui.Colors.RESET}")
    
    while True:
        try:
            if password:
                import getpass
                response = getpass.getpass(ui.print_prompt()).strip()
            else:
                response = input(ui.print_prompt()).strip()
            
            if should_quit(response):
                return None
            if not response and default is not None:
                return default
            if not response and required:
                ui.print_warning(t("setup.questions.required_field"))
                continue
            return response if response else default
        except (EOFError, KeyboardInterrupt):
            return None


def get_all_providers():
    """获取所有支持的提供商."""
    from agent.llm import get_all_providers
    return get_all_providers()


def load_config() -> dict:
    """加载现有配置."""
    config_file = os.path.join(CONFIG_DIR, "config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    
    if os.path.exists(CONFIG_FILE):
        try:
            import yaml
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    
    return {}


def save_config(config: dict):
    """保存配置到文件."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    config_file = os.path.join(CONFIG_DIR, "config.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def show_current_config(config: dict):
    """显示当前配置."""
    if not isinstance(config, dict):
        return
    
    print()
    ui.print_header_text(t("setup.banner.current_config"))
    ui.print_divider()
    
    # Language
    language = config.get('language', 'zh')
    if isinstance(language, str):
        language_display = t(f"setup.language.options.{language}")
        ui.print_config_item("🌐 " + t("setup.language.title").replace("🌐 ", ""), language_display)
    
    # LLM Provider
    llm = config.get('llm', {})
    provider = llm.get('provider', 'none')
    if provider == 'none':
        provider_display = t("setup.llm.not_configured")
    else:
        provider_display = t(f"setup.providers.{provider}")
    ui.print_config_item("🤖 " + t("menu.llm.label").replace("LLM ", ""), provider_display)
    
    if llm.get('model'):
        ui.print_config_item("📦 " + t("setup.llm.model"), llm['model'])
    
    # Model Config
    model_cfg = config.get('model', {})
    if model_cfg:
        ui.print_config_item("🔧 " + t("setup.model_config.max_tokens"), str(model_cfg.get('max_tokens', 4096)))
        ui.print_config_item("🌡️ " + t("setup.model_config.temperature"), str(model_cfg.get('temperature', 0.7)))
    
    # Terminal Config
    terminal = config.get('terminal', {})
    if terminal:
        backend = terminal.get('backend', 'local')
        backend_display = t(f"setup.terminal.backends.{backend}")
        ui.print_config_item(t("setup.terminal.title"), backend_display)
        ui.print_config_item("⏱️ Timeout", f"{terminal.get('timeout', 60)}s")
        ui.print_config_item("🕐 Lifetime", f"{terminal.get('lifetime_seconds', 300)}s")
    
    # Session Reset
    session_reset = config.get('session_reset', {})
    if session_reset:
        mode = session_reset.get('mode', 'both')
        mode_display = t(f"setup.session_reset.modes.{mode}")
        ui.print_config_item("🔄 Session Reset", mode_display)
        if mode in ('daily', 'both'):
            ui.print_config_item("⏰ Reset Time", f"{session_reset.get('at_hour', 4)}:00")
        if mode in ('idle', 'both'):
            ui.print_config_item("⏳ Idle Timeout", f"{session_reset.get('idle_minutes', 1440)} min")
    
    # Memory Config
    memory = config.get('memory', {})
    if memory:
        enabled = memory.get('enabled', True)
        ui.print_config_item(t("setup.memory.title"), t("setup.summary.configured") if enabled else t("setup.summary.not_configured"))
        if enabled:
            ui.print_config_item("📊 Vector Store", memory.get('vector_store', 'sqlite'))
    
    # Vision Config
    vision = config.get('vision', {})
    if vision:
        enabled = vision.get('enabled', False)
        ui.print_config_item(t("setup.vision.title"), t("setup.summary.configured") if enabled else t("setup.summary.not_configured"))
        if enabled:
            ui.print_config_item("🎯 Vision Provider", vision.get('provider', 'N/A'))
    
    # Tool Progress Display
    display = config.get('display', {})
    if display:
        tool_progress = display.get('tool_progress', 'all')
        ui.print_config_item("🛠️ Tool Progress", tool_progress)
    
    # Compression Config
    compression = config.get('compression', {})
    if compression:
        enabled = compression.get('enabled', True)
        ui.print_config_item(t("setup.compression.title"), t("setup.summary.configured") if enabled else t("setup.summary.not_configured"))
        if enabled:
            ui.print_config_item("📈 Threshold", f"{compression.get('threshold', 0.85) * 100:.0f}%")
    
    # STT Config
    stt = config.get('stt', {})
    if stt:
        enabled = stt.get('enabled', False)
        ui.print_config_item(t("setup.stt.title"), t("setup.summary.configured") if enabled else t("setup.summary.not_configured"))
        if enabled:
            ui.print_config_item("🎯 STT Provider", stt.get('provider', 'local'))
    
    # TTS Config
    tts = config.get('tts', {})
    if tts:
        enabled = tts.get('enabled', False)
        ui.print_config_item(t("setup.tts.title"), t("setup.summary.configured") if enabled else t("setup.summary.not_configured"))
        if enabled:
            ui.print_config_item("🎯 TTS Provider", tts.get('provider', 'openai'))
            ui.print_config_item("🎭 TTS Voice", tts.get('voice', 'alloy'))
    
    # Browser Config
    browser = config.get('browser', {})
    if browser:
        enabled = browser.get('enabled', False)
        ui.print_config_item(t("setup.browser.title"), t("setup.summary.configured") if enabled else t("setup.summary.not_configured"))
        if enabled:
            ui.print_config_item("🔒 Stealth Mode", t("utils.yes") if browser.get('advanced_stealth', False) else t("utils.no"))
    
    # Debug Config
    debug = config.get('debug_tools', {})
    if debug:
        web_debug = debug.get('web_tools', False)
        vision_debug = debug.get('vision_tools', False)
        if web_debug or vision_debug:
            ui.print_config_item("🐛 Debug Mode", t("setup.summary.configured"))
        else:
            ui.print_config_item("🐛 Debug Mode", t("setup.summary.not_configured"))
    
    # Preferences
    prefs = config.get('preferences', {})
    depth = prefs.get('explanation_depth', 'detailed')
    depth_display = {"brief": t("setup.preferences.explanation_depth.options.brief"), 
                    "moderate": t("setup.preferences.explanation_depth.options.moderate"), 
                    "detailed": t("setup.preferences.explanation_depth.options.detailed")}.get(depth, depth)
    ui.print_config_item(t("setup.preferences.explanation_depth.title").replace("📝 ", ""), depth_display)
    
    caching = prefs.get('enable_caching', True)
    ui.print_config_item(t("setup.preferences.caching.title").replace("⚡ ", ""), t("setup.summary.configured") if caching else t("setup.summary.not_configured"))
    
    # Intent Mode
    intent_mode = config.get('intent_mode', 'llm')
    mode_display = {"keyword": t("setup.preferences.intent.options.keyword"), 
                   "llm": t("setup.preferences.intent.options.llm"), 
                   "hybrid": t("setup.preferences.intent.options.hybrid")}.get(intent_mode, intent_mode)
    ui.print_config_item(t("setup.preferences.intent.title").replace("🎯 ", ""), mode_display)
    
    ui.print_divider()


def has_existing_config() -> bool:
    """检查是否存在配置文件."""
    config_file = os.path.join(CONFIG_DIR, "config.json")
    return os.path.exists(config_file) or os.path.exists(CONFIG_FILE)


# =============================================================================
# Section 1: Language
# =============================================================================

def setup_language(config: dict) -> str | None:
    """配置语言. 返回语言代码字符串."""
    ui.print_step(1, 1, t("setup.language.title"))
    
    language_options = [
        ("zh", t("setup.language.options.zh")),
        ("en", t("setup.language.options.en")),
        ("ja", t("setup.language.options.ja")),
        ("ko", t("setup.language.options.ko")),
    ]
    
    current = config.get('language', get_language())
    current_idx = next((i for i, (k, _) in enumerate(language_options) if k == current), 0)
    
    choice = ask_choice(t("setup.language.prompt"), language_options, default=current_idx, current_value=current)
    if choice is None:
        return None
    
    selected_lang = language_options[choice][0]
    
    # 立即更新 config 中的语言设置
    config['language'] = selected_lang
    
    # 临时设置环境变量，使语言设置在当前 session 中立即生效
    os.environ['HANDSOME_LANGUAGE'] = selected_lang
    from common.i18n import reset_language_cache
    reset_language_cache()
    
    ui.print_success(t("setup.language.selected", language=t(f"setup.language.options.{selected_lang}")))
    
    return selected_lang


# =============================================================================
# Section 2: LLM Provider & Model
# =============================================================================

def setup_llm_provider(config: dict) -> dict | None:
    """配置大模型 - 参考 Hermes 设计重构.
    
    流程：
    1. 显示当前配置状态
    2. 选择 Provider（支持保持不变）
    3. Provider 特定配置流程
    """
    ui.print_step(1, 1, t("setup.llm.title"))
    
    # Step 1: 显示当前状态
    _show_llm_current_status(config)
    
    # Step 2: 获取所有 Provider
    providers = get_all_providers()
    
    # 构建 Provider 选项列表
    provider_options = []
    for p in providers:
        display_name = p.get('display_name', p['name'])
        models = p.get('supported_models', [])
        models_str = ", ".join(models[:3])
        if len(models) > 3:
            models_str += "..."
        provider_options.append((p["name"], f"{display_name} ({models_str})"))
    
    # 获取当前配置
    current_provider = config.get('llm', {}).get('provider', '')
    current_model = config.get('llm', {}).get('model', '')
    
    # 添加特殊选项
    provider_options.append(("none", t("setup.llm.not_configured")))
    provider_options.append(("leave", t("setup.llm.keep_current", provider=current_provider or "none")))
    
    # 设置默认选中（当前 Provider 或第一个）
    if current_provider:
        current_idx = next(
            (i for i, (k, _) in enumerate(provider_options) if k == current_provider),
            0
        )
    else:
        current_idx = 0
    
    choice = ask_choice(t("setup.llm.select_provider"), provider_options, default=current_idx, current_value=current_provider)
    if choice is None:
        return None
    
    selected_provider = provider_options[choice][0]
    
    # 保持不变
    if selected_provider == "leave":
        ui.print_info(t("setup.llm.keep_current", provider=current_provider))
        return config.get('llm', {})
    
    # 不使用 LLM
    if selected_provider == "none":
        ui.print_info(t("setup.llm.using_basic_mode"))
        return {"provider": "none", "api_key": None, "model": None, "base_url": None}
    
    # Step 3: Provider 特定配置流程
    return _setup_provider_flow(selected_provider, config)


def _show_llm_current_status(config: dict) -> None:
    """显示当前 LLM 配置状态."""
    llm = config.get('llm', {})
    provider = llm.get('provider', '')
    model = llm.get('model', '')
    api_key = llm.get('api_key', '')
    
    # Use i18n for provider labels
    provider_display = t(f"setup.providers.{provider}") if provider else t("setup.llm.not_configured")
    model_display = model if model else "(not set)"
    
    print()
    ui.print_info(t("setup.llm.current_status"))
    ui.print_config_item(f"  {t('setup.llm.provider')}", provider_display)
    ui.print_config_item(f"  {t('setup.llm.model')}", model_display)
    if api_key:
        ui.print_info(t("setup.llm.api_key_masked", prefix=api_key[:4], suffix=api_key[-4:]))
    print()


def _setup_provider_flow(provider_id: str, config: dict) -> dict | None:
    """Provider 特定配置流程."""
    # 定义 Provider 分类
    api_key_providers = {
        "openai", "deepseek", "google", "minimax", "moonshot",
        "zhipu", "dashscope", "groq", "siliconflow"
    }
    oauth_providers = {"anthropic"}
    special_providers = {"openrouter"}
    
    if provider_id in oauth_providers:
        return _setup_oauth_provider(provider_id, config)
    elif provider_id == "openrouter":
        return _setup_openrouter_provider(provider_id, config)
    elif provider_id == "custom":
        return _setup_custom_provider(provider_id, config)
    elif provider_id in api_key_providers:
        return _setup_api_key_provider(provider_id, config)
    else:
        # 默认走 API Key 流程
        return _setup_api_key_provider(provider_id, config)


def _setup_api_key_provider(provider_id: str, config: dict) -> dict | None:
    """通用 API Key Provider 配置流程."""
    providers = get_all_providers()
    provider_info = next((p for p in providers if p["name"] == provider_id), None)
    
    if not provider_info:
        ui.print_error(f"Provider not found: {provider_id}")
        return None
    
    display_name = provider_info.get('display_name', provider_id)
    
    # 获取 API Key
    api_key_url = provider_info.get('api_key_url', '')
    if api_key_url:
        ui.print_info(f"Get {display_name} API Key: {api_key_url}")
    
    current_key = config.get('llm', {}).get('api_key', '')
    current_model = config.get('llm', {}).get('model', '')
    
    if current_key:
        ui.print_info(f"{t('setup.summary.configured')} API Key: {current_key[:4]}...{current_key[-4:]}")
        reuse = ask_yes_no("Keep existing API Key?", default=True)
        if reuse is None:
            return None
        if reuse:
            return {
                "provider": provider_id,
                "api_key": current_key,
                "model": current_model,
                "base_url": config.get('llm', {}).get('base_url'),
            }
    
    # 输入新 API Key
    api_key = ask_input(f"{display_name} API Key", password=True, required=True)
    if api_key is None:
        return None
    
    # 可选的 Base URL
    base_url = provider_info.get('base_url', '')
    use_custom_url = False
    if base_url:
        use_custom_url = ask_yes_no("Use custom API URL?", default=False)
    
    custom_url = None
    if use_custom_url:
        current_url = config.get('llm', {}).get('base_url', base_url)
        custom_url = ask_input("API URL", default=current_url)
        if custom_url is None:
            return None
    
    # 获取模型列表
    models = provider_info.get('supported_models', [])
    
    if models:
        return _prompt_model_selection(
            provider_id, models, current_model=current_model,
            api_key=api_key, base_url=custom_url
        )
    else:
        # 无模型列表，使用默认或手动输入
        return _prompt_model_selection_offline(
            provider_id, current_model=current_model,
            api_key=api_key, base_url=custom_url
        )


def _setup_oauth_provider(provider_id: str, config: dict) -> dict | None:
    """OAuth Provider 配置（如 Anthropic）."""
    current_key = config.get('llm', {}).get('api_key', '')
    current_model = config.get('llm', {}).get('model', '')
    
    has_creds = bool(current_key)
    
    if has_creds:
        ui.print_info(f"{t('setup.summary.configured')} API Key: {current_key[:12]}... ✓")
        print()
        print_info("  1. Use existing credentials")
        print_info("  2. Enter new API Key")
        print_info("  3. Cancel")
        
        try:
            choice = input("  Select [1/2/3]: ").strip()
        except (KeyboardInterrupt, EOFError):
            choice = "1"
        
        if choice == "3":
            return None
        elif choice == "2":
            current_key = ""
        # choice == "1" 或默认：使用现有凭证
    
    if not current_key:
        api_key = ask_input("API Key (sk-ant-...)", password=True, required=True)
        if api_key is None:
            return None
    else:
        api_key = current_key
    
    # 获取模型列表
    providers = get_all_providers()
    provider_info = next((p for p in providers if p["name"] == provider_id), None)
    models = provider_info.get('supported_models', []) if provider_info else []
    
    if models:
        return _prompt_model_selection(
            provider_id, models, current_model=current_model,
            api_key=api_key
        )
    else:
        return _prompt_model_selection_offline(
            provider_id, current_model=current_model,
            api_key=api_key
        )


def _setup_openrouter_provider(provider_id: str, config: dict) -> dict | None:
    """OpenRouter 配置."""
    ui.print_info("OpenRouter - unified entry for multiple models")
    ui.print_info("Get API Key: https://openrouter.ai/keys")
    
    current_key = config.get('llm', {}).get('api_key', '')
    
    if current_key:
        ui.print_info(f"{t('setup.summary.configured')} API Key: {current_key[:4]}...{current_key[-4:]}")
        reuse = ask_yes_no("Keep existing API Key?", default=True)
        if reuse is None:
            return None
        if reuse:
            return {
                "provider": provider_id,
                "api_key": current_key,
                "model": config.get('llm', {}).get('model'),
                "base_url": config.get('llm', {}).get('base_url'),
            }
    
    api_key = ask_input("OpenRouter API Key", password=True, required=True)
    if api_key is None:
        return None
    
    return _setup_api_key_provider(provider_id, config)


def _setup_custom_provider(provider_id: str, config: dict) -> dict | None:
    """自定义 API Endpoint 配置."""
    current_base_url = config.get('llm', {}).get('base_url', 'http://localhost:11434/v1')
    current_model = config.get('llm', {}).get('model', '')
    
    base_url = ask_input("API URL", default=current_base_url)
    if base_url is None:
        return None
    
    model = ask_input("Model name", default=current_model or "gpt-4o-mini")
    if model is None:
        return None
    
    api_key = ask_input("API Key (optional)", password=True, required=False)
    
    return {
        "provider": "custom",
        "api_key": api_key or None,
        "model": model,
        "base_url": base_url,
    }


def _prompt_model_selection(
    provider_id: str,
    models: list,
    current_model: str = "",
    api_key: str = "",
    base_url: str = None
) -> dict | None:
    """提示用户选择模型."""
    ui.print_header_text("Select model:")
    print()
    
    model_options = [(m, m) for m in models]
    
    # 尝试匹配当前模型
    current_idx = 0
    if current_model:
        try:
            current_idx = models.index(current_model)
        except ValueError:
            pass
    
    from cli.interactive_select import select_option_safe
    model_choice = select_option_safe(model_options, default_idx=current_idx, current_value=current_model)
    if model_choice is None:
        return None
    
    selected_model = models[model_choice]
    
    return {
        "provider": provider_id,
        "api_key": api_key,
        "model": selected_model,
        "base_url": base_url,
    }


def _prompt_model_selection_offline(
    provider_id: str,
    current_model: str = "",
    api_key: str = "",
    base_url: str = None
) -> dict | None:
    """离线模式模型选择（使用默认列表）."""
    ui.print_warning("Cannot get model list, using offline default list")
    print()
    
    default_models = _DEFAULT_PROVIDER_MODELS.get(provider_id, [])
    if default_models:
        ui.print_info(f"{provider_id} default model list:")
        model_options = [(m, m) for m in default_models]
        
        # 尝试匹配当前模型
        current_idx = 0
        if current_model and current_model in default_models:
            current_idx = default_models.index(current_model)
        
        from cli.interactive_select import select_option_safe
        model_choice = select_option_safe(model_options, default_idx=current_idx, current_value=current_model)
        if model_choice is None:
            return None
        
        selected_model = default_models[model_choice]
    else:
        ui.print_warning("No model list available, please input manually")
        selected_model = ask_input("Model name", default="gpt-4o-mini")
        if selected_model is None:
            return None
    
    return {
        "provider": provider_id,
        "api_key": api_key,
        "model": selected_model,
        "base_url": base_url,
    }


def setup_model_config(config: dict) -> dict | None:
    """配置模型参数."""
    ui.print_step(1, 1, t("setup.model_config.title"))
    
    model_cfg = config.get('model', {})
    
    max_tokens = ask_input(t("setup.model_config.max_tokens"), default=str(model_cfg.get('max_tokens', 4096)))
    if max_tokens is None:
        return None
    max_tokens = int(max_tokens) if max_tokens.isdigit() else 4096
    
    temperature = ask_input(t("setup.model_config.temperature"), default=str(model_cfg.get('temperature', 0.7)))
    if temperature is None:
        return None
    try:
        temperature = float(temperature)
        temperature = max(0.0, min(2.0, temperature))
    except ValueError:
        temperature = 0.7
    
    context_window = ask_input(t("setup.model_config.context_window"), default=str(model_cfg.get('context_window', 128000)))
    if context_window is None:
        return None
    context_window = int(context_window) if context_window.isdigit() else 128000
    
    return {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "context_window": context_window
    }


# =============================================================================
# Section 3: Terminal Backend
# =============================================================================

def _prompt_container_resources(config: dict) -> dict:
    """提示容器资源配置（Docker/Modal 等）."""
    terminal = config.setdefault('terminal', {})
    
    print()
    ui.print_info("Container resource configuration:")
    
    # 持久化文件系统
    current_persist = terminal.get('container_persistent', True)
    persist_label = "yes" if current_persist else "no"
    ui.print_info("  Persistent filesystem: keep files between sessions")
    ui.print_info("  Set to 'no' for temporary sandbox, reset each time")
    persist_str = ask_input("Persistent filesystem?", default=persist_label)
    terminal['container_persistent'] = persist_str.lower() in {"yes", "true", "y", "1"}
    
    # CPU
    current_cpu = terminal.get('container_cpu', 1)
    cpu_str = ask_input("CPU cores", default=str(current_cpu))
    try:
        terminal['container_cpu'] = float(cpu_str)
    except ValueError:
        pass
    
    # 内存
    current_mem = terminal.get('container_memory', 5120)
    mem_str = ask_input("Memory MB (5120 = 5GB)", default=str(current_mem))
    try:
        terminal['container_memory'] = int(mem_str)
    except ValueError:
        pass
    
    # 磁盘
    current_disk = terminal.get('container_disk', 51200)
    disk_str = ask_input("磁盘 MB (51200 = 50GB)", default=str(current_disk))
    try:
        terminal['container_disk'] = int(disk_str)
    except ValueError:
        pass
    
    return terminal


def setup_terminal(config: dict) -> dict | None:
    """配置 Terminal 后端."""
    ui.print_step(1, 1, t("setup.terminal.title"))
    
    terminal_cfg = config.get('terminal', {})
    
    backend_options = [
        ("local", t("setup.terminal.backends.local")),
        ("docker", t("setup.terminal.backends.docker")),
        ("ssh", t("setup.terminal.backends.ssh")),
        ("singularity", t("setup.terminal.backends.singularity")),
        ("modal", t("setup.terminal.backends.modal"))
    ]
    
    current_backend = terminal_cfg.get('backend', 'local')
    current_idx = next((i for i, (k, _) in enumerate(backend_options) if k == current_backend), 0)
    
    choice = ask_choice(t("setup.terminal.select_backend"), backend_options, default=current_idx, current_value=current_backend)
    if choice is None:
        return None
    
    backend = backend_options[choice][0]
    
    new_config = {"backend": backend}
    
    if backend == "local":
        ui.print_info(t("setup.terminal.using_local"))
    elif backend == "docker":
        ui.print_info(t("setup.terminal.using_docker"))
        image = ask_input(t("setup.terminal.docker_image"), default=terminal_cfg.get('docker_image', 'nikolaik/python-nodejs:python3.11-nodejs20'))
        if image is None:
            return None
        new_config["docker_image"] = image
        # 提示容器资源配置
        if ask_yes_no(t("setup.terminal.configure_resources"), default=False):
            _prompt_container_resources(config)
            # 重新构建 new_config 以包含最新值
            new_config = config.get('terminal', {}).copy()
            new_config["backend"] = backend
            new_config["docker_image"] = image
    elif backend == "ssh":
        ui.print_info(t("setup.terminal.using_ssh"))
        ssh_host = ask_input(t("setup.terminal.ssh_host"), default=terminal_cfg.get('ssh_host', ''))
        if ssh_host is None:
            return None
        new_config["ssh_host"] = ssh_host
        
        ssh_user = ask_input(t("setup.terminal.ssh_user"), default=terminal_cfg.get('ssh_user', 'root'))
        if ssh_user is None:
            return None
        new_config["ssh_user"] = ssh_user
        
        ssh_port = ask_input(t("setup.terminal.ssh_port"), default=str(terminal_cfg.get('ssh_port', 22)))
        if ssh_port is None:
            return None
        new_config["ssh_port"] = int(ssh_port) if ssh_port.isdigit() else 22
        
        ssh_key = ask_input(t("setup.terminal.ssh_key"), default=terminal_cfg.get('ssh_key', '~/.ssh/id_rsa'))
        if ssh_key is None:
            return None
        new_config["ssh_key"] = ssh_key
    elif backend == "singularity":
        ui.print_info(t("setup.terminal.using_singularity"))
        image = ask_input(t("setup.terminal.singularity_image"), default=terminal_cfg.get('singularity_image', 'docker://nikolaik/python-nodejs:python3.11-nodejs20'))
        if image is None:
            return None
        new_config["singularity_image"] = image
    elif backend == "modal":
        ui.print_info(t("setup.terminal.using_modal"))
        image = ask_input(t("setup.terminal.modal_image"), default=terminal_cfg.get('modal_image', 'nikolaik/python-nodejs:python3.11-nodejs20'))
        if image is None:
            return None
        new_config["modal_image"] = image
        # 提示容器资源配置
        if ask_yes_no(t("setup.terminal.configure_resources"), default=False):
            _prompt_container_resources(config)
            # 重新构建 new_config 以包含最新值
            new_config = config.get('terminal', {}).copy()
            new_config["backend"] = backend
            new_config["modal_image"] = image
    
    return new_config


# =============================================================================
# Section 4: Agent Settings (Enhanced)
# =============================================================================

def setup_agent_settings(config: dict) -> dict | None:
    """配置 Agent 设置."""
    ui.print_step(1, 1, t("setup.agent.title"))
    
    agent = config.get('agent', {})
    
    # Max Iterations / Max Turns
    current_max = str(agent.get('max_turns', 90))
    ui.print_info(t("setup.agent.max_iterations"))
    ui.print_info(t("setup.agent.max_iterations_hint"))
    ui.print_info(t("setup.agent.max_iterations_default"))
    max_iterations = ask_input(t("setup.agent.max_iterations"), default=current_max)
    if max_iterations is None:
        return None
    try:
        max_turns = int(max_iterations)
    except ValueError:
        max_turns = 90
    
    # Tool Progress Display
    print()
    ui.print_info(t("setup.agent.tool_progress"))
    ui.print_info(t("setup.agent.tool_progress_hint"))
    ui.print_info(f"  {t('setup.agent.tool_progress_modes.off')}")
    ui.print_info(f"  {t('setup.agent.tool_progress_modes.new')}")
    ui.print_info(f"  {t('setup.agent.tool_progress_modes.all')}")
    ui.print_info(f"  {t('setup.agent.tool_progress_modes.verbose')}")
    
    current_mode = config.get('display', {}).get('tool_progress', 'all')
    mode_options = [
        ("off", t("setup.agent.tool_progress_modes.off")),
        ("new", t("setup.agent.tool_progress_modes.new")),
        ("all", t("setup.agent.tool_progress_modes.all")),
        ("verbose", t("setup.agent.tool_progress_modes.verbose"))
    ]
    current_idx = next((i for i, (k, _) in enumerate(mode_options) if k == current_mode), 2)
    mode_choice = ask_choice(t("setup.agent.select_mode"), mode_options, default=current_idx, current_value=current_mode)
    if mode_choice is None:
        return None
    tool_progress = mode_options[mode_choice][0]
    
    # Session Reset 配置移到单独函数
    print()
    session_reset_result = setup_session_reset(config)
    if session_reset_result is None:
        return None
    
    # Context Compression
    print()
    compression_result = setup_compression(config)
    if compression_result is None:
        return None
    
    return {
        "max_turns": max_turns,
        "display": {"tool_progress": tool_progress},
        "session_reset": session_reset_result,
        "compression": compression_result
    }


# =============================================================================
# Section 5: Session Reset Policy
# =============================================================================

def setup_session_reset(config: dict) -> dict | None:
    """配置 Session 重置策略."""
    ui.print_step(1, 1, t("setup.session_reset.title"))
    
    session_reset = config.get('session_reset', {})
    
    mode_options = [
        ("both", t("setup.session_reset.modes.both")),
        ("daily", t("setup.session_reset.modes.daily")),
        ("idle", t("setup.session_reset.modes.idle")),
        ("none", t("setup.session_reset.modes.none"))
    ]
    
    current_mode = session_reset.get('mode', 'both')
    current_idx = next((i for i, (k, _) in enumerate(mode_options) if k == current_mode), 0)
    
    choice = ask_choice(t("setup.session_reset.select_mode"), mode_options, default=current_idx, current_value=current_mode)
    if choice is None:
        return None
    
    mode = mode_options[choice][0]
    new_config = {"mode": mode}
    
    if mode in ('daily', 'both'):
        at_hour = ask_input(t("setup.session_reset.daily_time"), default=str(session_reset.get('at_hour', 4)))
        if at_hour is None:
            return None
        try:
            hour = int(at_hour)
            hour = max(0, min(23, hour))
        except ValueError:
            hour = 4
        new_config["at_hour"] = hour
    
    if mode in ('idle', 'both'):
        idle_minutes = ask_input(t("setup.session_reset.idle_time"), default=str(session_reset.get('idle_minutes', 1440)))
        if idle_minutes is None:
            return None
        try:
            minutes = int(idle_minutes)
            minutes = max(1, minutes)
        except ValueError:
            minutes = 1440
        new_config["idle_minutes"] = minutes
    
    notify = ask_yes_no(t("setup.session_reset.send_notification"), default=session_reset.get('notify', True))
    if notify is None:
        return None
    new_config["notify"] = notify
    
    return new_config


# =============================================================================
# Section 6: Memory Config
# =============================================================================

def setup_memory(config: dict) -> dict | None:
    """配置记忆系统."""
    ui.print_step(1, 1, t("setup.memory.title"))
    
    memory = config.get('memory', {})
    memory_enabled = memory.get('enabled', True)
    
    # 使用 checkbox 模式让用户选择功能
    feature_options = [
        ("enabled", t("setup.memory.enable")),
        ("vector_store", t("setup.memory.vector_store")),
        ("embedding_model", t("setup.memory.embedding_model")),
        ("max_entries", t("setup.memory.max_entries")),
    ]
    
    # 默认选中的功能
    defaults = ["enabled"]
    if memory_enabled:
        defaults.append("vector_store")
        defaults.append("embedding_model")
        defaults.append("max_entries")
    
    print()
    selected = ask_checkbox(t("setup.memory.select_features"), options=feature_options, defaults=defaults)
    if selected is None:
        return None
    
    new_config = {"enabled": "enabled" in selected}
    
    if "vector_store" in selected:
        vector_options = [
            ("sqlite", t("setup.memory.stores.sqlite")),
            ("chroma", t("setup.memory.stores.chroma")),
            ("qdrant", t("setup.memory.stores.qdrant")),
            ("milvus", t("setup.memory.stores.milvus"))
        ]
        
        current_vector = memory.get('vector_store', 'sqlite')
        current_idx = next((i for i, (k, _) in enumerate(vector_options) if k == current_vector), 0)
        
        choice = ask_choice(t("setup.memory.vector_store"), vector_options, default=current_idx, current_value=current_vector)
        if choice is None:
            return None
        
        new_config["vector_store"] = vector_options[choice][0]
    
    if "embedding_model" in selected:
        embedding = ask_input(t("setup.memory.embedding_model"), default=memory.get('embedding_model', 'text-embedding-3-small'))
        if embedding is None:
            return None
        new_config["embedding_model"] = embedding
    
    if "max_entries" in selected:
        max_entries = ask_input(t("setup.memory.max_entries"), default=str(memory.get('max_entries', 1000)))
        if max_entries is None:
            return None
        new_config["max_entries"] = int(max_entries) if max_entries.isdigit() else 1000
    
    return new_config


# =============================================================================
# Section 7: Context Compression (Hermes-consistent default: 0.50)
# =============================================================================

def setup_compression(config: dict) -> dict | None:
    """配置 Context Compression."""
    ui.print_step(1, 1, t("setup.compression.title"))
    
    compression = config.get('compression', {})
    
    enabled = ask_yes_no(t("setup.compression.enable"), default=compression.get('enabled', True))
    if enabled is None:
        return None
    
    new_config = {"enabled": enabled}
    
    if enabled:
        # Hermes 默认值是 0.50，与 Hermes 保持一致
        current_threshold = compression.get('threshold', 0.50)
        threshold = ask_input(t("setup.compression.threshold"), default=str(current_threshold))
        if threshold is None:
            return None
        try:
            thresh = float(threshold)
            thresh = max(0.50, min(0.95, thresh))
        except ValueError:
            thresh = 0.50
        new_config["threshold"] = thresh
        
        summary_model = ask_input(t("setup.compression.summary_model"), default=compression.get('summary_model', 'openai/gpt-4o-mini'))
        if summary_model is None:
            return None
        new_config["summary_model"] = summary_model
    
    return new_config


# =============================================================================
# Section 8: STT (Speech-to-Text)
# =============================================================================

def setup_stt(config: dict) -> dict | None:
    """配置 STT."""
    ui.print_step(1, 1, t("setup.stt.title"))
    
    stt = config.get('stt', {})
    
    enabled = ask_yes_no(t("setup.stt.enable"), default=stt.get('enabled', False))
    if enabled is None:
        return None
    
    new_config = {"enabled": enabled}
    
    if enabled:
        provider_options = [
            ("local", t("setup.stt.providers.local")),
            ("groq", t("setup.stt.providers.groq")),
            ("openai", t("setup.stt.providers.openai"))
        ]
        
        current_provider = stt.get('provider', 'local')
        current_idx = next((i for i, (k, _) in enumerate(provider_options) if k == current_provider), 0)
        
        choice = ask_choice(t("setup.stt.select_provider"), provider_options, default=current_idx, current_value=current_provider)
        if choice is None:
            return None
        
        new_config["provider"] = provider_options[choice][0]
        
        model = ask_input(t("setup.stt.model"), default=stt.get('model', 'base'))
        if model is None:
            return None
        new_config["model"] = model
    
    return new_config


# =============================================================================
# Section 9: TTS (Text-to-Speech) - Enhanced with Local TTS
# =============================================================================

def _check_espeak_ng() -> bool:
    """Check if espeak-ng is installed."""
    import shutil
    return shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None


def _install_neutts_deps() -> bool:
    """Install NeuTTS dependencies. Returns True on success."""
    import subprocess
    import sys
    
    # 检查 espeak-ng
    if not _check_espeak_ng():
        print()
        print_warning("NeuTTS requires espeak-ng for phonemization")
        if sys.platform == "darwin":
            print_info("安装方式: brew install espeak-ng")
        elif sys.platform == "win32":
            print_info("安装方式: choco install espeak-ng")
        else:
            print_info("安装方式: sudo apt install espeak-ng")
        print()
        if ask_yes_no("Install espeak-ng now?", default=False):
            try:
                if sys.platform == "darwin":
                    subprocess.run(["brew", "install", "espeak-ng"], check=True)
                elif sys.platform == "win32":
                    subprocess.run(["choco", "install", "espeak-ng", "-y"], check=True)
                else:
                    subprocess.run(["sudo", "apt", "install", "-y", "espeak-ng"], check=True)
                print_success("espeak-ng installed")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print_warning(f"Cannot auto-install espeak-ng: {e}")
                print_info("Please install manually and run again")
                return False
        else:
            print_warning("espeak-ng must be installed to use NeuTTS")
    
    # 安装 neutts Python 包
    print()
    print_info("Installing neutts Python package...")
    print_info("TTS model (~300MB) will be downloaded on first use")
    print()
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "neutts[all]", "--quiet"],
            check=True, timeout=300,
        )
        print_success("neutts installed successfully")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_error(f"neutts installation failed: {e}")
        print_info("手动安装: python -m pip install -U neutts[all]")
        return False


def _install_kittentts_deps() -> bool:
    """Install KittenTTS dependencies. Returns True on success."""
    import subprocess
    import sys
    
    wheel_url = (
        "https://github.com/KittenML/KittenTTS/releases/download/"
        "0.8.1/kittentts-0.8.1-py3-none-any.whl"
    )
    print()
    print_info("Installing kittentts Python package (~25-80MB model downloaded on first use)...")
    print()
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", wheel_url, "soundfile", "--quiet"],
            check=True, timeout=300,
        )
        print_success("kittentts installed successfully")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print_error(f"kittentts installation failed: {e}")
        print_info(f"手动安装: python -m pip install -U '{wheel_url}' soundfile")
        return False


def setup_tts(config: dict) -> dict | None:
    """Configure TTS with multiple provider support (Hermes-compatible)."""
    print_header(t("setup.tts.title"))
    print_info(t("setup.tts.title"))
    print_info(f"   Guide: {_DOCS_BASE}/user-guide/tts")
    print()

    tts = config.get('tts', {})
    current_provider = tts.get('provider', 'edge')
    
    current_label = t(f"setup.tts.providers.{current_provider}")

    choices = [
        t("setup.tts.providers.edge"),
        t("setup.tts.providers.elevenlabs"),
        t("setup.tts.providers.openai"),
        t("setup.tts.providers.xai"),
        t("setup.tts.providers.minimax"),
        t("setup.tts.providers.mistral"),
        t("setup.tts.providers.gemini"),
        t("setup.tts.providers.neutts"),
        t("setup.tts.providers.kittentts"),
    ]
    providers = ["edge", "elevenlabs", "openai", "xai", "minimax", "mistral", "gemini", "neutts", "kittentts"]
    
    # 尝试找到当前 provider 的索引
    current_idx = 0
    try:
        current_idx = providers.index(current_provider)
    except ValueError:
        pass
    
    choices.append(t("setup.tts.keep_current", provider=current_label))
    keep_current_idx = len(choices) - 1
    
    provider_idx = ask_choice(t("setup.tts.select_provider"), choices, default=current_idx if current_idx < keep_current_idx else keep_current_idx)
    
    if provider_idx == keep_current_idx:
        print_info(t("setup.tts.keep_current", provider=current_label))
        return {}

    selected_provider = providers[provider_idx]
    new_config = {"provider": selected_provider}

    # 处理不同 provider 的 API Key
    if selected_provider == "neutts":
        # 检查是否已安装
        neutts_installed = importlib.util.find_spec("neutts") is not None
        if neutts_installed:
            print_success(t("setup.tts.neutts_installed"))
        else:
            print()
            print_info(t("setup.tts.installing"))
            print_info("  • Python package: neutts (~50MB install + ~300MB model on first use)")
            print_info("  • System package: espeak-ng (phonemizer)")
            print()
            if ask_yes_no(t("setup.tts.install_now"), default=True):
                if not _install_neutts_deps():
                    print_warning(t("setup.tts.install_failed"))
                    new_config["provider"] = "edge"
        return new_config

    elif selected_provider == "kittentts":
        kittentts_installed = importlib.util.find_spec("kittentts") is not None
        if kittentts_installed:
            print_success(t("setup.tts.kittentts_installed"))
        else:
            print()
            print_info(t("setup.tts.kittentts_description"))
            print_info("Voices: Jasper, Bella, Luna, Bruno, Rosie, Hugo, Kiki, Leo")
            print()
            if ask_yes_no(t("setup.tts.install_now"), default=True):
                if not _install_kittentts_deps():
                    print_warning("KittenTTS installation incomplete. Falling back to Edge TTS.")
                    new_config["provider"] = "edge"
        return new_config

    elif selected_provider == "elevenlabs":
        existing = os.environ.get('ELEVENLABS_API_KEY', '')
        if not existing:
            print()
            api_key = prompt("ElevenLabs API key", password=True)
            if api_key:
                _save_env_value('ELEVENLABS_API_KEY', api_key)
                print_success("ElevenLabs API key saved")
            else:
                print_warning("No API key provided. Falling back to Edge TTS.")
                new_config["provider"] = "edge"

    elif selected_provider == "openai":
        existing = os.environ.get('VOICE_TOOLS_OPENAI_KEY', '') or os.environ.get('OPENAI_API_KEY', '')
        if not existing:
            print()
            api_key = prompt("OpenAI API key for TTS", password=True)
            if api_key:
                _save_env_value('VOICE_TOOLS_OPENAI_KEY', api_key)
                print_success("OpenAI TTS API key saved")
            else:
                print_warning("No API key provided. Falling back to Edge TTS.")
                new_config["provider"] = "edge"

    elif selected_provider == "xai":
        existing = os.environ.get('XAI_API_KEY', '')
        if not existing:
            print()
            api_key = prompt("xAI API key for TTS", password=True)
            if api_key:
                _save_env_value('XAI_API_KEY', api_key)
                print_success("xAI TTS API key saved")
            else:
                print_warning("No API key provided. Falling back to Edge TTS.")
                new_config["provider"] = "edge"
        else:
            print_success("xAI TTS will use your existing XAI_API_KEY")
        
        # 语音选择
        voice_id = prompt("xAI voice_id (Enter for 'eve', or paste a custom voice ID)", default="eve")
        if voice_id and voice_id.strip():
            new_config["xai_voice_id"] = voice_id.strip()

    elif selected_provider == "minimax":
        existing = os.environ.get('MINIMAX_API_KEY', '')
        if not existing:
            print()
            api_key = prompt("MiniMax API key for TTS", password=True)
            if api_key:
                _save_env_value('MINIMAX_API_KEY', api_key)
                print_success("MiniMax TTS API key saved")
            else:
                print_warning("No API key provided. Falling back to Edge TTS.")
                new_config["provider"] = "edge"

    elif selected_provider == "mistral":
        existing = os.environ.get('MISTRAL_API_KEY', '')
        if not existing:
            print()
            api_key = prompt("Mistral API key for TTS", password=True)
            if api_key:
                _save_env_value('MISTRAL_API_KEY', api_key)
                print_success("Mistral TTS API key saved")
            else:
                print_warning("No API key provided. Falling back to Edge TTS.")
                new_config["provider"] = "edge"

    elif selected_provider == "gemini":
        existing = os.environ.get('GEMINI_API_KEY', '') or os.environ.get('GOOGLE_API_KEY', '')
        if not existing:
            print()
            print_info("Get a free API key at https://aistudio.google.com/app/apikey")
            api_key = prompt("Gemini API key for TTS", password=True)
            if api_key:
                _save_env_value('GEMINI_API_KEY', api_key)
                print_success("Gemini TTS API key saved")
            else:
                print_warning("No API key provided. Falling back to Edge TTS.")
                new_config["provider"] = "edge"

    # 声音选项（仅对需要声音的 Provider 显示）
    if selected_provider not in ("neutts", "kittentts", "gemini"):
        voice_options = [
            ("alloy", "Alloy - 中性"),
            ("echo", "Echo - 男声"),
            ("fable", "Fable - 英式"),
            ("onyx", "Onyx - 男声"),
            ("nova", "Nova - 女声"),
            ("shimmer", "Shimmer - 女声")
        ]
        
        current_voice = tts.get('voice', 'alloy')
        current_idx = next((i for i, (k, _) in enumerate(voice_options) if k == current_voice), 0)
        
        choice = ask_choice("选择 TTS Voice:", voice_options, default=current_idx, current_value=current_voice)
        if choice is None:
            return None
        
        new_config["voice"] = voice_options[choice][0]
    
    model = ask_input("TTS Model", default=tts.get('model', 'tts-1'))
    if model:
        new_config["model"] = model

    print_success(t("setup.tts.provider_set", provider=t(f"setup.tts.providers.{new_config['provider']}")))
    return new_config


# =============================================================================
# Section 10: Browser Tool
# =============================================================================

def setup_browser(config: dict) -> dict | None:
    """配置 Browser 工具."""
    ui.print_step(1, 1, t("setup.browser.title"))
    
    browser = config.get('browser', {})
    
    enabled = ask_yes_no(t("setup.browser.enable"), default=browser.get('enabled', False))
    if enabled is None:
        return None
    
    new_config = {"enabled": enabled}
    
    if enabled:
        proxies = ask_yes_no(t("setup.browser.residential_proxy"), default=browser.get('proxies', True))
        if proxies is None:
            return None
        new_config["proxies"] = proxies
        
        stealth = ask_yes_no(t("setup.browser.stealth_mode"), default=browser.get('advanced_stealth', False))
        if stealth is None:
            return None
        new_config["advanced_stealth"] = stealth
        
        session_timeout = ask_input(t("setup.browser.session_timeout"), default=str(browser.get('session_timeout', 300)))
        if session_timeout is None:
            return None
        new_config["session_timeout"] = int(session_timeout) if session_timeout.isdigit() else 300
        
        inactivity_timeout = ask_input(t("setup.browser.inactivity_timeout"), default=str(browser.get('inactivity_timeout', 120)))
        if inactivity_timeout is None:
            return None
        new_config["inactivity_timeout"] = int(inactivity_timeout) if inactivity_timeout.isdigit() else 120
    
    return new_config


# =============================================================================
# Section 11: Debug Tools
# =============================================================================

def setup_debug(config: dict) -> dict | None:
    """配置 Debug 工具."""
    ui.print_step(1, 1, t("setup.debug.title"))
    
    debug = config.get('debug_tools', {})
    
    web_debug = ask_yes_no(t("setup.debug.web_tools"), default=debug.get('web_tools', False))
    if web_debug is None:
        return None
    
    vision_debug = ask_yes_no(t("setup.debug.vision_tools"), default=debug.get('vision_tools', False))
    if vision_debug is None:
        return None
    
    moa_debug = ask_yes_no(t("setup.debug.moa_tools"), default=debug.get('moa_tools', False))
    if moa_debug is None:
        return None
    
    image_debug = ask_yes_no(t("setup.debug.image_tools"), default=debug.get('image_tools', False))
    if image_debug is None:
        return None
    
    return {
        "web_tools": web_debug,
        "vision_tools": vision_debug,
        "moa_tools": moa_debug,
        "image_tools": image_debug
    }


# =============================================================================
# Section 11b: Skills Hub Configuration
# =============================================================================

def setup_skills_hub(config: dict) -> dict | None:
    """配置 Skills Hub (GitHub 技能市场)."""
    ui.print_step(1, 1, t("setup.skills_hub.title"))
    
    # 检查 GITHUB_TOKEN 环境变量
    current_token = os.environ.get('GITHUB_TOKEN', '')
    has_token = bool(current_token)
    
    if has_token:
        ui.print_info(t("setup.skills_hub.token_configured"))
        ui.print_info(t("setup.skills_hub.token_hint", suffix=current_token[-4:] if len(current_token) > 4 else current_token))
        
        reuse = ask_yes_no(t("setup.skills_hub.keep_token"), default=True)
        if reuse is None:
            return None
        if reuse:
            return {"enabled": True}
    
    print()
    ui.print_info(t("setup.skills_hub.description"))
    ui.print_info(t("setup.skills_hub.requires_token"))
    ui.print_info(t("setup.skills_hub.get_token"))
    print()
    ui.print_info(t("setup.skills_hub.token_permissions"))
    ui.print_info(f"  - {t('setup.skills_hub.permission_repo')}")
    ui.print_info(f"  - {t('setup.skills_hub.permission_read_user')}")
    print()
    
    token = ask_input(t("setup.skills_hub.github_token"), password=True, required=False)
    if token is None:
        return None
    
    if token:
        # 保存到环境变量（会在下次运行时生效）
        config.setdefault('env', {})['GITHUB_TOKEN'] = token
        # 保存到 .env 文件
        _save_env_value('GITHUB_TOKEN', token)
        ui.print_success(t("setup.skills_hub.token_configured"))
        return {"enabled": True}
    else:
        ui.print_info(t("setup.skills_hub.skipped"))
        return {"enabled": False}


def _save_env_value(key: str, value: str) -> None:
    """保存环境变量到 .env 文件."""
    import os
    env_file = os.path.join(CONFIG_DIR, ".env")
    
    # 读取现有内容
    env_vars = {}
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            env_vars[parts[0].strip()] = parts[1].strip()
        except Exception:
            pass
    
    # 更新值
    env_vars[key] = value
    
    # 写回文件
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            for k, v in env_vars.items():
                f.write(f"{k}={v}\n")
    except Exception:
        pass


# =============================================================================
# Section 12: Preferences
# =============================================================================

def setup_depth(config: dict) -> dict | None:
    """配置响应详细程度."""
    ui.print_step(1, 1, t("setup.preferences.explanation_depth.title"))
    
    prefs = config.get('preferences', {})
    depth_options = [
        ("brief", t("setup.preferences.explanation_depth.options.brief")),
        ("moderate", t("setup.preferences.explanation_depth.options.moderate")),
        ("detailed", t("setup.preferences.explanation_depth.options.detailed"))
    ]
    current_depth = prefs.get('explanation_depth', 'detailed')
    current_idx = next((i for i, (k, _) in enumerate(depth_options) if k == current_depth), 2)
    
    choice = ask_choice(t("setup.preferences.explanation_depth.prompt"), depth_options, default=current_idx, current_value=current_depth)
    if choice is None:
        return None
    
    return {"explanation_depth": depth_options[choice][0]}


def setup_caching(config: dict) -> dict | None:
    """配置响应缓存."""
    ui.print_step(1, 1, t("setup.preferences.caching.title"))
    
    prefs = config.get('preferences', {})
    current_caching = prefs.get('enable_caching', True)
    
    use_caching = ask_yes_no(t("setup.preferences.caching.enable"), default=current_caching)
    if use_caching is None:
        return None
    
    return {"enable_caching": use_caching}


def setup_intent(config: dict) -> dict | None:
    """配置意图识别."""
    ui.print_step(1, 1, t("setup.preferences.intent.title"))
    
    mode_options = [
        ("llm", t("setup.preferences.intent.options.llm")),
        ("hybrid", t("setup.preferences.intent.options.hybrid")),
        ("keyword", t("setup.preferences.intent.options.keyword"))
    ]
    
    current_mode = config.get('intent_mode', 'llm')
    current_idx = next((i for i, (k, _) in enumerate(mode_options) if k == current_mode), 0)
    
    choice = ask_choice(t("setup.preferences.intent.prompt"), mode_options, default=current_idx, current_value=current_mode)
    if choice is None:
        return None
    
    return {"intent_mode": mode_options[choice][0]}


# =============================================================================
# Section 13: Messaging Platforms (Gateway)
# =============================================================================

def _setup_telegram():
    """Configure Telegram bot credentials and allowlist."""
    print_header("Telegram")
    
    existing = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if existing:
        print_info("Telegram: " + t("setup.summary.configured"))
        if not ask_yes_no("Reconfigure Telegram?", default=False):
            # Check missing allowlist on existing config
            if not os.environ.get('TELEGRAM_ALLOWED_USERS'):
                print_warning("⚠️  Telegram has no user allowlist - anyone can use your bot!")
                if ask_yes_no("Add allowed users now?", default=True):
                    print_info("   To find your Telegram user ID: message @userinfobot")
                    allowed_users = prompt("Allowed user IDs (comma-separated)")
                    if allowed_users:
                        _save_env_value('TELEGRAM_ALLOWED_USERS', allowed_users.replace(" ", ""))
                        print_success("Telegram allowlist configured")
            return

    print_info("Create a bot via @BotFather on Telegram")
    import re

    while True:
        token = prompt("Telegram bot token", password=True)
        if not token:
            return
        if not re.match(r"^\d+:[A-Za-z0-9_-]{30,}$", token):
            print_error(
                "Invalid token format. Expected: <numeric_id>:<alphanumeric_hash> "
                "(e.g., 123456789:ABCdefGHI-jklMNOpqrSTUvwxYZ)"
            )
            continue
        break
    _save_env_value('TELEGRAM_BOT_TOKEN', token)
    print_success("Telegram token saved")

    print()
    print_info("🔒 Security: Restrict who can use your bot")
    print_info("   To find your Telegram user ID:")
    print_info("   1. Message @userinfobot on Telegram")
    print_info("   2. It will reply with your numeric ID (e.g., 123456789)")
    print()
    allowed_users = prompt(
        "Allowed user IDs (comma-separated, leave empty for open access)"
    )
    if allowed_users:
        _save_env_value('TELEGRAM_ALLOWED_USERS', allowed_users.replace(" ", ""))
        print_success("Telegram allowlist configured - only listed users can use the bot")
    else:
        print_info("⚠️  No allowlist set - anyone who finds your bot can use it!")

    print()
    print_info("📬 Home Channel: where Handsome Agent delivers cron job results,")
    print_info("   cross-platform messages, and notifications.")
    print_info("   For Telegram DMs, this is your user ID (same as above).")

    first_user_id = allowed_users.split(",")[0].strip() if allowed_users else ""
    if first_user_id:
        if ask_yes_no(f"Use your user ID ({first_user_id}) as the home channel?", default=True):
            _save_env_value('TELEGRAM_HOME_CHANNEL', first_user_id)
            print_success(f"Telegram home channel set to {first_user_id}")
        else:
            home_channel = prompt("Home channel ID (or leave empty to set later with /set-home in Telegram)")
            if home_channel:
                _save_env_value('TELEGRAM_HOME_CHANNEL', home_channel)
    else:
        print_info("   You can also set this later by typing /set-home in your Telegram chat.")
        home_channel = prompt("Home channel ID (leave empty to set later)")
        if home_channel:
            _save_env_value('TELEGRAM_HOME_CHANNEL', home_channel)


def _setup_slack():
    """Configure Slack bot credentials."""
    print_header("Slack")
    existing = os.environ.get('SLACK_BOT_TOKEN', '')
    if existing:
        print_info("Slack: " + t("setup.summary.configured"))
        if not ask_yes_no("Reconfigure Slack?", default=False):
            return

    print_info("Steps to create a Slack app:")
    print_info("   1. Go to https://api.slack.com/apps → Create New App")
    print_info("      Pick 'From an app manifest' — we'll generate one for you below.")
    print_info("   2. Enable Socket Mode: Settings → Socket Mode → Enable")
    print_info("      • Create an App-Level Token with 'connections:write' scope")
    print_info("   3. Install to Workspace: Settings → Install App")
    print_info("   4. After installing, invite the bot to channels: /invite @YourBot")
    print()

    print_info("   Full guide: https://handsome-agent.nousresearch.com/docs/user-guide/messaging/slack/")
    print()

    bot_token = prompt("Slack Bot Token (xoxb-...)", password=True)
    if not bot_token:
        return
    _save_env_value('SLACK_BOT_TOKEN', bot_token)
    app_token = prompt("Slack App Token (xapp-...)", password=True)
    if app_token:
        _save_env_value('SLACK_APP_TOKEN', app_token)
    print_success("Slack tokens saved")

    print()
    print_info("🔒 Security: Restrict who can use your bot")
    print_info("   To find a Member ID: click a user's name → View full profile → ⋮ → Copy member ID")
    print()
    allowed_users = prompt(
        "Allowed user IDs (comma-separated, leave empty to deny everyone except paired users)"
    )
    if allowed_users:
        _save_env_value('SLACK_ALLOWED_USERS', allowed_users.replace(" ", ""))
        print_success("Slack allowlist configured")
    else:
        print_warning("⚠️  No Slack allowlist set - unpaired users will be denied by default.")

    print()
    print_info("📬 Home Channel: where Handsome Agent delivers cron job results,")
    print_info("   cross-platform messages, and notifications.")
    print_info("   To get a channel ID: open the channel in Slack, then right-click")
    print_info("   the channel name → Copy link — the ID starts with C (e.g. C01ABC2DE3F).")
    print_info("   You can also set this later by typing /set-home in a Slack channel.")
    home_channel = prompt("Home channel ID (leave empty to set later with /set-home)")
    if home_channel:
        _save_env_value('SLACK_HOME_CHANNEL', home_channel.strip())


def _setup_discord():
    """Configure Discord bot credentials."""
    print_header("Discord")
    existing = os.environ.get('DISCORD_BOT_TOKEN', '')
    if existing:
        print_info("Discord: " + t("setup.summary.configured"))
        if not ask_yes_no("Reconfigure Discord?", default=False):
            return

    print_info("Steps to create a Discord app:")
    print_info("   1. Go to https://discord.com/developers/applications")
    print_info("   2. Create New Application")
    print_info("   3. Bot → Add Bot → Reset Token → copy the token")
    print_info("   4. Enable Message Content Intent in Bot settings")
    print_info("   5. OAuth2 → URL Generator → check 'bot' scope and permissions")
    print_info("   6. Invite the bot to your server using the generated URL")
    print()

    bot_token = prompt("Discord Bot Token", password=True)
    if not bot_token:
        return
    _save_env_value('DISCORD_BOT_TOKEN', bot_token)
    print_success("Discord bot token saved")

    print()
    print_info("🔒 Security: Restrict who can use your bot")
    print_info("   Server admins can right-click a user → Copy User ID")
    print_info("   (Developer Mode must be enabled in User Settings)")
    print()
    allowed_users = prompt(
        "Allowed user IDs (comma-separated, leave empty for open access)"
    )
    if allowed_users:
        _save_env_value('DISCORD_ALLOWED_USERS', allowed_users.replace(" ", ""))
        print_success("Discord allowlist configured")
    else:
        print_info("⚠️  No allowlist set - anyone who can see the bot can use it!")


def _setup_whatsapp():
    """Configure WhatsApp Business API."""
    print_header("WhatsApp")
    existing = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
    if existing:
        print_info("WhatsApp: " + t("setup.summary.configured"))
        if not ask_yes_no("Reconfigure WhatsApp?", default=False):
            return

    print_info("WhatsApp Business API Setup:")
    print_info("   1. Create a Meta Business account")
    print_info("   2. Create a WhatsApp Business app in Meta Developer Console")
    print_info("   3. Generate a permanent access token")
    print_info("   4. Get your Phone Number ID and WhatsApp Business Account ID")
    print()

    access_token = prompt("WhatsApp Access Token", password=True)
    if not access_token:
        return
    _save_env_value('WHATSAPP_ACCESS_TOKEN', access_token)

    phone_id = prompt("Phone Number ID")
    if phone_id:
        _save_env_value('WHATSAPP_PHONE_ID', phone_id)

    business_account_id = prompt("WhatsApp Business Account ID")
    if business_account_id:
        _save_env_value('WHATSAPP_BUSINESS_ACCOUNT_ID', business_account_id)

    print_success("WhatsApp credentials saved")


def setup_gateway(config: dict):
    """Configure messaging platform integrations."""
    print_header(t("setup.gateway.title"))
    print_info(t("setup.gateway.description"))
    print_info(f"   {t('setup.gateway.guide', url=f'{_DOCS_BASE}/user-guide/messaging')}")
    print()

    platforms = [
        ("telegram", "Telegram", _setup_telegram),
        ("slack", "Slack", _setup_slack),
        ("discord", "Discord", _setup_discord),
        ("whatsapp", "WhatsApp", _setup_whatsapp),
    ]

    # Check which platforms are already configured
    configured = []
    if os.environ.get('TELEGRAM_BOT_TOKEN'):
        configured.append("Telegram")
    if os.environ.get('SLACK_BOT_TOKEN'):
        configured.append("Slack")
    if os.environ.get('DISCORD_BOT_TOKEN'):
        configured.append("Discord")
    if os.environ.get('WHATSAPP_ACCESS_TOKEN'):
        configured.append("WhatsApp")

    if configured:
        print_info(t("setup.gateway.configured", platforms=', '.join(configured)))
    print()

    print_info(t("setup.gateway.select_platform"))
    platform_options = [(p[0], p[1]) for p in platforms]
    platform_options.append(("done", t("utils.done")))

    while True:
        choice = ask_choice("选择平台:", platform_options, default=len(platform_options) - 1)
        if choice is None or choice == len(platform_options) - 1:
            break

        platform_id, platform_name, setup_func = platforms[choice]
        try:
            setup_func()
        except Exception as e:
            print_warning(f"配置 {platform_name} 时出错: {e}")

    print()
    print_success(f"{t('setup.gateway.title')} - {t('setup.summary.configured')}")


# =============================================================================
# Section 14: Tools Configuration (Web Search, etc.)
# =============================================================================

def setup_tools(config: dict, first_install: bool = False):
    """Configure tools — Web Search, Browser, Image Generation, etc."""
    print_header(t("setup.tools.title"))
    print_info(t("setup.tools.title"))
    print_info(f"   Guide: {_DOCS_BASE}/user-guide/tools")
    print()

    # Web Search Tools
    print_info("🌐 Web Search & Extract")
    print_info("   Enable web search and content extraction capabilities.")
    print_info("   Supported providers: Exa, Tavily, Firecrawl, SearXNG")
    print()

    exa_key = os.environ.get('EXA_API_KEY', '')
    tavily_key = os.environ.get('TAVILY_API_KEY', '')
    firecrawl_key = os.environ.get('FIRECRAWL_API_KEY', '')

    if exa_key or tavily_key or firecrawl_key:
        print_success(t("setup.summary.configured"))
    else:
        print_info(t("setup.summary.not_configured"))

    if ask_yes_no(t("setup.tools.web_search.prompt"), default=False):
        web_provider = ask_choice(
            t("setup.tools.web_search.select_provider"),
            [
                ("exa", t("setup.tools.web_search.providers.exa")),
                ("tavily", t("setup.tools.web_search.providers.tavily")),
                ("firecrawl", t("setup.tools.web_search.providers.firecrawl")),
                ("searxng", t("setup.tools.web_search.providers.searxng")),
            ],
            default=0
        )
        if web_provider is None:
            return

        provider_names = ["exa", "tavily", "firecrawl", "searxng"]
        selected = provider_names[web_provider]

        if selected == "exa":
            api_key = ask_input("Exa API Key", password=True, required=True)
            if api_key:
                _save_env_value('EXA_API_KEY', api_key)
        elif selected == "tavily":
            api_key = ask_input("Tavily API Key", password=True, required=True)
            if api_key:
                _save_env_value('TAVILY_API_KEY', api_key)
        elif selected == "firecrawl":
            api_key = ask_input("Firecrawl API Key", password=True, required=True)
            if api_key:
                _save_env_value('FIRECRAWL_API_KEY', api_key)
        elif selected == "searxng":
            base_url = ask_input("SearXNG URL", default="http://localhost:8888")
            if base_url:
                _save_env_value('SEARXNG_URL', base_url)

        print_success(t("setup.summary.configured"))

    # Browser Tools
    print()
    print_info("🌐 Browser Automation")
    print_info("   Enable automated browser interactions.")
    print_info("   Supported: Browserbase, Camofox, Local browser")

    browserbase_key = os.environ.get('BROWSERBASE_API_KEY', '')
    camofox_url = os.environ.get('CAMOFOX_URL', '')

    if browserbase_key or camofox_url:
        print_success(t("setup.summary.configured"))
    else:
        print_info(t("setup.summary.not_configured"))

    if ask_yes_no(t("setup.tools.browser_automation.prompt"), default=False):
        browser_provider = ask_choice(
            t("setup.tools.browser_automation.select_provider"),
            [
                ("browserbase", t("setup.tools.browser_automation.providers.browserbase")),
                ("camofox", t("setup.tools.browser_automation.providers.camofox")),
                ("local", t("setup.tools.browser_automation.providers.local")),
            ],
            default=0
        )
        if browser_provider is None:
            return

        provider_names = ["browserbase", "camofox", "local"]
        selected = provider_names[browser_provider]

        if selected == "browserbase":
            api_key = ask_input("Browserbase API Key", password=True, required=True)
            if api_key:
                _save_env_value('BROWSERBASE_API_KEY', api_key)
            project_id = ask_input("Browserbase Project ID", required=True)
            if project_id:
                _save_env_value('BROWSERBASE_PROJECT_ID', project_id)
        elif selected == "camofox":
            base_url = ask_input("Camofox URL", default="http://localhost:9222")
            if base_url:
                _save_env_value('CAMOFOX_URL', base_url)

        print_success(t("setup.summary.configured"))

    # Image Generation
    print()
    print_info("🎨 Image Generation")
    print_info("   Enable AI-powered image generation.")
    print_info("   Supported providers: Fal, OpenAI DALL-E")

    fal_key = os.environ.get('FAL_KEY', '')
    if fal_key:
        print_success(t("setup.summary.configured") + " (Fal)")
    else:
        print_info(t("setup.summary.not_configured"))

    if ask_yes_no(t("setup.tools.image_generation.prompt"), default=False):
        image_provider = ask_choice(
            t("setup.tools.image_generation.select_provider"),
            [
                ("fal", t("setup.tools.image_generation.providers.fal")),
                ("openai", t("setup.tools.image_generation.providers.openai")),
            ],
            default=0
        )
        if image_provider is None:
            return

        if image_provider == 0:
            api_key = ask_input("Fal API Key", password=True, required=True)
            if api_key:
                _save_env_value('FAL_KEY', api_key)
                print_success("Fal API key saved - image generation enabled!")

    print()
    print_success(f"{t('setup.tools.title')} - {t('setup.summary.configured')}")


# =============================================================================
# Section 15: Credential Pool (Same-Provider Fallback)
# =============================================================================

def _supports_same_provider_pool_setup(provider: str) -> bool:
    """Check if provider supports credential pooling."""
    if not provider or provider == "custom":
        return False
    if provider == "openrouter":
        return True
    # 其他支持 pool 的 provider 可以在这里添加
    return False


def setup_credential_pool(config: dict):
    """Configure same-provider fallback and credential rotation."""
    provider = config.get('model', {}).get('provider')
    if not provider:
        return

    if not _supports_same_provider_pool_setup(provider):
        return

    print_header("Same-Provider Fallback & Rotation")
    print_info(
        "Handsome Agent can keep multiple credentials for one provider and rotate between"
    )
    print_info(
        "them when a credential is exhausted or rate-limited."
    )
    print()

    if ask_yes_no("添加额外的凭证用于故障转移?", default=False):
        api_key = prompt("Additional API key for same provider", password=True)
        if api_key:
            # 保存到 pool
            pool_key = f"{provider.upper()}_POOL_KEYS"
            existing = os.environ.get(pool_key, '')
            if existing:
                new_pool = f"{existing},{api_key}"
            else:
                new_pool = api_key
            _save_env_value(pool_key, new_pool)
            print_success("Additional credential saved!")

    # 选择轮换策略
    print()
    strategy_labels = [
        "Fill-first / sticky — keep using the first healthy credential until it is exhausted",
        "Round robin — rotate to the next healthy credential after each selection",
        "Random — pick a random healthy credential each time",
    ]
    current_strategy = config.get('credential_pool_strategies', {}).get(provider, 'fill_first')
    default_idx = {"fill_first": 0, "round_robin": 1, "random": 2}.get(current_strategy, 0)

    strategy_idx = ask_choice(
        "Select same-provider rotation strategy:",
        strategy_labels,
        default=default_idx
    )

    strategy_value = ["fill_first", "round_robin", "random"][strategy_idx]
    config.setdefault('credential_pool_strategies', {})[provider] = strategy_value
    print_success(f"Saved {provider} rotation strategy: {strategy_value}")


# =============================================================================
# Section 16: Vision Configuration (Enhanced)
# =============================================================================

def setup_vision(config: dict) -> dict | None:
    """Configure vision and image analysis backend."""
    print_header(t("setup.vision.title"))
    print_info(t("setup.vision.title"))
    print()

    # 检查主模型是否已支持 vision
    llm = config.get('llm', {})
    provider = llm.get('provider', '')

    vision_capable = {"openai", "anthropic", "google", "moonshot", "zhipu", "dashscope"}
    if provider in vision_capable:
        print_info(t("setup.vision.already_supported", provider=provider))
        return {}

    # Vision options
    vision_choices = [
        t("setup.vision.options.openrouter"),
        t("setup.vision.options.openai_compatible"),
        t("setup.vision.options.skip"),
    ]
    vision_idx = ask_choice(t("setup.vision.prompt"), vision_choices, default=2)

    if vision_idx == 0:  # OpenRouter
        api_key = ask_input(t("setup.vision.openrouter_key"), password=True, required=True)
        if api_key:
            _save_env_value('OPENROUTER_API_KEY', api_key)
            config.setdefault('auxiliary', {}).setdefault('vision', {})['provider'] = 'openrouter'
            print_success("Vision will use Gemini via OpenRouter")
        return {}

    elif vision_idx == 1:  # OpenAI-compatible
        base_url = ask_input(t("setup.vision.base_url"), default="https://api.openai.com/v1")
        if base_url:
            is_native_openai = "api.openai.com" in base_url
            key_label = t("setup.vision.api_key") if is_native_openai else t("setup.vision.api_key")
            api_key = ask_input(key_label, password=True, required=True)
            if api_key:
                _save_env_value('OPENAI_API_KEY', api_key)
                config.setdefault('auxiliary', {}).setdefault('vision', {})['base_url'] = base_url

                # Select vision model
                if is_native_openai:
                    oai_vision_models = ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]
                    vm_choices = [(m, m) for m in oai_vision_models]
                    vm_choices.append(("custom", "Custom model"))
                    vm_idx = ask_choice(t("setup.vision.vision_model"), vm_choices, default=1)
                    if vm_idx is None:
                        return None
                    if vm_idx < len(oai_vision_models):
                        _save_env_value('AUXILIARY_VISION_MODEL', oai_vision_models[vm_idx])
                    else:
                        custom_model = ask_input(t("setup.vision.vision_model"), default="gpt-4o-mini")
                        if custom_model:
                            _save_env_value('AUXILIARY_VISION_MODEL', custom_model)
                else:
                    custom_model = ask_input(t("setup.vision.vision_model"), default="")
                    if custom_model:
                        _save_env_value('AUXILIARY_VISION_MODEL', custom_model)

                print_success(f"Vision configured with {base_url}")
        return {}

    return {}


# =============================================================================
# Default Agent Settings (应用推荐默认值)
# =============================================================================

def _apply_default_agent_settings(config: dict):
    """Apply recommended defaults for all agent settings without prompting."""
    config.setdefault("agent", {})["max_turns"] = 90

    config.setdefault("display", {})["tool_progress"] = "all"

    config.setdefault("compression", {})["enabled"] = True
    config["compression"]["threshold"] = 0.50  # 与 Hermes 一致

    config.setdefault("session_reset", {}).update({
        "mode": "both",
        "idle_minutes": 1440,
        "at_hour": 4,
    })

    save_config(config)
    print_success("Applied recommended defaults:")
    print_info("  Max iterations: 90")
    print_info("  Tool progress: all")
    print_info("  Compression threshold: 0.50")
    print_info("  Session reset: inactivity (1440 min) + daily (4:00)")
    print_info("  Run `handsome setup agent` later to customize.")


# =============================================================================
# Full Setup Wizard
# =============================================================================

def run_full_setup_wizard():
    """运行完整的配置向导流程."""
    config = load_config()  # 加载现有配置（如果有）

    print_setup_banner(config)
    print(f"\n🔄 {t('setup.full_config.title')}...\n")
    
    sections = [
        ("language", t("setup.language.title"), setup_language),
        ("llm", t("setup.llm.title"), setup_llm_provider),
        ("vision", t("setup.vision.title"), setup_vision),
        ("model", t("setup.model_config.title"), setup_model_config),
        ("terminal", t("setup.terminal.title"), setup_terminal),
        ("agent", t("setup.agent.title"), setup_agent_settings),
        ("memory", t("setup.memory.title"), setup_memory),
        ("stt", t("setup.stt.title"), setup_stt),
        ("tts", t("setup.tts.title"), setup_tts),
        ("gateway", t("setup.gateway.title"), setup_gateway),
        ("tools", t("setup.tools.title"), setup_tools),
        ("browser", t("setup.browser.title"), setup_browser),
        ("debug_tools", t("setup.debug.title"), setup_debug),
        ("depth", t("setup.preferences.explanation_depth.title"), setup_depth),
        ("caching", t("setup.preferences.caching.title"), setup_caching),
        ("intent", t("setup.preferences.intent.title"), setup_intent),
    ]
    
    total = len(sections)
    for i, (key, title, setup_func) in enumerate(sections, 1):
        print("\n" + "─" * 60)
        ui.print_info(t("setup.full_config.step", current=i, total=total, title=title))
        
        result = setup_func(config)
        if result is None:
            ui.print_info(t("setup.common.cancel"))
            return None
        
        if key == 'llm':
            config['llm'] = result
        elif key == 'depth':
            config.setdefault('preferences', {}).update(result)
        elif key == 'caching':
            config.setdefault('preferences', {}).update(result)
        else:
            config[key] = result

    # 使用增强的 Banner 显示配置摘要
    from cli.banner import print_setup_summary as _print_summary
    _print_summary(_build_config_status(config))

    save_ask = ask_yes_no(t("setup.full_config.save_prompt"), default=True)
    if save_ask is None or not save_ask:
        return None

    save_config(config)
    ui.print_success(t("setup.common.saved"))
    ui.print_setup_complete()
    ui.print_header_text(t("setup.banner.run_commands"))
    print(f"  {ui.Theme.ACCENT}python -m cli.main --interactive{ui.Colors.RESET}    # {t('cli.welcome')}")
    print(f"  {ui.Theme.ACCENT}python -m cli.main -q \"your question\"{ui.Colors.RESET}   # {t('cli.running')}")
    print()

    return config


def _build_config_status(config: dict) -> dict:
    """构建配置状态摘要"""
    status = {
        "llm": {},
        "terminal": {},
        "memory": {},
        "tools": {"count": 0}
    }

    # LLM
    llm = config.get('llm', {})
    if llm.get('provider') and llm.get('provider') != 'none':
        status["llm"] = {
            "configured": True,
            "provider": llm.get('provider', 'unknown'),
            "model": llm.get('model', 'unknown')
        }
    else:
        status["llm"] = {"configured": False}

    # Terminal
    terminal = config.get('terminal', {})
    status["terminal"] = {
        "backend": terminal.get('backend', 'local')
    }

    # Memory
    memory = config.get('memory', {})
    status["memory"] = {
        "enabled": memory.get('enabled', True),
        "vector_store": memory.get('vector_store', 'sqlite')
    }

    return status


# =============================================================================
# Quick Configuration Wizard (一次配置一个重要选项)
# =============================================================================

def run_quick_config_wizard():
    """快速配置向导 - 每次只配置一个重要选项"""
    config = load_config()
    print_setup_banner(config)
    print(f"\n{t('setup.quick_config.title')}\n")
    print(t("setup.quick_config.description") + "\n")
    
    important_sections = [
        ("language", t("setup.language.title"), setup_language),
        ("llm", t("setup.llm.title"), setup_llm_provider),
        ("vision", t("setup.vision.title"), setup_vision),
        ("model", t("setup.model_config.title"), setup_model_config),
        ("terminal", t("setup.terminal.title"), setup_terminal),
        ("agent", t("setup.agent.title"), setup_agent_settings),
        ("tts", t("setup.tts.title"), setup_tts),
        ("gateway", t("setup.gateway.title"), setup_gateway),
        ("tools", t("setup.tools.title"), setup_tools),
    ]
    
    for i, (key, title, setup_func) in enumerate(important_sections, 1):
        ui.print_info(f"{i}/{len(important_sections)}: {title}")
        print("─" * 50)
        
        result = setup_func(config)
        if result is not None:
            if key == 'llm':
                config['llm'] = result
            elif key in ('depth', 'caching'):
                config.setdefault('preferences', {}).update(result)
            else:
                config[key] = result
            save_config(config)
            ui.print_success(t("setup.common.saved"))
        
        print("\n")
        print_setup_banner(config)
        print(f"\n{t('setup.quick_config.title')}\n")

        remaining = len(important_sections) - i
        if remaining > 0:
            ui.print_info(t("setup.quick_config.remaining", count=remaining))
            continue_config = ask_yes_no(t("setup.quick_config.continue_prompt"), default=True)
            if continue_config is None or not continue_config:
                ui.print_info(t("setup.common.cancel"))
                return

    ui.print_success(t("setup.quick_config.all_complete"))
    from cli.banner import print_setup_summary as _print_summary2
    _print_summary2(_build_config_status(config))


# =============================================================================
# Main Setup Wizard
# =============================================================================
# Multi-Level Menu System (多级菜单系统)
# =============================================================================

class MenuNode:
    """菜单节点，支持嵌套子菜单."""
    def __init__(self, id: str, label: str, icon: str = "", action: str = None, children: list = None, hint: str = ""):
        self.id = id
        self.label = label
        self.icon = icon
        self.action = action  # 如果是叶子节点，对应的 setup 函数名
        self.children = children  # 子菜单列表
        self.hint = hint  # 选项说明


def run_setup_wizard():
    """运行设置向导."""
    config = load_config()

    # 始终显示 Setup Banner（带当前配置信息）
    print_setup_banner(config)

    # 如果没有配置文件，显示提示
    if not has_existing_config():
        print()
        ui.print_warning("⚠️  " + t("setup.summary.not_configured"))
        print()
        ui.print_info(t("menu.quick_start.title") + " - " + t("menu.quick.label"))
        print()
    
    # 定义多级菜单结构
    menu_tree = _build_menu_tree()
    
    # 启动菜单导航
    _navigate_menu(menu_tree, config)


def _build_menu_tree() -> MenuNode:
    """构建多级菜单树结构."""
    # 定义叶子节点（实际配置项）
    leaf_nodes = {
        # 快速开始
        "quick": MenuNode("quick", "快速配置向导", hint="使用推荐配置，快速完成设置", action="quick"),
        "reset_all": MenuNode("reset_all", "重新全部配置", hint="清空配置，重新开始", action="reset_all"),
        
        # AI 配置
        "llm": MenuNode("llm", "大模型配置", hint="选择 AI 提供商和模型", action="llm"),
        "vision": MenuNode("vision", "视觉分析", hint="图片理解能力配置", action="vision"),
        "model": MenuNode("model", "模型参数", hint="max_tokens、temperature 等", action="model"),
        "intent": MenuNode("intent", "意图识别模式", hint="如何理解用户意图", action="intent"),
        
        # 通讯与语音
        "gateway": MenuNode("gateway", "消息平台", hint="Telegram、Slack 等", action="gateway"),
        "tts": MenuNode("tts", "文字转语音", hint="TTS 语音合成", action="tts"),
        "stt": MenuNode("stt", "语音转文字", hint="语音识别输入", action="stt"),
        
        # 系统设置
        "agent": MenuNode("agent", "Agent 设置", hint="迭代次数、工具进度等", action="agent"),
        "terminal": MenuNode("terminal", "Terminal 后端", hint="命令执行环境", action="terminal"),
        "memory": MenuNode("memory", "记忆系统", hint="向量数据库配置", action="memory"),
        "language": MenuNode("language", "语言设置", hint="界面显示语言", action="language"),
        
        # 工具与扩展
        "tools": MenuNode("tools", t("menu.tools_config.label"), hint=t("menu.tools_config.hint"), action="tools"),
        "browser": MenuNode("browser", "Browser 自动化", hint="无头浏览器控制", action="browser"),
        "debug_tools": MenuNode("debug_tools", "Debug 配置", hint="调试工具开关", action="debug_tools"),
        "skills_hub": MenuNode("skills_hub", "Skills Hub", hint="GitHub 技能市场", action="skills_hub"),
        
        # 系统偏好
        "depth": MenuNode("depth", "响应详细程度", hint="AI 回复详细程度", action="depth"),
        "caching": MenuNode("caching", "响应缓存", hint="启用响应缓存加速", action="caching"),
        
        # 辅助功能
        "view": MenuNode("view", "查看当前配置", hint="显示所有配置项", action="view"),
    }
    
    # 构建菜单树
    return MenuNode("root", "主菜单", children=[
        # 快速开始
        MenuNode("quick_start", "🚀 快速开始", hint="快速配置或重置所有设置", children=[
            leaf_nodes["quick"],
            leaf_nodes["reset_all"],
        ]),
        # AI 配置
        MenuNode("ai", "🤖 AI 配置", hint="大模型、视觉、参数、意图识别", children=[
            leaf_nodes["llm"],
            leaf_nodes["vision"],
            leaf_nodes["model"],
            leaf_nodes["intent"],
        ]),
        # 通讯与语音
        MenuNode("communication", "💬 通讯与语音", hint="消息平台、TTS、STT", children=[
            leaf_nodes["gateway"],
            leaf_nodes["tts"],
            leaf_nodes["stt"],
        ]),
        # 系统设置
        MenuNode("system", "⚙️ 系统设置", hint="Agent、Terminal、记忆、语言", children=[
            leaf_nodes["agent"],
            leaf_nodes["terminal"],
            leaf_nodes["memory"],
            leaf_nodes["language"],
        ]),
        # 工具与扩展
        MenuNode("tools_menu", "🛠️ 工具与扩展", hint="工具配置、浏览器、调试、Skills", children=[
            leaf_nodes["tools"],
            leaf_nodes["browser"],
            leaf_nodes["debug_tools"],
            leaf_nodes["skills_hub"],
        ]),
        # 系统偏好
        MenuNode("preferences", "🎨 系统偏好", hint="响应详细程度、缓存", children=[
            leaf_nodes["depth"],
            leaf_nodes["caching"],
        ]),
        # 辅助功能
        MenuNode("utility", "📋 辅助功能", hint="查看当前配置", children=[
            leaf_nodes["view"],
        ]),
    ])


def _translate_menu(key: str, fallback: str) -> str:
    """翻译菜单文本，失败时返回默认值."""
    # 菜单项翻译映射 - 中文键 -> 翻译后文本
    menu_translations = {
        # 主菜单和子菜单标题
        "主菜单": t("menu.root.title"),
        "🚀 快速开始": t("menu.quick_start.title"),
        "🤖 AI 配置": t("menu.ai.title"),
        "💬 通讯与语音": t("menu.communication.title"),
        "📱 通讯与语音": t("menu.communication.title"),
        "⚙️ 系统设置": t("menu.system.title"),
        "🛠️ 工具与扩展": t("menu.tools.title"),
        "工具配置": t("menu.tools_config.label"),
        "💡 系统偏好": t("menu.preferences.title"),
        "🎨 系统偏好": t("menu.preferences.title"),
        "🔧 辅助功能": t("menu.auxiliary.title"),
        "📋 辅助功能": t("menu.auxiliary.title"),
        
        # 叶子节点标签
        "快速配置向导": t("menu.quick.label"),
        "重新全部配置": t("menu.reset_all.label"),
        "大模型配置": t("menu.llm.label"),
        "视觉分析": t("menu.vision.label"),
        "模型参数": t("menu.model.label"),
        "意图识别模式": t("menu.intent.label"),
        "消息平台": t("menu.gateway.label"),
        "文字转语音": t("menu.tts.label"),
        "语音转文字": t("menu.stt.label"),
        "Agent 设置": t("menu.agent.label"),
        "Terminal 后端": t("menu.terminal.label"),
        "记忆系统": t("menu.memory.label"),
        "语言设置": t("menu.language.label"),
        "工具配置": t("menu.tools.label"),
        "Browser 自动化": t("menu.browser.label"),
        "Debug 配置": t("menu.debug.label"),
        "Skills Hub": t("menu.skills_hub.label"),
        "响应详细程度": t("menu.depth.label"),
        "响应缓存": t("menu.caching.label"),
        "查看当前配置": t("menu.view.label"),
        "↩ 返回": t("menu.back.label"),
        "请选择:": t("menu.select.prompt"),
        "❌ 退出配置": t("menu.exit.label"),
        
        # Hint 提示文本
        "使用推荐配置，快速完成设置": t("menu.quick.hint"),
        "清空配置，重新开始": t("menu.reset_all.hint"),
        "选择 AI 提供商和模型": t("menu.llm.hint"),
        "图片理解能力配置": t("menu.vision.hint"),
        "max_tokens、temperature 等": t("menu.model.hint"),
        "如何理解用户意图": t("menu.intent.hint"),
        "Telegram、Slack 等": t("menu.gateway.hint"),
        "TTS 语音合成": t("menu.tts.hint"),
        "语音识别输入": t("menu.stt.hint"),
        "迭代次数、工具进度等": t("menu.agent.hint"),
        "命令执行环境": t("menu.terminal.hint"),
        "向量数据库配置": t("menu.memory.hint"),
        "界面显示语言": t("menu.language.hint"),
        "Web 搜索、浏览器等": t("menu.tools.hint"),
        "无头浏览器控制": t("menu.browser.hint"),
        "调试工具开关": t("menu.debug.hint"),
        "GitHub 技能市场": t("menu.skills_hub.hint"),
        "AI 回复详细程度": t("menu.depth.hint"),
        "启用响应缓存加速": t("menu.caching.hint"),
        "显示所有配置项": t("menu.view.hint"),
        "快速配置或重置所有设置": t("menu.quick_start.hint"),
        "大模型、视觉、参数、意图识别": t("menu.ai.hint"),
        "消息平台、TTS、STT": t("menu.communication.hint"),
        "Agent、Terminal、记忆、语言": t("menu.system.hint"),
        "工具配置、浏览器、调试、Skills": t("menu.tools.hint"),
        "响应详细程度、缓存": t("menu.preferences.hint"),
        "查看当前配置": t("menu.auxiliary.hint"),
    }
    return menu_translations.get(key, fallback)


def _navigate_menu(node: MenuNode, config: dict):
    """递归导航菜单."""
    if node.children is None:
        # 叶子节点，执行操作
        return _execute_menu_action(node.id, config)
    
    # 显示当前菜单
    while True:
        print()
        # 主菜单不显示标题，子菜单显示
        if node.id != "root":
            ui.print_header_text(_translate_menu(node.label, node.label))
            print()
        
        options = []
        for child in node.children:
            # 格式：名称 + 空格 + hint（灰色显示）
            label = _translate_menu(child.label, child.label)
            hint = _translate_menu(child.hint, child.hint) if child.hint else ""
            display = label
            if hint:
                display = f"{label}  {ui.Theme.SECONDARY_DIM}{hint}{ui.Colors.RESET}"
            options.append((child.id, display))
        
        # 添加返回选项（主菜单不需要显示）
        if node.id != "root":
            options.append(("back", _translate_menu("↩ 返回", "↩ 返回")))
        
        # 主菜单添加退出选项
        if node.id == "root":
            options.append(("exit", _translate_menu("❌ 退出配置", "❌ 退出配置")))
        
        print()
        choice = ask_choice(_translate_menu("请选择:", "请选择:"), options)
        
        if choice is None:
            return
        
        selected_id = options[choice][0]
        
        if selected_id == "back":
            return  # 返回上级
        
        if selected_id == "exit":
            ui.print_success(t("setup.common.exit_msg") or "已退出配置")
            return False
        else:
            # 找到对应的节点
            child_node = None
            for child in node.children:
                if child.id == selected_id:
                    child_node = child
                    break
            
            if child_node and child_node.children:
                _navigate_menu(child_node, config)
            elif child_node:
                result = _execute_menu_action(child_node.id, config)
                if result is False:
                    # 用户退出
                    return


def _execute_menu_action(action_id: str, config: dict) -> bool:
    """执行菜单动作. 返回 False 表示退出."""
    if action_id == "view":
        show_current_config(config)
        return True
    elif action_id == "quick":
        run_quick_config_wizard()
        return True
    elif action_id == "reset_all":
        result = run_full_setup_wizard()
        return True
    elif action_id == "back":
        return True
    else:
        # 执行配置函数
        setup_func_map = {
            "language": setup_language,
            "llm": setup_llm_provider,
            "vision": setup_vision,
            "model": setup_model_config,
            "terminal": setup_terminal,
            "agent": setup_agent_settings,
            "session_reset": setup_session_reset,
            "memory": setup_memory,
            "compression": setup_compression,
            "stt": setup_stt,
            "tts": setup_tts,
            "gateway": setup_gateway,
            "tools": setup_tools,
            "skills_hub": setup_skills_hub,
            "browser": setup_browser,
            "debug_tools": setup_debug,
            "depth": setup_depth,
            "caching": setup_caching,
            "intent": setup_intent,
        }
        
        setup_func = setup_func_map.get(action_id)
        if setup_func:
            print("\n" + "─" * 60)
            try:
                result = setup_func(config)
                if result is not None:
                    if isinstance(result, dict):
                        # LLM 配置保存到 llm 键，其他保存到对应键
                        if action_id == "llm":
                            config.setdefault('llm', {}).update(result)
                        else:
                            config.setdefault('preferences', {}).update(result)
                    else:
                        config[action_id] = result
                    save_config(config)
                    ui.print_success(t("setup.common.saved"))
            except KeyboardInterrupt:
                ui.print_info(t("setup.common.cancel"))
                print()
        return True