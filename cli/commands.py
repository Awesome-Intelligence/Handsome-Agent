#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slash commands registry for Agent-Z.

This module defines all available slash commands (e.g., /help, /compress)
and their metadata. Commands are registered in COMMAND_REGISTRY and can
be discovered by the agent to provide autocomplete.

🚪 Access - 💬 CLI - 斜杠命令注册表

参考 Hermes 的 commands.py 设计，增强版：
- 子命令支持
- 平台特定命令
- 动态补全
- 命令分类增强
- 帮助格式化
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, List, Dict, Any


class CommandCategory(Enum):
    """Command categories."""
    GENERAL = "general"
    SESSION = "session"
    TOOLS = "tools"
    CONFIG = "config"
    INFO = "info"
    EXIT = "exit"


@dataclass
class SubCommand:
    """Sub-command definition."""
    name: str
    description: str = ""
    handler: Optional[Callable] = None
    completions: Optional[List[str]] = None


@dataclass
class CommandDef:
    """Command definition with enhanced metadata."""
    name: str
    handler: Callable
    description: str = ""
    usage: str = ""
    aliases: List[str] = field(default_factory=list)
    category: CommandCategory = CommandCategory.GENERAL
    subcommands: Dict[str, SubCommand] = field(default_factory=dict)
    completions: Optional[List[str]] = None
    platform_specific: Optional[str] = None  # e.g., "telegram", "discord"
    examples: List[str] = field(default_factory=list)
    since: str = "1.0.0"  # Version when command was added


# COMMAND_REGISTRY: Dict[str, CommandDef]
# All registered commands
COMMAND_REGISTRY: Dict[str, CommandDef] = {}

# Platform-specific commands
PLATFORM_COMMANDS: Dict[str, List[str]] = {}


def register_command(
    name: str,
    handler: Callable,
    description: str = "",
    usage: str = "",
    aliases: Optional[List[str]] = None,
    category: CommandCategory = CommandCategory.GENERAL,
    subcommands: Optional[Dict[str, SubCommand]] = None,
    completions: Optional[List[str]] = None,
    platform: Optional[str] = None,
    examples: Optional[List[str]] = None,
    since: str = "1.0.0",
) -> None:
    """Register a slash command.

    Args:
        name: Command name (without leading slash)
        handler: Function to call when command is invoked
        description: Short description shown in help
        usage: Usage example
        aliases: Alternative command names
        category: Command category (CommandCategory enum)
        subcommands: Dict of sub-command definitions
        completions: List of completion suggestions
        platform: Platform-specific command (e.g., "telegram")
        examples: List of usage examples
        since: Version when command was added
    """
    global COMMAND_REGISTRY, PLATFORM_COMMANDS

    cmd_def = CommandDef(
        name=name,
        handler=handler,
        description=description,
        usage=usage,
        aliases=aliases or [],
        category=category,
        subcommands=subcommands or {},
        completions=completions,
        platform_specific=platform,
        examples=examples or [],
        since=since,
    )

    # Register main name
    COMMAND_REGISTRY[name] = cmd_def

    # Register aliases
    if aliases:
        for alias in aliases:
            COMMAND_REGISTRY[alias] = cmd_def

    # Register platform-specific commands
    if platform:
        if platform not in PLATFORM_COMMANDS:
            PLATFORM_COMMANDS[platform] = []
        PLATFORM_COMMANDS[platform].append(name)


def register_subcommand(
    parent_name: str,
    sub_name: str,
    description: str = "",
    handler: Optional[Callable] = None,
    completions: Optional[List[str]] = None,
) -> None:
    """Register a sub-command for an existing command.

    Args:
        parent_name: Parent command name
        sub_name: Sub-command name
        description: Sub-command description
        handler: Handler function
        completions: Completion suggestions
    """
    global COMMAND_REGISTRY

    if parent_name not in COMMAND_REGISTRY:
        return

    parent = COMMAND_REGISTRY[parent_name]
    parent.subcommands[sub_name] = SubCommand(
        name=sub_name,
        description=description,
        handler=handler,
        completions=completions,
    )


def get_command(name: str) -> Optional[CommandDef]:
    """Get command info by name or alias."""
    return COMMAND_REGISTRY.get(name)


def get_commands_by_category(category: CommandCategory) -> List[CommandDef]:
    """Get all commands in a category."""
    commands = []
    seen = set()

    for cmd in COMMAND_REGISTRY.values():
        if cmd.category == category and id(cmd) not in seen:
            commands.append(cmd)
            seen.add(id(cmd))

    return commands


