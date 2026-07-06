#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terminal command execution tools for the agent.
"""

import subprocess
import os
import json
from typing import Optional, Dict, List
from . import ToolResult, register_tool


BROWSER_PATHS = {
    'edge': [
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ],
    'chrome': [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
    'firefox': [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ],
    'brave': [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    ],
    'opera': [
        r"C:\Program Files\Opera\launcher.exe",
        r"C:\Program Files (x86)\Opera\launcher.exe",
    ],
    'vivaldi': [
        r"C:\Program Files\Vivaldi\Application\vivaldi.exe",
        r"C:\Program Files (x86)\Vivaldi\Application\vivaldi.exe",
    ],
}


@register_tool(
    name="detect_browsers",
    description="检测系统已安装的浏览器",
    parameters=[]
)
def detect_browsers() -> ToolResult:
    """检测系统已安装的浏览器"""
    try:
        installed = {}
        for browser, paths in BROWSER_PATHS.items():
            for path in paths:
                if os.path.exists(path):
                    installed[browser] = path
                    break
        
        if not installed:
            return ToolResult(
                success=True,
                output="未检测到任何已安装的浏览器",
                metadata={"browsers": {}, "count": 0}
            )
        
        result_str = f"检测到 {len(installed)} 个已安装的浏览器:\n"
        for browser, path in installed.items():
            result_str += f"  - {browser}: {path}\n"
        
        return ToolResult(
            success=True,
            output=result_str.strip(),
            metadata={"browsers": installed, "count": len(installed)}
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="open_browser",
    description="智能打开浏览器，自动检测已安装的浏览器",
    parameters=[
        {"name": "browser_name", "type": "string", "required": False, "description": "指定的浏览器名称 (chrome/edge/firefox)，不指定则自动选择第一个可用的"},
        {"name": "url", "type": "string", "required": False, "description": "要打开的网址，不指定则打开空白页"}
    ]
)
def open_browser(browser_name: Optional[str] = None, url: Optional[str] = None) -> ToolResult:
    """智能打开浏览器"""
    try:
        installed = {}
        for browser, paths in BROWSER_PATHS.items():
            for path in paths:
                if os.path.exists(path):
                    installed[browser] = path
                    break
        
        if not installed:
            return ToolResult(
                success=False,
                output="",
                error="未检测到任何已安装的浏览器"
            )
        
        if browser_name:
            browser_lower = browser_name.lower()
            if browser_lower not in installed:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"指定的浏览器 '{browser_name}' 未安装。可用浏览器: {', '.join(installed.keys())}"
                )
            browser_path = installed[browser_lower]
            browser_type = browser_lower
        else:
            browser_type = list(installed.keys())[0]
            browser_path = installed[browser_type]
        
        if url:
            cmd = [browser_path, url]
        else:
            if browser_type == 'chrome':
                cmd = [browser_path, '--new-window']
            elif browser_type == 'edge':
                cmd = [browser_path, '--new-window']
            else:
                cmd = [browser_path]
        
        subprocess.Popen(cmd, shell=False)
        
        return ToolResult(
            success=True,
            output=f"已启动 {browser_type} 浏览器" + (f"，访问: {url}" if url else "")
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="list_browsers",
    description="列出系统已安装的浏览器",
    parameters=[]
)
def list_browsers() -> ToolResult:
    """列出系统已安装的浏览器"""
    return detect_browsers()


@register_tool(
    name="execute_terminal",
    description="执行终端命令",
    parameters=[
        {"name": "command", "type": "string", "required": True, "description": "要执行的命令"},
        {"name": "workdir", "type": "string", "required": False, "description": "工作目录"},
        {"name": "timeout", "type": "integer", "required": False, "description": "超时时间(秒)"},
        {"name": "shell", "type": "boolean", "required": False, "description": "是否使用shell"}
    ]
)
def execute_terminal(command: str, workdir: Optional[str] = None, timeout: int = 60, shell: bool = True) -> ToolResult:
    """执行终端命令"""
    try:
        cwd = workdir if workdir else os.getcwd()
        
        use_shell = shell or os.name == 'nt'
        
        if use_shell:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
        else:
            result = subprocess.run(
                command,
                shell=False,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                executable=None
            )
        
        output = result.stdout if result.stdout else ""
        error = result.stderr if result.stderr else ""
        
        if result.returncode == 0:
            return ToolResult(
                success=True,
                output=output or "命令执行成功(无输出)",
                metadata={
                    "exit_code": result.returncode,
                    "stdout": output,
                    "stderr": error
                }
            )
        else:
            return ToolResult(
                success=False,
                output=output or "",
                error=f"命令执行失败 (退出码: {result.returncode})\n{error}",
                metadata={
                    "exit_code": result.returncode,
                    "stdout": output,
                    "stderr": error
                }
            )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output="", error=f"命令执行超时 ({timeout}秒)")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="run_python",
    description="执行Python代码",
    parameters=[
        {"name": "code", "type": "string", "required": True, "description": "Python代码"},
        {"name": "timeout", "type": "integer", "required": False, "description": "超时时间(秒)"}
    ]
)
def run_python(code: str, timeout: int = 30) -> ToolResult:
    """执行Python代码"""
    try:
        import tempfile
        import sys
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            error = result.stderr
            
            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output=output or "代码执行成功(无输出)",
                    data={"exit_code": 0, "stdout": output, "stderr": error}
                )
            else:
                return ToolResult(
                    success=False,
                    output=output,
                    error=f"Python执行错误:\n{error}",
                    data={"exit_code": result.returncode, "stdout": output, "stderr": error}
                )
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass
                
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output="", error=f"代码执行超时 ({timeout}秒)")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="get_system_info",
    description="获取系统信息",
    parameters=[
        {"name": "info_type", "type": "string", "required": False, "description": "信息类型: os/cpu/memory/disk/all"}
    ]
)
def get_system_info(info_type: str = "all") -> ToolResult:
    """获取系统信息"""
    try:
        import platform
        import psutil
        
        result = {}
        
        if info_type in ("all", "os"):
            result["os"] = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }
        
        if info_type in ("all", "cpu"):
            result["cpu"] = {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "usage_percent": psutil.cpu_percent(interval=1)
            }
        
        if info_type in ("all", "memory"):
            mem = psutil.virtual_memory()
            result["memory"] = {
                "total": f"{mem.total / (1024**3):.2f} GB",
                "available": f"{mem.available / (1024**3):.2f} GB",
                "percent": mem.percent
            }
        
        if info_type in ("all", "disk"):
            disk = psutil.disk_usage('/')
            result["disk"] = {
                "total": f"{disk.total / (1024**3):.2f} GB",
                "used": f"{disk.used / (1024**3):.2f} GB",
                "free": f"{disk.free / (1024**3):.2f} GB",
                "percent": disk.percent
            }
        
        import json
        return ToolResult(success=True, output=json.dumps(result, indent=2))
    except ImportError:
        return ToolResult(success=True, output=f"系统: {platform.system()} {platform.release()}")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))
