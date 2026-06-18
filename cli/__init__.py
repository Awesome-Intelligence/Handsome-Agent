"""
TUI module for the Handsome Agent.

This package contains the Text User Interface implementation that provides
user interaction capabilities and argument parsing with rich terminal UI.

Directory Structure:
    cli/
    ├── main.py              # 主入口
    ├── _parser.py           # 参数解析
    ├── commands/            # CLI 命令系统
    │   ├── doctor.py       # 诊断检查
    │   └── sessions.py     # 会话管理
    ├── tui/                 # TUI 渲染层
    │   └── curses_ui.py    # Curses UI 组件
    ├── components/          # UI 组件
    │   ├── ui.py           # UI 组件（门面）
    │   ├── colors.py       # 颜色和主题
    │   ├── output.py       # 输出函数
    │   └── banner.py       # Banner 渲染
    └── compat.py           # 向后兼容导入
"""

# Patch Textual's LayerLogger before any imports
def _early_textual_patch():
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

_early_textual_patch()

# Re-export from compat layer for backward compatibility
from . import compat

# Re-export main modules for easy access
from . import main
from . import _parser
from . import ui
from . import colors
from . import cli_output
from . import banner
from . import curses_ui
from . import status
from . import setup_wizard

# 从项目根目录的 _version.py 导入版本信息
import sys
from pathlib import Path

_version_path = Path(__file__).resolve().parent.parent / "_version.py"
if _version_path.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_version", _version_path)
    _version_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_version_module)
    __version__ = _version_module.__version__
    __release_date__ = _version_module.__release_date__
else:
    # 降级：如果找不到 _version.py，使用默认值
    __version__ = "0.0.1"
    __release_date__ = "2026.06.18"

# Expose key components at package level
__all__ = [
    "main",
    "_parser",
    "ui",
    "colors",
    "cli_output",
    "banner",
    "curses_ui",
    "status",
    "setup_wizard",
    "compat",
]