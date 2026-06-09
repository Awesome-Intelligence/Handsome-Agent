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
from cli import ui
from common.i18n import t

ui.enable_ansi_support()

# 导入增强的 Banner 模块 (🚪 Access - 🚪 Gateway - 欢迎横幅)
from cli.banner import print_setup_banner, print_simple_banner, print_setup_summary


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
            ui.print_substep(f"{question} {suffix}")
            ui.print_substep(f"{ui.Theme.SECONDARY_DIM}(输入 q 返回上一级){ui.Colors.RESET}")
            response = input(ui.print_prompt()).strip()
            
            if should_quit(response):
                return None
            if not response:
                return default
            if response in ['y', 'yes', '是', '好']:
                return True
            if response in ['n', 'no', '否', '不']:
                return False
            ui.print_warning("请输入 y 或 n")
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
    from cli.interactive_select import print_menu_with_logo
    result = print_menu_with_logo(options, question, current_value)
    return result


def ask_input(question: str, default: str = None, password: bool = False, required: bool = True) -> str | None:
    """询问用户输入."""
    if default:
        prompt_text = f"{question} (直接回车使用默认值: {default})"
    else:
        prompt_text = question
    
    print()
    ui.print_substep(prompt_text)
    if required:
        ui.print_substep(f"{ui.Theme.SECONDARY_DIM}(输入 q 返回上一级){ui.Colors.RESET}")
    
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
                ui.print_warning("此项为必填项，请输入值")
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
    ui.print_header_text("📋 当前配置:")
    ui.print_divider()
    
    # Language
    language = config.get('language', 'zh')
    if isinstance(language, str):
        language_display = {"zh": "中文", "en": "English"}.get(language, language)
        ui.print_config_item("🌐 显示语言", language_display)
    
    # LLM Provider
    llm = config.get('llm', {})
    provider = llm.get('provider', 'none')
    if provider == 'none':
        provider_display = "未配置 (使用基础模式)"
    else:
        provider_display = {
            "openai": "OpenAI",
            "anthropic": "Anthropic Claude",
            "google": "Google Gemini",
            "deepseek": "DeepSeek",
            "minimax": "MiniMax",
            "moonshot": "Kimi (月之暗面)",
            "zhipu": "智谱AI",
            "dashscope": "阿里通义千问",
            "groq": "Groq",
            "siliconflow": "SiliconFlow",
            "custom": "自定义 API"
        }.get(provider, provider)
    ui.print_config_item("🤖 大模型", provider_display)
    
    if llm.get('model'):
        ui.print_config_item("📦 模型", llm['model'])
    
    # Model Config
    model_cfg = config.get('model', {})
    if model_cfg:
        ui.print_config_item("🔧 Max Tokens", str(model_cfg.get('max_tokens', 4096)))
        ui.print_config_item("🌡️ Temperature", str(model_cfg.get('temperature', 0.7)))
    
    # Terminal Config
    terminal = config.get('terminal', {})
    if terminal:
        backend = terminal.get('backend', 'local')
        backend_display = {
            "local": "本地",
            "docker": "Docker",
            "ssh": "SSH 远程",
            "singularity": "Singularity",
            "modal": "Modal Cloud"
        }.get(backend, backend)
        ui.print_config_item("💻 Terminal 后端", backend_display)
        ui.print_config_item("⏱️ 超时时间", f"{terminal.get('timeout', 60)}s")
        ui.print_config_item("🕐 生命周期", f"{terminal.get('lifetime_seconds', 300)}s")
    
    # Workspace Config
    workspace = config.get('workspace', {})
    if workspace:
        workspace_path = workspace.get('path', str(Path.home() / ".handsome_agent"))
        ui.print_config_item("📁 工作空间", workspace_path)
    
    # Session Reset
    session_reset = config.get('session_reset', {})
    if session_reset:
        mode = session_reset.get('mode', 'both')
        mode_display = {
            "daily": "每日重置",
            "idle": "空闲超时重置",
            "both": "两者（优先触发）",
            "none": "从不自动重置"
        }.get(mode, mode)
        ui.print_config_item("🔄 Session 重置", mode_display)
        if mode in ('daily', 'both'):
            ui.print_config_item("⏰ 重置时间", f"{session_reset.get('at_hour', 4)}:00")
        if mode in ('idle', 'both'):
            ui.print_config_item("⏳ 空闲超时", f"{session_reset.get('idle_minutes', 1440)} 分钟")
    
    # Memory Config
    memory = config.get('memory', {})
    if memory:
        enabled = memory.get('enabled', True)
        ui.print_config_item("🧠 记忆系统", "已启用" if enabled else "已禁用")
        if enabled:
            ui.print_config_item("📊 Vector Store", memory.get('vector_store', 'sqlite'))
    
    # Compression Config
    compression = config.get('compression', {})
    if compression:
        enabled = compression.get('enabled', True)
        ui.print_config_item("🗜️ Context 压缩", "已启用" if enabled else "已禁用")
        if enabled:
            ui.print_config_item("📈 压缩阈值", f"{compression.get('threshold', 0.85) * 100:.0f}%")
    
    # STT Config
    stt = config.get('stt', {})
    if stt:
        enabled = stt.get('enabled', False)
        ui.print_config_item("🎤 STT", "已启用" if enabled else "已禁用")
        if enabled:
            ui.print_config_item("🎯 STT Provider", stt.get('provider', 'local'))
    
    # TTS Config
    tts = config.get('tts', {})
    if tts:
        enabled = tts.get('enabled', False)
        ui.print_config_item("🔊 TTS", "已启用" if enabled else "已禁用")
        if enabled:
            ui.print_config_item("🎯 TTS Provider", tts.get('provider', 'openai'))
            ui.print_config_item("🎭 TTS Voice", tts.get('voice', 'alloy'))
    
    # Browser Config
    browser = config.get('browser', {})
    if browser:
        enabled = browser.get('enabled', False)
        ui.print_config_item("🌐 Browser 工具", "已启用" if enabled else "已禁用")
        if enabled:
            ui.print_config_item("🔒 高级隐身", "是" if browser.get('advanced_stealth', False) else "否")
    
    # Debug Config
    debug = config.get('debug_tools', {})
    if debug:
        web_debug = debug.get('web_tools', False)
        vision_debug = debug.get('vision_tools', False)
        if web_debug or vision_debug:
            ui.print_config_item("🐛 Debug 模式", "已启用")
        else:
            ui.print_config_item("🐛 Debug 模式", "已禁用")
    
    # Logging Config
    logging_cfg = config.get('logging', {})
    if logging_cfg:
        file_enabled = logging_cfg.get('file_enabled', False)
        ui.print_config_item("📄 文件日志", "已启用" if file_enabled else "已禁用")
    
    # Preferences
    prefs = config.get('preferences', {})
    depth = prefs.get('explanation_depth', 'detailed')
    depth_display = {"brief": "简洁", "moderate": "适中", "detailed": "详细"}.get(depth, depth)
    ui.print_config_item("📝 响应详细程度", depth_display)
    
    caching = prefs.get('enable_caching', True)
    ui.print_config_item("⚡ 缓存", "已启用" if caching else "已禁用")
    
    # Intent Mode
    intent_mode = config.get('intent_mode', 'llm')
    mode_display = {"keyword": "关键词模式", "llm": "大模型模式", "hybrid": "混合模式"}.get(intent_mode, intent_mode)
    ui.print_config_item("🎯 意图识别", mode_display)
    
    ui.print_divider()


