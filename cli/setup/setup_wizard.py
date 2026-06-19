#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handsome Agent Setup Wizard.

参考 Hermes 和 OpenClaw 的配置设计，支持：
1. Model & Provider — 选择你的 AI provider 和 model
2. Terminal Backend — 配置命令执行环境
3. Agent Settings — iterations、compression、session reset
4. Tools — 配置 TTS、web search、image generation 等
5. Messaging Platforms — 连接 Telegram、Discord 等

Config files are stored in ~/.handsome_agent/ for easy access.
"""

import os
import sys
import json
from pathlib import Path
from common.terminal.colors import enable_ansi_support, Colors, Theme
from common.terminal.ui import (
    print_header,
    print_header_text,
    print_divider,
    print_substep,
    print_info,
    print_warning,
    print_success,
    print_error,
    print_prompt,
    print_config_item,
    print_setup_complete,
    print_provider_list,
)
from common.terminal.banner import (
    build_welcome_banner,
    print_simple_banner,
)
from cli.ui.banner import print_setup_banner, print_setup_summary

enable_ansi_support()

from cli.setup.interactive_select import print_menu_with_logo

CONFIG_DIR = os.path.expanduser("~/.handsome_agent")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.yaml")


QUIT_COMMANDS = ['quit', 'exit', 'q', '退出', 'back', 'b', '返回']


def should_quit(response: str) -> bool:
    """检查是否要退出."""
    return response.lower() in [c.lower() for c in QUIT_COMMANDS]


def ask_yes_no(question: str, default: bool = True) -> bool | None:
    """询问是/否."""
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            print_substep(f"{question} {suffix}")
            print_substep(f"{Theme.SECONDARY_DIM}(输入 q 返回上一级){Colors.RESET}")
            response = input(print_prompt()).strip()
            
            if should_quit(response):
                return None
            if not response:
                return default
            if response in ['y', 'yes', '是', '好']:
                return True
            if response in ['n', 'no', '否', '不']:
                return False
            print_warning("请输入 y 或 n")
        except (EOFError, KeyboardInterrupt):
            return None


def ask_yes_no_options(question: str, default: bool = True) -> bool | None:
    """使用选项列表询问是/否."""
    yes_label = "是"
    no_label = "否"
    
    options = [
        ("yes", yes_label),
        ("no", no_label),
    ]
    default_value = "yes" if default else "no"
    current_idx = 0 if default else 1
    
    choice = ask_choice(question, options, default=current_idx, current_value=default_value)
    if choice is None:
        return None
    return options[choice][0] == "yes"


def ask_choice(question: str, options: list, default: int = 0, current_value: str = None) -> int | None:
    """让用户从选项中选择."""
    print()
    result = print_menu_with_logo(options, question, current_value)
    return result


def ask_input(question: str, default: str = None, password: bool = False, required: bool = True) -> str | None:
    """询问用户输入."""
    if default:
        prompt_text = f"{question} (直接回车使用默认值: {default})"
    else:
        prompt_text = question
    
    print()
    print_substep(prompt_text)
    if required:
        print_substep(f"{Theme.SECONDARY_DIM}(输入 q 返回上一级){Colors.RESET}")
    
    while True:
        try:
            if password:
                import getpass
                response = getpass.getpass(print_prompt()).strip()
            else:
                response = input(print_prompt()).strip()
            
            if should_quit(response):
                return None
            if not response and default is not None:
                return default
            if not response and required:
                print_warning("此项为必填项，请输入值")
                continue
            return response if response else default
        except (EOFError, KeyboardInterrupt):
            return None


def get_all_providers():
    """获取所有支持的提供商."""
    try:
        from agent.llm import get_all_providers
        return get_all_providers()
    except ImportError:
        return []


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
    print_header_text("📋 当前配置:")
    print_divider()
    
    language = config.get('language', 'zh')
    if isinstance(language, str):
        language_display = {"zh": "中文", "en": "English"}.get(language, language)
        print_config_item("🌐 显示语言", language_display)
    
    llm = config.get('llm', {})
    provider = llm.get('provider', 'none')
    if provider == 'none':
        provider_display = "未配置 (使用基础模式)"
    else:
        provider_display = provider
    print_config_item("🤖 大模型", provider_display)
    
    if llm.get('model'):
        print_config_item("📦 模型", llm['model'])
    
    print_divider()


def has_existing_config() -> bool:
    """检查是否存在配置文件."""
    config_file = os.path.join(CONFIG_DIR, "config.json")
    return os.path.exists(config_file) or os.path.exists(CONFIG_FILE)


def print_step(current: int, total: int, title: str):
    """打印步骤标题"""
    print()
    print_info(f"步骤 {current}/{total}: {title}")


def setup_language(config: dict) -> dict | None:
    """配置语言."""
    print_step(1, 1, "🌐 语言设置")
    
    language_options = [
        ("zh", "中文 (Chinese) - 默认"),
        ("en", "English (英文)")
    ]
    
    current = config.get('language', 'zh')
    current_idx = next((i for i, (k, _) in enumerate(language_options) if k == current), 0)
    
    choice = ask_choice("请选择显示语言:", language_options, default=current_idx, current_value=current)
    if choice is None:
        return None
    
    return {"language": language_options[choice][0]}


def setup_llm_provider(config: dict) -> dict | None:
    """配置大模型."""
    print_step(1, 1, "🤖 大模型配置")
    
    providers = get_all_providers()
    provider_options = [(p["id"], f"{p['name']} - {p['description']}") for p in providers]
    provider_options.append(("none", "暂不使用 (使用基础模板模式)"))
    
    current_provider = config.get('llm', {}).get('provider', 'none')
    current_idx = next((i for i, (k, _) in enumerate(provider_options) if k == current_provider), len(provider_options) - 1)
    
    choice = ask_choice("请选择大模型提供商:", provider_options, default=current_idx, current_value=current_provider)
    if choice is None:
        return None
    
    provider_id = provider_options[choice][0]
    
    if provider_id == "none":
        print_info("将使用基础模板模式")
        return {"provider": "none", "api_key": None, "model": None, "base_url": None}
    
    provider_info = next((p for p in providers if p["id"] == provider_id), None)
    
    if not provider_info:
        print_error(f"未找到提供商: {provider_id}")
        return None
    
    new_config = {
        "provider": provider_id,
        "api_key": None,
        "model": provider_info.get("default_model"),
        "base_url": provider_info.get("base_url"),
    }
    
    print_substep(f"请设置 {provider_info.get('name')} API Key")
    if provider_info.get("api_key_url"):
        print_substep(f"获取地址: {provider_info.get('api_key_url')}")
    
    current_key = config.get('llm', {}).get('api_key', '')
    if current_key:
        print_info(f"已配置 API Key: {current_key[:4]}...{current_key[-4:]}")
        reuse = ask_yes_no("是否保留现有 API Key?", default=True)
        if reuse is None:
            return None
        if reuse:
            new_config["api_key"] = current_key
            new_config["model"] = config.get('llm', {}).get('model')
            return new_config
    
    api_key = ask_input("API Key", password=True, required=True)
    if api_key is None:
        return None
    new_config["api_key"] = api_key
    
    return new_config


def setup_model_config(config: dict) -> dict | None:
    """配置模型参数."""
    print_step(1, 1, "🔧 模型参数配置")
    
    model_cfg = config.get('model', {})
    
    max_tokens = ask_input("Max Tokens", default=str(model_cfg.get('max_tokens', 4096)))
    if max_tokens is None:
        return None
    max_tokens = int(max_tokens) if max_tokens.isdigit() else 4096
    
    temperature = ask_input("Temperature (0.0-2.0)", default=str(model_cfg.get('temperature', 0.7)))
    if temperature is None:
        return None
    try:
        temperature = float(temperature)
        temperature = max(0.0, min(2.0, temperature))
    except ValueError:
        temperature = 0.7
    
    context_window = ask_input("Context Window", default=str(model_cfg.get('context_window', 128000)))
    if context_window is None:
        return None
    context_window = int(context_window) if context_window.isdigit() else 128000
    
    return {
        "max_tokens": max_tokens,
        "temperature": temperature,
        "context_window": context_window
    }


def setup_terminal(config: dict) -> dict | None:
    """配置 Terminal 后端."""
    print_step(1, 1, "💻 Terminal 后端配置")
    
    terminal_cfg = config.get('terminal', {})
    
    backend_options = [
        ("local", "本地执行 (默认) - 直接在本地执行命令"),
        ("docker", "Docker 容器 - 在隔离容器中执行命令"),
    ]
    
    current_backend = terminal_cfg.get('backend', 'local')
    current_idx = next((i for i, (k, _) in enumerate(backend_options) if k == current_backend), 0)
    
    choice = ask_choice("请选择 Terminal 后端:", backend_options, default=current_idx, current_value=current_backend)
    if choice is None:
        return None
    
    backend = backend_options[choice][0]
    return {"backend": backend}


def setup_agent_settings(config: dict) -> dict | None:
    """配置 Agent 设置."""
    print_step(1, 1, "⚙️ Agent 设置")
    
    agent = config.get('agent', {})
    
    max_iterations = ask_input("最大迭代次数", default=str(agent.get('max_iterations', 10)))
    if max_iterations is None:
        return None
    
    timeout = ask_input("超时时间（秒）", default=str(agent.get('timeout_seconds', 60)))
    if timeout is None:
        return None
    
    return {
        "max_iterations": int(max_iterations) if max_iterations.isdigit() else 10,
        "timeout_seconds": float(timeout) if timeout.replace('.', '').isdigit() else 60.0
    }


def setup_session_reset(config: dict) -> dict | None:
    """配置 Session 重置策略."""
    print_step(1, 1, "🔄 Session 重置策略")
    
    session_reset = config.get('session_reset', {})
    
    mode_options = [
        ("both", "两者 (默认) - 每日重置或空闲超时，优先触发"),
        ("daily", "每日重置 - 每天特定时间重置会话"),
        ("idle", "空闲超时 - 空闲指定时间后重置会话"),
        ("none", "从不 - 不自动重置，使用 Context Compression 管理")
    ]
    
    current_mode = session_reset.get('mode', 'both')
    current_idx = next((i for i, (k, _) in enumerate(mode_options) if k == current_mode), 0)
    
    choice = ask_choice("请选择 Session 重置模式:", mode_options, default=current_idx, current_value=current_mode)
    if choice is None:
        return None
    
    mode = mode_options[choice][0]
    new_config = {"mode": mode}
    
    return new_config


def setup_workspace(config: dict) -> dict | None:
    """配置工作空间路径."""
    print_step(1, 1, "📁 工作空间配置")
    
    workspace = config.get('workspace', {})
    current_path = workspace.get('path', str(Path.home() / ".handsome_agent"))
    
    print()
    print_info(f"  当前值: {current_path}")
    print()
    
    use_custom = ask_yes_no_options("是否修改工作空间路径?", default=False)
    if use_custom is None:
        return None
    
    if not use_custom:
        return workspace
    
    new_path = ask_input("请输入新的工作空间路径", default=current_path, required=True)
    if new_path is None:
        return None
    
    new_path = str(Path(new_path).expanduser().resolve())
    return {"path": new_path}


def setup_memory(config: dict) -> dict | None:
    """配置记忆系统."""
    print_step(1, 1, "🧠 记忆系统配置")
    
    memory = config.get('memory', {})
    
    enabled = ask_yes_no("是否启用记忆系统?", default=memory.get('enabled', True))
    if enabled is None:
        return None
    
    return {"enabled": enabled}


def setup_compression(config: dict) -> dict | None:
    """配置 Context Compression."""
    print_step(1, 1, "🗜️ Context 压缩配置")
    
    compression = config.get('compression', {})
    
    enabled = ask_yes_no("是否启用 Context Compression?", default=compression.get('enabled', True))
    if enabled is None:
        return None
    
    return {"enabled": enabled}


def setup_stt(config: dict) -> dict | None:
    """配置 STT."""
    print_step(1, 1, "🎤 语音转文字配置")
    
    stt = config.get('stt', {})
    
    enabled = ask_yes_no("是否启用 STT?", default=stt.get('enabled', False))
    if enabled is None:
        return None
    
    return {"enabled": enabled}


def setup_tts(config: dict) -> dict | None:
    """配置 TTS."""
    print_step(1, 1, "🔊 文字转语音配置")
    
    tts = config.get('tts', {})
    
    enabled = ask_yes_no("是否启用 TTS?", default=tts.get('enabled', False))
    if enabled is None:
        return None
    
    return {"enabled": enabled}


def setup_browser(config: dict) -> dict | None:
    """配置 Browser 工具."""
    print_step(1, 1, "🌐 Browser 工具配置")
    
    browser = config.get('browser', {})
    
    enabled = ask_yes_no("是否启用 Browser 工具?", default=browser.get('enabled', False))
    if enabled is None:
        return None
    
    return {"enabled": enabled}


def setup_debug(config: dict) -> dict | None:
    """配置 Debug 工具."""
    print_step(1, 1, "🐛 Debug 配置")
    
    debug = config.get('debug_tools', {})
    
    web_debug = ask_yes_no("启用 Web Tools Debug?", default=debug.get('web_tools', False))
    if web_debug is None:
        return None
    
    vision_debug = ask_yes_no("启用 Vision Tools Debug?", default=debug.get('vision_tools', False))
    if vision_debug is None:
        return None
    
    return {
        "web_tools": web_debug,
        "vision_tools": vision_debug,
    }


def setup_logging(config: dict) -> dict | None:
    """配置日志设置."""
    print_step(1, 1, "📄 日志设置")
    
    logging_cfg = config.get('logging', {})
    
    enabled = ask_yes_no("是否启用文件日志保存?", default=logging_cfg.get('file_enabled', False))
    if enabled is None:
        return None
    
    return {"file_enabled": enabled}


def setup_depth(config: dict) -> dict | None:
    """配置响应详细程度."""
    print_step(1, 1, "📝 响应详细程度")
    
    prefs = config.get('preferences', {})
    depth_options = [
        ("brief", "简洁 - 只返回要点"),
        ("moderate", "适中 - 适度详细"),
        ("detailed", "详细 - 完整说明")
    ]
    current_depth = prefs.get('explanation_depth', 'detailed')
    current_idx = next((i for i, (k, _) in enumerate(depth_options) if k == current_depth), 2)
    
    choice = ask_choice("请选择响应详细程度:", depth_options, default=current_idx, current_value=current_depth)
    if choice is None:
        return None
    
    return {"explanation_depth": depth_options[choice][0]}


def setup_caching(config: dict) -> dict | None:
    """配置响应缓存."""
    print_step(1, 1, "⚡ 响应缓存")
    
    prefs = config.get('preferences', {})
    current_caching = prefs.get('enable_caching', True)
    
    use_caching = ask_yes_no("是否启用响应缓存?", default=current_caching)
    if use_caching is None:
        return None
    
    return {"enable_caching": use_caching}


def setup_intent(config: dict) -> dict | None:
    """配置意图识别."""
    print_step(1, 1, "🎯 意图识别配置")
    
    mode_options = [
        ("llm", "大模型模式 - 优先使用 AI 理解意图，智能但需要 API"),
        ("hybrid", "混合模式 - 关键词优先，低置信度时调用 AI"),
        ("keyword", "关键词模式 - 仅使用关键词匹配，无需 API")
    ]
    
    current_mode = config.get('intent_mode', 'llm')
    current_idx = next((i for i, (k, _) in enumerate(mode_options) if k == current_mode), 0)
    
    choice = ask_choice("请选择意图识别模式:", mode_options, default=current_idx, current_value=current_mode)
    if choice is None:
        return None
    
    return {"intent_mode": mode_options[choice][0]}


def _build_config_status(config: dict) -> dict:
    """构建配置状态摘要"""
    status = {
        "llm": {},
        "terminal": {},
        "memory": {},
    }

    llm = config.get('llm', {})
    if llm.get('provider') and llm.get('provider') != 'none':
        status["llm"] = {
            "configured": True,
            "provider": llm.get('provider', 'unknown'),
            "model": llm.get('model', 'unknown')
        }
    else:
        status["llm"] = {"configured": False}

    terminal = config.get('terminal', {})
    status["terminal"] = {"backend": terminal.get('backend', 'local')}

    memory = config.get('memory', {})
    status["memory"] = {
        "enabled": memory.get('enabled', True),
        "vector_store": memory.get('vector_store', 'sqlite')
    }

    return status


def run_full_setup_wizard():
    """运行完整的配置向导流程."""
    config = {}

    print_setup_banner()
    print("\n🔄 开始全新配置...\n")
    
    sections = [
        ("language", "🌐 语言设置", setup_language),
        ("llm", "🤖 大模型配置", setup_llm_provider),
        ("model", "🔧 模型参数", setup_model_config),
        ("terminal", "💻 Terminal 后端", setup_terminal),
    ]
    
    total = len(sections)
    for i, (key, title, setup_func) in enumerate(sections, 1):
        print("\n" + "─" * 60)
        print_info(f"步骤 {i}/{total}: {title}")
        
        result = setup_func(config)
        if result is None:
            print_info("已取消配置")
            return None
        
        if key == 'llm':
            config['llm'] = result
        elif key in ('depth', 'caching'):
            config.setdefault('preferences', {}).update(result)
        else:
            config[key] = result

    print_setup_summary(_build_config_status(config))

    save_ask = ask_yes_no("\n是否保存当前配置?", default=True)
    if save_ask is None or not save_ask:
        return None

    save_config(config)
    print_success("✅ 配置已保存!")
    print_setup_complete()

    return config


def run_quick_config_wizard():
    """快速配置向导"""
    config = load_config()
    print_setup_banner()
    print("\n🚀 快速配置向导\n")
    
    important_sections = [
        ("language", "🌐 语言设置", setup_language),
        ("llm", "🤖 大模型配置", setup_llm_provider),
    ]
    
    for i, (key, title, setup_func) in enumerate(important_sections, 1):
        print_info(f"第 {i}/{len(important_sections)} 项: {title}")
        print("─" * 50)
        
        result = setup_func(config)
        if result is not None:
            if key == 'llm':
                config['llm'] = result
            else:
                config[key] = result
            save_config(config)
            print_success("✅ 配置已保存!")
    
    print_success("✅ 快速配置完成!")
    print_setup_summary(_build_config_status(config))


def run_setup_wizard():
    """运行设置向导."""
    config = load_config()

    print_setup_banner()

    if not has_existing_config():
        print()
        print_warning("⚠️  尚未配置系统")
        print()
        print_info("请选择「🚀 快速配置向导」开始配置")
        print()
    
    while True:
        main_options = [
            ("quick", "🚀 快速配置向导"),
            ("view", "📋 查看当前配置"),
            ("reset_all", "🔄 重新全部配置"),
            ("language", "🌐 语言设置"),
            ("llm", "🤖 大模型配置"),
            ("quit", "❌ 退出配置")
        ]
        
        print()
        choice = ask_choice("请选择操作:", main_options)
        
        if choice is None:
            print_info("退出配置")
            return
        
        option_id = main_options[choice][0]
        
        if option_id == "view":
            show_current_config(config)
        elif option_id == "quick":
            run_quick_config_wizard()
        elif option_id == "reset_all":
            result = run_full_setup_wizard()
            if result is not None:
                config = result
        elif option_id == "quit":
            break
