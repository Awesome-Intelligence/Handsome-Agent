#!/usr/bin/env python3
"""
MCP Tool Module - Model Context Protocol Tool

Provides MCP integration functionality:
- MCP client connection
- MCP tool invocation
- MCP resource access

Based on Hermes Agent's mcp_tool.py implementation.

Usage:
    from tools.mcp_tool import mcp_list_servers, mcp_call_tool
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("MCPTool")


class MCPServerManager:
    """MCP服务器管理器"""
    
    def __init__(self):
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._config_path = Path.home() / ".agent_z" / "mcp_servers.json"
    
    def _load_config(self):
        """加载配置"""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载MCP配置失败: {e}")
        return {"servers": {}}
    
    def _save_config(self, config):
        """保存配置"""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存MCP配置失败: {e}")
    
    def add_server(
        self,
        name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        """添加MCP服务器配置"""
        config = self._load_config()
        config["servers"][name] = {
            "command": command,
            "args": args or [],
            "env": env or {},
        }
        self._save_config(config)
        logger.info(f"添加MCP服务器: {name}")
    
    def remove_server(self, name: str):
        """移除MCP服务器配置"""
        config = self._load_config()
        if name in config["servers"]:
            del config["servers"][name]
            self._save_config(config)
            logger.info(f"移除MCP服务器: {name}")
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有配置的MCP服务器"""
        config = self._load_config()
        servers = []
        for name, server_config in config["servers"].items():
            servers.append({
                "name": name,
                "command": server_config["command"],
                "args": server_config.get("args", []),
            })
        return servers


# 全局管理器实例
_mcp_manager = MCPServerManager()


def mcp_add_server(
    name: str,
    command: str,
    args: Optional[List[str]] = None,
) -> str:
    """
    添加MCP服务器配置。
    
    Args:
        name: 服务器名称
        command: 启动命令
        args: 可选的命令参数
    
    Returns:
        JSON 格式的结果字符串
    """
    _mcp_manager.add_server(name, command, args)
    
    result = {
        "success": True,
        "message": f"MCP服务器已添加: {name}",
        "server": {
            "name": name,
            "command": command,
            "args": args or [],
        },
    }
    
    return json.dumps(result, ensure_ascii=False)


def mcp_remove_server(name: str) -> str:
    """
    移除MCP服务器配置。
    
    Args:
        name: 服务器名称
    
    Returns:
        JSON 格式的结果字符串
    """
    _mcp_manager.remove_server(name)
    
    result = {
        "success": True,
        "message": f"MCP服务器已移除: {name}",
    }
    
    return json.dumps(result, ensure_ascii=False)


def mcp_list_servers() -> str:
    """
    列出所有配置的MCP服务器。
    
    Returns:
        JSON 格式的结果字符串
    """
    servers = _mcp_manager.list_servers()
    
    result = {
        "success": True,
        "servers": servers,
        "total": len(servers),
        "note": "这是一个模拟实现。完整的MCP功能需要额外的MCP客户端库集成。",
    }
    
    return json.dumps(result, ensure_ascii=False)


