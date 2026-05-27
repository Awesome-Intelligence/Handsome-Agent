"""tools.definitions - 标准化的工具定义"""
from .file_tools import FILE_TOOLS
from .shell_tools import SHELL_TOOLS
from .web_tools import WEB_TOOLS
from .openclaw_tools import OPENCLAW_TOOLS, COMPUTER_USE_ACTIONS

__all__ = ["FILE_TOOLS", "SHELL_TOOLS", "WEB_TOOLS", "OPENCLAW_TOOLS", "COMPUTER_USE_ACTIONS"]