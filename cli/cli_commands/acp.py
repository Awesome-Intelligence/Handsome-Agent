#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP command - ACP server management (Editor Integration)

🚪 Access - 💬 CLI - ACP 服务器管理

提供 ACP (Agent Code Protocol) 服务器管理功能，
用于编辑器集成（如 VSCode、Neovim 等）。
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
    return config_dir / "acp.pid"


def get_socket_path() -> Path:
    """获取 Unix socket 路径"""
    config_dir = Path.home() / ".agent_z"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "acp.sock"


def is_acp_running() -> Optional[int]:
    """检查 ACP 服务器是否运行，返回 PID 或 None"""
    pid_file = get_pid_file()
    
    if not pid_file.exists():
        return None
    
    try:
        pid = int(pid_file.read_text().strip())
        if _is_process_running(pid):
            return pid
        else:
            pid_file.unlink(missing_ok=True)
            return None
    except Exception:
        return None


def _is_process_running(pid: int) -> bool:
    """检查进程是否运行"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def start_acp_server() -> None:
    """启动 ACP 服务器"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error, print_info
    
    print_header("🚀 启动 ACP 服务器")
    
    # 检查是否已运行
    existing_pid = is_acp_running()
    if existing_pid:
        print_error(f"ACP 服务器已在运行 (PID: {existing_pid})")
        return
    
    print_info("启动 ACP 服务器（编辑器集成服务）...")
    
    try:
        # 尝试多种启动方式
        cmd = None
        
        # 方式 1: 作为模块运行
        if _is_module_available("acp.server"):
            cmd = [sys.executable, "-m", "acp.server"]
        # 方式 2: 作为包运行
        elif _is_module_available("cli.stdio"):
            cmd = [sys.executable, "-m", "cli.stdio"]
        
        if cmd is None:
            # 方式 3: 使用 stdio 模式启动 agent
            cmd = [sys.executable, "-m", "cli.main", "--stdio"]
        
        # 启动进程
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path.cwd()),
        )
        
        # 保存 PID
        pid_file = get_pid_file()
        pid_file.write_text(str(proc.pid))
        
        # 等待进程启动
        time.sleep(1)
        
        if proc.poll() is None:
            socket_path = get_socket_path()
            print_success(f"ACP 服务器已启动 (PID: {proc.pid})")
            print_info(f"Socket: {socket_path}")
            print_info("编辑器插件可以连接到 ACP 服务器")
        else:
            print_error("ACP 服务器启动失败")
            pid_file.unlink(missing_ok=True)
            
    except Exception as e:
        print_error(f"启动失败: {e}")


def stop_acp_server() -> None:
    """停止 ACP 服务器"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error, print_info
    
    print_header("🛑 停止 ACP 服务器")
    
    pid = is_acp_running()
    
    if not pid:
        print_error("ACP 服务器未运行")
        return
    
    print_info(f"停止 ACP 服务器 (PID: {pid})...")
    
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False)
        else:
            os.kill(pid, signal.SIGTERM)
        
        # 等待进程停止
        for _ in range(10):
            if not _is_process_running(pid):
                break
            time.sleep(0.5)
        
        if _is_process_running(pid):
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False)
            else:
                os.kill(pid, signal.SIGKILL)
        
        # 删除 PID 文件和 socket
        get_pid_file().unlink(missing_ok=True)
        get_socket_path().unlink(missing_ok=True)
        
        print_success("ACP 服务器已停止")
        
    except Exception as e:
        print_error(f"停止失败: {e}")


def check_acp_status() -> None:
    """查看 ACP 服务器状态"""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error, print_info
    
    print_header("📊 ACP 服务器状态")
    
    pid = is_acp_running()
    
    if pid:
        print_success(f"🟢 ACP 服务器运行中 (PID: {pid})")
        
        socket_path = get_socket_path()
        if socket_path.exists():
            print_info(f"Socket: {socket_path}")
        else:
            print_info("Socket 模式")
        
        print()
        print_info("支持的编辑器插件:")
        print("  • VSCode (agentz-vscode)")
        print("  • Neovim (agentz-nvim)")
        print("  • Helix (agentz-helix)")
        
    else:
        print_error("🔴 ACP 服务器未运行")
        print_info("使用 'agentz acp start' 启动")
        print()
        print_info("ACP 服务器用于编辑器集成，提供:")
        print("  • 实时代码补全")
        print("  • 智能重命名")
        print("  • 跳转到定义")


def _is_module_available(module_name: str) -> bool:
    """检查模块是否可用"""
    try:
        __import__(module_name.replace(".", "_"))
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ACP server management")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    start_parser = subparsers.add_parser("start", help="Start ACP server")
    stop_parser = subparsers.add_parser("stop", help="Stop ACP server")
    status_parser = subparsers.add_parser("status", help="Check ACP server status")
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_acp_server()
    elif args.command == "stop":
        stop_acp_server()
    elif args.command == "status":
        check_acp_status()
    else:
        check_acp_status()