def has_existing_config() -> bool:
    """检查是否存在配置文件."""
    config_file = os.path.join(CONFIG_DIR, "config.json")
    return os.path.exists(config_file) or os.path.exists(CONFIG_FILE)


# =============================================================================
# Section 1: Language
# =============================================================================

def setup_language(config: dict) -> dict | None:
    """配置语言."""
    ui.print_step(1, 1, "🌐 语言设置")
    
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


# =============================================================================
# Section 2: LLM Provider & Model
# =============================================================================

def setup_llm_provider(config: dict) -> dict | None:
    """配置大模型."""
    ui.print_step(1, 1, "🤖 大模型配置")
    
    providers = get_all_providers()
    ui.print_provider_list(providers)
    provider_options = [(p["id"], f"{p['name']} - {p['description']}") for p in providers]
    provider_options.append(("none", "暂不使用 (使用基础模板模式)"))
    
    current_provider = config.get('llm', {}).get('provider', 'none')
    current_idx = next((i for i, (k, _) in enumerate(provider_options) if k == current_provider), len(provider_options) - 1)
    
    choice = ask_choice("请选择大模型提供商:", provider_options, default=current_idx, current_value=current_provider)
    if choice is None:
        return None
    
    provider_id = provider_options[choice][0]
    
    if provider_id == "none":
        ui.print_info("将使用基础模板模式")
        return {"provider": "none", "api_key": None, "model": None, "base_url": None}
    
    provider_info = next((p for p in providers if p["id"] == provider_id), None)
    
    if not provider_info:
        ui.print_error(f"未找到提供商: {provider_id}")
        return None
    
    new_config = {
        "provider": provider_id,
        "api_key": None,
        "model": provider_info.get("default_model"),
        "base_url": provider_info.get("base_url"),
    }
    
    if provider_id == "custom":
        new_config["base_url"] = ask_input("API地址", default="http://localhost:11434/v1")
        if new_config["base_url"] is None:
            return None
    else:
        default_url = provider_info.get('base_url', '')
        current_url = config.get('llm', {}).get('base_url') or default_url
        ui.print_substep(f"默认API地址: `{default_url}`")
        use_custom_url = ask_yes_no("是否使用自定义API地址?", default=False)
        if use_custom_url is None:
            return None
        if use_custom_url:
            new_url = ask_input("请输入自定义API地址", default=current_url)
            if new_url is None:
                return None
            new_config["base_url"] = new_url
    
    ui.print_substep(f"请设置 {provider_info.get('name')} API Key")
    if provider_info.get("api_key_url"):
        ui.print_substep(f"获取地址: {provider_info.get('api_key_url')}")
    
    current_key = config.get('llm', {}).get('api_key', '')
    if current_key:
        ui.print_info(f"已配置 API Key: {current_key[:4]}...{current_key[-4:]}")
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
    
    from agent.llm import get_provider_models
    current_model = config.get('llm', {}).get('model')
    
    ui.print_info("正在获取模型列表...")
    models = get_provider_models(provider_id, api_key)
    
    if models:
        ui.print_header_text("请选择模型:")
        model_options = [(m, m) for m in models]
        current_model_idx = next((i for i, (m_id, _) in enumerate(model_options) if m_id == current_model), 0)
        print(f"\n当前值: {model_options[current_model_idx][1]}")
        
        from cli.interactive_select import select_option_safe
        model_choice = select_option_safe(model_options, default_idx=current_model_idx, current_value=current_model)
        if model_choice is None:
            return None
        new_config["model"] = models[model_choice]
    else:
        ui.print_warning("没有可用的模型，请检查API配置")
    
    return new_config


