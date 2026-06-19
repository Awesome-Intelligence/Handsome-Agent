#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provider management for Handsome Agent CLI.

🚪 Access - 💬 CLI - Provider 管理

提供 LLM Provider 统一管理功能：列出 Provider、显示信息、检查状态。
"""

import os
from typing import Dict, List, Optional, Any


# Provider 定义
PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "display_name": "OpenAI",
        "website": "https://openai.com",
        "models": [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
        ],
        "default_model": "gpt-4o",
        "capabilities": ["chat", "vision", "function_calling", "json_mode"],
        "pricing": {"input": 5.0, "output": 15.0},  # $/1M tokens
        "context_windows": {"gpt-4o": 128000, "gpt-4o-mini": 128000},
        "status": "active",
        "env_vars": ["OPENAI_API_KEY"],
    },
    "anthropic": {
        "name": "Anthropic",
        "display_name": "Anthropic (Claude)",
        "website": "https://anthropic.com",
        "models": [
            "claude-3-5-sonnet-20241022", "claude-3-5-sonnet-latest",
            "claude-3-opus-20240229", "claude-3-opus-latest",
            "claude-3-sonnet-20240229", "claude-3-sonnet-latest",
            "claude-3-haiku-20240307", "claude-3-haiku-latest",
        ],
        "default_model": "claude-3-5-sonnet-20241022",
        "capabilities": ["chat", "vision", "function_calling", "long_context"],
        "pricing": {"input": 3.0, "output": 15.0},
        "context_windows": {"claude-3-5-sonnet-20241022": 200000},
        "status": "active",
        "env_vars": ["ANTHROPIC_API_KEY"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "display_name": "DeepSeek",
        "website": "https://deepseek.com",
        "models": [
            "deepseek-chat", "deepseek-coder",
        ],
        "default_model": "deepseek-chat",
        "capabilities": ["chat", "function_calling", "coding"],
        "pricing": {"input": 0.14, "output": 0.28},
        "context_windows": {"deepseek-chat": 64000},
        "status": "active",
        "env_vars": ["DEEPSEEK_API_KEY"],
    },
    "google": {
        "name": "Google",
        "display_name": "Google (Gemini)",
        "website": "https://ai.google.dev",
        "models": [
            "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash",
            "gemini-1.5-flash-8b", "gemini-pro",
        ],
        "default_model": "gemini-1.5-flash",
        "capabilities": ["chat", "vision", "function_calling"],
        "pricing": {"input": 0.075, "output": 0.3},
        "context_windows": {"gemini-1.5-flash": 1000000},
        "status": "active",
        "env_vars": ["GOOGLE_API_KEY"],
    },
    "minimax": {
        "name": "MiniMax",
        "display_name": "MiniMax",
        "website": "https://www.minimax.io",
        "models": [
            "MiniMax-Text-01", "abab6.5s-chat", "abab6.5-chat",
        ],
        "default_model": "MiniMax-Text-01",
        "capabilities": ["chat", "function_calling"],
        "pricing": {"input": 0.1, "output": 0.1},
        "context_windows": {"MiniMax-Text-01": 1000000},
        "status": "active",
        "env_vars": ["MINIMAX_API_KEY"],
    },
    "moonshot": {
        "name": "Moonshot",
        "display_name": "Moonshot AI",
        "website": "https://www.moonshot.cn",
        "models": [
            "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k",
        ],
        "default_model": "moonshot-v1-8k",
        "capabilities": ["chat", "long_context"],
        "pricing": {"input": 0.06, "output": 0.06},
        "context_windows": {"moonshot-v1-128k": 128000},
        "status": "active",
        "env_vars": ["MOONSHOT_API_KEY"],
    },
    "groq": {
        "name": "Groq",
        "display_name": "Groq",
        "website": "https://console.groq.com",
        "models": [
            "llama-3.1-70b-versatile", "llama-3.1-8b-instant",
            "mixtral-8x7b-32768", "gemma2-9b-it",
        ],
        "default_model": "llama-3.1-8b-instant",
        "capabilities": ["chat", "fast_inference"],
        "pricing": {"input": 0, "output": 0},  # Free tier available
        "context_windows": {"llama-3.1-70b-versatile": 128000},
        "status": "active",
        "env_vars": ["GROQ_API_KEY"],
    },
    "zhipu": {
        "name": "Zhipu",
        "display_name": "Zhipu AI (智谱清言)",
        "website": "https://www.zhipuai.cn",
        "models": [
            "glm-4", "glm-4-flash", "glm-4-plus",
            "glm-3-turbo",
        ],
        "default_model": "glm-4-flash",
        "capabilities": ["chat", "function_calling"],
        "pricing": {"input": 0.1, "output": 0.1},
        "context_windows": {"glm-4": 128000},
        "status": "active",
        "env_vars": ["ZHIPU_API_KEY"],
    },
    "dashscope": {
        "name": "DashScope",
        "display_name": "阿里云 DashScope",
        "website": "https://www.aliyun.com/product/dashscope",
        "models": [
            "qwen-turbo", "qwen-plus", "qwen-max",
            "qwen2-72b-instruct", "qwen2-57b-a14b-instruct",
        ],
        "default_model": "qwen-turbo",
        "capabilities": ["chat", "vision", "function_calling"],
        "pricing": {"input": 0.02, "output": 0.06},
        "context_windows": {"qwen-max": 32000},
        "status": "active",
        "env_vars": ["DASHSCOPE_API_KEY"],
    },
    "volcengine": {
        "name": "VolcEngine",
        "display_name": "火山引擎 (豆包)",
        "website": "https://www.volcengine.com",
        "models": [
            "doubao-pro-32k", "doubao-lite-32k",
        ],
        "default_model": "doubao-pro-32k",
        "capabilities": ["chat", "function_calling"],
        "pricing": {"input": 0.05, "output": 0.05},
        "context_windows": {"doubao-pro-32k": 32000},
        "status": "active",
        "env_vars": ["VOLC_ACCESS_KEY", "VOLC_SECRET_KEY"],
    },
}


def list_providers(json_output: bool = False) -> None:
    """List all available providers.
    
    Args:
        json_output: Output as JSON
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_info
    
    print_header("📡 LLM Provider 列表")
    
    providers_list = []
    for key, provider in PROVIDERS.items():
        # 检查 API Key 是否已设置
        env_vars = provider.get("env_vars", [])
        has_key = any(os.environ.get(v) for v in env_vars)
        
        providers_list.append({
            "id": key,
            "name": provider["display_name"],
            "models_count": len(provider.get("models", [])),
            "default_model": provider.get("default_model", ""),
            "configured": has_key,
            "status": provider.get("status", "unknown"),
        })
    
    if json_output:
        import json
        print(json.dumps({"providers": providers_list}, indent=2, ensure_ascii=False))
        return
    
    print()
    print(color("  ID", Colors.BOLD), end="")
    print(color(" " * 12, Colors.DIM), end="")
    print(color("Name", Colors.DIM), end="")
    print(color(" " * 20, Colors.DIM), end="")
    print(color("Models", Colors.DIM), end="")
    print(color(" " * 6, Colors.DIM), end="")
    print(color("Default", Colors.DIM), end="")
    print(color(" " * 16, Colors.DIM), end="")
    print(color("Status", Colors.DIM))
    print(color("-" * 100, Colors.DIM))
    
    for p in providers_list:
        status_icon = f"{Colors.GREEN}●{Colors.RESET}" if p["configured"] else f"{Colors.YELLOW}○{Colors.RESET}"
        name = p["name"][:22] if len(p["name"]) > 22 else p["name"]
        default = p["default_model"][:18] if len(p["default_model"]) > 18 else p["default_model"]
        
        print(f"  {color(p['id'], Colors.AVOCADO_BRIGHT):12s} {status_icon} {name:22s} {p['models_count']:6d} {default:18s}")
    
    print()