def list_commands(
    category: Optional[CommandCategory] = None,
    include_platform_specific: bool = False,
) -> List[CommandDef]:
    """List all registered commands.

    Args:
        category: Filter by category
        include_platform_specific: Include platform-specific commands

    Returns:
        List of CommandDef
    """
    if category:
        commands = get_commands_by_category(category)
    else:
        commands = list(COMMAND_REGISTRY.values())

    # Remove duplicates
    seen = set()
    unique_commands = []
    for cmd in commands:
        if id(cmd) not in seen:
            seen.add(id(cmd))
            # Filter platform-specific if requested
            if include_platform_specific or not cmd.platform_specific:
                unique_commands.append(cmd)

    return unique_commands


def get_categories() -> List[str]:
    """Get list of all command categories."""
    categories = set()
    for cmd in COMMAND_REGISTRY.values():
        if not cmd.platform_specific:
            categories.add(cmd.category.value)
    return sorted(list(categories))


def get_command_help(command: CommandDef, full: bool = False) -> str:
    """Format help for a command.

    Args:
        command: Command definition
        full: Include examples and details

    Returns:
        Formatted help text
    """
    lines = []

    # Name and description
    lines.append(f"/{command.name}")

    if command.aliases:
        alias_str = ", ".join(f"/{a}" for a in command.aliases)
        lines.append(f"  Aliases: {alias_str}")

    lines.append(f"  {command.description}")

    # Usage
    if command.usage:
        lines.append(f"  Usage: {command.usage}")

    # Subcommands
    if command.subcommands:
        lines.append("  Subcommands:")
        for sub_name, sub in command.subcommands.items():
            lines.append(f"    /{command.name} {sub_name} - {sub.description}")

    # Examples
    if full and command.examples:
        lines.append("  Examples:")
        for example in command.examples:
            lines.append(f"    {example}")

    # Platform specific
    if command.platform_specific:
        lines.append(f"  [{command.platform_specific} only]")

    lines.append(f"  (since v{command.since})")

    return "\n".join(lines)


def format_help(category: Optional[str] = None, full: bool = False) -> str:
    """Format help text for all commands.

    Args:
        category: Filter by category
        full: Include detailed help

    Returns:
        Formatted help text
    """
    categories = get_categories() if not category else [category]
    lines = []

    for cat in categories:
        commands = get_commands_by_category(CommandCategory(cat))
        if not commands:
            continue

        lines.append(f"\n{cat.upper()}:")
        lines.append("")

        for cmd in commands:
            lines.append(f"  /{cmd.name} - {cmd.description}")

    lines.append("")
    lines.append("Type /help <command> for detailed help.")

    return "\n".join(lines)


# ============================================================================
# Built-in Commands
# ============================================================================

def _cmd_help(args: str, context: dict) -> str:
    """Handle /help command."""
    if args:
        # Get help for specific command
        cmd_name = args.split()[0].lstrip("/")
        cmd = get_command(cmd_name)
        if cmd:
            return get_command_help(cmd, full=True)
        return f"Unknown command: /{cmd_name}"
    return format_help()


def _cmd_status(args: str, context: dict) -> str:
    """Handle /status command."""
    from cli.cli_commands.status import show_status

    lines = ["System Status:", ""]
    lines.append("  ✓ CLI Ready")

    # TODO: Add more status info
    return "\n".join(lines)


def _cmd_clear(args: str, context: dict) -> str:
    """Handle /clear command."""
    return "__CLEAR__"


def _cmd_rollback(args: str, context: dict) -> str:
    """Handle /rollback command."""
    return "__ROLLBACK__"


def _cmd_undo(args: str, context: dict) -> str:
    """Handle /undo command."""
    return "__UNDO__"


def _cmd_exit(args: str, context: dict) -> str:
    """Handle /exit command."""
    return "__EXIT__"


def _cmd_quit(args: str, context: dict) -> str:
    """Handle /quit command."""
    return "__EXIT__"


def _cmd_skill(args: str, context: dict) -> str:
    """Handle /skill command."""
    if not args:
        return "Usage: /skill <skill_name> - Activate a skill"

    skill_name = args.strip()
    return f"__ACTIVATE_SKILL__{skill_name}"


def _cmd_model(args: str, context: dict) -> str:
    """Handle /model command."""
    if not args:
        return "Usage: /model <model_name> - Switch model"

    model_name = args.strip()
    return f"__SWITCH_MODEL__{model_name}"


def _cmd_context(args: str, context: dict) -> str:
    """Handle /context command."""
    if not args:
        return "Usage: /context <info> - Add context for current task"

    return f"__ADD_CONTEXT__{args}"


