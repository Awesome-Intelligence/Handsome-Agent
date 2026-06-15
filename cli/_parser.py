#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Top-level argparse construction for the Handsome Agent CLI.

Lives in its own module so other modules (e.g. `relaunch.py`) can
introspect the parser to discover which flags exist without running
the `main` fn.

🚪 Access - 💬 CLI - 参数解析器

Only the top-level parser and the `chat` subparser live here. Every other
subparser (model, skills, setup, ...) is built inline in `main.py`
because its dispatch is tightly coupled to module-level `cmd_*` functions.
"""

import argparse

# `--profile` / `-p` is consumed by the profile system before
# argparse runs (it sets HANDSOME_HOME and strips itself from `sys.argv`),
# so it isn't on the parser. Listed here so all "carry over on relaunch"
# metadata lives in one file.
PRE_ARGPARSE_INHERITED_FLAGS: list[tuple[str, bool]] = [
    ("--profile", True),
    ("-p", True),
]


def _inherited_flag(parser, *args, **kwargs):
    """Register a flag that should be carried over when the CLI re-execs itself.

    Equivalent to ``parser.add_argument(...)`` plus tagging the resulting
    Action with ``inherit_on_relaunch = True`` so the relaunch table builder
    can find it via introspection.
    """
    action = parser.add_argument(*args, **kwargs)
    action.inherit_on_relaunch = True
    return action


_EPILOGUE = """
Examples:
    handsome                     Start interactive chat
    handsome chat -q "Hello"     Single query mode
    handsome setup               Run setup wizard
    handsome status              Show system status
    handsome model               Select default model
    handsome skills              Manage skills
    handsome config              View configuration
    handsome config edit         Edit config in $EDITOR
    handsome config set model    Set a config value

For more help on a command:
    handsome <command> --help
