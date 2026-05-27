#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code execution and analysis tools for the agent.
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
from typing import Optional, List, Dict, Any
from . import ToolResult, register_tool


@register_tool(
    name="execute_code",
    description="执行Python代码（带工具支持）",
    parameters=[
        {"name": "code", "type": "string", "required": True, "description": "Python代码"},
        {"name": "tools", "type": "array", "required": False, "description": "可用的工具列表"},
        {"name": "timeout", "type": "integer", "required": False, "description": "超时时间(秒)"}
    ]
)
def execute_code(code: str, tools: Optional[List[str]] = None, timeout: int = 30) -> ToolResult:
    """执行Python代码"""
    try:
        tools = tools or []
        
        tool_imports = []
        tool_funcs = []
        
        if "terminal" in tools or "shell" in tools:
            tool_imports.append("import subprocess")
            tool_funcs.append("""
def shell(command, timeout=60):
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
    return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
""")
        
        if "read_file" in tools:
            tool_imports.append("import os")
            tool_funcs.append("""
def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"
""")
        
        if "write_file" in tools:
            tool_funcs.append("""
def write_file(path, content):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Written to {path}"
    except Exception as e:
        return f"Error: {e}"
""")
        
        if "web_search" in tools:
            tool_imports.extend(["import urllib.request", "import json"])
            tool_funcs.append("""
def web_search(query, limit=5):
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8')[:1000]
    except Exception as e:
        return f"Error: {e}"
""")
        
        full_code = "\n".join(tool_imports) + "\n" + "\n".join(tool_funcs) + "\n\n# User code:\n" + code
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(full_code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout.strip() if result.stdout else "(无输出)"
            error = result.stderr.strip() if result.stderr else ""
            
            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output=f"执行成功:\n{output}",
                    data={"exit_code": 0, "stdout": result.stdout, "stderr": result.stderr}
                )
            else:
                return ToolResult(
                    success=False,
                    output=output,
                    error=f"执行错误:\n{error}",
                    data={"exit_code": result.returncode}
                )
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, output="", error=f"执行超时 ({timeout}秒)")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="analyze_code",
    description="分析Python代码结构",
    parameters=[
        {"name": "code", "type": "string", "required": True, "description": "Python代码"},
        {"name": "detail", "type": "boolean", "required": False, "description": "详细分析"}
    ]
)
def analyze_code(code: str, detail: bool = False) -> ToolResult:
    """分析Python代码结构"""
    try:
        tree = ast.parse(code)
        
        info = {
            "functions": [],
            "classes": [],
            "imports": [],
            "complexity": 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                info["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "docstring": ast.get_docstring(node) or ""
                })
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                info["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    info["imports"].extend([alias.name for alias in node.names])
                else:
                    info["imports"].append(f"{node.module}")
        
        info["complexity"] = len([n for n in ast.walk(tree) if isinstance(n, (ast.If, ast.For, ast.While, ast.With))])
        
        output = f"📊 代码分析结果:\n\n"
        output += f"函数: {len(info['functions'])} 个\n"
        output += f"类: {len(info['classes'])} 个\n"
        output += f"导入: {len(info['imports'])} 个\n"
        output += f"复杂度: {info['complexity']}\n\n"
        
        if detail and info["functions"]:
            output += "函数列表:\n"
            for func in info["functions"]:
                output += f"  • {func['name']}({', '.join(func['args'])}) - 第{func['line']}行\n"
        
        if detail and info["classes"]:
            output += "\n类列表:\n"
            for cls in info["classes"]:
                output += f"  • {cls['name']} - 第{cls['line']}行\n"
                if cls["methods"]:
                    output += f"    方法: {', '.join(cls['methods'])}\n"
        
        return ToolResult(success=True, output=output, data=info)
        
    except SyntaxError as e:
        return ToolResult(success=False, output="", error=f"语法错误: {e}")
    except Exception as e:
        return ToolResult(success=False, output="", error=str(e))


@register_tool(
    name="format_json",
    description="格式化JSON数据",
    parameters=[
        {"name": "data", "type": "string", "required": True, "description": "JSON字符串"},
        {"name": "indent", "type": "integer", "required": False, "description": "缩进空格数"}
    ]
)
def format_json(data: str, indent: int = 2) -> ToolResult:
    """格式化JSON数据"""
    try:
        parsed = json.loads(data)
        formatted = json.dumps(parsed, indent=indent, ensure_ascii=False)
        return ToolResult(success=True, output=formatted)
    except json.JSONDecodeError as e:
        return ToolResult(success=False, output="", error=f"JSON解析错误: {e}")


@register_tool(
    name="validate_syntax",
    description="验证Python代码语法",
    parameters=[
        {"name": "code", "type": "string", "required": True, "description": "Python代码"}
    ]
)
def validate_syntax(code: str) -> ToolResult:
    """验证Python代码语法"""
    try:
        ast.parse(code)
        return ToolResult(success=True, output="✅ 语法正确")
    except SyntaxError as e:
        return ToolResult(success=False, output="", error=f"❌ 语法错误 (行 {e.lineno}): {e.msg}")
