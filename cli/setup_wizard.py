#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Handsome Agent Setup Wizard.
支持选择性配置，可以单独配置某个模块。
Logo 始终显示在顶部。
"""

import os
import sys
import json
from cli import ui

# 启用跨平台 ANSI 颜色支持
ui.enable_ansi_support()


CONFIG_FILE = os.path.expanduser("~/.custom_agent_config.json")


QUIT_COMMANDS = ['quit', 'exit', 'q', '退出']


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


def ask_choice(question: str, options: list, default: int = 0, current_value: str = None) -> int | None:
    """让用户从选项中选择.
    
    Args:
        question: 问题/标题
        options: 选项列表
        default: 默认选中索引
        current_value: 当前已配置的值（用于标记）
    """
    print()
    
    from cli.interactive_select import select_option_safe, print_menu_with_logo
    
    # 打印 Logo + 菜单（传递当前配置值用于标记）
    result = print_menu_with_logo(options, question, current_value)
    
    if result is None:
        return None
    return result


def ask_input(question: str, default: str = None, password: bool = False, required: bool = True) -> str | None:
    """询问用户输入."""
    if default:
        prompt = f"{question} (直接回车使用默认值: {default})"
    else:
        prompt = question
    
    print()
    ui.print_substep(prompt)
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
    from llm_integration import get_all_providers
    return get_all_providers()


def load_config() -> dict:
    """加载现有配置."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config: dict):
    """保存配置到文件."""
    os.makedirs(os.path.dirname(CONFIG_FILE) or ".", exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def show_current_config(config: dict):
    """显示当前配置."""
    print()
    ui.print_header_text("📋 当前配置:")
    ui.print_divider()
    
    # 语言
    language = config.get('language', 'zh')
    language_display = {"zh": "中文", "en": "English", "ko": "한국어", "ja": "日本語"}.get(language, language)
    ui.print_config_item("🌐 显示语言", language_display)
    
    # LLM
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
    
    # 偏好设置
    prefs = config.get('preferences', {})
    depth = prefs.get('explanation_depth', 'detailed')
    depth_display = {"brief": "简洁", "moderate": "适中", "detailed": "详细"}.get(depth, depth)
    ui.print_config_item("📝 响应详细程度", depth_display)
    
    caching = prefs.get('enable_caching', True)
    ui.print_config_item("⚡ 缓存", "已启用" if caching else "已禁用")
    
    # 意图识别
    intent_mode = config.get('intent_mode', 'llm')
    mode_display = {"keyword": "关键词模式", "llm": "大模型模式", "hybrid": "混合模式"}.get(intent_mode, intent_mode)
    ui.print_config_item("🎯 意图识别", mode_display)
    
    ui.print_divider()


def has_existing_config() -> bool:
    """检查是否存在配置文件."""
    return os.path.exists(CONFIG_FILE)


def setup_language(config: dict) -> dict | None:
    """配置语言."""
    ui.print_step(1, 1, "🌐 语言设置")
    
    language_options = [
        ("zh", "中文 (Chinese) - 默认"),
        ("en", "English (英文)"),
        ("ko", "한국어 (韩语)"),
        ("ja", "日本語 (日语)")
    ]
    
    current = config.get('language', 'zh')
    current_idx = next((i for i, (k, _) in enumerate(language_options) if k == current), 0)
    
    choice = ask_choice("请选择显示语言:", language_options, default=current_idx, current_value=current)
    if choice is None:
        return None
    
    return {"language": language_options[choice][0]}


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
    
    new_config = {
        "provider": provider_id,
        "api_key": None,
        "model": provider_info["default_model"] if provider_info else None,
        "base_url": provider_info["base_url"] if provider_info else None,
    }
    
    # API 地址配置
    if provider_id == "custom":
        new_config["base_url"] = ask_input("API地址", default="http://localhost:11434/v1")
        if new_config["base_url"] is None:
            return None
    else:
        current_url = config.get('llm', {}).get('base_url') or provider_info.get('base_url', '')
        ui.print_substep(f"默认API地址: {current_url or '无'}")
        use_custom_url = ask_yes_no("是否使用自定义API地址?", default=False)
        if use_custom_url is None:
            return None
        if use_custom_url:
            new_url = ask_input("请输入自定义API地址", default=current_url)
            if new_url is None:
                return None
            new_config["base_url"] = new_url
    
    # API Key 配置
    ui.print_substep(f"请设置 {provider_info['name']} API Key")
    if provider_info.get("api_key_url"):
        ui.print_substep(f"获取地址: {provider_info['api_key_url']}")
    
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
    
    # 模型选择
    from llm_integration import get_provider_models
    
    current_model = config.get('llm', {}).get('model')
    models = get_provider_models(provider_id)
    
    if models:
        ui.print_header_text("请选择模型:")
        model_options = [(m["id"], f"{m['name']} - {m['description']}") for m in models]
        current_model_idx = next((i for i, (m_id, _) in enumerate(model_options) if m_id == current_model), 0)
        print(f"\n当前值: {model_options[current_model_idx][1]}")
        
        from cli.interactive_select import select_option_safe
        model_choice = select_option_safe(model_options, default_idx=current_model_idx, current_value=current_model)
        if model_choice is None:
            return None
        new_config["model"] = models[model_choice]["id"]
    else:
        ui.print_warning("没有可用的模型，请检查API配置")
    
    return new_config


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


def run_full_setup_wizard():
    """运行完整的配置向导流程."""
    config = {}
    
    # 显示 Logo
    ui.print_banner()
    print("\n🔄 开始全新配置...\n")
    
    # 1. 语言设置
    print("\n" + "─" * 60)
    result = setup_language(config)
    if result is None:
        return None
    config.update(result)
    
    # 2. 大模型配置
    print("\n" + "─" * 60)
    result = setup_llm_provider(config)
    if result is None:
        return None
    config["llm"] = result
    
    # 3. 响应详细程度
    print("\n" + "─" * 60)
    result = setup_depth(config)
    if result is None:
        return None
    config.setdefault("preferences", {}).update(result)
    
    # 4. 响应缓存
    print("\n" + "─" * 60)
    result = setup_caching(config)
    if result is None:
        return None
    config.setdefault("preferences", {}).update(result)
    
    # 5. 意图识别
    print("\n" + "─" * 60)
    result = setup_intent(config)
    if result is None:
        return None
    config.update(result)
    
    # 显示配置摘要
    ui.print_banner()
    show_current_config(config)
    
    # 确认保存
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


def run_setup_wizard():
    """运行设置向导."""
    # 加载现有配置
    config = load_config()
    
    # 首次使用提示
    if not has_existing_config():
        ui.print_banner()
        ui.print_info("首次配置向导")
        # 自动启动完整配置向导
        result = run_full_setup_wizard()
        if result is not None:
            config = result
        return
    
    # 主菜单循环
    while True:
        # 主菜单选项
        main_options = [
            ("view", "📋 查看当前配置"),
            ("reset_all", "🔄 重新全部配置"),
            ("language", "🌐 语言设置"),
            ("llm", "🤖 大模型配置"),
            ("depth", "📝 响应详细程度"),
            ("caching", "⚡ 响应缓存"),
            ("intent", "🎯 意图识别模式"),
            ("save", "💾 保存配置"),
            ("quit", "❌ 退出配置")
        ]
        
        print()
        choice = ask_choice("请选择操作:", main_options)
        
        if choice is None:
            ui.print_info("退出配置")
            return
        
        action = main_options[choice][0]
        
        if action == "quit":
            ui.print_info("退出配置")
            return
        
        if action == "view":
            # 显示当前配置
            show_current_config(config)
            input("\n按回车键继续...")
            continue
        
        if action == "save":
            # 保存配置
            save_config(config)
            ui.print_success("✅ 配置已保存!")
            input("\n按回车键继续...")
            continue
        
        if action == "reset_all":
            # 重新全部配置 - 启动完整配置向导
            if ask_yes_no("确定要重新配置全部选项吗？当前配置将被清空。", default=False):
                result = run_full_setup_wizard()
                if result is not None:
                    config = result
            continue
        
        # 根据选择执行对应配置
        if action == "language":
            result = setup_language(config)
            if result:
                config.update(result)
        
        elif action == "llm":
            result = setup_llm_provider(config)
            if result:
                config["llm"] = result
        
        elif action == "depth":
            result = setup_depth(config)
            if result:
                config.setdefault("preferences", {}).update(result)
        
        elif action == "caching":
            result = setup_caching(config)
            if result:
                config.setdefault("preferences", {}).update(result)
        
        elif action == "intent":
            result = setup_intent(config)
            if result:
                config.update(result)
        
        # 配置完成后自动返回主菜单（不自动保存）


if __name__ == "__main__":
    run_setup_wizard()