def mcp_call_tool(
    server_name: str,
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> str:
    """
    调用MCP工具。
    
    Args:
        server_name: MCP服务器名称
        tool_name: 工具名称
        arguments: 工具参数
    
    Returns:
        JSON 格式的结果字符串
    """
    # 注意：这里只是模拟实现，真实的MCP调用需要MCP客户端库支持
    # 当前版本将返回一个模拟的调用结果
    
    result = {
        "success": True,
        "server": server_name,
        "tool": tool_name,
        "arguments": arguments or {},
        "result": (
            "这是一个模拟的MCP工具调用结果。"
            "完整的MCP功能需要集成MCP客户端库（如 mcp 或 anthropic-mcp）。"
        ),
        "note": "这是一个模拟实现。完整的MCP功能需要额外的MCP客户端库集成。",
    }
    
    return json.dumps(result, ensure_ascii=False)


def mcp_list_tools(server_name: str) -> str:
    """
    列出MCP服务器提供的工具。
    
    Args:
        server_name: MCP服务器名称
    
    Returns:
        JSON 格式的结果字符串
    """
    # 注意：这里只是模拟实现，真实的工具列表需要连接到MCP服务器
    # 当前版本将返回一个模拟的工具列表
    
    result = {
        "success": True,
        "server": server_name,
        "tools": [
            {"name": "example_tool_1", "description": "示例工具1"},
            {"name": "example_tool_2", "description": "示例工具2"},
        ],
        "note": "这是一个模拟实现。完整的MCP功能需要额外的MCP客户端库集成。",
    }
    
    return json.dumps(result, ensure_ascii=False)


def check_mcp_requirements() -> bool:
    """
    检查MCP工具需求。
    由于这是模拟实现，始终返回True。
    """
    return True


# 工具定义
MCP_ADD_SERVER_SCHEMA = {
    "name": "mcp_add_server",
    "description": (
        "Add an MCP (Model Context Protocol) server configuration. "
        "MCP servers provide additional tools and resources that the agent can use."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name to identify the MCP server."
            },
            "command": {
                "type": "string",
                "description": "Command to start the MCP server."
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional arguments for the command.",
            },
        },
        "required": ["name", "command"],
    },
}


MCP_REMOVE_SERVER_SCHEMA = {
    "name": "mcp_remove_server",
    "description": "Remove an MCP server configuration.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name of the MCP server to remove."
            },
        },
        "required": ["name"],
    },
}


MCP_LIST_SERVERS_SCHEMA = {
    "name": "mcp_list_servers",
    "description": "List all configured MCP servers.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


MCP_CALL_TOOL_SCHEMA = {
    "name": "mcp_call_tool",
    "description": (
        "Call a tool provided by an MCP server. "
        "Use this ONLY when you need capabilities from a configured MCP server. "
        "For common tasks like web search, use built-in tools (web_search, web_extract) instead."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "server_name": {
                "type": "string",
                "description": "Name of the MCP server."
            },
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to call."
            },
            "arguments": {
                "type": "object",
                "description": "Arguments to pass to the tool.",
            },
        },
        "required": ["server_name", "tool_name"],
    },
}


MCP_LIST_TOOLS_SCHEMA = {
    "name": "mcp_list_tools",
    "description": "List tools provided by an MCP server.",
    "parameters": {
        "type": "object",
        "properties": {
            "server_name": {
                "type": "string",
                "description": "Name of the MCP server."
            },
        },
        "required": ["server_name"],
    },
}


# 注册工具
registry.register(
    name="mcp_add_server",
    toolset="mcp",
    schema=MCP_ADD_SERVER_SCHEMA,
    handler=lambda args, **kw: mcp_add_server(
        name=args.get("name", ""),
        command=args.get("command", ""),
        args=args.get("args"),
    ),
    check_fn=check_mcp_requirements,
    emoji="➕",
)


registry.register(
    name="mcp_remove_server",
    toolset="mcp",
    schema=MCP_REMOVE_SERVER_SCHEMA,
    handler=lambda args, **kw: mcp_remove_server(args.get("name", "")),
    check_fn=check_mcp_requirements,
    emoji="🗑️",
)


registry.register(
    name="mcp_list_servers",
    toolset="mcp",
    schema=MCP_LIST_SERVERS_SCHEMA,
    handler=lambda args, **kw: mcp_list_servers(),
    check_fn=check_mcp_requirements,
    emoji="📋",
)


# 注：mcp_call_tool 已移除
# 参考 Hermes 设计：每个 MCP server 的工具应该动态注册为单独的工具（如 mcp_{server}_{tool}）
# 而不是提供一个通用的 "call tool" 工具
# 当前实现是模拟版本，真正的 MCP 工具注册需要连接 MCP server 获取工具列表


registry.register(
    name="mcp_list_tools",
    toolset="mcp",
    schema=MCP_LIST_TOOLS_SCHEMA,
    handler=lambda args, **kw: mcp_list_tools(args.get("server_name", "")),
    check_fn=check_mcp_requirements,
    emoji="📦",
)
