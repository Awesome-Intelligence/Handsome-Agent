# 🧠 Decision - 📊 Context - CLI 命令

"""
Compression Commands - 上下文压缩 CLI 命令

提供压缩功能的命令行接口：
1. /compress - 手动触发压缩
2. /usage - 显示压缩统计和使用信息

Usage:
    from agent.context.compression_commands import handle_compress_command, handle_usage_command

    # 在交互式 CLI 中
    if command == "/compress":
        handle_compress_command(session_id, focus_topic)
    elif command == "/usage":
        handle_usage_command(session_id)
"""

from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger

logger = get_decision_logger(__name__, sublayer="context")


class CompressionCommands:
    """
    压缩命令处理器

    提供压缩相关的 CLI 命令实现。
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._integration = None

    def set_integration(self, integration: Any) -> None:
        """设置压缩集成器"""
        self._integration = integration

    def handle_compress(
        self,
        args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        处理 /compress 命令

        Args:
            args: 命令参数列表

        Returns:
            命令结果字典
        """
        if not self._integration:
            return {
                "success": False,
                "error": "Compression not initialized",
                "message": "压缩功能未初始化",
            }

        focus_topic = None
        force = False

        if args:
            for arg in args:
                if arg.startswith("--focus="):
                    focus_topic = arg.split("=", 1)[1]
                elif arg == "--force":
                    force = True

        if force:
            self._integration.request_compression(focus_topic)
            return {
                "success": True,
                "message": f"压缩已请求 (focus: {focus_topic or '无'})",
                "pending": True,
            }

        # 即使非 force 模式，也设置 focus_topic 以便 compress 使用
        if focus_topic:
            self._integration._focus_topic = focus_topic

        messages = self._get_current_messages()
        if not messages:
            return {
                "success": False,
                "error": "No messages to compress",
                "message": "没有可压缩的消息",
            }

        compressed = self._integration.compress(messages)
        stats = self._integration.get_stats()

        # 清理 focus_topic
        self._integration._focus_topic = None

        if len(compressed) >= len(messages):
            return {
                "success": True,
                "message": "当前消息不需要压缩",
                "stats": stats,
            }

        return {
            "success": True,
            "message": f"压缩完成: {len(messages)} -> {len(compressed)} 条消息 (focus: {focus_topic or '无'})",
            "original_count": len(messages),
            "compressed_count": len(compressed),
            "stats": stats,
        }

    def handle_usage(self) -> Dict[str, Any]:
        """
        处理 /usage 命令

        Returns:
            使用统计字典
        """
        if not self._integration:
            return {
                "success": False,
                "error": "Compression not initialized",
                "message": "压缩功能未初始化",
            }

        stats = self._integration.get_stats()
        status = self._integration.get_status()

        return {
            "success": True,
            "stats": stats,
            "status": status,
            "message": self._format_usage_message(stats, status),
        }

    def handle_status(self) -> Dict[str, Any]:
        """
        处理 /compression-status 命令

        Returns:
            状态字典
        """
        if not self._integration:
            return {
                "success": False,
                "error": "Compression not initialized",
                "message": "压缩功能未初始化",
            }

        status = self._integration.get_status()

        return {
            "success": True,
            "status": status,
            "message": self._format_status_message(status),
        }

    def _get_current_messages(self) -> List[Dict[str, Any]]:
        """获取当前消息（子类可覆盖）"""
        return []

    def _format_usage_message(self, stats: Dict[str, Any], status: Dict[str, Any]) -> str:
        """格式化 usage 消息"""
        lines = ["=" * 50, "  📊 Context Usage Report", "=" * 50, ""]

        lines.append(f"  压缩状态: {'✅ 已启用' if status.get('enabled') else '❌ 已禁用'}")
        lines.append(f"  自动压缩: {'✅ 开启' if status.get('auto_compress') else '❌ 关闭'}")
        lines.append("")

        lines.append("  📈 Token 使用:")
        lines.append(f"    - 最近 Prompt Tokens: {stats.get('last_prompt_tokens', 0):,}")
        lines.append(f"    - 最近 Completion Tokens: {stats.get('last_completion_tokens', 0):,}")

        if stats.get("compression_count"):
            lines.append("")
            lines.append("  📉 压缩统计:")
            lines.append(f"    - 压缩次数: {stats.get('compression_count', 0)}")
            lines.append(f"    - 上下文长度: {stats.get('context_length', 0):,}")
            lines.append(f"    - 压缩阈值: {stats.get('threshold_tokens', 0):,}")
            lines.append(f"    - 低效压缩次数: {stats.get('ineffective_count', 0)}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)

    def _format_status_message(self, status: Dict[str, Any]) -> str:
        """格式化 status 消息"""
        lines = ["=" * 50, "  🔧 Compression Status", "=" * 50, ""]

        enabled = status.get("enabled", False)
        auto = status.get("auto_compress", False)
        initialized = status.get("initialized", False)

        lines.append(f"  功能状态: {'✅ 正常' if initialized else '❌ 未初始化'}")
        lines.append(f"  启用状态: {'✅ 已启用' if enabled else '❌ 已禁用'}")
        lines.append(f"  自动压缩: {'✅ 开启' if auto else '❌ 关闭'}")

        if initialized:
            lines.append("")
            lines.append("  可用命令:")
            lines.append("    /compress           - 手动压缩上下文")
            lines.append("    /compress --focus=X - 聚焦压缩（保留特定主题）")
            lines.append("    /usage             - 显示使用统计")
            lines.append("    /compression-status - 显示压缩状态")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)