"""


def build_top_level_parser():
    """Build the top-level parser, the subparsers action, and the `chat` subparser.

    Returns ``(parser, subparsers, chat_parser)``. The caller wires
    ``chat_parser.set_defaults(func=cmd_chat)`` and continues registering
    other subparsers via ``subparsers.add_parser(...)``.
    """
    parser = argparse.ArgumentParser(
        prog="handsome",
        description="Handsome Agent - AI assistant with tool-calling capabilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EPILOGUE,
    )

    # =========================================================================
    # Top-level arguments
    # =========================================================================
    parser.add_argument(
        "--version", "-V", action="store_true", help="Show version and exit"
    )
    parser.add_argument(
        "-z",
        "--oneshot",
        metavar="PROMPT",
        default=None,
        help=(
            "One-shot mode: send a single prompt and print ONLY the final "
            "response text to stdout. No banner, no spinner, no tool "
            "previews. Tools, memory, and skills are loaded as normal; "
            "approvals are auto-bypassed. Intended for scripts / pipes."
        ),
    )
    # --model / --provider are accepted at the top level so they can pair
    # with -z without needing the `chat` subcommand.
    _inherited_flag(
        parser,
        "-m",
        "--model",
        default=None,
        help="Model override for this invocation (e.g. gpt-4o, deepseek-v4-pro).",
    )
    _inherited_flag(
        parser,
        "--provider",
        default=None,
        help="Provider override for this invocation (e.g. openai, deepseek).",
    )
    parser.add_argument(
        "-t",
        "--toolsets",
        default=None,
        help="Comma-separated toolsets to enable for this invocation.",
    )
    parser.add_argument(
        "--resume",
        "-r",
        metavar="SESSION",
        default=None,
        help="Resume a previous session by ID or title",
    )
    parser.add_argument(
        "--continue",
        "-c",
        dest="continue_last",
        nargs="?",
        const=True,
        default=None,
        metavar="SESSION_NAME",
        help="Resume a session by name, or the most recent if no name given",
    )
    _inherited_flag(
        parser,
        "--skills",
        "-s",
        action="append",
        default=None,
        help="Preload one or more skills for the session (repeat flag or comma-separate)",
    )
    _inherited_flag(
        parser,
        "--yolo",
        action="store_true",
        default=False,
        help="Bypass all dangerous command approval prompts (use at your own risk)",
    )
    _inherited_flag(
        parser,
        "--ignore-user-config",
        action="store_true",
        default=False,
        help="Ignore config.yaml and fall back to built-in defaults",
    )
    _inherited_flag(
        parser,
        "--ignore-rules",
        action="store_true",
        default=False,
        help="Skip auto-injection of AGENTS.md, SOUL.md, and preloaded skills",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Verbose output",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        help="Quiet mode: suppress banner, spinner, and tool previews.",
    )
    parser.add_argument(
        "--textual",
        action="store_true",
        default=False,
        help="Use Textual TUI (modern terminal UI)",
    )
    parser.add_argument(
        "--no-textual",
        action="store_true",
        default=False,
        help="Disable Textual TUI, use traditional CLI",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # =========================================================================
    # chat command
    # =========================================================================
    chat_parser = subparsers.add_parser(
        "chat",
        help="Interactive chat with the agent",
        description="Start an interactive chat session with Handsome Agent",
    )
    chat_parser.add_argument(
        "--query", help="Single query (non-interactive mode)"
    )
    chat_parser.add_argument(
        "--image", help="Optional local image path to attach to a single query"
    )
    _inherited_flag(
        chat_parser,
        "-m", "--model", help="Model to use (e.g., gpt-4o, deepseek-v4-pro)",
    )
    chat_parser.add_argument(
        "-t", "--toolsets", help="Comma-separated toolsets to enable"
    )
    _inherited_flag(
        chat_parser,
        "-s",
        "--skills",
        action="append",
        default=argparse.SUPPRESS,
        help="Preload one or more skills for the session",
    )
    _inherited_flag(
        chat_parser,
        "--provider",
        default=None,
        help="Inference provider (default: auto).",
    )
    chat_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Verbose output",
    )
    chat_parser.add_argument(
        "-Q",
        "--quiet",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Quiet mode: suppress banner, spinner, and tool previews.",
    )
    chat_parser.add_argument(
        "--resume",
        "-r",
        metavar="SESSION_ID",
        default=argparse.SUPPRESS,
        help="Resume a previous session by ID",
    )
    chat_parser.add_argument(
        "--continue",
        "-c",
        dest="continue_last",
        nargs="?",
        const=True,
        default=argparse.SUPPRESS,
        metavar="SESSION_NAME",
        help="Resume a session by name, or the most recent if no name given",
    )
    _inherited_flag(
        chat_parser,
        "--yolo",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Bypass all dangerous command approval prompts",
    )
    _inherited_flag(
        chat_parser,
        "--ignore-user-config",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Ignore config.yaml and fall back to built-in defaults",
    )
    _inherited_flag(
        chat_parser,
        "--ignore-rules",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Skip auto-injection of AGENTS.md, SOUL.md, and preloaded skills",
    )
    chat_parser.add_argument(
        "--checkpoints",
        action="store_true",
        default=False,
        help="Enable filesystem checkpoints before destructive operations",
    )
    chat_parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        metavar="N",
        help="Maximum tool-calling iterations per conversation turn (default: 90)",
    )
    chat_parser.add_argument(
        "--compress",
        action="store_true",
        default=False,
        help="Compress context before starting chat",
    )
    chat_parser.add_argument(
        "--usage",
        action="store_true",
        default=False,
        help="Show token usage statistics",
    )

    # =========================================================================
    # setup command
    # =========================================================================
    setup_parser = subparsers.add_parser(
        "setup",
        help="Run setup wizard",
        description="Interactive configuration wizard",
    )
    setup_parser.add_argument(
        "--quick",
        action="store_true",
        default=False,
        help="Run quick setup (only essential options)",
    )
    setup_parser.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="Run full setup (all options)",
    )

    # =========================================================================
    # status command
    # =========================================================================
    status_parser = subparsers.add_parser(
        "status",
        help="Show system status",
        description="Display system configuration and status",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output as JSON",
    )
    status_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Show detailed status",
    )

    # =========================================================================
    # model command
    # =========================================================================
    model_parser = subparsers.add_parser(
        "model",
        help="Model management",
        description="Select and manage models",
    )
    model_subparsers = model_parser.add_subparsers(dest="model_command", help="Model command")

    model_list_parser = model_subparsers.add_parser(
        "list",
        help="List available models",
    )
    model_list_parser.add_argument(
        "--provider",
        default=None,
        help="Filter by provider",
    )
    model_list_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output as JSON",
    )

    model_set_parser = model_subparsers.add_parser(
        "set",
        help="Set default model",
    )
    model_set_parser.add_argument(
        "model_name",
        help="Model name (e.g., gpt-4o)",
    )
    model_set_parser.add_argument(
        "--provider",
        default=None,
        help="Provider name",
    )

    # =========================================================================
    # skills command
    # =========================================================================
    skills_parser = subparsers.add_parser(
        "skills",
        help="Skills management",
        description="Manage skills and bundles",
    )
    skills_subparsers = skills_parser.add_subparsers(dest="skills_command", help="Skills command")

    skills_list_parser = skills_subparsers.add_parser(
        "list",
        help="List available skills",
    )
    skills_list_parser.add_argument(
        "--installed",
        action="store_true",
        default=False,
        help="Show only installed skills",
    )
    skills_list_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output as JSON",
    )

    skills_search_parser = skills_subparsers.add_parser(
        "search",
        help="Search for skills",
    )
    skills_search_parser.add_argument(
        "query",
        help="Search query",
    )

    # =========================================================================
    # config command
    # =========================================================================
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="View and edit configuration",
    )
    config_subparsers = config_parser.add_subparsers(dest="config_command", help="Config command")

    config_show_parser = config_subparsers.add_parser(
        "show",
        help="Show current configuration",
    )
    config_show_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output as JSON",
    )

    config_edit_parser = config_subparsers.add_parser(
        "edit",
        help="Edit configuration in $EDITOR",
    )

    config_set_parser = config_subparsers.add_parser(
        "set",
        help="Set a configuration value",
    )
    config_set_parser.add_argument(
        "key",
        help="Configuration key (e.g., model.provider)",
    )
    config_set_parser.add_argument(
        "value",
        help="Configuration value",
    )

    config_get_parser = config_subparsers.add_parser(
        "get",
        help="Get a configuration value",
    )
    config_get_parser.add_argument(
        "key",
        help="Configuration key (e.g., model.provider)",
    )

    # =========================================================================
    # logs command
    # =========================================================================
    logs_parser = subparsers.add_parser(
        "logs",
        help="View logs",
        description="View Handsome Agent logs",
    )
    logs_parser.add_argument(
        "-n", "--lines",
        type=int,
        default=50,
        help="Number of lines to show",
    )
    logs_parser.add_argument(
        "-l", "--level",
        choices=["debug", "info", "warning", "error"],
        help="Filter by log level",
    )
    logs_parser.add_argument(
        "-s", "--search",
        help="Search keyword",
    )
    logs_parser.add_argument(
        "-f", "--follow",
        action="store_true",
        help="Follow log (like tail -f)",
    )

    # =========================================================================
    # gateway command
    # =========================================================================
    gateway_parser = subparsers.add_parser(
        "gateway",
        help="Gateway service management",
        description="Start, stop, or check gateway status",
    )
    gateway_subparsers = gateway_parser.add_subparsers(dest="gateway_command", help="Gateway command")

    gateway_start_parser = gateway_subparsers.add_parser("start", help="Start gateway")
    gateway_stop_parser = gateway_subparsers.add_parser("stop", help="Stop gateway")
    gateway_status_parser = gateway_subparsers.add_parser("status", help="Check gateway status")
    gateway_restart_parser = gateway_subparsers.add_parser("restart", help="Restart gateway")

    # =========================================================================
    # cron command
    # =========================================================================
    cron_parser = subparsers.add_parser(
        "cron",
        help="Cron job management",
        description="List and manage cron jobs",
    )
    cron_subparsers = cron_parser.add_subparsers(dest="cron_command", help="Cron command")

    cron_list_parser = cron_subparsers.add_parser("list", help="List cron jobs")
    cron_list_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output as JSON",
    )
    cron_status_parser = cron_subparsers.add_parser("status", help="Check cron status")

    # =========================================================================
    # acp command
    # =========================================================================
    acp_parser = subparsers.add_parser(
        "acp",
        help="ACP server management",
        description="Start, stop, or check ACP server status (Editor Integration)",
    )
    acp_subparsers = acp_parser.add_subparsers(dest="acp_command", help="ACP command")

    acp_start_parser = acp_subparsers.add_parser("start", help="Start ACP server")
    acp_stop_parser = acp_subparsers.add_parser("stop", help="Stop ACP server")
    acp_status_parser = acp_subparsers.add_parser("status", help="Check ACP server status")

    # =========================================================================
    # sessions command (extend)
    # =========================================================================
    # Note: sessions_parser should already exist from earlier code
    # Add recap subcommand to existing sessions parser
    sessions_parser = subparsers.add_parser(
        "sessions",
        help="Session management",
        description="Manage chat sessions",
    )
    sessions_subparsers = sessions_parser.add_subparsers(dest="sessions_subcommand", help="Sessions command")

    sessions_list_parser = sessions_subparsers.add_parser(
        "list",
        help="List all sessions",
    )
    sessions_list_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output as JSON",
    )

    sessions_browse_parser = sessions_subparsers.add_parser(
        "browse",
        help="Browse sessions interactively",
    )
    sessions_browse_parser.add_argument(
        "--tui",
        action="store_true",
        help="Use TUI picker",
    )

    sessions_recap_parser = sessions_subparsers.add_parser(
        "recap",
        help="Generate session recap",
    )
    sessions_recap_parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID (default: last session)",
    )
    sessions_recap_parser.add_argument(
        "-f", "--format",
        choices=["markdown", "text", "json"],
        default="markdown",
        help="Output format",
    )

    # =========================================================================
    # uninstall command
    # =========================================================================
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Uninstall Handsome Agent",
        description="Remove configuration and uninstall agent",
    )
    uninstall_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Skip confirmation",
    )
    uninstall_parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup before uninstall",
    )
    uninstall_subparsers = uninstall_parser.add_subparsers(dest="uninstall_action", help="Uninstall action")
    uninstall_subparsers.add_parser("backup", help="Create backup")
    uninstall_restore_parser = uninstall_subparsers.add_parser("restore", help="Restore from backup")
    uninstall_restore_parser.add_argument(
        "backup_path",
        nargs="?",
        help="Backup file path",
    )
    uninstall_subparsers.add_parser("list", help="List available backups")

    # =========================================================================
    # doctor command (already exists)
    # =========================================================================
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run diagnostic checks",
        description="Check system configuration and dependencies",
    )
    doctor_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Verbose output",
    )

    # =========================================================================
    # providers command
    # =========================================================================
    providers_parser = subparsers.add_parser(
        "providers",
        help="Provider management",
        description="List and manage LLM providers",
    )
    providers_subparsers = providers_parser.add_subparsers(dest="providers_command", help="Provider command")

    providers_list_parser = providers_subparsers.add_parser("list", help="List all providers")
    providers_list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    providers_info_parser = providers_subparsers.add_parser("info", help="Show provider info")
    providers_info_parser.add_argument("provider_id", help="Provider ID")

    providers_status_parser = providers_subparsers.add_parser("status", help="Check provider status")
    providers_status_parser.add_argument("provider_id", nargs="?", help="Provider ID (optional)")

    # =========================================================================
    # models command
    # =========================================================================
    models_parser = subparsers.add_parser(
        "models",
        help="Model catalog",
        description="List and compare models",
    )
    models_subparsers = models_parser.add_subparsers(dest="models_command", help="Model command")

    models_list_parser = models_subparsers.add_parser("list", help="List all models")
    models_list_parser.add_argument("--provider", help="Filter by provider")
    models_list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    models_info_parser = models_subparsers.add_parser("info", help="Show model info")
    models_info_parser.add_argument("model_id", help="Model ID")

    models_compare_parser = models_subparsers.add_parser("compare", help="Compare two models")
    models_compare_parser.add_argument("model1", help="First model ID")
    models_compare_parser.add_argument("model2", help="Second model ID")

    # =========================================================================
    # profiles command
    # =========================================================================
    profiles_parser = subparsers.add_parser(
        "profiles",
        help="Profile management",
        description="Manage configuration profiles",
    )
    profiles_subparsers = profiles_parser.add_subparsers(dest="profiles_command", help="Profile command")

    profiles_list_parser = profiles_subparsers.add_parser("list", help="List profiles")
    profiles_list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    profiles_create_parser = profiles_subparsers.add_parser("create", help="Create profile")
    profiles_create_parser.add_argument("name", help="Profile name")
    profiles_create_parser.add_argument("--copy", help="Copy from profile")

    profiles_switch_parser = profiles_subparsers.add_parser("switch", help="Switch profile")
    profiles_switch_parser.add_argument("name", help="Profile name")

    profiles_delete_parser = profiles_subparsers.add_parser("delete", help="Delete profile")
    profiles_delete_parser.add_argument("name", help="Profile name")
    profiles_delete_parser.add_argument("-f", "--force", action="store_true", help="Force delete")

    # =========================================================================
    # backup command
    # =========================================================================
    backup_parser = subparsers.add_parser(
        "backup",
        help="Backup management",
        description="Create and restore backups",
    )
    backup_subparsers = backup_parser.add_subparsers(dest="backup_command", help="Backup command")

    backup_create_parser = backup_subparsers.add_parser("create", help="Create backup")
    backup_create_parser.add_argument("--name", help="Backup name")

    backup_list_parser = backup_subparsers.add_parser("list", help="List backups")
    backup_list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    backup_restore_parser = backup_subparsers.add_parser("restore", help="Restore backup")
    backup_restore_parser.add_argument("backup_id", help="Backup ID")
    backup_restore_parser.add_argument("-f", "--force", action="store_true", help="Force restore")

    backup_delete_parser = backup_subparsers.add_parser("delete", help="Delete backup")
    backup_delete_parser.add_argument("backup_id", help="Backup ID")

    # =========================================================================
    # auth command
    # =========================================================================
    auth_parser = subparsers.add_parser(
        "auth",
        help="Authentication management",
        description="Manage API keys and credentials",
    )
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command", help="Auth command")

    auth_add_parser = auth_subparsers.add_parser("add", help="Add credential")
    auth_add_parser.add_argument("provider", help="Provider ID")
    auth_add_parser.add_argument("api_key", help="API Key")

    auth_list_parser = auth_subparsers.add_parser("list", help="List credentials")
    auth_list_parser.add_argument("--json", action="store_true", help="Output as JSON")

    auth_delete_parser = auth_subparsers.add_parser("delete", help="Delete credential")
    auth_delete_parser.add_argument("provider", help="Provider ID")

    auth_test_parser = auth_subparsers.add_parser("test", help="Test connection")
    auth_test_parser.add_argument("provider", help="Provider ID")

    return parser, subparsers, chat_parser