def setup_model_config(config: dict) -> dict | None:
    """配置模型参数."""
    ui.print_step(1, 1, "🔧 模型参数配置")
    
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


# =============================================================================
# Section 3: Terminal Backend
# =============================================================================

def setup_terminal(config: dict) -> dict | None:
    """配置 Terminal 后端."""
    ui.print_step(1, 1, "💻 Terminal 后端配置")
    
    terminal_cfg = config.get('terminal', {})
    
    backend_options = [
        ("local", "本地执行 (默认) - 直接在本地执行命令"),
        ("docker", "Docker 容器 - 在隔离容器中执行命令"),
        ("ssh", "SSH 远程 - 在远程服务器上执行命令"),
        ("singularity", "Singularity - 使用 Singularity 容器"),
        ("modal", "Modal Cloud - 使用 Modal 云服务")
    ]
    
    current_backend = terminal_cfg.get('backend', 'local')
    current_idx = next((i for i, (k, _) in enumerate(backend_options) if k == current_backend), 0)
    
    choice = ask_choice("请选择 Terminal 后端:", backend_options, default=current_idx, current_value=current_backend)
    if choice is None:
        return None
    
    backend = backend_options[choice][0]
    
    new_config = {"backend": backend}
    
    if backend == "local":
        ui.print_info("使用本地执行环境")
    elif backend == "docker":
        ui.print_info("Docker 容器环境")
        image = ask_input("Docker Image", default=terminal_cfg.get('docker_image', 'nikolaik/python-nodejs:python3.11-nodejs20'))
        if image is None:
            return None
        new_config["docker_image"] = image
    elif backend == "ssh":
        ui.print_info("SSH 远程执行")
        ssh_host = ask_input("SSH Host", default=terminal_cfg.get('ssh_host', ''))
        if ssh_host is None:
            return None
        new_config["ssh_host"] = ssh_host
        
        ssh_user = ask_input("SSH User", default=terminal_cfg.get('ssh_user', 'root'))
        if ssh_user is None:
            return None
        new_config["ssh_user"] = ssh_user
        
        ssh_port = ask_input("SSH Port", default=str(terminal_cfg.get('ssh_port', 22)))
        if ssh_port is None:
            return None
        new_config["ssh_port"] = int(ssh_port) if ssh_port.isdigit() else 22
        
        ssh_key = ask_input("SSH Key Path", default=terminal_cfg.get('ssh_key', '~/.ssh/id_rsa'))
        if ssh_key is None:
            return None
        new_config["ssh_key"] = ssh_key
    elif backend == "singularity":
        ui.print_info("Singularity 容器环境")
        image = ask_input("Singularity Image", default=terminal_cfg.get('singularity_image', 'docker://nikolaik/python-nodejs:python3.11-nodejs20'))
        if image is None:
            return None
        new_config["singularity_image"] = image
    elif backend == "modal":
        ui.print_info("Modal Cloud 环境")
        image = ask_input("Modal Image", default=terminal_cfg.get('modal_image', 'nikolaik/python-nodejs:python3.11-nodejs20'))
        if image is None:
            return None
        new_config["modal_image"] = image
    
    return new_config


