"""
CLI module for the Handsome Agent.

This package contains the Command Line Interface implementation that provides
user interaction capabilities and argument parsing.

Directory Structure:
    cli/
    ├── __init__.py          # 包初始化
    ├── main.py              # 主入口
    ├── _parser.py           # 参数解析 (向后兼容)
    ├── commands.py          # 斜杠命令注册 (向后兼容)
    │
    ├── core/                # 核心模块
    │   ├── _parser.py       # 参数解析器
    │   └── commands.py      # 斜杠命令注册表
    │
    ├── ui/                  # UI 层
    │   ├── banner.py        # Banner 渲染
    │   └── ...              # (其他 UI 组件在 common/terminal/)
    │
    ├── cli_commands/        # CLI 命令
    │   ├── acp.py          # ACP 命令
    │   ├── auth.py         # 认证命令
    │   ├── config.py       # 配置命令
    │   ├── doctor.py        # 诊断命令
    │   ├── dump.py         # 配置转储
    │   ├── debug.py        # 调试命令
    │   ├── gateway.py      # 网关命令
    │   ├── llm.py          # LLM 命令
    │   ├── logs.py         # 日志命令
    │   ├── models.py       # 模型命令
    │   ├── providers.py     # Provider 命令
    │   ├── session_recap.py # 会话摘要
    │   ├── sessions.py      # 会话命令
    │   ├── skills.py       # 技能命令
    │   └── uninstall.py    # 卸载命令
    │
    ├── config/              # 配置模块
    │   ├── config.py        # 配置加载
    │   ├── config_cli.py   # 配置 CLI
    │   ├── model_cli.py    # 模型 CLI
    │   ├── profiles.py     # 配置文件
    │   ├── skills_config.py # 技能配置
    │   └── tools_config.py # 工具配置
    │
    ├── setup/               # 安装向导
    │   ├── setup_wizard.py # 安装向导
    │   ├── env_loader.py   # 环境加载
    │   └── interactive_select.py # 交互选择
    │
    ├── system/              # 系统功能
    │   ├── backup.py       # 备份
    │   ├── callbacks.py    # 回调系统
    │   ├── hooks.py        # 钩子
    │   ├── relaunch.py     # 重启
    │   └── compat.py       # 兼容性
    │
    └── proxy/               # 代理服务
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

# Re-export main modules for easy access
from . import main
from . import _parser
from . import commands

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
# 注意：某些模块需要延迟导入以避免循环依赖
__all__ = [
    "main",
    "_parser",
    "commands",
]
