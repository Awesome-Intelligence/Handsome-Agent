# 🚪 Access - 💬 CLI UI Layer
# CLI UI 组件模块
#
# 注意：
# - 通用终端 UI 功能请使用 common.terminal 模块
# - 本模块仅包含 CLI 特有的 UI 组件

# 重新导出 common.terminal.ui 中的 ui 实例
from common.terminal.ui import ui

__all__ = ["ui"]
