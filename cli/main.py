#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Handsome Agent
Provides Text User Interface for testing and interaction
"""

import asyncio
import argparse
import sys
import os
import json
import logging

# 首先解析命令行参数，以便在导入其他模块之前配置日志
parser = argparse.ArgumentParser(prog='Handsome Agent')
parser.add_argument(
    "--explanation-depth",
    choices=["brief", "moderate", "detailed"],
    default="detailed",
    help="Level of detail in explanations"
)
# 只解析已知参数，避免影响后续的参数解析
args, _ = parser.parse_known_args()

# 检查日志是否已经被配置
# 如果 root logger 已经有 handler（且不是 NullHandler），说明已经配置过了
_logging_already_configured = False
if len(logging.root.handlers) > 0:
    # 检查是否已经有有效的 console handler
    for handler in logging.root.handlers:
        if not isinstance(handler, logging.NullHandler):
            _logging_already_configured = True
            break

if not _logging_already_configured:
    # 日志尚未被配置，需要设置
    
    # 在导入任何其他模块之前，立即禁用所有日志输出
    # 移除所有 handler
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # 添加 NullHandler 来吸收所有日志（在 brief 模式下保持）
    logging.root.addHandler(logging.NullHandler())
    
    # 设置 root logger 级别为 CRITICAL + 1（最高级别，不输出任何日志）
    logging.root.setLevel(logging.CRITICAL + 1)
    
    # 现在导入核心模块（此时日志被禁用，不会输出任何日志）
    from core.logging_manager import configure_logging
    
    # 根据配置重新启用日志
    if args.explanation_depth != "brief":
        LOG_LEVEL_MAP = {
            "moderate": logging.INFO,
            "detailed": logging.DEBUG,
        }
        level = LOG_LEVEL_MAP.get(args.explanation_depth, logging.DEBUG)
        
        # 移除 NullHandler
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # 添加控制台 handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logging.root.addHandler(console_handler)
        
        # 设置 root logger 级别
        logging.root.setLevel(level)
    
    # 在 brief 模式下，保持日志禁用状态
else:
    # 日志已经被配置（例如从 main.py 调用），保持现有配置
    pass

from core import CustomAgent, AgentConfig
from core.exceptions import AgentError, InputValidationError, ResponseGenerationError
from advanced_reasoning.integration import enhance_agent_with_advanced_reasoning

CONFIG_FILE = os.path.expanduser("~/.custom_agent_config.json")

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
    
    if not has_existing_config():
        ui.print_header("首次运行 Handsome Agent")
        print()
        ui.print_info("提示: 运行 'python -m cli.main --setup' 可配置大模型")
        ui.print_info("使用 --query 参数可跳过设置直接查询")
        print()


async def interactive_mode(agent: CustomAgent, model_name: str = "Knowledge Base"):
    """Run the agent in interactive mode.
    
    Args:
        agent: The CustomAgent instance to use for processing user input.
        model_name: Name of the model to display in status bar.
    """
    from cli import ui
    
    ui.print_banner()
    
    # Initialize status bar
    ui.status_bar.update_model(model_name)
    ui.status_bar.set_tools(["file", "terminal", "web"])
    ui.print_status_bar()
    
    print()
    ui.print_header("交互模式", "Type 'quit' or 'exit' to end the session.")
    
    while True:
        try:
            print()
            ui.print_user_input()
            user_input = input().strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                ui.print_success("再见!")
                break
                
            if not user_input:
                continue
                
            # Show processing indicator
            print()
            spinner = ui.Spinner("思考中...")
            spinner.start()
            
            try:
                response = await agent.respond(user_input)
                
                # Update status bar with token info
                ui.status_bar.add_tokens(len(response.content.split()))
                
                # Clear spinner line
                print("\r" + " " * 50 + "\r", end="", flush=True)
                
                ui.print_agent_response(response.content, response.confidence_score)
                
                # Show updated status
                ui.print_status_bar()
            finally:
                pass
            
        except KeyboardInterrupt:
            print()
            ui.print_success("再见!")
            break
        except EOFError:
            ui.print_success("再见!")
            break
        except InputValidationError as e:
            ui.print_error(f"输入错误: {e}")
        except ResponseGenerationError as e:
            ui.print_error(f"响应生成错误: {e}")
        except AgentError as e:
            ui.print_error(f"Agent错误: {e}")
        except Exception as e:
            ui.print_error(f"未知错误: {e}")


async def single_query_mode(agent: CustomAgent, query: str, model_name: str = "Knowledge Base"):
    """Run the agent with a single query.
    
    Args:
        agent: The CustomAgent instance to use.
        query: The user's query string.
        model_name: Name of the model to display in status bar.
        
    Raises:
        InputValidationError: If the query is invalid.
        ResponseGenerationError: If response generation fails.
        AgentError: For other agent-related errors.
    """
    from cli import ui
    
    ui.print_banner()
    
    # Initialize status bar
    ui.status_bar.update_model(model_name)
    ui.print_status_bar()
    
    ui.print_header("查询结果", f"Query: {query[:50]}{'...' if len(query) > 50 else ''}")
    
    try:
        # Show processing indicator
        spinner = ui.Spinner("思考中...")
        spinner.start()
        
        try:
            response = await agent.respond(query)
            
            # Clear spinner line
            print("\r" + " " * 50 + "\r", end="", flush=True)
            
            ui.print_agent_response(response.content, response.confidence_score)
        finally:
            pass
        
    except InputValidationError as e:
        ui.print_error(f"输入错误: {e}")
    except ResponseGenerationError as e:
        ui.print_error(f"响应生成错误: {e}")
    except AgentError as e:
        ui.print_error(f"Agent错误: {e}")
    except Exception as e:
        ui.print_error(f"未知错误: {e}")


def list_sessions():
    """List all sessions."""
    from core.session import session_manager
    
    sessions = session_manager.list_sessions()
    
    if not sessions:
        print("No sessions found.")
        return
    
    print("Available sessions:")
    for session_id in sessions:
        print(f"  - {session_id}")


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Handsome Agent - 智能问答助手，支持大模型集成"
    )
    
    # Main commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Interactive mode
    subparsers.add_parser('chat', help='Start interactive chat mode')
    
    # Setup command
    subparsers.add_parser('setup', help='Run setup wizard')
    
    # List sessions
    subparsers.add_parser('sessions', help='List all sessions')
    
    # Version
    subparsers.add_parser('version', help='Show version')
    
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
        "--query", "-q",
        type=str,
        help="Single query to process"
    )
    parser.add_argument(
        "--explanation-depth",
        choices=["brief", "moderate", "detailed"],
        default="detailed",
        help="Level of detail in explanations"
    )
    parser.add_argument(
        "--format",
        choices=["plain", "structured", "markdown"],
        default="markdown",
        help="Response format"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=4000,
        help="Maximum response length"
    )
    parser.add_argument(
        "--advanced-reasoning",
        action="store_true",
        help="Enable advanced AI reasoning capabilities"
    )
    parser.add_argument(
        "--enable-caching",
        type=bool,
        default=True,
        help="Enable LRU response caching for performance"
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="Maximum time allowed for response generation (0 = disabled)"
    )
    parser.add_argument(
        "--language", "-L",
        choices=["zh", "en", "ko", "ja"],
        default=None,
        help="Language for log messages (zh/en/ko/ja). Default: use saved config"
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default=None,
        help="Logging level (debug/info/warning/error). Default: use saved config or 'info'"
    )
    parser.add_argument(
        "--detailed-logs",
        action="store_true",
        default=None,
        help="Enable detailed processing logs (default: True)"
    )
    parser.add_argument(
        "--no-detailed-logs",
        action="store_true",
        help="Disable detailed processing logs"
    )
    parser.add_argument(
        "--summary-logs",
        action="store_true",
        default=None,
        help="Enable summary logs (default: True)"
    )
    parser.add_argument(
        "--no-summary-logs",
        action="store_true",
        help="Disable summary logs (not recommended)"
    )
    
    # Add LLM arguments if available
    if LLM_AVAILABLE:
        from cli.llm_cli import add_llm_arguments
        add_llm_arguments(parser)
    
    args = parser.parse_args()
    
    # Handle subcommands first
    if args.command == 'setup':
        from cli.setup_wizard import run_setup_wizard
        run_setup_wizard()
        return
    elif args.command == 'sessions':
        list_sessions()
        return
    elif args.command == 'version':
        print("Handsome Agent V 0.0.1")
        print("Inspired by Hermes Agent")
        return
    elif args.command == 'chat':
        pass
    
    # Handle setup mode
    if args.setup or args.reset_config:
        if args.reset_config and os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        from cli.setup_wizard import run_setup_wizard
        run_setup_wizard()
        return
    
    # Load saved configuration
    saved_config = load_saved_config()
    
    # Run setup wizard on first run (if not in non-interactive mode)
    if not has_existing_config():
        run_setup_if_needed()
        saved_config = load_saved_config()
    
    saved_display = saved_config.get("display", {})
    saved_prefs = saved_config.get("preferences", {})
    
    if saved_prefs.get("explanation_depth"):
        args.explanation_depth = saved_prefs["explanation_depth"]
    if saved_prefs.get("response_format"):
        args.format = saved_prefs["response_format"]
    if saved_prefs.get("enable_caching") is not None:
        args.enable_caching = saved_prefs["enable_caching"]
    
    # Load language from config (top-level, set by setup wizard)
    language = saved_config.get("language", saved_prefs.get("language", "zh"))
    if args.language:
        language = args.language
    
    # Load intent mode from config
    intent_mode = saved_config.get("intent_mode", "llm")
    
    # Get display options
    verbose = saved_display.get("verbose", False)
    show_reasoning = saved_display.get("show_reasoning", False)
    
    # Handle log configuration
    log_level = saved_prefs.get("log_level", "info")
    if args.log_level:
        log_level = args.log_level
    
    # Map explanation_depth to log settings
    explanation_depth = saved_prefs.get("explanation_depth", "moderate")
    
    if explanation_depth == "brief":
        enable_detailed_logs = False
        enable_summary_logs = False
    elif explanation_depth == "moderate":
        enable_detailed_logs = False
        enable_summary_logs = True
    else:
        enable_detailed_logs = True
        enable_summary_logs = True
    
    # Command line overrides
    if args.detailed_logs is not None:
        enable_detailed_logs = args.detailed_logs
    if args.no_detailed_logs:
        enable_detailed_logs = False
    if args.summary_logs is not None:
        enable_summary_logs = args.summary_logs
    if args.no_summary_logs:
        enable_summary_logs = False
    
    # Handle LLM configuration from saved config or args
    llm_provider = None
    model_name = "Knowledge Base"
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
                model_name = saved_llm.get("model", "LLM")
            except Exception as e:
                print(f"Warning: Failed to load saved LLM config: {e}")
        
        if hasattr(args, 'llm_provider') and args.llm_provider:
            from cli.llm_cli import setup_environment_variables, create_llm_config_from_args
            setup_environment_variables(args)
            llm_config = create_llm_config_from_args(args)
            if llm_config:
                llm_provider = setup_llm_integration(llm_config)
                model_name = args.llm_model if hasattr(args, 'llm_model') else "LLM"
    
    # 在创建 agent 之前，先配置日志级别（如果尚未配置）
    if not _logging_already_configured:
        from core.logging_manager import set_log_level
        set_log_level(explanation_depth)
    
    # Create agent configuration
    config = AgentConfig(
        name="CustomAgent",
        explanation_depth=args.explanation_depth,
        response_format=args.format,
        max_response_length=args.max_length,
        enable_caching=args.enable_caching,
        timeout_seconds=args.timeout_seconds,
        language=language,
        log_level=log_level,
        enable_detailed_logs=enable_detailed_logs,
        enable_summary_logs=enable_summary_logs,
        intent_mode=intent_mode
    )
    
    # Create agent with appropriate reasoning module
    if llm_provider is not None:
        from core.logging_manager import get_logger
        logger = get_logger("CLI")
        logger.debug(f"LLM provider loaded: {type(llm_provider)}")
        agent = enhance_agent_with_advanced_reasoning(config, llm_provider)
    elif args.advanced_reasoning:
        agent = enhance_agent_with_advanced_reasoning(config)
    else:
        agent = CustomAgent(config)
    
    if args.interactive:
        asyncio.run(interactive_mode(agent, model_name))
    elif args.query:
        asyncio.run(single_query_mode(agent, args.query, model_name))
    else:
        asyncio.run(interactive_mode(agent, model_name))


if __name__ == "__main__":
    main()