def _cmd_compress(args: str, context: dict) -> str:
    """Handle /compress command."""
    return "__COMPRESS__"


def _cmd_token(args: str, context: dict) -> str:
    """Handle /token command."""
    return "__TOKEN_COUNT__"


def _cmd_goal(args: str, context: dict) -> str:
    """Handle /goal command."""
    args = args.strip()

    # 检查是否是特殊子命令
    if args.startswith("status"):
        # 显示当前 Goal 状态
        goal_manager = _get_goal_manager()
        if goal_manager:
            return goal_manager.status_line()
        return "No active goal"

    elif args.startswith("pause"):
        # 暂停 Goal
        goal_manager = _get_goal_manager()
        if goal_manager and goal_manager.is_active():
            goal_manager.pause()
            return "Goal paused"
        return "No active goal to pause"

    elif args.startswith("resume"):
        # 恢复 Goal
        goal_manager = _get_goal_manager()
        if goal_manager and goal_manager.has_goal():
            goal_manager.resume()
            return "Goal resumed"
        return "No goal to resume"

    elif args.startswith("clear"):
        # 清除 Goal
        goal_manager = _get_goal_manager()
        if goal_manager and goal_manager.has_goal():
            goal_manager.clear()
            return "Goal cleared"
        return "No active goal"

    elif args == "":
        # 无参数，显示状态
        goal_manager = _get_goal_manager()
        if goal_manager:
            return goal_manager.status_line()
        return "No active goal. Set one with /goal <text>."

    else:
        # 创建新 Goal（剩余文本作为 Goal 内容）
        goal_text = args.strip()
        if goal_text:
            goal_manager = _get_goal_manager()
            if goal_manager:
                goal_manager.set(goal_text)
                # 返回特殊标记，通知 CLI 启动 agent 执行
                return f"__START_GOAL__{goal_text}"
        return "Usage: /goal <text>"


def _cmd_subgoal(args: str, context: dict) -> str:
    """Handle /subgoal command."""
    parts = args.strip().split(maxsplit=1)
    subcmd = parts[0] if parts else ""
    subarg = parts[1] if len(parts) > 1 else ""

    goal_manager = _get_goal_manager()
    if not goal_manager or not goal_manager.has_goal():
        return "No active goal. Use /goal <text> first."

    if not subcmd:
        return "Usage: /subgoal <text> | list | remove <n> | clear"

    if subcmd == "list":
        subgoals = goal_manager.get_subgoals()
        if not subgoals:
            return "No subgoals. Use /subgoal <text> to add one."
        lines = ["Subgoals:"]
        for i, sg in enumerate(subgoals, start=1):
            lines.append(f"  {i}. {sg}")
        return "\n".join(lines)

    elif subcmd == "remove":
        try:
            idx = int(subarg)
            removed = goal_manager.remove_subgoal(idx)
            return f"Removed subgoal {idx}: {removed[:50]}..."
        except (ValueError, IndexError) as e:
            return f"Invalid subgoal index: {e}"

    elif subcmd == "clear":
        count = goal_manager.clear_subgoals()
        return f"Cleared {count} subgoals"

    else:
        # 添加子目标
        subgoal_text = (subcmd + " " + subarg).strip()
        if subgoal_text:
            goal_manager.add_subgoal(subgoal_text)
            return f"Subgoal added: {subgoal_text[:50]}..."
        return "Usage: /subgoal <text>"


# GoalManager 实例缓存 - 使用 session_id 作为键
_goal_manager_cache: Dict[str, Any] = {}

# 今日 session 缓存，避免每次调用 get_or_create_today_session() 创建新 session
_today_session_cache: Optional[Any] = None


def _get_goal_manager():
    """获取当前会话的 GoalManager 实例（单例模式）
    
    使用 session_id 作为缓存键，确保同一会话复用同一个 GoalManager 实例。
    直接使用 session.store 来持久化 goal，避免 FileSessionStore 的路径问题。
    """
    global _today_session_cache
    
    from agent.goal import GoalManager
    from agent.session import session_manager
    from datetime import datetime

    # 检查缓存的 session 是否是今天的
    today = datetime.now().strftime("%Y%m%d")
    
    if _today_session_cache is None or not _today_session_cache.session_id.startswith(today):
        # 创建或获取今日 session
        _today_session_cache = session_manager.get_or_create_today_session()
    
    session = _today_session_cache
    session_id = session.session_id

    # 返回缓存的实例
    if session_id in _goal_manager_cache:
        return _goal_manager_cache[session_id]

    # 创建新实例并缓存
    goal_manager = GoalManager(session_id=session_id)
    
    # 直接使用 session 的 store 来持久化 goal
    goal_manager._session_db = session.store
    
    # 手动加载已有 goal（因为 GoalManager 初始化时用的不是 session.store）
    loaded_goal = goal_manager._load_goal_from_db()
    if loaded_goal:
        goal_manager._current_goal = loaded_goal
    
    _goal_manager_cache[session_id] = goal_manager
    return goal_manager


