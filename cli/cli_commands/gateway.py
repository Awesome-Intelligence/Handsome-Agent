#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gateway command - Gateway service management

🚪 Access - 💬 CLI - Gateway 服务管理

提供 Gateway 服务管理功能：启动、停止、查看状态。
"""

import sys
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional


def get_pid_file() -> Path:
    """获取 PID 文件路径"""
    config_dir = Path.home() / ".agent_z"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "gateway.pid"


def get_log_file() -> Path:
    """获取日志文件路径"""
    config_dir = Path.home() / ".agent_z"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "logs" / "gateway.log"


def is_gateway_running() -> Optional[int]:
    """检查 Gateway 是否运行，返回 PID 或 None"""
    pid_file = get_pid_file()

    if not pid_file.exists():
        return None

    try:
        pid = int(pid_file.read_text().strip())
        # 检查进程是否存在
        if _is_process_running(pid):
            return pid
        else:
            # PID 文件过期，删除
            pid_file.unlink(missing_ok=True)
            return None
    except Exception:
        return None


def _is_process_running(pid: int) -> bool:
    """检查进程是否运行"""
    try:
        if sys.platform == "win32":
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


def start_gateway() -> None:
    """启动 Gateway 服务"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error, print_info

    print_header("🚀 启动 Gateway")

    # 检查是否已运行
    existing_pid = is_gateway_running()
    if existing_pid:
        print_error(f"Gateway 已在运行 (PID: {existing_pid})")
        return

    # 确保日志目录存在
    log_file = get_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    print_info("启动 Gateway 服务...")

    try:
        # 启动 Gateway 进程
        # 尝试多种启动方式
        cmd = None

        # 方式 1: 作为模块运行
        if _is_module_available("gateway.server"):
            cmd = [sys.executable, "-m", "gateway.server"]
        # 方式 2: 直接运行 gateway 脚本
        elif _is_file_available("gateway/__main__.py"):
            cmd = [sys.executable, "-m", "gateway"]

        if cmd is None:
            # 方式 3: 查找可执行文件
            for exe_path in [
                Path.home() / ".agent_z" / "bin" / "gateway",
                Path(sys.prefix) / "bin" / "gateway",
            ]:
                if exe_path.exists():
                    cmd = [str(exe_path)]
                    break

        if cmd is None:
            print_error("无法找到 Gateway 启动方式")
            print_info("请确保 gateway 包已安装或配置正确")
            return

        # 启动进程
        log_fd = open(log_file, "a", encoding="utf-8")
        proc = subprocess.Popen(
            cmd,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            cwd=str(Path.cwd()),
        )

        # 保存 PID
        pid_file = get_pid_file()
        pid_file.write_text(str(proc.pid))

        # 等待进程启动
        time.sleep(1)

        if proc.poll() is None:
            print_success(f"Gateway 已启动 (PID: {proc.pid})")
            print_info(f"日志文件: {log_file}")
        else:
            print_error("Gateway 启动失败")
            pid_file.unlink(missing_ok=True)

    except Exception as e:
        print_error(f"启动失败: {e}")


def stop_gateway() -> None:
    """停止 Gateway 服务"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error, print_info

    print_header("🛑 停止 Gateway")

    pid = is_gateway_running()

    if not pid:
        print_error("Gateway 未运行")
        return

    print_info(f"停止 Gateway (PID: {pid})...")

    try:
        if sys.platform == "win32":
            # Windows: 使用 taskkill
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False)
        else:
            # Unix: 发送 SIGTERM
            os.kill(pid, signal.SIGTERM)

        # 等待进程停止
        for _ in range(10):
            if not _is_process_running(pid):
                break
            time.sleep(0.5)

        # 检查是否真的停止了
        if _is_process_running(pid):
            # 强制停止
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False)
            else:
                os.kill(pid, signal.SIGKILL)

        # 删除 PID 文件
        get_pid_file().unlink(missing_ok=True)

        print_success("Gateway 已停止")

    except Exception as e:
        print_error(f"停止失败: {e}")


def check_gateway_status() -> None:
    """查看 Gateway 状态"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error, print_info

    print_header("📊 Gateway 状态")

    pid = is_gateway_running()

    if pid:
        print_success(f"🟢 Gateway 运行中 (PID: {pid})")

        # 显示启动时间（如果可能）
        try:
            import psutil

            proc = psutil.Process(pid)
            started = proc.create_time()
            uptime = time.time() - started
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            print_info(f"运行时间: {hours}h {minutes}m")
        except Exception:
            pass

        # 显示日志文件位置
        log_file = get_log_file()
        print_info(f"日志文件: {log_file}")

    else:
        print_error("🔴 Gateway 未运行")
        print_info("使用 'agentz gateway start' 启动")


