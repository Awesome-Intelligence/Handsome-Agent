#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
First-run setup wizard for Handsome Agent.
Simplified configuration - just the essentials.
"""

import os
import sys
import json
from cli import ui


CONFIG_FILE = os.path.expanduser("~/.custom_agent_config.json")


QUIT_COMMANDS = ['quit', 'exit', 'q', '退出']


def should_quit(response: str) -> bool:
    """Check if user wants to quit."""
    return response.lower() in [c.lower() for c in QUIT_COMMANDS]


def ask_yes_no(question: str, default: bool = True) -> bool | None:
    """Ask a yes/no question. Returns None if user quits."""
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            ui.print_substep(f"{question} {suffix}")
            ui.print_substep(f"{ui.Theme.SECONDARY_DIM}(输入 q 退出){ui.Colors.RESET}")
            response = input(ui.print_prompt()).strip().lower()
            
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


def ask_choice(question: str, options: list, default: int = 0) -> int | None:
    """Ask user to choose from options with numbered input."""
    print()
    ui.print_header_text(question)
    
    from cli.interactive_select import select_option
    result = select_option(options)
    
    if result is None:
        return None
    return result


def ask_input(question: str, default: str = None, password: bool = False, required: bool = True) -> str | None:
    """Ask user for input. Returns None if user quits."""
    if default:
        prompt = f"{question} (直接回车使用默认值: {default})"
    else:
        prompt = question
    
    print()
    ui.print_substep(prompt)
    if required:
        ui.print_substep(f"{ui.Theme.SECONDARY_DIM}(输入 q 退出){ui.Colors.RESET}")
    
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
    """Get all supported providers."""
    from llm_integration import get_all_providers
    return get_all_providers()


def setup_llm_provider() -> dict | None:
    """Setup LLM provider configuration."""
    ui.print_step(1, 2, "大模型配置")
    
    providers = get_all_providers()
    ui.print_provider_list(providers)
    provider_options = [(p["id"], f"{p['name']} - {p['description']}") for p in providers]
    provider_options.append(("none", "暂不使用 (使用基础模板模式)"))
    
    choice = ask_choice("请选择要使用的大模型提供商:", provider_options)
    if choice is None:
        return None
    provider_id = provider_options[choice][0]
    
    if provider_id == "none":
        ui.print_info("跳过大模型配置，使用基础模板模式")
        ui.print_end_step()
        return {"provider": "none", "api_key": None, "model": None, "base_url": None}
    
    provider_info = next((p for p in providers if p["id"] == provider_id), None)
    
    config = {
        "provider": provider_id,
        "api_key": None,
        "model": provider_info["default_model"] if provider_info else None,
        "base_url": provider_info["base_url"] if provider_info else None,
    }
    
    if provider_id == "custom":
        config["base_url"] = ask_input("API地址", default="http://localhost:11434/v1")
        if config["base_url"] is None:
            return None
    else:
        ui.print_substep(f"默认API地址: {provider_info.get('base_url', '无')}")
        use_custom_url = ask_yes_no("是否使用自定义API地址?", default=False)
        if use_custom_url is None:
            return None
        if use_custom_url:
            ui.print_substep(f"当前默认地址: {provider_info.get('base_url', '')}")
            new_url = ask_input("请输入自定义API地址")
            if new_url is None:
                return None
            config["base_url"] = new_url
    
    ui.print_substep(f"请设置 {provider_info['name']} API Key")
    if provider_info.get("api_key_url"):
        ui.print_substep(f"获取地址: {provider_info['api_key_url']}")
    
    api_key = ask_input("API Key", password=True, required=True)
    if api_key is None:
        return None
    config["api_key"] = api_key
    
    from llm_integration import PROVIDER_MODELS, fetch_models_from_api
    
    ui.print_info("正在从API获取模型列表...")
    try:
        api_models = fetch_models_from_api(
            provider_id,
            config["api_key"],
            config.get("base_url")
        )
        if api_models:
            models = api_models
            ui.print_success(f"成功获取 {len(models)} 个模型")
        else:
            ui.print_warning("API获取失败，使用默认模型列表")
            models = PROVIDER_MODELS.get(provider_id, [])
    except Exception as e:
        ui.print_warning(f"获取模型列表失败: {e}")
        models = PROVIDER_MODELS.get(provider_id, [])
    
    if models:
        ui.print_header_text("请选择模型:")
        from cli.interactive_select import select_option
        model_choice = select_option([(m.id, f"{m.name} - {m.description}") for m in models])
        if model_choice is None:
            return None
        config["model"] = models[model_choice].id
    else:
        ui.print_warning("没有可用的模型，请检查API配置")
    
    ui.print_end_step()
    return config


def setup_preferences() -> dict | None:
    """Setup basic preferences."""
    ui.print_step(2, 2, "偏好设置")
    
    language_options = [
        ("zh", "中文 (Chinese) - 默认"),
        ("en", "English (英文)"),
        ("ko", "한국어 (韩语)"),
        ("ja", "日本語 (日语)")
    ]
    choice = ask_choice("请选择日志显示语言:", language_options, default=0)
    if choice is None:
        return None
    language = language_options[choice][0]
    
    depth_options = [
        ("brief", "简洁 - 只返回要点"),
        ("moderate", "适中 - 适度详细"),
        ("detailed", "详细 - 完整说明")
    ]
    choice = ask_choice("请选择解释详细程度:", depth_options, default=2)
    if choice is None:
        return None
    explanation_depth = depth_options[choice][0]
    
    ui.print_end_step()
    return {
        "explanation_depth": explanation_depth,
        "response_format": "markdown",
        "enable_caching": True,
        "max_response_length": 4000,
        "language": language
    }


def confirm_and_save(config: dict) -> bool:
    """Confirm and save configuration."""
    print()
    ui.print_header_text("配置摘要:")
    ui.print_divider()
    
    if config.get("llm"):
        llm = config["llm"]
        provider_display = {
            "openai": "OpenAI", "anthropic": "Anthropic Claude", "google": "Google Gemini",
            "deepseek": "DeepSeek", "minimax": "MiniMax", "moonshot": "Kimi",
            "zhipu": "智谱AI", "dashscope": "阿里通义", "groq": "Groq",
            "siliconflow": "SiliconFlow", "none": "不使用",
        }.get(llm.get('provider', 'none'), llm.get('provider', 'none'))
        
        ui.print_config_item("大模型", provider_display)
        if llm.get("model"):
            ui.print_config_item("模型", llm['model'])
    
    prefs = config.get("preferences", {})
    ui.print_config_item("详细程度", prefs.get('explanation_depth', 'detailed'))
    ui.print_config_item("显示语言", prefs.get('language', 'zh'))
    
    ui.print_divider()
    
    confirm = ask_yes_no("确认保存配置?", default=True)
    if confirm is None:
        return False
    if confirm:
        save_config(config)
        ui.print_success("配置已保存!")
        return True
    else:
        ui.print_warning("配置未保存。")
        return False


def save_config(config: dict):
    """Save configuration to file."""
    os.makedirs(os.path.dirname(CONFIG_FILE) or ".", exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def has_existing_config() -> bool:
    """Check if configuration file exists."""
    return os.path.exists(CONFIG_FILE)


def run_setup_wizard():
    """Run the complete setup wizard."""
    ui.print_banner()
    
    if has_existing_config():
        ui.print_warning("检测到已有配置")
        reset = ask_yes_no("是否重新配置?", default=False)
        if reset is None:
            return
        if not reset:
            ui.print_info("保持现有配置")
            return
    
    config = {}
    
    llm_config = setup_llm_provider()
    if llm_config is None:
        ui.print_info("设置已取消")
        return
    config["llm"] = llm_config
    
    preferences = setup_preferences()
    if preferences is None:
        ui.print_info("设置已取消")
        return
    config["preferences"] = preferences
    
    if confirm_and_save(config):
        ui.print_setup_complete()
        ui.print_header_text("运行方式:")
        print(f"  {ui.Theme.ACCENT}python -m cli.main --interactive{ui.Colors.RESET}    # 交互模式")
        print(f"  {ui.Theme.ACCENT}python -m cli.main -q \"你的问题\"{ui.Colors.RESET}   # 单次查询")
        print()
    else:
        ui.print_info("设置已取消")


if __name__ == "__main__":
    run_setup_wizard()