def handle_compress_command(
    session_id: str,
    args: Optional[List[str]] = None,
    integration: Any = None,
) -> Dict[str, Any]:
    """
    处理 /compress 命令（便捷函数）

    Args:
        session_id: 会话 ID
        args: 命令参数
        integration: 压缩集成器实例

    Returns:
        命令结果字典
    """
    handler = CompressionCommands(session_id)
    if integration:
        handler.set_integration(integration)
    return handler.handle_compress(args)


def handle_usage_command(
    session_id: str,
    integration: Any = None,
) -> Dict[str, Any]:
    """
    处理 /usage 命令（便捷函数）

    Args:
        session_id: 会话 ID
        integration: 压缩集成器实例

    Returns:
        使用统计字典
    """
    handler = CompressionCommands(session_id)
    if integration:
        handler.set_integration(integration)
    return handler.handle_usage()


def handle_status_command(
    session_id: str,
    integration: Any = None,
) -> Dict[str, Any]:
    """
    处理 /compression-status 命令（便捷函数）

    Args:
        session_id: 会话 ID
        integration: 压缩集成器实例

    Returns:
        状态字典
    """
    handler = CompressionCommands(session_id)
    if integration:
        handler.set_integration(integration)
    return handler.handle_status()


COMMANDS = {
    "/compress": {
        "handler": handle_compress_command,
        "description": "手动触发上下文压缩",
        "help": "/compress [--focus=主题]  - 手动压缩上下文",
    },
    "/usage": {
        "handler": handle_usage_command,
        "description": "显示 Token 使用和压缩统计",
        "help": "/usage  - 显示使用统计",
    },
    "/compression-status": {
        "handler": handle_status_command,
        "description": "显示压缩功能状态",
        "help": "/compression-status  - 显示压缩状态",
    },
}


def is_compression_command(text: str) -> bool:
    """
    检查文本是否为压缩命令

    Args:
        text: 输入文本

    Returns:
        是否为压缩命令
    """
    return text.strip().lower() in COMMANDS.keys()


def parse_compression_command(text: str) -> tuple:
    """
    解析压缩命令

    Args:
        text: 命令文本（如 "/compress --focus=python"）

    Returns:
        (command_name, args) 元组
    """
    parts = text.strip().split()
    if not parts:
        return None, []

    command = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    if command not in COMMANDS:
        return None, []

    return command, args


__all__ = [
    "CompressionCommands",
    "handle_compress_command",
    "handle_usage_command",
    "handle_status_command",
    "is_compression_command",
    "parse_compression_command",
    "COMMANDS",
]
