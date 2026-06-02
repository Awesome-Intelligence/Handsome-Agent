#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modern CLI - 现代版命令行接口

使用新的 Agent 和整合后的工具系统
"""

import asyncio
import argparse
import sys
import os
import json
import logging
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent.agent import Agent, AgentResponse
from tools.integrated_tools import initialize_tools

CONFIG_FILE = os.path.expanduser("~/.handsome_agent/config.json")


def load_saved_config() -> dict:
    """加载保存的配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║           Handsome Agent - Modern Edition                     ║
║           Powered by LLM-driven Decision Engine               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_header(title: str, subtitle: str = ""):
    """打印标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print(f"{'=' * 60}\n")


async def interactive_mode(agent: Agent):
    """交互模式"""
    
    # 显示会话摘要（如果继续现有会话）
    if agent._session and agent._session.messages:
        print_header("Previous Conversation", agent._session.session_id)
        recent_msgs = agent._session.messages[-10:]  # 最近10条
        for msg in recent_msgs:
            role_icon = "●" if msg.role == "user" else "◆"
            content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
            print(f"  {role_icon} {msg.role}: {content}")
        print()
    
    print_header("Interactive Mode", "Type 'quit' or 'exit' to end")
    
    while True:
        try:
            user_input = input("\n🤔 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            # 显示正在处理的提示
            print("\n⚙️  Processing...", end="", flush=True)
            
            # 处理用户输入
            response = await agent.chat(user_input)
            
            # 清除处理提示
            print("\r" + " " * 30 + "\r", end="", flush=True)
            
            # 显示工具使用信息
            if response.tool_used:
                print(f"\n🔧 Used tool: {response.tool_used}")
            
            # 显示响应
            print(f"\n🤖 Agent:")
            print(response.content)
            
            # 显示执行时间
            if response.execution_time > 0:
                print(f"\n⏱️  Response time: {response.execution_time:.2f}s")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


async def single_query_mode(agent: Agent, query: str):
    """单次查询模式"""
    print_header("Single Query Mode", query[:60])
    
    print("\n⚙️  Processing...", end="", flush=True)
    
    response = await agent.chat(query)
    
    # 清除处理提示
    print("\r" + " " * 30 + "\r", end="", flush=True)
    
    if response.tool_used:
        print(f"\n🔧 Used tool: {response.tool_used}")
    
    print(f"\n🤖 Agent:")
    print(response.content)


def list_tools(agent: Agent):
    """列出所有可用工具"""
    tools = agent.get_tool_list()
    
    print_header("Available Tools", f"Total: {len(tools)}")
    
    # 按类别分组
    categories = {}
    for tool in tools:
        cat = tool.get('category', 'general')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tool)
    
    for cat, cat_tools in sorted(categories.items()):
        print(f"\n📦 {cat.upper()}:")
        for tool in sorted(cat_tools, key=lambda t: t['name']):
            print(f"  - {tool['name']}: {tool['description']}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Handsome Agent - Modern CLI (LLM-driven)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cli.modern_cli                  # Start interactive mode
  python -m cli.modern_cli -q "打开计算器"    # Run single query
  python -m cli.modern_cli --tools          # List available tools
        """
    )
    
    # 主要命令
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive mode (default)"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Run a single query and exit"
    )
    parser.add_argument(
        "--tools",
        action="store_true",
        help="List all available tools"
    )
    parser.add_argument(
        "--test-init",
        action="store_true",
        help="Test tool initialization only"
    )
    
    # 日志选项
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose logging"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all logging except errors"
    )
    
    # Session options
    parser.add_argument(
        "--continue", "-c",
        action="store_true",
        help="Continue today's session (default behavior)"
    )
    parser.add_argument(
        "--session", "-s",
        type=str,
        default=None,
        help="Resume a specific session by ID or 'last' for latest"
    )
    parser.add_argument(
        "--new-session", "-n",
        action="store_true",
        help="Force create a new session"
    )
    
    args = parser.parse_args()
    
    # 配置日志
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 尝试加载 LLM 配置
    llm_provider = None
    saved_config = load_saved_config()
    
    if saved_config.get('llm', {}).get('provider'):
        try:
            from llm_integration import LLMConfig, setup_llm_integration
            
            llm_config = LLMConfig(
                provider=saved_config['llm'].get('provider'),
                api_key=saved_config['llm'].get('api_key'),
                model=saved_config['llm'].get('model'),
                base_url=saved_config['llm'].get('base_url'),
                temperature=saved_config.get('llm_params', {}).get('temperature', 0.7)
            )
            llm_provider = setup_llm_integration(llm_config)
            print("✅ LLM integration loaded!")
        except Exception as e:
            print(f"⚠️  Could not load LLM integration: {e}")
            print("   Running in tool-only mode.")
    
    # 初始化工具（在 LLM 配置之后）
    initialize_tools()
    
    # 创建 Agent
    session_id = args.session if args.session else "last"
    force_new = args.new_session
    agent = Agent(
        llm_provider=llm_provider,
        session_id=session_id,
        force_new_session=force_new
    )
    
    # 显示会话信息
    if agent._session:
        print(f"📝 Session: {agent._session.session_id}")
    
    # 只测试初始化
    if args.test_init:
        print_banner()
        print(f"✅ System initialized successfully!")
        print(f"   Tools loaded: {len(agent.get_tool_list())}")
        print(f"   LLM available: {'Yes' if llm_provider else 'No'}")
        return
    
    # 列出工具
    if args.tools:
        print_banner()
        list_tools(agent)
        return
    
    # 单次查询
    if args.query:
        print_banner()
        asyncio.run(single_query_mode(agent, args.query))
        return
    
    # 交互模式（默认）
    print_banner()
    asyncio.run(interactive_mode(agent))


if __name__ == "__main__":
    main()
