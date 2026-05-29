#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entry point for the Handsome Agent
"""

import sys
import os
import logging

# 在导入任何模块之前，先解析命令行参数来确定日志级别
import argparse
parser = argparse.ArgumentParser(prog='Handsome Agent')
parser.add_argument(
    "--explanation-depth",
    choices=["brief", "moderate", "detailed"],
    default="detailed",
    help="Level of detail in explanations"
)
parser.add_argument(
    "--query", "-q",
    type=str,
    help="Single query to process"
)
args, _ = parser.parse_known_args()

# 全局日志配置标志，防止重复配置
_logging_configured = False

def configure_logging_once(depth):
    """配置日志系统（只配置一次）"""
    global _logging_configured
    if _logging_configured:
        return
    
    LOG_LEVEL_MAP = {
        "brief": logging.CRITICAL + 1,
        "moderate": logging.INFO,
        "detailed": logging.DEBUG,
    }
    level = LOG_LEVEL_MAP.get(depth, logging.DEBUG)
    
    # 移除所有已存在的 handler
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()
    
    if depth == "brief":
        # brief 模式：不输出任何日志
        logging.root.addHandler(logging.NullHandler())
        logging.root.setLevel(logging.CRITICAL + 1)
    
    # 禁用 propagate，防止日志重复
    logging.root.propagate = False
    
    _logging_configured = True

# 在导入任何模块之前配置日志
configure_logging_once(args.explanation_depth)

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入核心模块
from core import CustomAgent, AgentConfig

# 创建 agent
config = AgentConfig(explanation_depth=args.explanation_depth)
agent = CustomAgent(config)

# 运行查询
if args.query:
    import asyncio
    response = asyncio.run(agent.respond(args.query))
    print(f"\n🤖 Assistant:\n\n{response.content}")
else:
    from cli.main import interactive_mode
    interactive_mode(agent, config)

if __name__ == "__main__":
    pass