# ============================================================================
# Register Built-in Commands
# ============================================================================

# General commands
register_command(
    name="help",
    handler=_cmd_help,
    description="Show available commands",
    usage="/help or /help <command>",
    category=CommandCategory.GENERAL,
    examples=[
        "/help",
        "/help skill",
        "/help model",
    ],
    since="1.0.0",
)

register_command(
    name="status",
    handler=_cmd_status,
    description="Show system status",
    usage="/status",
    category=CommandCategory.INFO,
    since="1.0.0",
)

register_command(
    name="clear",
    handler=_cmd_clear,
    description="Clear screen",
    usage="/clear",
    category=CommandCategory.GENERAL,
    since="1.0.0",
)

register_command(
    name="exit",
    handler=_cmd_exit,
    description="Exit the CLI",
    usage="/exit",
    aliases=["quit", "q", "bye"],
    category=CommandCategory.EXIT,
    since="1.0.0",
)

register_command(
    name="quit",
    handler=_cmd_quit,
    description="Exit the CLI (alias for /exit)",
    category=CommandCategory.EXIT,
    since="1.0.0",
)

# Session commands
register_command(
    name="rollback",
    handler=_cmd_rollback,
    description="Rollback to previous checkpoint",
    usage="/rollback [steps]",
    category=CommandCategory.SESSION,
    since="1.0.0",
)

register_command(
    name="undo",
    handler=_cmd_undo,
    description="Undo last operation",
    usage="/undo",
    aliases=["u"],
    category=CommandCategory.SESSION,
    since="1.0.0",
)

# Tool commands
register_command(
    name="skill",
    handler=_cmd_skill,
    description="Activate a skill",
    usage="/skill <skill_name>",
    category=CommandCategory.TOOLS,
    since="1.0.0",
)

register_command(
    name="model",
    handler=_cmd_model,
    description="Switch model",
    usage="/model <model_name>",
    category=CommandCategory.TOOLS,
    completions=["gpt-4o", "claude-3-5-sonnet", "deepseek-v4-pro"],
    since="1.0.0",
)

register_command(
    name="context",
    handler=_cmd_context,
    description="Add context for current task",
    usage="/context <info>",
    aliases=["ctx"],
    category=CommandCategory.TOOLS,
    since="1.0.0",
)

register_command(
    name="compress",
    handler=_cmd_compress,
    description="Compress conversation history",
    usage="/compress",
    category=CommandCategory.SESSION,
    since="1.0.0",
)

register_command(
    name="token",
    handler=_cmd_token,
    description="Show token count",
    usage="/token",
    category=CommandCategory.INFO,
    since="1.0.0",
)

register_command(
    name="goal",
    handler=_cmd_goal,
    description="Manage persistent goals with Judge mechanism",
    usage="/goal <text> | /goal status | /goal pause | /goal resume | /goal clear",
    category=CommandCategory.SESSION,
    examples=[
        "/goal Implement user authentication",
        "/goal status",
        "/goal pause",
        "/goal resume",
        "/goal clear",
    ],
    since="1.0.0",
)

register_command(
    name="subgoal",
    handler=_cmd_subgoal,
    description="Manage subgoals for the active goal",
    usage="/subgoal <text> | /subgoal list | /subgoal remove <n> | /subgoal clear",
    category=CommandCategory.SESSION,
    examples=[
        "/subgoal Add login form",
        "/subgoal list",
        "/subgoal remove 1",
        "/subgoal clear",
    ],
    since="1.0.0",
)


# ============================================================================
# Public API
# ============================================================================

def parse_command(input_str: str) -> tuple[str, str]:
    """Parse a command string into (command, args).

    Args:
        input_str: Input string (e.g., "/help foo bar")

    Returns:
        Tuple of (command_name, args_string)
    """
    input_str = input_str.strip()
    if not input_str.startswith("/"):
        return "", ""

    parts = input_str.split(None, 1)
    command = parts[0][1:]  # Remove leading slash
    args = parts[1] if len(parts) > 1 else ""

    return command, args


