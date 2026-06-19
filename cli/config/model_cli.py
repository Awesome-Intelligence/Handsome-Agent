#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model CLI - Model management commands

🚪 Access - 💬 CLI - 模型管理
"""

import json
from pathlib import Path


# Supported providers and their default models
PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
    },
    "anthropic": {
        "name": "Anthropic",
        "default_model": "claude-3-5-sonnet-20240620",
        "models": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-sonnet-20240229"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_model": "deepseek-v4-pro",
        "models": ["deepseek-v4-pro", "deepseek-chat"],
    },
    "ollama": {
        "name": "Ollama (Local)",
        "default_model": "llama3",
        "models": ["llama3", "mistral", "codellama"],
    },
}


def _get_config_file() -> Path:
    """Get config file path."""
    config_dir = Path.home() / ".handsome_agent"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "config.json"


def _load_config() -> dict:
    """Load config from file."""
    config_file = _get_config_file()
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict):
    """Save config to file."""
    config_file = _get_config_file()
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def list_models(provider: str = None, json_output: bool = False):
    """List available models.

    Args:
        provider: Filter by provider
        json_output: Output as JSON
    """
    from common.terminal.ui import print_header

    if provider:
        if provider in PROVIDERS:
            provider_info = PROVIDERS[provider]
            if json_output:
                print(json.dumps(provider_info, indent=2))
            else:
                print_header(f"{provider_info['name']} 模型")
                print(f"默认模型: {provider_info['default_model']}")
                print("\n可用模型:")
                for model in provider_info["models"]:
                    marker = " <- 默认" if model == provider_info["default_model"] else ""
                    print(f"  * {model}{marker}")
        else:
            print(f"Unknown provider: {provider}")
            print(f"Available: {', '.join(PROVIDERS.keys())}")
    else:
        # List all providers
        if json_output:
            print(json.dumps(PROVIDERS, indent=2))
        else:
            print_header("可用模型")

            for provider_id, provider_info in PROVIDERS.items():
                print(f"\n  [{provider_id}] {provider_info['name']}")
                print(f"    默认: {provider_info['default_model']}")
                print(f"    模型: {', '.join(provider_info['models'][:3])}")


def set_default_model(model_name: str, provider: str = None):
    """Set default model.

    Args:
        model_name: Model name
        provider: Provider name (optional)
    """
    from common.terminal.ui import print_success

    config = _load_config()

    # Initialize llm section
    if "llm" not in config:
        config["llm"] = {}
    if "model" not in config:
        config["model"] = {}

    # Set provider if specified
    if provider:
        config["llm"]["provider"] = provider
    elif not config["llm"].get("provider"):
        # Try to infer provider from model name
        for prov_id, prov_info in PROVIDERS.items():
            if model_name in prov_info["models"]:
                config["llm"]["provider"] = prov_id
                break

    # Set model
    config["model"]["name"] = model_name

    _save_config(config)

    provider_str = f" ({config['llm']['provider']})" if config["llm"].get("provider") else ""
    print_success(f"已设置默认模型: {model_name}{provider_str}")


if __name__ == "__main__":
    import sys
    list_models()
