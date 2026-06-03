#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Doctor - Diagnostic checks for system configuration.

🚪 Access - 💬 CLI - 诊断检查

参考 Hermes 的 doctor.py 设计，增强版：
- API Key 检测
- 网络连接检查
- 配置完整性验证
- 修复建议
"""

import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any


def check_python_version() -> Tuple[bool, str]:
    """Check Python version."""
    version = sys.version_info
    required = (3, 8)
    ok = version >= required
    msg = f"Python {version.major}.{version.minor}.{version.micro}"
    if not ok:
        msg += f" (required: >= {'.'.join(map(str, required))}"
    return ok, msg


def check_platform() -> Tuple[bool, str]:
    """Check platform."""
    system = platform.system()
    return True, f"{system} ({platform.release()})"


def check_config() -> Tuple[bool, str]:
    """Check configuration file."""
    config_path = Path.home() / ".handsome_agent" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True, f"Config exists: {config_path}"
        except Exception as e:
            return False, f"Config invalid: {e}"
    return False, "Config not found"


def check_auth_store() -> Tuple[bool, str]:
    """Check authentication store."""
    auth_path = Path.home() / ".handsome_agent" / "auth.json"
    if not auth_path.exists():
        return False, "Auth store not found"

    try:
        with open(auth_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True, f"Auth store exists"
    except Exception as e:
        return True, f"Auth store exists (encrypted)"


def check_api_keys() -> Tuple[bool, List[str]]:
    """Check API keys configuration."""
    # 检查环境变量中的 API Key
    keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "GROQ_API_KEY",
        "GOOGLE_API_KEY",
    ]

    found_keys = []
    missing_keys = []

    for key in keys:
        if os.getenv(key):
            found_keys.append(key)

    # 返回找到的 Keys
    if found_keys:
        return True, found_keys

    return False, missing_keys


def check_skills_dir() -> Tuple[bool, str]:
    """Check skills directory."""
    skills_dir = Path(__file__).parent.parent / "skills"
    if skills_dir.exists():
        count = len([d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        return True, f"Skills dir: {skills_dir} ({count} skills)"
    return False, f"Skills dir not found: {skills_dir}"


def check_tools_dir() -> Tuple[bool, str]:
    """Check tools directory."""
    tools_dir = Path(__file__).parent.parent / "tools"
    if tools_dir.exists():
        count = len([d for d in tools_dir.rglob("*.py") if d.is_file()])
        return True, f"Tools dir: {count} tools"
    return True, f"Tools dir: (default)"


def check_log_dir() -> Tuple[bool, str]:
    """Check logs directory."""
    log_dir = Path.home() / ".handsome_agent" / "logs"
    if log_dir.exists():
        return True, f"Logs dir: {log_dir}"
    return True, f"Logs dir (will be created): {log_dir}"


def check_dependencies() -> Tuple[bool, List[str]]:
    """Check required dependencies."""
    missing = []
    required = [
        ("yaml", "PyYAML"),
        ("rich", "Rich"),
        ("httpx", "HTTPX"),
        ("dotenv", "python-dotenv"),
    ]

    for module, display_name in required:
        try:
            __import__(module)
        except ImportError:
            missing.append(display_name)

    ok = len(missing) == 0
    return ok, missing


def check_network() -> Tuple[bool, str]:
    """Check network connectivity."""
    try:
        import httpx
        # 尝试连接 API 端点
        endpoints = [
            "https://api.openai.com",
            "https://api.anthropic.com",
            "https://api.deepseek.com",
        ]

        for endpoint in endpoints[:1]:  # 只检查第一个端点
            try:
                resp = httpx.get(endpoint, timeout=5.0)
                return True, f"Network OK: {endpoint}"
            except httpx.ConnectError:
                pass
            except Exception:
                pass

        return True, "Network: Unable to verify (may be offline"

    except ImportError:
        return True, "Network check skipped (httpx not installed"

    return True, "Network OK"


def run_diagnostics() -> Dict[str, Any]:
    """Run all diagnostic checks.

    Returns:
        Dict of check results
    """
    checks = {
        "Python 版本": check_python_version,
        "平台": check_platform,
        "配置文件": check_config,
        "认证存储": check_auth_store,
        "技能目录": check_skills_dir,
        "工具目录": check_tools_dir,
        "日志目录": check_log_dir,
        "依赖包": check_dependencies,
        "网络连接": check_network,
    }

    results = {}
    all_ok = True

    for name, check_func in checks.items():
        ok, msg = check_func()
        results[name] = {"ok": ok, "message": msg}
        if not ok:
            all_ok = False

    # API Keys 检查
    api_ok, keys = check_api_keys()
    results["API Keys"] = {"ok": api_ok, "message": keys}

    results["_all_ok"] = all_ok

    return results


def print_diagnostics():
    """Print diagnostic results."""
    from cli import ui

    results = run_diagnostics()
    all_ok = results.pop("_all_ok", True)

    ui.print_header("系统诊断")

    print()
    for name, result in results.items():
        ok = result["ok"]
        msg = result["message"]

        if ok:
            if isinstance(msg, list):
                if msg:
                    ui.print_success(f"✓ {name}")
                    for key in msg:
                        print(f"    {key}")
            else:
                ui.print_success(f"✓ {name}: {msg}")
        else:
            if isinstance(msg, list):
                ui.print_error(f"✗ {name}: Missing: {', '.join(msg)}")
            else:
                ui.print_error(f"✗ {name}: {msg}")

    print()
    if all_ok:
        ui.print_success("✓ All checks passed!")
    else:
        ui.print_warning("⚠ Some checks failed. Run 'python -m cli.setup' to fix.")

    return all_ok


def export_diagnostics() -> Dict:
    """Export diagnostics as a dict for debugging."""
    results = run_diagnostics()
    results.pop("_all_ok", True)

    results["_system"] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "user": os.getenv("USER") or os.getenv("USERNAME") or "unknown",
    }

    return results


if __name__ == "__main__":
    print_diagnostics()