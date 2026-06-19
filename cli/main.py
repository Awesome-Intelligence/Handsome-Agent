#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Handsome Agent

Provides Text User Interface for testing and interaction.
Updated to use the new _parser.py and commands.py modules.

🚪 Access - 💬 CLI - 主入口

参考 Hermes 的 main.py 设计，使用统一的参数解析器。
"""

# 首先 patch Textual 的 LayerLogger（在任何导入之前）
def _patch_textual_logger():
    """Patch Textual's LayerLogger for compatibility."""
    try:
        from textual._log import LayerLogger
        LayerLogger.system = lambda *args, **kwargs: None
        LayerLogger.info = lambda *args, **kwargs: None
        LayerLogger.debug = lambda *args, **kwargs: None
        LayerLogger.warning = lambda *args, **kwargs: None
        LayerLogger.error = lambda *args, **kwargs: None
        LayerLogger.critical = lambda *args, **kwargs: None
    except ImportError:
        pass

_patch_textual_logger()

import asyncio
import argparse
import sys
import os
import json
import logging

from agent.context.compression_commands import (
    is_compression_command,
    parse_compression_command,
    handle_compress_command,
    handle_usage_command,
    handle_status_command,
)
from agent.context.compression_integration import CompressionIntegration

# 首先解析命令行参数，以便在导入其他模块之前配置日志
_pre_parser = argparse.ArgumentParser(add_help=False)
_pre_parser.add_argument(
    "--explanation-depth",
    choices=["brief", "moderate", "detailed"],
    default="detailed",
    help="Level of detail in explanations"
)
_args, _ = _pre_parser.parse_known_args()

# 检查日志是否已经被配置
_logging_already_configured = False
if len(logging.root.handlers) > 0:
    for handler in logging.root.handlers:
        if not isinstance(handler, logging.NullHandler):
            _logging_already_configured = True
            break

if not _logging_already_configured:
    # 日志尚未被配置，需要设置
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.root.addHandler(logging.NullHandler())
    logging.root.setLevel(logging.CRITICAL + 1)

# 导入 Agent
from agent.agent import Agent, AgentResponse
from common.exceptions import AgentError, InputValidationError, ResponseGenerationError
from common.logging_manager import get_access_logger

# 常量
CONFIG_FILE = os.path.expanduser("~/.handsome_agent/config.json")

# LLM 可用性检测
LLM_AVAILABLE = False
try:
    from llm_integration import LLMConfig, setup_llm_integration
    LLM_AVAILABLE = True
except ImportError:
    pass