def get_provider_info(provider_id: str) -> None:
    """Show detailed information about a provider.
    
    Args:
        provider_id: Provider ID (e.g., 'openai')
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_error, print_info
    
    print_header(f"📡 Provider: {provider_id}")
    
    if provider_id not in PROVIDERS:
        print_error(f"Provider not found: {provider_id}")
        print_info(f"Available providers: {', '.join(PROVIDERS.keys())}")
        return
    
    provider = PROVIDERS[provider_id]
    
    # 检查 API Key
    env_vars = provider.get("env_vars", [])
    has_key = any(os.environ.get(v) for v in env_vars)
    
    print()
    print(color(f"  Name: ", Colors.DIM) + color(provider["display_name"], Colors.WHITE))
    print(color(f"  Website: ", Colors.DIM) + color(provider.get("website", "N/A"), Colors.AVOCADO_BRIGHT))
    print(color(f"  Default Model: ", Colors.DIM) + color(provider.get("default_model", "N/A"), Colors.WHITE))
    print(color(f"  Status: ", Colors.DIM) + (f"{Colors.GREEN}Configured{Colors.RESET}" if has_key else f"{Colors.YELLOW}Not Configured{Colors.RESET}"))
    print()
    
    print(color(f"  Models ({len(provider.get('models', []))}):", Colors.AVOCADO_BRIGHT))
    for model in provider.get("models", []):
        context = provider.get("context_windows", {}).get(model, "N/A")
        if context != "N/A":
            context_str = f"{context // 1000}K"
        else:
            context_str = "?"
        print(f"    • {model} ({context_str} context)")
    
    print()
    print(color(f"  Capabilities:", Colors.AVOCADO_BRIGHT))
    for cap in provider.get("capabilities", []):
        print(f"    • {cap}")
    
    print()
    print(color(f"  Pricing ($/1M tokens):", Colors.AVOCADO_BRIGHT))
    pricing = provider.get("pricing", {})
    print(f"    Input: ${pricing.get('input', 'N/A')}")
    print(f"    Output: ${pricing.get('output', 'N/A')}")
    
    print()
    print(color(f"  Environment Variables:", Colors.AVOCADO_BRIGHT))
    for var in env_vars:
        value = os.environ.get(var, "")
        masked = var + ": " + ("*" * 8 if value else "(not set)")
        print(f"    • {masked}")


def check_provider_status(provider_id: Optional[str] = None) -> None:
    """Check provider connection status.
    
    Args:
        provider_id: Specific provider to check, or None for all
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error
    
    print_header("🔍 Provider 状态检查")
    
    providers_to_check = [provider_id] if provider_id else list(PROVIDERS.keys())
    
    print()
    
    for p_id in providers_to_check:
        if p_id not in PROVIDERS:
            continue
        
        provider = PROVIDERS[p_id]
        env_vars = provider.get("env_vars", [])
        
        # 检查 API Key
        has_key = any(os.environ.get(v) for v in env_vars)
        
        if has_key:
            print_success(f"  {color('✓', Colors.GREEN)} {provider['display_name']}: Configured")
        else:
            missing = [v for v in env_vars if not os.environ.get(v)]
            print_error(f"  {color('✗', Colors.RED)} {provider['display_name']}: Missing {', '.join(missing)}")
    
    print()


def search_provider(query: str) -> List[str]:
    """Search providers by name or model.
    
    Args:
        query: Search query
        
    Returns:
        List of matching provider IDs
    """
    results = []
    query_lower = query.lower()
    
    for p_id, provider in PROVIDERS.items():
        # 匹配 Provider 名称
        if query_lower in provider["name"].lower():
            results.append(p_id)
            continue
        
        # 匹配模型
        for model in provider.get("models", []):
            if query_lower in model.lower():
                results.append(p_id)
                break
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Provider management")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    list_parser = subparsers.add_parser("list", help="List all providers")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    info_parser = subparsers.add_parser("info", help="Show provider info")
    info_parser.add_argument("provider_id", help="Provider ID")
    
    status_parser = subparsers.add_parser("status", help="Check provider status")
    status_parser.add_argument("provider_id", nargs="?", help="Provider ID (optional)")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_providers(json_output=args.json)
    elif args.command == "info":
        get_provider_info(args.provider_id)
    elif args.command == "status":
        check_provider_status(args.provider_id)
    else:
        list_providers()