# =============================================================================
# Section 4: Agent Settings
# =============================================================================

def setup_agent_settings(config: dict) -> dict | None:
    """配置 Agent 设置."""
    ui.print_step(1, 1, "⚙️ Agent 设置")
    
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


# =============================================================================
# Section 5: Session Reset Policy
# =============================================================================

def setup_session_reset(config: dict) -> dict | None:
    """配置 Session 重置策略."""
    ui.print_step(1, 1, "🔄 Session 重置策略")
    
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
    
    if mode in ('daily', 'both'):
        at_hour = ask_input("每日重置时间 (小时 0-23)", default=str(session_reset.get('at_hour', 4)))
        if at_hour is None:
            return None
        try:
            hour = int(at_hour)
            hour = max(0, min(23, hour))
        except ValueError:
            hour = 4
        new_config["at_hour"] = hour
    
    if mode in ('idle', 'both'):
        idle_minutes = ask_input("空闲超时时间（分钟）", default=str(session_reset.get('idle_minutes', 1440)))
        if idle_minutes is None:
            return None
        try:
            minutes = int(idle_minutes)
            minutes = max(1, minutes)
        except ValueError:
            minutes = 1440
        new_config["idle_minutes"] = minutes
    
    notify = ask_yes_no("是否发送重置通知?", default=session_reset.get('notify', True))
    if notify is None:
        return None
    new_config["notify"] = notify
    
    return new_config


# =============================================================================
# Section 6: Workspace Config
# =============================================================================