def load_saved_config() -> dict:
    """Load saved configuration from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def has_existing_config() -> bool:
    """Check if configuration file exists."""
    return os.path.exists(CONFIG_FILE)


def run_setup_if_needed():
    """Run setup wizard if no configuration exists."""
    from cli import ui

    # 初始化工作空间
    from agent.session import session_manager

    workspace_manager = get_workspace_manager()
    is_first_run = not workspace_manager.is_workspace_setup_completed()

    if is_first_run:
        ui.print_header("🎉 欢迎使用 Handsome Agent")
        print()
        ui.print_info("正在初始化工作空间...")

        workspace_manager.ensure_workspace()

        ui.print_success(f"工作空间已创建: {workspace_manager.workspace_dir}")
        ui.print_info("配置文件已复制到工作空间，您可以随时修改")
        print()

        workspace_manager.mark_setup_complete()

    if not has_existing_config():
        ui.print_header("首次运行 Handsome Agent")
        print()
        ui.print_info("提示: 运行 'python -m cli.main --setup' 可配置大模型")
        ui.print_info("使用 --query 参数可跳过设置直接查询")
        print()


def get_workspace_manager():
    """Get workspace manager instance."""
    from agent.workspace import get_workspace_manager as _get_workspace_manager
    return _get_workspace_manager()


# ============================================================================
# Mode Functions
# ============================================================================

async def interactive_mode(agent: Agent, model_name: str = "Agent"):
    """Run the agent in interactive mode.

    Args:
        agent: The Agent instance to use for processing user input.
        model_name: Name of the model to display in status bar.
    """
    # 🚪 Access - 💬 CLI - 初始化 CLI 日志记录器
    logger = get_access_logger("CLI", sublayer="cli")
    logger.info("Interactive mode started")
    
    from cli import ui
    from cli.banner import build_welcome_banner, print_simple_banner
    from cli.commands import execute_command

    # 初始化压缩集成器
    compression_integration = None
    if hasattr(agent, 'llm_provider') and agent.llm_provider:
        try:
            compression_integration = CompressionIntegration(
                session_id=agent._session.session_id if agent._session else "cli",
                model=model_name,
                llm_client=agent.llm_provider,
            )
        except Exception:
            pass

    # 使用增强的 Banner 显示欢迎界面
    try:
        config_status = {
            "llm_configured": bool(agent.llm_provider),
            "tools_configured": True,
        }

        # 获取配置信息
        provider = None
        context_length = None
        try:
            from common.config import load_config
            cfg = load_config()
            if cfg.get('llm', {}).get('provider'):
                provider = cfg.get('llm', {}).get('provider')
            if cfg.get('model', {}).get('context_window'):
                context_length = cfg.get('model', {}).get('context_window')
        except:
            pass

        build_welcome_banner(
            model=model_name,
            provider=provider,
            cwd=os.getcwd(),
            tools_count=4,
            skills_count=0,
            context_length=context_length,
            config_status=config_status,
        )
    except Exception:
        print_simple_banner()

    # Initialize status bar
    ui.status_bar.update_model(model_name)
    ui.status_bar.set_tools(["file", "terminal", "web", "app-launcher"])
    ui.print_status_bar()

    print()

    # 显示压缩命令帮助
    if compression_integration:
        print("  Commands:")
        print("    /compress              - 手动压缩上下文")
        print("    /compress --focus=X    - 聚焦压缩")
        print("    /usage                - 显示 Token 使用统计")
        print("    /compression-status   - 显示压缩功能状态")
        print()

    # Command context
    context = {"agent": agent, "model_name": model_name}

    while True:
        try:
            ui.print_user_input()
            user_input = input().strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                logger.info("Interactive mode ended")
                ui.print_success("再见!")
                break

            if not user_input:
                continue

            # 🚪 Access - 💬 CLI - 记录用户输入
            logger.info(f"User input: {user_input[:50]}...")

            # Check for slash commands
            if user_input.startswith('/'):
                result = execute_command(user_input, context)

                # Handle special markers
                if result == "__CLEAR__":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue
                elif result == "__ROLLBACK__":
                    ui.print_info("Rolling back to previous checkpoint...")
                    # TODO: Implement rollback
                    continue
                elif result.startswith("__ACTIVATE_SKILL__"):
                    skill_name = result[len("__ACTIVATE_SKILL__"):]
                    ui.print_success(f"Activating skill: {skill_name}")
                    continue
                elif result.startswith("__SWITCH_MODEL__"):
                    new_model = result[len("__SWITCH_MODEL__"):]
                    ui.print_success(f"Switching to model: {new_model}")
                    # TODO: Implement model switch
                    continue
                elif result.startswith("__ADD_CONTEXT__"):
                    context_info = result[len("__ADD_CONTEXT__"):]
                    ui.print_info(f"Added context: {context_info}")
                    continue

                # Regular command output
                if result:
                    print(result)
                continue

            # Handle context compression commands
            if is_compression_command(user_input):
                command, args = parse_compression_command(user_input)
                if command == "/compress":
                    result = handle_compress_command(
                        agent._session.session_id if agent._session else "cli",
                        args,
                        compression_integration,
                    )
                    ui.print_info(result.get('message', '压缩命令执行完成'))
                elif command == "/usage":
                    result = handle_usage_command(
                        agent._session.session_id if agent._session else "cli",
                        compression_integration,
                    )
                    print(result.get('message', ''))
                elif command == "/compression-status":
                    result = handle_status_command(
                        agent._session.session_id if agent._session else "cli",
                        compression_integration,
                    )
                    print(result.get('message', ''))
                continue

            # Show processing indicator (spinner will output directly without extra newline)
            spinner = ui.Spinner("思考中...")
            spinner.start()

            try:
                response = await agent.chat(user_input)

                # Update status bar with token info
                ui.status_bar.add_tokens(len(response.content.split()))

                # Clear spinner line
                print("\r" + " " * 50 + "\r", end="", flush=True)

                # 🚪 Access - 💬 CLI - 记录 Agent 响应（打印在响应内容之前）
                logger.info(f"Agent response: {response.content[:100]}...")

                # If a tool was used, show that info
                if response.tool_used:
                    ui.print_info(f"🔧 Used tool: {response.tool_used}")

                ui.print_agent_response(response.content, response.confidence_score)

                # Show updated status
                ui.print_status_bar()
            finally:
                pass

        except KeyboardInterrupt:
            print()
            logger.info("Interactive mode ended (KeyboardInterrupt)")
            ui.print_success("再见!")
            break
        except EOFError:
            print()
            logger.info("Interactive mode ended (EOF)")
            ui.print_success("再见!")
            break
        except Exception as e:
            logger.error(f"Interactive mode error: {e}")
            ui.print_error(f"错误: {e}")


async def single_query_mode(agent: Agent, query: str, model_name: str = "Agent"):
    """Run the agent with a single query.

    Args:
        agent: The Agent instance to use.
        query: The user's query string.
        model_name: Name of the model to display in status bar.
    """
    # 🚪 Access - 💬 CLI - 初始化 CLI 日志记录器
    logger = get_access_logger("CLI", sublayer="cli")
    logger.info(f"Single query mode started: {query[:50]}...")
    
    from cli import ui
    from cli.banner import print_simple_banner

    print_simple_banner()

    # Initialize status bar
    ui.status_bar.update_model(model_name)
    ui.print_status_bar()

    ui.print_header("查询结果", f"Query: {query[:50]}{'...' if len(query) > 50 else ''}")

    try:
        # Show processing indicator
        spinner = ui.Spinner("思考中...")
        spinner.start()

        try:
            response = await agent.chat(query)

            # Clear spinner line
            print("\r" + " " * 50 + "\r", end="", flush=True)

            # If a tool was used, show that info
            if response.tool_used:
                ui.print_info(f"🔧 Used tool: {response.tool_used}")

            ui.print_agent_response(response.content, response.confidence_score)
            
            # 🚪 Access - 💬 CLI - 记录 Agent 响应
            logger.info(f"Agent response: {response.content[:100]}...")
            logger.info("Single query mode completed")
        finally:
            pass

    except Exception as e:
        logger.error(f"Single query mode failed: {e}")
        ui.print_error(f"错误: {e}")


def list_sessions():
    """List all sessions."""
    from agent.session import session_manager

    sessions = session_manager.list_sessions()

    if not sessions:
        print("No sessions found.")
        return

    print("Available sessions:")
    for session_id in sessions:
        print(f"  - {session_id}")


# ============================================================================
# Command Handlers
# ============================================================================

def cmd_setup(args: argparse.Namespace):
    """Handle setup command."""
    from cli.setup import run_setup_wizard, run_quick_config_wizard

    if args.quick:
        run_quick_config_wizard()
    else:
        run_setup_wizard()


def cmd_status(args: argparse.Namespace):
    """Handle status command."""
    from cli.status import show_status

    show_status(verbose=args.verbose, json_output=args.json)


def cmd_model_list(args: argparse.Namespace):
    """Handle 'model list' command."""
    from cli.model_cli import list_models

    list_models(provider=args.provider, json_output=args.json)


def cmd_model_set(args: argparse.Namespace):
    """Handle 'model set' command."""
    from cli.model_cli import set_default_model

    set_default_model(args.model_name, provider=args.provider)


def cmd_skills_list(args: argparse.Namespace):
    """Handle 'skills list' command."""
    from cli.skills_cli import list_skills

    list_skills(only_installed=args.installed, json_output=args.json)


def cmd_skills_search(args: argparse.Namespace):
    """Handle 'skills search' command."""
    from cli.skills_cli import search_skills

    search_skills(args.query)


def cmd_config_show(args: argparse.Namespace):
    """Handle 'config show' command."""
    from cli.config_cli import show_config

    show_config(json_output=args.json)


def cmd_config_edit(args: argparse.Namespace):
    """Handle 'config edit' command."""
    from cli.config_cli import edit_config

    edit_config()


def cmd_config_set(args: argparse.Namespace):
    """Handle 'config set' command."""
    from cli.config_cli import set_config

    set_config(args.key, args.value)


def cmd_config_get(args: argparse.Namespace):
    """Handle 'config get' command."""
    from cli.config_cli import get_config

    get_config(args.key)


def cmd_logs(args: argparse.Namespace):
    """Handle 'logs' command."""
    from cli.cli_commands.logs import show_logs, tail_logs

    if args.follow:
        tail_logs(args.lines)
    else:
        show_logs(lines=args.lines, level=args.level, search=args.search)


def cmd_gateway(args: argparse.Namespace):
    """Handle 'gateway' command."""
    from cli.cli_commands.gateway import (
        start_gateway,
        stop_gateway,
        check_gateway_status,
        restart_gateway,
    )

    if args.gateway_command == "start":
        start_gateway()
    elif args.gateway_command == "stop":
        stop_gateway()
    elif args.gateway_command == "status":
        check_gateway_status()
    elif args.gateway_command == "restart":
        restart_gateway()
    else:
        # Default: show status
        check_gateway_status()


def cmd_cron(args: argparse.Namespace):
    """Handle 'cron' command."""
    from cli.cli_commands.cron import list_cron_jobs, check_cron_status

    if args.cron_command == "list":
        list_cron_jobs(json_output=args.json)
    elif args.cron_command == "status":
        check_cron_status()
    else:
        # Default: show list
        list_cron_jobs()


def cmd_acp(args: argparse.Namespace):
    """Handle 'acp' command."""
    from cli.cli_commands.acp import (
        start_acp_server,
        stop_acp_server,
        check_acp_status,
    )

    if args.acp_command == "start":
        start_acp_server()
    elif args.acp_command == "stop":
        stop_acp_server()
    elif args.acp_command == "status":
        check_acp_status()
    else:
        # Default: show status
        check_acp_status()


def cmd_sessions(args: argparse.Namespace):
    """Handle 'sessions' command."""
    from cli.cli_commands.sessions import list_sessions, browse_sessions

    if args.sessions_subcommand == "list":
        list_sessions(json_output=args.json)
    elif args.sessions_subcommand == "browse":
        session_id = browse_sessions(tui=args.tui)
        if session_id:
            print(f"Selected session: {session_id}")
    elif args.sessions_subcommand == "recap":
        from cli.cli_commands.session_recap import generate_session_recap
        generate_session_recap(session_id=args.session_id, format=args.format)
    else:
        # Default: show list
        list_sessions()


def cmd_uninstall(args: argparse.Namespace):
    """Handle 'uninstall' command."""
    from cli.cli_commands.uninstall import (
        uninstall_agent,
        restore_from_backup,
        list_backups,
    )

    if args.uninstall_action == "backup":
        print("Creating backup...")
        # Backup is done as part of uninstall
    elif args.uninstall_action == "restore":
        restore_from_backup(args.backup_path)
    elif args.uninstall_action == "list":
        list_backups()
    else:
        uninstall_agent(force=args.force, backup=not args.no_backup)


def cmd_doctor(args: argparse.Namespace):
    """Handle 'doctor' command."""
    from cli.cli_commands.doctor import run_diagnostics

    run_diagnostics(verbose=args.verbose)


def cmd_providers(args: argparse.Namespace):
    """Handle 'providers' command."""
    from cli.providers import list_providers, get_provider_info, check_provider_status

    if args.providers_command == "list":
        list_providers(json_output=args.json)
    elif args.providers_command == "info":
        get_provider_info(args.provider_id)
    elif args.providers_command == "status":
        check_provider_status(args.provider_id)
    else:
        list_providers()


def cmd_models(args: argparse.Namespace):
    """Handle 'models' command."""
    from cli.models import list_models, get_model_info, compare_models

    if args.models_command == "list":
        list_models(provider=args.provider, json_output=args.json)
    elif args.models_command == "info":
        get_model_info(args.model_id)
    elif args.models_command == "compare":
        compare_models(args.model1, args.model2)
    else:
        list_models()


def cmd_profiles(args: argparse.Namespace):
    """Handle 'profiles' command."""
    from cli import profiles

    if args.profiles_command == "list":
        profiles.list_profiles()
    elif args.profiles_command == "create":
        profiles.create_profile(args.name, copy_from=args.copy)
    elif args.profiles_command == "switch":
        profiles.switch_profile(args.name)
    elif args.profiles_command == "delete":
        profiles.delete_profile(args.name, force=args.force)
    else:
        profiles.list_profiles()


def cmd_backup(args: argparse.Namespace):
    """Handle 'backup' command."""
    from cli import backup

    if args.backup_command == "create":
        backup.backup_config(args.name)
    elif args.backup_command == "list":
        backup.list_backups()
    elif args.backup_command == "restore":
        backup.restore_backup(args.backup_id)
    elif args.backup_command == "delete":
        backup.delete_backup(args.backup_id)
    else:
        backup.list_backups()


def cmd_auth(args: argparse.Namespace):
    """Handle 'auth' command."""
    from cli import auth_cli

    if args.auth_command == "add":
        auth_cli.add_credential(args.provider, args.api_key)
    elif args.auth_command == "list":
        auth_cli.list_credentials()
    elif args.auth_command == "delete":
        auth_cli.delete_credential(args.provider)
    elif args.auth_command == "test":
        auth_cli.test_connection(args.provider)
    else:
        auth_cli.list_credentials()


def should_use_textual(args: argparse.Namespace) -> bool:
    """Determine if Textual UI should be used.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        True if Textual UI should be used, False otherwise
    """
    # Check if textual is available
    try:
        from tui import TEXTUAL_AVAILABLE
        if not TEXTUAL_AVAILABLE:
            return False
    except ImportError:
        return False
    
    # Explicit --no-textual disables it
    if getattr(args, 'no_textual', False):
        return False
    
    # Explicit --textual flag takes precedence
    if getattr(args, 'textual', False):
        return True
    
    # Non-TTY environment check (pipes, redirects, cron, etc.)
    if not sys.stdout.isatty():
        return False
    
    # Terminal size check
    try:
        import shutil
        terminal_size = shutil.get_terminal_size()
        if terminal_size.columns < 40:
            return False
    except Exception:
        return False
    
    # Default: use traditional CLI
    return False


def run_textual_mode(args: argparse.Namespace, agent: Agent, model_name: str) -> int:
    """Run the agent in Textual TUI mode.
    
    Args:
        args: Parsed command line arguments
        agent: The Agent instance
        model_name: Model name for display
        
    Returns:
        Exit code
    """
    from cli.tui import (
        run_textual_app, 
        TEXTUAL_AVAILABLE,
        get_textual_import_error,
        get_textual_install_hint,
        is_textual_compatible,
    )
    
    if not TEXTUAL_AVAILABLE:
        # 显示友好的安装提示
        print(get_textual_install_hint())
        return 1
    
    # 检查环境兼容性（显式指定 --textual 时跳过检查）
    if not getattr(args, 'textual', False):
        compatible, reason = is_textual_compatible()
        if not compatible:
            print(f"\n⚠ 无法启动 Textual TUI: {reason}")
            print("自动回退到传统 CLI 模式...\n")
            return 1
    
    # Get session info
    session_id = None
    if agent._session:
        session_id = agent._session.session_id
    
    # Get model info
    provider = None
    context_length = None
    try:
        from common.config import load_config
        cfg = load_config()
        if cfg.get('llm', {}).get('provider'):
            provider = cfg.get('llm', {}).get('provider')
        if cfg.get('model', {}).get('context_window'):
            context_length = cfg.get('model', {}).get('context_window')
    except Exception:
        pass
    
    return run_textual_app(
        model_name=model_name,
        provider=provider,
        cwd=os.getcwd(),
        session_id=session_id,
        context_length=context_length,
        agent=agent,  # 传递 Agent 实例给 TUI
    )


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main function to handle command line arguments."""

    # 使用新的参数解析器
    from cli._parser import build_top_level_parser

    parser, subparsers, chat_parser = build_top_level_parser()

    # =========================================================================
    # Register additional subparsers (model, skills, config)
    # =========================================================================

    # model command - already defined in _parser.py
    # skills command - already defined in _parser.py
    # config command - already defined in _parser.py

    # =========================================================================
    # Legacy arguments (for backwards compatibility)
    # =========================================================================

    parser.add_argument(
        "--setup",
        action="store_true",
        help="运行设置向导配置大模型"
    )
    parser.add_argument(
        "--reset-config",
        action="store_true",
        help="重置配置文件并重新运行设置向导"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to process"
    )

    # Add LLM arguments if available
    if LLM_AVAILABLE:
        from cli.llm_cli import add_llm_arguments
        add_llm_arguments(parser)

    args = parser.parse_args()

    # =========================================================================
    # Handle commands
    # =========================================================================

    # Handle subcommands
    if args.command == 'setup':
        cmd_setup(args)
        return
    elif args.command == 'status':
        cmd_status(args)
        return
    elif args.command == 'model':
        if args.model_command == 'list':
            cmd_model_list(args)
        elif args.model_command == 'set':
            cmd_model_set(args)
        return
    elif args.command == 'skills':
        if args.skills_command == 'list':
            cmd_skills_list(args)
        elif args.skills_command == 'search':
            cmd_skills_search(args)
        return
    elif args.command == 'config':
        if args.config_command == 'show':
            cmd_config_show(args)
        elif args.config_command == 'edit':
            cmd_config_edit(args)
        elif args.config_command == 'set':
            cmd_config_set(args)
        elif args.config_command == 'get':
            cmd_config_get(args)
        return
    elif args.command == 'logs':
        cmd_logs(args)
        return
    elif args.command == 'gateway':
        cmd_gateway(args)
        return
    elif args.command == 'cron':
        cmd_cron(args)
        return
    elif args.command == 'acp':
        cmd_acp(args)
        return
    elif args.command == 'sessions':
        cmd_sessions(args)
        return
    elif args.command == 'uninstall':
        cmd_uninstall(args)
        return
    elif args.command == 'doctor':
        cmd_doctor(args)
        return
    elif args.command == 'providers':
        cmd_providers(args)
        return
    elif args.command == 'models':
        cmd_models(args)
        return
    elif args.command == 'profiles':
        cmd_profiles(args)
        return
    elif args.command == 'backup':
        cmd_backup(args)
        return
    elif args.command == 'auth':
        cmd_auth(args)
        return

    # Handle legacy setup mode
    if args.setup or args.reset_config:
        if args.reset_config and os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        from cli.setup import run_setup_wizard
        run_setup_wizard()
        return

    # =========================================================================
    # Chat mode (interactive or single query)
    # =========================================================================

    # Load saved configuration
    saved_config = load_saved_config()

    # Run setup wizard on first run (if not in non-interactive mode)
    if not has_existing_config():
        run_setup_if_needed()
        saved_config = load_saved_config()

    saved_display = saved_config.get("display", {})
    saved_prefs = saved_config.get("preferences", {})

    # Get explanation depth from args or config (default: detailed)
    explanation_depth = getattr(args, 'explanation_depth', saved_prefs.get("explanation_depth", "detailed"))

    # Load language from config
    language = saved_config.get("language", saved_prefs.get("language", "zh"))

    # Get display options
    verbose = getattr(args, 'verbose', False) or saved_display.get("verbose", False)

    # Handle log configuration
    log_level = saved_prefs.get("log_level", "info")

    # Map explanation_depth to log settings
    if explanation_depth == "brief":
        enable_detailed_logs = False
        enable_summary_logs = False
    elif explanation_depth == "moderate":
        enable_detailed_logs = False
        enable_summary_logs = True
    else:
        enable_detailed_logs = True
        enable_summary_logs = True

    # Handle LLM configuration from saved config or args
    llm_provider = None
    model_name = "Handsome Agent"
    saved_llm_params = saved_config.get("llm_params", {})

    if LLM_AVAILABLE:
        saved_llm = saved_config.get("llm", {})
        if saved_llm.get("provider") and saved_llm.get("provider") != "none":
            try:
                llm_config = LLMConfig(
                    provider=saved_llm.get("provider"),
                    api_key=saved_llm.get("api_key"),
                    model=saved_llm.get("model"),
                    base_url=saved_llm.get("base_url"),
                    temperature=saved_llm_params.get("temperature", 0.7),
                    max_tokens=saved_llm_params.get("max_tokens", 4096),
                    timeout=saved_llm_params.get("timeout", 60.0),
                    enable_fallback=saved_llm_params.get("enable_fallback", True),
                    enable_detailed_logs=enable_detailed_logs
                )
                llm_provider = setup_llm_integration(llm_config)
                model_name = saved_llm.get("model", "Handsome Agent")
            except Exception as e:
                print(f"Warning: Failed to load saved LLM config: {e}")

        # Command line model override
        if args.model:
            model_name = args.model

    # 在创建 agent 之前，先配置日志级别
    if not _logging_already_configured:
        from common.logging_manager import configure_logging
        from common.config import get_logs_dir
        
        # 从 config.json 读取日志配置（兼容 preferences 和 logging 两种格式）
        saved_config = load_saved_config()
        logging_cfg = saved_config.get('logging', {})
        # 兼容旧格式：preferences 中也有 file_enabled
        if not logging_cfg:
            prefs = saved_config.get('preferences', {})
            logging_cfg = {
                'file_enabled': prefs.get('file_enabled', False),
                'max_file_size': prefs.get('max_file_size', 10 * 1024 * 1024),
                'backup_count': prefs.get('backup_count', 5),
                'rotation': prefs.get('rotation', 'daily'),
            }
        
        configure_logging({
            "log_level": explanation_depth,
            "file_enabled": logging_cfg.get('file_enabled', False),
            "file_path": str(get_logs_dir() / "handsome-agent.log"),
            "max_file_size": logging_cfg.get('max_file_size', 50 * 1024 * 1024),
            "backup_count": logging_cfg.get('backup_count', 30),
            "rotation": logging_cfg.get('rotation', 'daily'),
            # 启用文件日志时，控制台不显示时间（文件日志已有完整时间戳）
            "console_show_time": not logging_cfg.get('file_enabled', False),
        })

    # Create Agent!
    print()
    print("✨ Using LLM-driven Agent!")
    print()

    # Session options
    session_id = getattr(args, 'session', None) or "last"
    force_new = getattr(args, 'new_session', False) or False

    agent = Agent(
        llm_provider=llm_provider,
        enable_session=True,
        session_id=session_id,
        force_new_session=force_new
    )

    # 注册 LLM 调用回调
    from cli import ui
    if agent.llm_provider:
        agent.llm_provider.register_llm_call_callback(ui.status_bar.increment_llm_call)

    # 显示会话信息
    if agent._session:
        print(f"📝 Session: {agent._session.session_id}")
        if agent._session.messages:
            print(f"   Messages: {len(agent._session.messages)}")

    # Run in appropriate mode
    if should_use_textual(args):
        exit_code = run_textual_mode(args, agent, model_name)
        return exit_code
    
    if args.interactive:
        asyncio.run(interactive_mode(agent, model_name))
    elif args.query:
        asyncio.run(single_query_mode(agent, args.query, model_name))
    elif args.oneshot:
        asyncio.run(single_query_mode(agent, args.oneshot, model_name))
    else:
        asyncio.run(interactive_mode(agent, model_name))


if __name__ == "__main__":
    main()