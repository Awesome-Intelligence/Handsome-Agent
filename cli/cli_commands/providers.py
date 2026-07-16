#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Provider management for Agent-Z CLI.

🚪 Access - 💬 CLI - Provider 管理

提供 LLM Provider 统一管理功能：列出 Provider、显示信息、检查状态。

本模块自 v8.x 起作为兼容层：Provider 元数据字典与查询函数
已上移到 ``common.llm_providers.catalog``，CLI 仅保留命令渲染逻辑。
"""

import os
from typing import Dict, List, Optional, Any

# 兼容性 re-export：Provider 元数据来自 common 层
from common.llm_providers import (
    PROVIDERS,
    get_provider_info as _get_provider_info_dict,
    get_provider_ids,
)


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
        status_icon = (
            f"{Colors.GREEN}●{Colors.RESET}"
            if p["configured"]
            else f"{Colors.YELLOW}○{Colors.RESET}"
        )
        name = p["name"][:22] if len(p["name"]) > 22 else p["name"]
        default = (
            p["default_model"][:18]
            if len(p["default_model"]) > 18
            else p["default_model"]
        )

        print(
            f"  {color(p['id'], Colors.AVOCADO_BRIGHT):12s} "
            f"{status_icon} {name:22s} {p['models_count']:6d} {default:18s}"
        )

    print()


def get_provider_info(provider_id: str) -> Optional[Dict[str, Any]]:
    """Show detailed information about a provider.

    Args:
        provider_id: Provider ID (e.g., 'openai')

    Returns:
        Provider metadata dict, or None if not found
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_error, print_info

    print_header(f"📡 Provider: {provider_id}")

    provider = PROVIDERS.get(provider_id)
    if provider is None:
        print_error(f"Provider not found: {provider_id}")
        print_info(f"Available providers: {', '.join(PROVIDERS.keys())}")
        return None

    # 检查 API Key
    env_vars = provider.get("env_vars", [])
    has_key = any(os.environ.get(v) for v in env_vars)

    print()
    print(color("  Name: ", Colors.DIM) + color(provider["display_name"], Colors.WHITE))
    print(color("  Website: ", Colors.DIM) + color(provider.get("website", "N/A"), Colors.AVOCADO_BRIGHT))
    print(color("  Default Model: ", Colors.DIM) + color(provider.get("default_model", "N/A"), Colors.WHITE))
    print(color("  Status: ", Colors.DIM) + (f"{Colors.GREEN}Configured{Colors.RESET}" if has_key else f"{Colors.YELLOW}Not Configured{Colors.RESET}"))
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
    print(color("  Capabilities:", Colors.AVOCADO_BRIGHT))
    for cap in provider.get("capabilities", []):
        print(f"    • {cap}")

    print()
    print(color("  Pricing ($/1M tokens):", Colors.AVOCADO_BRIGHT))
    pricing = provider.get("pricing", {})
    print(f"    Input: ${pricing.get('input', 'N/A')}")
    print(f"    Output: ${pricing.get('output', 'N/A')}")

    print()
    print(color("  Environment Variables:", Colors.AVOCADO_BRIGHT))
    for var in env_vars:
        value = os.environ.get(var, "")
        masked = var + ": " + ("*" * 8 if value else "(not set)")
        print(f"    • {masked}")

    return provider


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


__all__ = [
    "PROVIDERS",
    "list_providers",
    "get_provider_info",
    "check_provider_status",
    "search_provider",
]


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