def setup_workspace(config: dict) -> dict | None:
    """配置工作空间路径."""
    ui.print_step(1, 1, t("setup.workspace.title"))
    
    workspace = config.get('workspace', {})
    current_path = workspace.get('path', str(Path.home() / ".handsome_agent"))
    
    print()
    ui.print_info(t("setup.workspace.description"))
    print()
    ui.print_info(f"  {t('setup.workspace.current')}: {current_path}")
    print()
    
    use_custom = ask_yes_no_options(t("setup.workspace.change_prompt"), default=False)
    if use_custom is None:
        return None
    
    if not use_custom:
        return workspace
    
    new_path = ask_input(
        t("setup.workspace.new_path"),
        default=current_path,
        required=True
    )
    if new_path is None:
        return None
    
    # 验证路径
    new_path = str(Path(new_path).expanduser().resolve())
    
    # 确认目录不存在或为空
    path_obj = Path(new_path)
    if path_obj.exists() and any(path_obj.iterdir()):
        ui.print_warning(t("setup.workspace.directory_not_empty"))
        confirm = ask_yes_no_options(t("setup.workspace.confirm_overwrite"), default=False)
        if confirm is None or not confirm:
            return workspace
    
    return {"path": new_path}


# =============================================================================
# Section 7: Memory Config
# =============================================================================

def setup_memory(config: dict) -> dict | None:
    """配置记忆系统."""
    ui.print_step(1, 1, "🧠 记忆系统配置")
    
    memory = config.get('memory', {})
    
    enabled = ask_yes_no("是否启用记忆系统?", default=memory.get('enabled', True))
    if enabled is None:
        return None
    
    new_config = {"enabled": enabled}
    
    if enabled:
        vector_options = [
            ("sqlite", "SQLite (默认) - 轻量级，适合本地"),
            ("chroma", "Chroma - 向量数据库，适合生产环境"),
            ("qdrant", "Qdrant - 云原生向量数据库"),
            ("milvus", "Milvus - 大规模向量搜索")
        ]
        
        current_vector = memory.get('vector_store', 'sqlite')
        current_idx = next((i for i, (k, _) in enumerate(vector_options) if k == current_vector), 0)
        
        choice = ask_choice("请选择 Vector Store:", vector_options, default=current_idx, current_value=current_vector)
        if choice is None:
            return None
        
        new_config["vector_store"] = vector_options[choice][0]
        
        embedding = ask_input("Embedding Model", default=memory.get('embedding_model', 'text-embedding-3-small'))
        if embedding is None:
            return None
        new_config["embedding_model"] = embedding
        
        max_entries = ask_input("最大记忆条数", default=str(memory.get('max_entries', 1000)))
        if max_entries is None:
            return None
        new_config["max_entries"] = int(max_entries) if max_entries.isdigit() else 1000
    
    return new_config


# =============================================================================
# Section 8: Context Compression
# =============================================================================

def setup_compression(config: dict) -> dict | None:
    """配置 Context Compression."""
    ui.print_step(1, 1, "🗜️ Context 压缩配置")
    
    compression = config.get('compression', {})
    
    enabled = ask_yes_no("是否启用 Context Compression?", default=compression.get('enabled', True))
    if enabled is None:
        return None
    
    new_config = {"enabled": enabled}
    
    if enabled:
        threshold = ask_input("压缩阈值 (0.5-1.0, 达到上下文上限的百分比)", default=str(compression.get('threshold', 0.85)))
        if threshold is None:
            return None
        try:
            t = float(threshold)
            t = max(0.5, min(1.0, t))
        except ValueError:
            t = 0.85
        new_config["threshold"] = t
        
        summary_model = ask_input("摘要模型", default=compression.get('summary_model', 'openai/gpt-4o-mini'))
        if summary_model is None:
            return None
        new_config["summary_model"] = summary_model
    
    return new_config


# =============================================================================
# Section 9: STT (Speech-to-Text)
# =============================================================================

