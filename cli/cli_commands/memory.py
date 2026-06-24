#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory CLI module - 记忆管理命令行工具

提供以下功能：
- status: 查看记忆状态和使用情况
- list: 列出所有记忆条目
- setup: 交互式记忆配置向导
- providers: Provider 诊断和管理

🚪 Access - 💬 CLI - 记忆管理
"""

import sys
from typing import Optional

from common.terminal.colors import Colors, Theme
from common.terminal.ui import print_header, print_substep, print_info, print_divider
from common.config import get_settings, Settings


def show_memory_status() -> None:
    """显示记忆状态和使用情况"""
    from agent.memory.memory_store import MemoryStore, get_memory_dir
    from pathlib import Path

    print_header("记忆状态")
    print()

    try:
        store = MemoryStore.from_config(get_settings().memory)
        store.load_from_disk()

        stats = store.get_stats()
        mem_dir = get_memory_dir()

        print_info("记忆存储位置:")
        print_substep(f"  {mem_dir}")
        print()

        print_info("使用统计:")
        print_substep(f"  记忆条目数: {stats['memory_entries']}")
        print_substep(f"  用户画像条目数: {stats['user_entries']}")
        print_substep(f"  记忆字符: {stats['memory_char_count']:,}/{stats['memory_char_limit']:,} ({stats['memory_char_limit']})")
        print_substep(f"  用户画像字符: {stats['user_char_count']:,}/{stats['user_char_limit']:,} ({stats['user_char_limit']})")
        print_substep(f"  最大条目限制: {stats['max_entries'] or '无限制'}")
        print()

        # 快照状态信息已移除（v10.1.0+）
        # 原脏标记机制已被快照功能替代

    except Exception as e:
        print_substep(f"  无法加载记忆: {e}")
        print()


def list_memory_entries(target: str = "memory") -> None:
    """列出记忆条目"""
    from agent.memory.memory_store import MemoryStore

    print_header(f"记忆条目 ({target})")
    print()

    try:
        store = MemoryStore.from_config(get_settings().memory)
        store.load_from_disk()

        result = store.read(target)

        if not result.get("entries"):
            print_substep("  暂无记忆条目")
            print()
            return

        print_info(f"共 {len(result['entries'])} 条记忆:")
        print()

        for i, entry in enumerate(result["entries"], 1):
            preview = entry[:80] + "..." if len(entry) > 80 else entry
            print_substep(f"  [{i}] {preview}")
            print()

        print_info(f"使用情况: {result['usage']}")
        print()

    except Exception as e:
        print_substep(f"  无法读取记忆: {e}")
        print()


def setup_memory() -> None:
    """交互式记忆配置向导"""
    from cli.setup.interactive_select import ask_choice, print_menu_with_logo
    from common.config import update_settings

    print_header("记忆配置向导")
    print()

    settings = get_settings()
    current_config = settings.memory

    print_info("当前配置:")
    print_substep(f"  记忆字符限制: {current_config.memory_char_limit:,}")
    print_substep(f"  用户画像字符限制: {current_config.user_char_limit:,}")
    print_substep(f"  最大条目数: {current_config.max_entries or '无限制'}")
    print_substep(f"  语义检索: {'启用' if current_config.semantic_retrieval_enabled else '禁用'}")
    print()
    print_divider()
    print()

    # 字符限制配置
    print_info("选择记忆字符限制:")

    char_limit_options = [
        ("1", "紧凑 (1,500 chars)"),
        ("2", "标准 (2,200 chars) - 推荐"),
        ("3", "扩展 (4,000 chars)"),
        ("4", "宽松 (8,000 chars)"),
    ]

    char_limit_map = {
        "1": 1500,
        "2": 2200,
        "3": 4000,
        "4": 8000,
    }

    try:
        choice = print_menu_with_logo(char_limit_options, "记忆字符限制", current_config.memory_char_limit)
        if choice is not None:
            selected = char_limit_options[choice][0]
            new_memory_limit = char_limit_map.get(selected, 2200)
        else:
            new_memory_limit = current_config.memory_char_limit
    except (EOFError, KeyboardInterrupt):
        print()
        print_substep("  配置取消")
        return

    # 语义检索配置
    print_info("是否启用语义检索:")

    semantic_options = [
        ("1", "启用 - 基于语义相似度检索"),
        ("2", "禁用 - 基于关键词检索"),
    ]

    try:
        choice = print_menu_with_logo(
            semantic_options,
            "语义检索",
            "1" if current_config.semantic_retrieval_enabled else "2"
        )
        if choice is not None:
            enable_semantic = choice == 0
        else:
            enable_semantic = current_config.semantic_retrieval_enabled
    except (EOFError, KeyboardInterrupt):
        print()
        print_substep("  配置取消")
        return

    # 保存配置
    try:
        from common.config import Settings

        new_settings = Settings(
            memory=type(current_config)(
                memory_char_limit=new_memory_limit,
                user_char_limit=current_config.user_char_limit,
                max_entries=current_config.max_entries,
                semantic_retrieval_enabled=enable_semantic,
                semantic_max_results=current_config.semantic_max_results,
                semantic_min_score=current_config.semantic_min_score,
            )
        )

        # 保留其他配置
        new_settings.llm = settings.llm
        new_settings.agent = settings.agent
        new_settings.context = settings.context
        new_settings.gateway = settings.gateway

        update_settings(new_settings)

        print()
        print_info("配置已保存!")
        print_substep(f"  记忆字符限制: {new_memory_limit:,}")
        print_substep(f"  语义检索: {'启用' if enable_semantic else '禁用'}")
        print()

    except Exception as e:
        print()
        print_substep(f"  保存配置失败: {e}")
        print()


def diagnose_providers(args: Optional[list] = None) -> None:
    """
    诊断所有或指定的 Memory Provider。
    
    显示 Provider 状态、可用性、工具和配置信息。
    """
    from plugins.memory import diagnose_all_providers, diagnose_provider
    
    print_header("Memory Provider 诊断")
    print()
    
    # 确定要诊断的 Provider
    target_name = None
    if args and len(args) > 0 and not args[0].startswith("-"):
        target_name = args[0]
    
    try:
        if target_name:
            # 诊断指定的 Provider
            print_info(f"诊断 Provider: {target_name}")
            print()
            
            diagnostics = diagnose_provider(target_name, force_refresh=True)
            _print_provider_diagnostics(diagnostics)
        else:
            # 诊断所有 Provider
            print_info("诊断所有 Providers...")
            print()
            
            all_diagnostics = diagnose_all_providers(force_refresh=True)
            
            for name, diagnostics in all_diagnostics.items():
                _print_provider_diagnostics(diagnostics)
                print()
        
        print_divider()
        print()
        
        # 显示健康检查摘要
        healthy_count = sum(1 for d in all_diagnostics.values() if d.is_valid)
        total_count = len(all_diagnostics)
        
        if healthy_count == total_count:
            print_info(f"✓ 所有 Provider 健康 ({healthy_count}/{total_count})")
        else:
            print_substep(f"⚠ {healthy_count}/{total_count} Provider 健康")
        
        print()
        
    except Exception as e:
        print_substep(f"  诊断失败: {e}")
        print()


def _print_provider_diagnostics(diagnostics) -> None:
    """打印单个 Provider 的诊断信息"""
    from plugins.memory import ProviderStatus
    
    # 状态
    status_icon = {
        ProviderStatus.LOADED: "⚡",
        ProviderStatus.AVAILABLE: "✓",
        ProviderStatus.FOUND_BUT_UNAVAILABLE: "⚠",
        ProviderStatus.NOT_FOUND: "✗",
        ProviderStatus.ERROR: "✗",
        ProviderStatus.CONFIG_INVALID: "⚠",
    }
    
    status = diagnostics.status
    icon = status_icon.get(status, "?")
    
    print_info(f"{icon} Provider: {diagnostics.name}")
    print_substep(f"  状态: {status.value}")
    
    if diagnostics.path:
        print_substep(f"  路径: {diagnostics.path}")
    
    # 可用性
    if diagnostics.is_available:
        print_substep("  可用性: ✓ 可用")
    else:
        print_substep("  可用性: ✗ 不可用")
    
    # 错误
    if diagnostics.error:
        print_substep(f"  错误: {diagnostics.error}")
    
    # 工具
    if diagnostics.available_tools:
        print_substep(f"  工具: {', '.join(diagnostics.available_tools)}")
    
    # 警告
    if diagnostics.warnings:
        print_substep("  警告:")
        for warning in diagnostics.warnings:
            print_substep(f"    - {warning}")
    
    # 配置模式
    if diagnostics.config_schema:
        print_substep(f"  配置字段: {len(diagnostics.config_schema)} 个")
        for field in diagnostics.config_schema:
            required = "必需" if field.get("required") else "可选"
            print_substep(f"    - {field.get('key')} ({required})")
    
    # 建议
    if diagnostics.config_errors:
        print_substep("  配置错误:")
        for error in diagnostics.config_errors:
            print_substep(f"    - {error}")


def health_check_command(args: Optional[list] = None) -> None:
    """执行 Provider 健康检查"""
    from plugins.memory import health_check_provider
    
    print_header("Memory Provider 健康检查")
    print()
    
    # 确定要检查的 Provider
    target_name = "builtin"
    if args and len(args) > 0 and not args[0].startswith("-"):
        target_name = args[0]
    
    try:
        print_info(f"检查 Provider: {target_name}")
        print()
        
        result = health_check_provider(target_name)
        
        # 检查结果
        if result["healthy"]:
            print_info("✓ Provider 健康检查通过")
        else:
            print_substep("✗ Provider 健康检查失败")
        
        print()
        print_info("检查项:")
        
        for check_name, check_result in result.get("checks", {}).items():
            if check_result.get("passed"):
                status_icon = "✓"
            else:
                status_icon = "✗"
            
            print_substep(f"  {status_icon} {check_name}: {check_result.get('error') or '通过'}")
        
        print()
        
    except Exception as e:
        print_substep(f"  健康检查失败: {e}")
        print()


def memory_command(args: Optional[list] = None) -> int:
    """
    Memory CLI 命令入口

    Usage:
        handsome memory status    # 查看状态
        handsome memory list      # 列出条目
        handsome memory setup     # 配置向导
        handsome memory providers # Provider 诊断
        handsome memory health    # 健康检查
    """
    if args is None:
        args = sys.argv[2:] if len(sys.argv) > 2 else []

    if not args or args[0] in ["--help", "-h", "help"]:
        print_header("记忆管理命令")
        print()
        print_info("可用子命令:")
        print_substep("  status     - 查看记忆状态和使用情况")
        print_substep("  list       - 列出所有记忆条目")
        print_substep("  setup      - 交互式配置向导")
        print_substep("  providers  - Provider 诊断")
        print_substep("  health     - Provider 健康检查")
        print()
        print_info("示例:")
        print_substep("  handsome memory status")
        print_substep("  handsome memory list")
        print_substep("  handsome memory setup")
        print_substep("  handsome memory providers")
        print_substep("  handsome memory providers honcho")
        print_substep("  handsome memory health")
        print()
        return 0

    subcommand = args[0]

    try:
        if subcommand == "status":
            show_memory_status()
        elif subcommand == "list":
            target = "memory"
            if len(args) > 1:
                if args[1] in ["memory", "user"]:
                    target = args[1]
            list_memory_entries(target)
        elif subcommand == "setup":
            setup_memory()
        elif subcommand == "providers":
            diagnose_providers(args[1:] if len(args) > 1 else None)
        elif subcommand == "health":
            health_check_command(args[1:] if len(args) > 1 else None)
        else:
            print_substep(f"  未知子命令: {subcommand}")
            print_substep("  运行 'handsome memory --help' 查看帮助")
            return 1

    except (EOFError, KeyboardInterrupt):
        print()
        print_substep("  操作取消")
        return 130

    except Exception as e:
        print_substep(f"  错误: {e}")
        return 1

    return 0


__all__ = [
    "memory_command",
    "show_memory_status",
    "list_memory_entries",
    "setup_memory",
    "diagnose_providers",
    "health_check_command",
]
