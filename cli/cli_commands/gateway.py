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
        log_fd = open(log_file, 'a', encoding='utf-8')
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


def _is_module_available(module_name: str) -> bool:
    """检查模块是否可用"""
    try:
        __import__(module_name.replace(".", "_"))
        return True
    except ImportError:
        return False


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
    
    args = parser.parse_args()
    
    if args.command == "start":
        start_gateway()
    elif args.command == "stop":
        stop_gateway()
    elif args.command == "status":
        check_gateway_status()
    elif args.command == "restart":
        restart_gateway()
    else:
        # 默认显示状态
        check_gateway_status()