def setup_stt(config: dict) -> dict | None:
    """配置 STT."""
    ui.print_step(1, 1, "🎤 语音转文字配置")
    
    stt = config.get('stt', {})
    
    enabled = ask_yes_no("是否启用 STT?", default=stt.get('enabled', False))
    if enabled is None:
        return None
    
    new_config = {"enabled": enabled}
    
    if enabled:
        provider_options = [
            ("local", "本地 (faster-whisper) - 无需 API Key，本地运行"),
            ("groq", "Groq - 免费 Tier，快速"),
            ("openai", "OpenAI - Whisper API")
        ]
        
        current_provider = stt.get('provider', 'local')
        current_idx = next((i for i, (k, _) in enumerate(provider_options) if k == current_provider), 0)
        
        choice = ask_choice("请选择 STT Provider:", provider_options, default=current_idx, current_value=current_provider)
        if choice is None:
            return None
        
        new_config["provider"] = provider_options[choice][0]
        
        model = ask_input("STT Model", default=stt.get('model', 'base'))
        if model is None:
            return None
        new_config["model"] = model
    
    return new_config


# =============================================================================
# Section 10: TTS (Text-to-Speech)
# =============================================================================

def setup_tts(config: dict) -> dict | None:
    """配置 TTS."""
    ui.print_step(1, 1, "🔊 文字转语音配置")
    
    tts = config.get('tts', {})
    
    enabled = ask_yes_no("是否启用 TTS?", default=tts.get('enabled', False))
    if enabled is None:
        return None
    
    new_config = {"enabled": enabled}
    
    if enabled:
        provider_options = [
            ("openai", "OpenAI TTS (默认) - 质量好"),
            ("edge", "Edge TTS - 免费，Microsoft"),
            ("elevenlabs", "ElevenLabs - 高质量，付费")
        ]
        
        current_provider = tts.get('provider', 'openai')
        current_idx = next((i for i, (k, _) in enumerate(provider_options) if k == current_provider), 0)
        
        choice = ask_choice("请选择 TTS Provider:", provider_options, default=current_idx, current_value=current_provider)
        if choice is None:
            return None
        
        new_config["provider"] = provider_options[choice][0]
        
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
        
        choice = ask_choice("请选择 TTS Voice:", voice_options, default=current_idx, current_value=current_voice)
        if choice is None:
            return None
        
        new_config["voice"] = voice_options[choice][0]
        
        model = ask_input("TTS Model", default=tts.get('model', 'tts-1'))
        if model is None:
            return None
        new_config["model"] = model
    
    return new_config


# =============================================================================
# Section 11: Browser Tool
# =============================================================================

def setup_browser(config: dict) -> dict | None:
    """配置 Browser 工具."""
    ui.print_step(1, 1, "🌐 Browser 工具配置")
    
    browser = config.get('browser', {})
    
    enabled = ask_yes_no("是否启用 Browser 工具?", default=browser.get('enabled', False))
    if enabled is None:
        return None
    
    new_config = {"enabled": enabled}
    
    if enabled:
        proxies = ask_yes_no("是否启用 Residential Proxies?", default=browser.get('proxies', True))
        if proxies is None:
            return None
        new_config["proxies"] = proxies
        
        stealth = ask_yes_no("是否启用高级隐身模式? (需要 Scale Plan)", default=browser.get('advanced_stealth', False))
        if stealth is None:
            return None
        new_config["advanced_stealth"] = stealth
        
        session_timeout = ask_input("Session 超时（秒）", default=str(browser.get('session_timeout', 300)))
        if session_timeout is None:
            return None
        new_config["session_timeout"] = int(session_timeout) if session_timeout.isdigit() else 300
        
        inactivity_timeout = ask_input("空闲超时（秒）", default=str(browser.get('inactivity_timeout', 120)))
        if inactivity_timeout is None:
            return None
        new_config["inactivity_timeout"] = int(inactivity_timeout) if inactivity_timeout.isdigit() else 120
    
    return new_config


# =============================================================================
# Section 12: Debug Tools
# =============================================================================