def execute_command(input_str: str, context: dict) -> str:
    """Execute a command string.

    Args:
        input_str: Input string (e.g., "/help")
        context: Context dict with session info

    Returns:
        Command output or special markers (e.g., "__CLEAR__")
    """
    command, args = parse_command(input_str)
    if not command:
        return ""

    cmd_def = get_command(command)
    if not cmd_def:
        return f"Unknown command: /{command}. Type /help for available commands."

    # Check if it's a subcommand
    if args and cmd_def.subcommands:
        sub_name = args.split()[0]
        if sub_name in cmd_def.subcommands:
            sub = cmd_def.subcommands[sub_name]
            if sub.handler:
                return sub.handler(args[len(sub_name):].strip(), context)
            return f"Sub-command not implemented: {command} {sub_name}"

    return cmd_def.handler(args, context)


# ============================================================================
# Autocomplete Support
# ============================================================================

def get_completions(
    partial: str,
    context: Optional[dict] = None,
) -> List[str]:
    """Get command completions for a partial command string.

    Args:
        partial: Partial command string (e.g., "/he")
        context: Optional context for dynamic completions

    Returns:
        List of matching command names
    """
    if not partial.startswith("/"):
        # Complete command names without slash
        prefix = partial.lstrip("/")
        matches = []

        for name in COMMAND_REGISTRY:
            # Skip aliases (duplicates)
            cmd = COMMAND_REGISTRY[name]
            if name in cmd.aliases:
                continue

            if name.startswith(prefix):
                matches.append(f"/{name}")

        return matches[:10]  # Limit to 10 completions

    prefix = partial[1:]  # Remove leading slash

    # Check for subcommand completion
    if " " in partial:
        parts = partial.split(" ", 1)
        cmd_name = parts[0][1:]
        sub_prefix = parts[1] if len(parts) > 1 else ""

        cmd = get_command(cmd_name)
        if cmd and cmd.subcommands:
            matches = []
            for sub_name in cmd.subcommands:
                if sub_name.startswith(sub_prefix):
                    matches.append(f"/{cmd_name} {sub_name}")
            return matches[:10]

        # Check custom completions
        if cmd and cmd.completions:
            matches = []
            for comp in cmd.completions:
                if comp.startswith(sub_prefix):
                    matches.append(f"/{cmd_name} {comp}")
            return matches[:10]

        return []

    # Main command completion
    matches = []
    seen = set()

    for name in COMMAND_REGISTRY:
        cmd = COMMAND_REGISTRY[name]

        # Skip aliases and duplicates
        if name in cmd.aliases or name in seen:
            continue
        seen.add(name)

        if name.startswith(prefix):
            matches.append(f"/{name}")

    return matches[:10]


def get_command_suggestions(
    current: str,
    history: Optional[List[str]] = None,
) -> List[str]:
    """Get intelligent command suggestions based on history.

    Args:
        current: Current input
        history: Command history

    Returns:
        List of suggested commands
    """
    suggestions = []

    if not current.startswith("/"):
        return suggestions

    # Suggest recent commands with same prefix
    if history:
        prefix = current.lower()
        for cmd in reversed(history):
            if cmd.lower().startswith(prefix):
                suggestions.append(cmd)
                if len(suggestions) >= 3:
                    break

    # Always suggest /help if partial matches
    if not suggestions:
        suggestions = get_completions(current)

    return suggestions


# ============================================================================
# Platform-specific Commands
# ============================================================================

def get_platform_commands(platform: str) -> List[CommandDef]:
    """Get commands for a specific platform.

    Args:
        platform: Platform name (e.g., "telegram", "discord")

    Returns:
        List of platform-specific commands
    """
    command_names = PLATFORM_COMMANDS.get(platform, [])
    return [COMMAND_REGISTRY[name] for name in command_names if name in COMMAND_REGISTRY]


if __name__ == "__main__":
    # Test commands
    print("Registered commands by category:")
    for cat in get_categories():
        print(f"\n  {cat.upper()}:")
        commands = get_commands_by_category(CommandCategory(cat))
        for cmd in commands:
            print(f"    /{cmd.name}: {cmd.description}")

    print("\n" + "=" * 50)
    print("Parse test:")
    cmd, args = parse_command("/help foo bar")
    print(f"  '/help foo bar' -> command='{cmd}', args='{args}'")

    print("\nCompletions test:")
    completions = get_completions("/he")
    print(f"  '/he' -> {completions}")

    completions = get_completions("/skill ")
    print(f"  '/skill ' -> {completions}")

    print("\nHelp test:")
    cmd = get_command("help")
    if cmd:
        print(get_command_help(cmd))
