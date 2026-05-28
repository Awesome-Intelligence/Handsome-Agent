#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统操作脚本 - 提供打开文件夹、浏览器等功能
"""

import subprocess
import os
import sys
import json


def open_folder(path=None):
    """打开文件夹"""
    try:
        target_path = path if path else os.getcwd()
        
        if not os.path.exists(target_path):
            return json.dumps({
                "success": False,
                "error": f"路径不存在: {target_path}"
            })
        
        if os.name == 'nt':
            # Windows
            subprocess.Popen(['explorer.exe', target_path])
        elif sys.platform == 'darwin':
            # macOS
            subprocess.Popen(['open', target_path])
        else:
            # Linux
            subprocess.Popen(['xdg-open', target_path])
        
        return json.dumps({
            "success": True,
            "output": f"已打开文件夹: {target_path}"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def open_browser(url=None, browser=None):
    """打开浏览器"""
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
    
    try:
        # 检测已安装的浏览器
        installed = {}
        for browser_name, paths in BROWSER_PATHS.items():
            for path in paths:
                if os.path.exists(path):
                    installed[browser_name] = path
                    break
        
        if not installed:
            return json.dumps({
                "success": False,
                "error": "未检测到任何已安装的浏览器"
            })
        
        # 选择浏览器
        if browser and browser.lower() in installed:
            browser_path = installed[browser.lower()]
            browser_type = browser.lower()
        else:
            browser_type = list(installed.keys())[0]
            browser_path = installed[browser_type]
        
        # 构建命令
        if url:
            cmd = [browser_path, url]
        else:
            cmd = [browser_path]
        
        subprocess.Popen(cmd, shell=False)
        
        result = {
            "success": True,
            "output": f"已启动 {browser_type} 浏览器" + (f"，访问: {url}" if url else "")
        }
        
        return json.dumps(result)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def list_browsers():
    """列出已安装的浏览器"""
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
    
    installed = {}
    for browser_name, paths in BROWSER_PATHS.items():
        for path in paths:
            if os.path.exists(path):
                installed[browser_name] = path
                break
    
    return json.dumps({
        "success": True,
        "output": f"检测到 {len(installed)} 个已安装的浏览器: {', '.join(installed.keys())}",
        "browsers": installed
    })


def get_system_info(info_type="all"):
    """获取系统信息"""
    try:
        import platform
        
        result = {}
        
        if info_type in ("all", "os"):
            result["os"] = {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            }
        
        if info_type in ("all", "cpu") or info_type in ("all", "memory") or info_type in ("all", "disk"):
            try:
                import psutil
                
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
            except ImportError:
                result["warning"] = "psutil 未安装，无法获取详细系统信息"
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "请指定操作: open_folder, open_browser, list_browsers, get_system_info"}))
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "open_folder":
        path = sys.argv[2] if len(sys.argv) > 2 else None
        print(open_folder(path))
    
    elif action == "open_browser":
        url = None
        browser = None
        for arg in sys.argv[2:]:
            if arg.startswith("url="):
                url = arg[4:]
            elif arg.startswith("browser="):
                browser = arg[8:]
        print(open_browser(url, browser))
    
    elif action == "list_browsers":
        print(list_browsers())
    
    elif action == "get_system_info":
        info_type = sys.argv[2] if len(sys.argv) > 2 else "all"
        print(get_system_info(info_type))
    
    else:
        print(json.dumps({"success": False, "error": f"未知操作: {action}"}))