def setup_debug(config: dict) -> dict | None:
    """配置 Debug 工具."""
    ui.print_step(1, 1, "🐛 Debug 配置")
    
    debug = config.get('debug_tools', {})
    
    web_debug = ask_yes_no("启用 Web Tools Debug?", default=debug.get('web_tools', False))
    if web_debug is None:
        return None
    
    vision_debug = ask_yes_no("启用 Vision Tools Debug?", default=debug.get('vision_tools', False))
    if vision_debug is None:
        return None
    
    moa_debug = ask_yes_no("启用 MOA Tools Debug?", default=debug.get('moa_tools', False))
    if moa_debug is None:
        return None
    
    image_debug = ask_yes_no("启用 Image Tools Debug?", default=debug.get('image_tools', False))
    if image_debug is None:
        return None
    
    return {
        "web_tools": web_debug,
        "vision_tools": vision_debug,
        "moa_tools": moa_debug,
        "image_tools": image_debug
    }


# =============================================================================
# Section 14: Logging Config
# =============================================================================

def setup_logging(config: dict) -> dict | None:
    """配置日志设置."""
    ui.print_step(1, 1, "📄 日志设置")
    
    logging_cfg = config.get('logging', {})
    
    enabled = ask_yes_no("是否启用文件日志保存?", default=logging_cfg.get('file_enabled', False))
    if enabled is None:
        return None
    
    new_config = {"file_enabled": enabled}
    
    if enabled:
        max_size = ask_input(
            "单个日志文件最大大小 (MB)",
            default=str(logging_cfg.get('max_file_size', 10 * 1024 * 1024) // (1024 * 1024))
        )
        if max_size is None:
            return None
        try:
            size_mb = int(max_size)
            new_config["max_file_size"] = size_mb * 1024 * 1024
        except ValueError:
            new_config["max_file_size"] = 10 * 1024 * 1024
        
        backup_count = ask_input(
            "保留备份文件数量",
            default=str(logging_cfg.get('backup_count', 5))
        )
        if backup_count is None:
            return None
        new_config["backup_count"] = int(backup_count) if backup_count.isdigit() else 5
    
    return new_config


# =============================================================================
# Section 13: Preferences
# =============================================================================

def setup_depth(config: dict) -> dict | None:
    """配置响应详细程度."""
    ui.print_step(1, 1, "📝 响应详细程度")
    
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
    ui.print_step(1, 1, "⚡ 响应缓存")
    
    prefs = config.get('preferences', {})
    current_caching = prefs.get('enable_caching', True)
    
    use_caching = ask_yes_no("是否启用响应缓存?", default=current_caching)
    if use_caching is None:
        return None
    
    return {"enable_caching": use_caching}


def setup_intent(config: dict) -> dict | None:
    """配置意图识别."""
    ui.print_step(1, 1, "🎯 意图识别配置")
    
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


# =============================================================================
# Full Setup Wizard
# =============================================================================

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
        ("agent", "⚙️ Agent 设置", setup_agent_settings),
        ("session_reset", "🔄 Session 重置策略", setup_session_reset),
        ("memory", "🧠 记忆系统", setup_memory),
        ("compression", "🗜️ Context 压缩", setup_compression),
        ("stt", "🎤 STT 配置", setup_stt),
        ("tts", "🔊 TTS 配置", setup_tts),
        ("browser", "🌐 Browser 工具", setup_browser),
        ("debug_tools", "🐛 Debug 配置", setup_debug),
        ("logging", "📄 日志设置", setup_logging),
        ("depth", "📝 响应详细程度", setup_depth),
        ("caching", "⚡ 响应缓存", setup_caching),
        ("intent", "🎯 意图识别模式", setup_intent),
    ]
    
    total = len(sections)
    for i, (key, title, setup_func) in enumerate(sections, 1):
        print("\n" + "─" * 60)
        ui.print_info(f"步骤 {i}/{total}: {title}")
        
        result = setup_func(config)
        if result is None:
            ui.print_info("已取消配置")
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

    save_ask = ask_yes_no("\n是否保存当前配置?", default=True)
    if save_ask is None or not save_ask:
        return None

    save_config(config)
    ui.print_success("✅ 配置已保存!")
    ui.print_setup_complete()
    ui.print_header_text("运行方式:")
    print(f"  {ui.Theme.ACCENT}python -m cli.main --interactive{ui.Colors.RESET}    # 交互模式")
    print(f"  {ui.Theme.ACCENT}python -m cli.main -q \"你的问题\"{ui.Colors.RESET}   # 单次查询")
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
    print_setup_banner()
    print("\n🚀 快速配置向导\n")
    print("按顺序引导配置重要选项，每个选项配置完成后返回主菜单。\n")
    
    important_sections = [
        ("language", "🌐 语言设置", setup_language),
        ("llm", "🤖 大模型配置", setup_llm_provider),
        ("model", "🔧 模型参数", setup_model_config),
        ("terminal", "💻 Terminal 后端", setup_terminal),
        ("session_reset", "🔄 Session 重置策略", setup_session_reset),
        ("memory", "🧠 记忆系统", setup_memory),
    ]
    
    for i, (key, title, setup_func) in enumerate(important_sections, 1):
        ui.print_info(f"第 {i}/{len(important_sections)} 项: {title}")
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
            ui.print_success("✅ 配置已保存!")
        
        print("\n")
        print_setup_banner()
        print("🚀 快速配置向导\n")

        remaining = len(important_sections) - i
        if remaining > 0:
            ui.print_info(f"还剩 {remaining} 个选项")
            continue_config = ask_yes_no("是否继续配置下一个选项?", default=True)
            if continue_config is None or not continue_config:
                ui.print_info("已退出快速配置向导")
                return

    ui.print_success("✅ 所有重要选项配置完成!")
    from cli.banner import print_setup_summary as _print_summary2
    _print_summary2(_build_config_status(config))