def restart_gateway() -> None:
    """重启 Gateway 服务"""
    stop_gateway()
    time.sleep(1)
    start_gateway()


def get_env_file() -> Path:
    """获取 .env 文件路径"""
    config_dir = Path.home() / ".agent_z"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / ".env"


def _save_env_value(key: str, value: str) -> None:
    """保存环境变量到 .env 文件"""
    env_file = get_env_file()
    lines = []
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()

    # 更新或添加
    found = False
    new_lines = []
    for line in lines:
        if line.strip() and not line.strip().startswith("#"):
            if line.split("=", 1)[0].strip() == key:
                new_lines.append(f"{key}={value}")
                found = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}")

    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def setup_gateway() -> None:
    """配置 Messaging Gateway（微信等平台）"""
    from common.terminal.ui import (
        print_header,
        print_success,
        print_error,
        print_info,
        print_warning,
    )

    print_header("📱 配置 Messaging Gateway")

    # 检查 aiohttp
    try:
        import aiohttp  # noqa: F401
    except ImportError:
        print_error("缺少 aiohttp，请先安装：")
        print_info("  pip install aiohttp")
        return

    print()
    print_info("支持的平台：")
    print_info("  1. 微信 (Weixin) - 通过 iLink Bot API")
    print()

    try:
        choice = input("选择平台 (1): ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        print()
        print_warning("已取消")
        return

    if choice == "1":
        _setup_weixin()


def _setup_weixin() -> None:
    """配置微信"""
    from common.terminal.ui import (
        print_header,
        print_success,
        print_error,
        print_info,
        print_warning,
    )
    from common.config import get_agent_z_home
    from gateway.adapters.weixin_adapter import qr_login, AIOHTTP_AVAILABLE

    if not AIOHTTP_AVAILABLE:
        print_error("微信适配器需要 aiohttp，请先安装：")
        print_info("  pip install aiohttp")
        return

    print_header("📱 微信配置")
    print_info("通过 iLink Bot API 连接微信个人号")
    print()
    print_info("步骤：")
    print_info("  1. 用微信扫描二维码")
    print_info("  2. 在微信中确认登录")
    print()

    try:
        confirm = input("开始扫码? (Y/n): ").strip().lower() or "y"
    except (EOFError, KeyboardInterrupt):
        print()
        print_warning("已取消")
        return

    if confirm == "n":
        print_info("已取消")
        return

    import asyncio

    try:
        agent_z_home = str(get_agent_z_home())
        credentials = asyncio.run(qr_login(agent_z_home))
    except KeyboardInterrupt:
        print()
        print_warning("已取消")
        return
    except Exception as exc:
        print_error(f"QR 登录失败: {exc}")
        return

    if not credentials:
        print_warning("登录未完成")
        return

    # 保存凭证
    account_id = credentials.get("account_id", "")
    token = credentials.get("token", "")
    base_url = credentials.get("base_url", "https://ilinkai.weixin.qq.com")

    _save_env_value("WEIXIN_ACCOUNT_ID", account_id)
    _save_env_value("WEIXIN_TOKEN", token)
    _save_env_value("WEIXIN_BASE_URL", base_url)

    print()
    print_success("✅ 微信连接成功!")
    print_info(f"  account_id: {account_id[:8]}...")
    print()
    print_info("下一步：")
    print_info("  agentz gateway start   # 启动 Gateway")
    print_info("  然后直接向你的微信发送消息即可")


def _is_module_available(module_name: str) -> bool:
    """检查模块是否可用"""
    import importlib.util
    return importlib.util.find_spec(module_name) is not None


def _is_file_available(path: str) -> bool:
    """检查文件是否存在"""
    return Path(path).exists()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gateway service management")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    start_parser = subparsers.add_parser("start", help="Start gateway")
    stop_parser = subparsers.add_parser("stop", help="Stop gateway")
    status_parser = subparsers.add_parser("status", help="Check gateway status")
    restart_parser = subparsers.add_parser("restart", help="Restart gateway")
    setup_parser = subparsers.add_parser("setup", help="Configure messaging platforms")

    args = parser.parse_args()

    if args.command == "start":
        start_gateway()
    elif args.command == "stop":
        stop_gateway()
    elif args.command == "status":
        check_gateway_status()
    elif args.command == "restart":
        restart_gateway()
    elif args.command == "setup":
        setup_gateway()
    else:
        # 默认显示状态
        check_gateway_status()
