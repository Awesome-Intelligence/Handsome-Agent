#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Browser Tool Module

Provides functionality for browser automation using agent-browser CLI.

Based on Hermes Agent's browser_tool.py implementation.

Features:
- Local mode: Headless Chromium via agent-browser
- Session isolation per task ID
- Element interaction via selectors
- Text-based page snapshots using accessibility tree

Environment Variables:
- BROWSERBASE_API_KEY: API key for Browserbase cloud mode
- BROWSER_USE_API_KEY: API key for Browser Use cloud mode

Usage:
    from tools.browser_tool import browser_navigate, browser_snapshot, browser_click

    result = browser_navigate(url="https://example.com", task_id="task_123")
    snapshot = browser_snapshot(task_id="task_123")
"""

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("BrowserTool")

# Default settings
DEFAULT_TIMEOUT = 30
SNAPSHOT_SUMMARIZE_THRESHOLD = 8000


def _get_config() -> dict:
    """获取浏览器配置"""
    try:
        from common.config import settings
        
        return {
            "provider": getattr(settings, 'BROWSER_PROVIDER', None) or "local",
            "browserbase_key": getattr(settings, 'BROWSERBASE_API_KEY', None),
            "browserbase_project": getattr(settings, 'BROWSERBASE_PROJECT_ID', None),
            "browser_use_key": getattr(settings, 'BROWSER_USE_API_KEY', None),
            "command_timeout": getattr(settings, 'BROWSER_TIMEOUT', DEFAULT_TIMEOUT),
        }
    except Exception:
        pass
    
    return {
        "provider": os.environ.get("BROWSER_PROVIDER", "local"),
        "browserbase_key": os.environ.get("BROWSERBASE_API_KEY"),
        "browserbase_project": os.environ.get("BROWSERBASE_PROJECT_ID"),
        "browser_use_key": os.environ.get("BROWSER_USE_API_KEY"),
        "command_timeout": int(os.environ.get("BROWSER_TIMEOUT", str(DEFAULT_TIMEOUT))),
    }


def _find_browser_cli() -> Optional[str]:
    """查找浏览器 CLI 工具"""
    # Check common locations
    possible_paths = [
        "agent-browser",
        shutil.which("agent-browser"),
        shutil.which("npx"),
        Path.home() / ".local" / "bin" / "agent-browser",
        Path.home() / ".npm-global" / "bin" / "agent-browser",
    ]
    
    for path in possible_paths:
        if path and shutil.which(path):
            return path
    
    # Try npx agent-browser
    if shutil.which("npx"):
        return "npx"
    
    return None


def _run_browser_command(args: List[str], timeout: int) -> Dict[str, Any]:
    """运行浏览器命令"""
    cli = _find_browser_cli()
    
    if not cli:
        raise RuntimeError("agent-browser CLI not found. Install with: npm install -g agent-browser")
    
    cmd = [cli, *args] if cli != "npx" else ["npx", "agent-browser", *args]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Browser command timed out after {timeout}s")


def browser_navigate(
    url: str,
    task_id: Optional[str] = None,
    new_tab: bool = False,
    wait_after: float = 2.0
) -> str:
    """
    Navigate to a URL in the browser.
    
    Args:
        url: Target URL
        task_id: Session/task identifier
        new_tab: Open in new tab
        wait_after: Wait time after navigation
        
    Returns:
        JSON string with navigation result
    """
    task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
    config = _get_config()
    
    try:
        args = [
            "navigate",
            "--url", url,
            "--task-id", task_id
        ]
        
        if new_tab:
            args.append("--new-tab")
        
        if wait_after > 0:
            args.extend(["--wait", str(wait_after)])
        
        result = _run_browser_command(args, config["command_timeout"])
        
        return json.dumps({
            "success": result["success"],
            "task_id": task_id,
            "url": url,
            "message": "Navigated successfully" if result["success"] else result["stderr"]
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser navigate error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def browser_snapshot(
    task_id: str,
    full_page: bool = False,
    element: Optional[str] = None,
    summarize: bool = True
) -> str:
    """
    Get current page snapshot.
    
    Args:
        task_id: Session/task identifier
        full_page: Capture full page screenshot
        element: Capture specific element only
        summarize: Use LLM to summarize long content
        
    Returns:
        JSON string with page snapshot
    """
    config = _get_config()
    
    try:
        args = ["snapshot", "--task-id", task_id]
        
        if full_page:
            args.append("--full-page")
        
        if element:
            args.extend(["--element", element])
        
        result = _run_browser_command(args, config["command_timeout"])
        
        if not result["success"]:
            return json.dumps({
                "success": False,
                "error": result["stderr"],
                "task_id": task_id
            }, ensure_ascii=False)
        
        content = result["stdout"]
        
        # Summarize if too long
        if summarize and len(content) > SNAPSHOT_SUMMARIZE_THRESHOLD:
            try:
                content = _summarize_content(content, task_id)
            except Exception as e:
                logger.warning(f"Summarization failed: {e}")
        
        return json.dumps({
            "success": True,
            "task_id": task_id,
            "content": content,
            "length": len(content)
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser snapshot error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def browser_click(
    ref: str,
    task_id: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left"
) -> str:
    """
    Click on a page element.
    
    Args:
        ref: Element reference (@e1, @e2, etc. or CSS selector)
        task_id: Session/task identifier
        x: X offset within element
        y: Y offset within element
        button: Mouse button (left, right, middle)
        
    Returns:
        JSON string with click result
    """
    config = _get_config()
    
    try:
        args = ["click", "--task-id", task_id, "--ref", ref]
        
        if x is not None:
            args.extend(["--x", str(x)])
        if y is not None:
            args.extend(["--y", str(y)])
        if button != "left":
            args.extend(["--button", button])
        
        result = _run_browser_command(args, config["command_timeout"])
        
        return json.dumps({
            "success": result["success"],
            "task_id": task_id,
            "ref": ref,
            "message": "Clicked successfully" if result["success"] else result["stderr"]
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser click error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def browser_type(
    ref: str,
    text: str,
    task_id: str,
    clear_first: bool = True,
    press_enter: bool = False
) -> str:
    """
    Type text into an input field.
    
    Args:
        ref: Input element reference
        text: Text to type
        task_id: Session/task identifier
        clear_first: Clear existing content first
        press_enter: Press Enter after typing
        
    Returns:
        JSON string with result
    """
    config = _get_config()
    
    try:
        args = ["type", "--task-id", task_id, "--ref", ref, "--text", text]
        
        if clear_first:
            args.append("--clear")
        if press_enter:
            args.append("--enter")
        
        result = _run_browser_command(args, config["command_timeout"])
        
        return json.dumps({
            "success": result["success"],
            "task_id": task_id,
            "ref": ref,
            "text_length": len(text),
            "message": "Typed successfully" if result["success"] else result["stderr"]
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser type error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def browser_scroll(
    task_id: str,
    direction: str = "down",
    amount: int = 500,
    selector: Optional[str] = None
) -> str:
    """
    Scroll the page.
    
    Args:
        task_id: Session/task identifier
        direction: Scroll direction (up, down, left, right)
        amount: Scroll amount in pixels
        selector: Scroll to specific element
        
    Returns:
        JSON string with result
    """
    config = _get_config()
    
    try:
        args = ["scroll", "--task-id", task_id, "--direction", direction]
        
        if amount != 500:
            args.extend(["--amount", str(amount)])
        if selector:
            args.extend(["--to", selector])
        
        result = _run_browser_command(args, config["command_timeout"])
        
        return json.dumps({
            "success": result["success"],
            "task_id": task_id,
            "direction": direction,
            "message": "Scrolled successfully" if result["success"] else result["stderr"]
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser scroll error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def browser_press(
    key: str,
    task_id: str,
    modifiers: Optional[List[str]] = None
) -> str:
    """
    Press a keyboard key.
    
    Args:
        key: Key name (Enter, Escape, Tab, Backspace, etc.)
        task_id: Session/task identifier
        modifiers: Modifier keys (Control, Alt, Shift, Meta)
        
    Returns:
        JSON string with result
    """
    config = _get_config()
    
    try:
        args = ["press", "--task-id", task_id, "--key", key]
        
        if modifiers:
            args.extend(["--modifiers", ",".join(modifiers)])
        
        result = _run_browser_command(args, config["command_timeout"])
        
        return json.dumps({
            "success": result["success"],
            "task_id": task_id,
            "key": key,
            "message": "Key pressed successfully" if result["success"] else result["stderr"]
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser press error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def browser_back(task_id: str) -> str:
    """Navigate back in browser history."""
    config = _get_config()
    
    try:
        result = _run_browser_command(
            ["back", "--task-id", task_id],
            config["command_timeout"]
        )
        
        return json.dumps({
            "success": result["success"],
            "task_id": task_id,
            "message": "Navigated back" if result["success"] else result["stderr"]
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser back error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def browser_get_images(task_id: str) -> str:
    """Get all images from the current page."""
    config = _get_config()
    
    try:
        result = _run_browser_command(
            ["get-images", "--task-id", task_id],
            config["command_timeout"]
        )
        
        if result["success"]:
            try:
                images = json.loads(result["stdout"])
            except json.JSONDecodeError:
                images = []
            
            return json.dumps({
                "success": True,
                "task_id": task_id,
                "images": images
            }, ensure_ascii=False)
        
        return json.dumps({
            "success": False,
            "error": result["stderr"],
            "task_id": task_id
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser get_images error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def browser_vision(
    question: str,
    task_id: str,
    annotate: bool = False
) -> str:
    """
    Use AI vision to analyze the page.
    
    Args:
        question: Question about the page content
        task_id: Session/task identifier
        annotate: Return annotated screenshot
        
    Returns:
        JSON string with analysis
    """
    config = _get_config()
    
    try:
        args = ["vision", "--task-id", task_id, "--question", question]
        
        if annotate:
            args.append("--annotate")
        
        result = _run_browser_command(args, config["command_timeout"])
        
        if result["success"]:
            return json.dumps({
                "success": True,
                "task_id": task_id,
                "answer": result["stdout"],
                "annotated": annotate
            }, ensure_ascii=False)
        
        return json.dumps({
            "success": False,
            "error": result["stderr"],
            "task_id": task_id
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser vision error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def browser_console(
    expression: str,
    task_id: str,
    clear: bool = False
) -> str:
    """
    Execute JavaScript in the page console.
    
    Args:
        expression: JavaScript expression to execute
        task_id: Session/task identifier
        clear: Clear console before execution
        
    Returns:
        JSON string with result
    """
    config = _get_config()
    
    try:
        args = ["console", "--task-id", task_id, "--expression", expression]
        
        if clear:
            args.append("--clear")
        
        result = _run_browser_command(args, config["command_timeout"])
        
        return json.dumps({
            "success": result["success"],
            "task_id": task_id,
            "output": result["stdout"],
            "error": result["stderr"] if not result["success"] else None
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Browser console error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "task_id": task_id
        }, ensure_ascii=False)


def _summarize_content(content: str, task_id: str) -> str:
    """Summarize long page content using LLM"""
    # This would use the agent's LLM to summarize
    # For now, just truncate
    return content[:SNAPSHOT_SUMMARIZE_THRESHOLD] + "...\n[Content truncated - too long]"


def check_browser_requirements() -> bool:
    """检查浏览器工具是否可用"""
    cli = _find_browser_cli()
    return cli is not None


def check_browser_vision_requirements() -> bool:
    """检查浏览器视觉工具是否可用"""
    return check_browser_requirements()


# Schema definitions
BROWSER_NAVIGATE_SCHEMA = {
    "name": "browser_navigate",
    "description": "Navigate to a URL in the browser",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target URL"},
            "new_tab": {"type": "boolean", "description": "Open in new tab", "default": False},
            "wait_after": {"type": "number", "description": "Wait after navigation (seconds)", "default": 2}
        },
        "required": ["url"]
    }
}

BROWSER_SNAPSHOT_SCHEMA = {
    "name": "browser_snapshot",
    "description": "Get current page snapshot/aria tree",
    "parameters": {
        "type": "object",
        "properties": {
            "full_page": {"type": "boolean", "description": "Capture full page", "default": False},
            "element": {"type": "string", "description": "Capture specific element"}
        },
        "required": []
    }
}

BROWSER_CLICK_SCHEMA = {
    "name": "browser_click",
    "description": "Click on a page element",
    "parameters": {
        "type": "object",
        "properties": {
            "ref": {"type": "string", "description": "Element reference (@e1, @e2, etc.)"},
            "x": {"type": "integer", "description": "X offset within element"},
            "y": {"type": "integer", "description": "Y offset within element"},
            "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"}
        },
        "required": ["ref"]
    }
}

BROWSER_TYPE_SCHEMA = {
    "name": "browser_type",
    "description": "Type text into an input field",
    "parameters": {
        "type": "object",
        "properties": {
            "ref": {"type": "string", "description": "Input element reference"},
            "text": {"type": "string", "description": "Text to type"},
            "clear_first": {"type": "boolean", "default": True},
            "press_enter": {"type": "boolean", "default": False}
        },
        "required": ["ref", "text"]
    }
}

BROWSER_SCROLL_SCHEMA = {
    "name": "browser_scroll",
    "description": "Scroll the page",
    "parameters": {
        "type": "object",
        "properties": {
            "direction": {"type": "string", "enum": ["up", "down", "left", "right"], "default": "down"},
            "amount": {"type": "integer", "description": "Scroll amount in pixels", "default": 500},
            "selector": {"type": "string", "description": "Scroll to specific element"}
        },
        "required": []
    }
}

BROWSER_PRESS_SCHEMA = {
    "name": "browser_press",
    "description": "Press a keyboard key",
    "parameters": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key name (Enter, Escape, Tab, etc.)"},
            "modifiers": {"type": "array", "items": {"type": "string"}, "description": "Modifier keys"}
        },
        "required": ["key"]
    }
}

BROWSER_BACK_SCHEMA = {
    "name": "browser_back",
    "description": "Navigate back in browser history",
    "parameters": {"type": "object", "properties": {}, "required": []}
}

BROWSER_GET_IMAGES_SCHEMA = {
    "name": "browser_get_images",
    "description": "Get all images from current page",
    "parameters": {"type": "object", "properties": {}, "required": []}
}

BROWSER_VISION_SCHEMA = {
    "name": "browser_vision",
    "description": "Use AI vision to analyze the page",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Question about page content"},
            "annotate": {"type": "boolean", "default": False}
        },
        "required": ["question"]
    }
}

BROWSER_CONSOLE_SCHEMA = {
    "name": "browser_console",
    "description": "Execute JavaScript in page console",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "JavaScript expression"},
            "clear": {"type": "boolean", "default": False}
        },
        "required": ["expression"]
    }
}


# Register all browser tools
registry.register(
    name="browser_navigate",
    toolset="browser",
    schema=BROWSER_NAVIGATE_SCHEMA,
    handler=lambda args, **kw: browser_navigate(
        url=args.get("url", ""),
        task_id=kw.get("task_id"),
        new_tab=args.get("new_tab", False),
        wait_after=args.get("wait_after", 2.0)
    ),
    check_fn=check_browser_requirements,
    emoji="🌐",
)

registry.register(
    name="browser_snapshot",
    toolset="browser",
    schema=BROWSER_SNAPSHOT_SCHEMA,
    handler=lambda args, **kw: browser_snapshot(
        task_id=kw.get("task_id"),
        full_page=args.get("full_page", False),
        element=args.get("element")
    ),
    check_fn=check_browser_requirements,
    emoji="📸",
)

registry.register(
    name="browser_click",
    toolset="browser",
    schema=BROWSER_CLICK_SCHEMA,
    handler=lambda args, **kw: browser_click(
        ref=args.get("ref", ""),
        task_id=kw.get("task_id"),
        x=args.get("x"),
        y=args.get("y"),
        button=args.get("button", "left")
    ),
    check_fn=check_browser_requirements,
    emoji="👆",
)

registry.register(
    name="browser_type",
    toolset="browser",
    schema=BROWSER_TYPE_SCHEMA,
    handler=lambda args, **kw: browser_type(
        ref=args.get("ref", ""),
        text=args.get("text", ""),
        task_id=kw.get("task_id"),
        clear_first=args.get("clear_first", True),
        press_enter=args.get("press_enter", False)
    ),
    check_fn=check_browser_requirements,
    emoji="⌨️",
)

registry.register(
    name="browser_scroll",
    toolset="browser",
    schema=BROWSER_SCROLL_SCHEMA,
    handler=lambda args, **kw: browser_scroll(
        task_id=kw.get("task_id"),
        direction=args.get("direction", "down"),
        amount=args.get("amount", 500),
        selector=args.get("selector")
    ),
    check_fn=check_browser_requirements,
    emoji="📜",
)

registry.register(
    name="browser_press",
    toolset="browser",
    schema=BROWSER_PRESS_SCHEMA,
    handler=lambda args, **kw: browser_press(
        key=args.get("key", ""),
        task_id=kw.get("task_id"),
        modifiers=args.get("modifiers")
    ),
    check_fn=check_browser_requirements,
    emoji="⌨️",
)

registry.register(
    name="browser_back",
    toolset="browser",
    schema=BROWSER_BACK_SCHEMA,
    handler=lambda args, **kw: browser_back(task_id=kw.get("task_id")),
    check_fn=check_browser_requirements,
    emoji="◀️",
)

registry.register(
    name="browser_get_images",
    toolset="browser",
    schema=BROWSER_GET_IMAGES_SCHEMA,
    handler=lambda args, **kw: browser_get_images(task_id=kw.get("task_id")),
    check_fn=check_browser_requirements,
    emoji="🖼️",
)

registry.register(
    name="browser_vision",
    toolset="browser",
    schema=BROWSER_VISION_SCHEMA,
    handler=lambda args, **kw: browser_vision(
        question=args.get("question", ""),
        task_id=kw.get("task_id"),
        annotate=args.get("annotate", False)
    ),
    check_fn=check_browser_vision_requirements,
    emoji="👁️",
)

registry.register(
    name="browser_console",
    toolset="browser",
    schema=BROWSER_CONSOLE_SCHEMA,
    handler=lambda args, **kw: browser_console(
        expression=args.get("expression", ""),
        task_id=kw.get("task_id"),
        clear=args.get("clear", False)
    ),
    check_fn=check_browser_requirements,
    emoji="🖥️",
)