# =============================================================================
# Main Setup Wizard
# =============================================================================

def run_setup_wizard():
    """运行设置向导."""
    config = load_config()

    # 始终显示 Setup Banner
    print_setup_banner()

    # 如果没有配置文件，显示提示
    if not has_existing_config():
        print()
        ui.print_warning("⚠️  尚未配置系统")
        print()
        ui.print_info("请选择「🚀 快速配置向导」开始配置，或选择其他选项进行单独配置。")
        print()
    
    while True:
        main_options = [
            ("quick", "🚀 快速配置向导"),
            ("view", "📋 查看当前配置"),
            ("reset_all", "🔄 重新全部配置"),
            ("language", "🌐 语言设置"),
            ("llm", "🤖 大模型配置"),
            ("model", "🔧 模型参数"),
            ("terminal", "💻 Terminal 后端"),
            ("workspace", "📁 工作空间"),
            ("agent", "⚙️ Agent 设置"),
            ("session_reset", "🔄 Session 重置策略"),
            ("memory", "🧠 记忆系统"),
            ("compression", "🗜️ Context 压缩"),
            ("stt", "🎤 STT 配置"),
            ("tts", "🔊 TTS 配置"),
            ("browser", "🌐 Browser 工具"),
            ("debug_tools", "🐛 Debug 配置"),
            ("logging", "📄 日志设置"),
            ("depth", "📝 响应详细程度"),
            ("caching", "⚡ 响应缓存"),
            ("intent", "🎯 意图识别模式"),
            ("quit", "❌ 退出配置")
        ]
        
        print()
        choice = ask_choice("请选择操作:", main_options)
        
        if choice is None:
            ui.print_info("退出配置")
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
        else:
            setup_func_map = {
                "language": setup_language,
                "llm": setup_llm_provider,
                "model": setup_model_config,
                "terminal": setup_terminal,
                "workspace": setup_workspace,
                "agent": setup_agent_settings,
                "session_reset": setup_session_reset,
                "memory": setup_memory,
                "compression": setup_compression,
                "stt": setup_stt,
                "tts": setup_tts,
                "browser": setup_browser,
                "debug_tools": setup_debug,
                "logging": setup_logging,
                "depth": setup_depth,
                "caching": setup_caching,
                "intent": setup_intent,
            }
            
            setup_func = setup_func_map.get(option_id)
            if setup_func:
                print("\n" + "─" * 60)
                result = setup_func(config)
                if result is not None:
                    if option_id in ('depth', 'caching'):
                        config.setdefault('preferences', {}).update(result)
                    else:
                        config[option_id] = result
                    save_config(config)
                    ui.print_success("✅ 配置已保存!")